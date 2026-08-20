"""
Decoder sources: PyAV (FFmpeg) pulls bytes off the network or a pipe on a
background thread, resamples to the engine format, and parks the result
in a ring buffer that the audio callback drains.

Buffering, reconnection and metadata all live here, which is what makes
this more predictable than handing a URL to an external player: when a
stream stalls we know about it and can re-buffer instead of going silent.
"""

import os
import subprocess
import sys
import threading
import time

import numpy as np

from core.audio.engine import AudioSource
from core.audio.icy import HlsStream, USER_AGENT, open_icy
from core.audio.ring import RingBuffer

# FFmpeg wants microseconds. Long enough for slow stations, short enough
# that a dead host does not pin the decoder thread for a minute.
_FFMPEG_OPTIONS = {
    'user_agent': USER_AGENT,
    'timeout': '5000000',
    'rw_timeout': '5000000',
    'reconnect': '1',
    'reconnect_streamed': '1',
    'reconnect_delay_max': '4',
    'icy': '1',
}


class DecoderSource(AudioSource):
    """Base class: owns the decode thread, the ring buffer and re-buffering."""

    def __init__(self, engine, label='', buffer_seconds=8.0, prebuffer_seconds=0.6,
                 connect_attempts=2, reconnect_attempts=4):
        super().__init__(samplerate=engine.samplerate, channels=engine.channels)
        self.engine = engine
        self.label = label
        # A station that never played once is probably dead, so give up on
        # it quickly and let the static come back. A station that was
        # playing and dropped out is worth chasing much harder.
        self.connect_attempts = connect_attempts
        self.reconnect_attempts = reconnect_attempts

        self.ring = RingBuffer(int(self.samplerate * buffer_seconds), self.channels)
        self._prebuffer = int(self.samplerate * prebuffer_seconds)
        self._ready = False
        self._scratch = np.zeros((engine.blocksize, self.channels), dtype=np.float32)

        self.state = 'idle'  # idle | connecting | buffering | playing | error | stopped
        self.last_error = None
        self.title = None
        self.station_name = None
        self.codec = None
        self.underruns = 0
        self.frames_decoded = 0

        self._stop = threading.Event()
        self._thread = None

    # -- lifecycle ----------------------------------------------------- #

    def start(self):
        if self._thread is not None:
            return
        self.state = 'connecting'
        self._thread = threading.Thread(target=self._run, name='decode-%s' % self.label,
                                        daemon=True)
        self._thread.start()

    def close(self):
        """
        Stops decoding and waits for the thread to unwind.

        Tearing the FFmpeg container down here would mean closing it while
        the decode thread is still inside it, which is a crash. Instead we
        unblock whatever the thread is waiting on and let it release its
        own resources on the way out.
        """
        self._stop.set()
        try:
            self._unblock()
        except Exception:
            pass
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
            if thread.is_alive():
                print('DecoderSource[%s] did not stop in time' % self.label)
        self.state = 'stopped'

    @property
    def stopped(self):
        return self._stop.is_set()

    @property
    def failed(self):
        return self.state == 'error'

    # -- audio callback side ------------------------------------------- #

    def pull(self, frames):
        if len(self._scratch) != frames:
            self._scratch = np.zeros((frames, self.channels), dtype=np.float32)

        available = self.ring.available
        if not self._ready:
            # Hold silence until we have a cushion, so a slow start or a
            # network hiccup does not turn into a stutter loop.
            if available < self._prebuffer:
                self._scratch[:] = 0.0
                return self._scratch
            self._ready = True
            if self.state in ('connecting', 'buffering'):
                self.state = 'playing'
        elif available < frames:
            self._ready = False
            self.underruns += 1
            if self.state == 'playing':
                self.state = 'buffering'

        self.ring.read_into(self._scratch)
        return self._scratch

    # -- decode thread ------------------------------------------------- #

    def _open(self):
        """Returns an open av.container. Subclasses implement."""
        raise NotImplementedError

    def _release(self):
        """
        Tears down whatever `_open` acquired. Only ever called on the
        decode thread, so it is safe to touch the FFmpeg container here.
        """

    def _unblock(self):
        """
        Called from another thread to wake a decode thread that is parked
        in a network or pipe read. Must not touch the FFmpeg container.
        """

    def _refresh_metadata(self):
        """Called periodically while decoding, for live title updates."""

    def _run(self):
        attempt = 0
        while not self._stop.is_set():
            attempt += 1
            decoded_before = self.frames_decoded
            try:
                self._decode_once()
                if self._stop.is_set():
                    break
                # Clean EOF on a live stream means the server dropped us.
                self.last_error = self.last_error or 'stream ended'
            except Exception as e:
                self.last_error = '%s: %s' % (type(e).__name__, e)
                # Errors raised by our own teardown are not worth logging.
                if not self._stop.is_set():
                    print('DecoderSource[%s] %s' % (self.label, self.last_error))
            finally:
                self._release()

            if self._stop.is_set():
                break
            # Audio came through, so the budget starts over: this was a
            # dropout, not a station that cannot be reached at all.
            if self.frames_decoded > decoded_before:
                attempt = 1
            budget = self.reconnect_attempts if self.frames_decoded else self.connect_attempts
            if attempt >= budget:
                break

            self._ready = False
            self.state = 'connecting'
            if self._stop.wait(min(0.5 * (2 ** (attempt - 1)), 3.0)):
                break

        if not self._stop.is_set():
            self.state = 'error'
            self.last_error = self.last_error or 'stream unavailable'

    def _decode_once(self):
        import av

        if self._stop.is_set():
            return
        container = self._open()
        if container is None:
            raise IOError('could not open stream')
        if self._stop.is_set():
            return

        stream = container.streams.audio[0]
        stream.thread_type = 'AUTO'
        self.codec = stream.codec_context.name
        self.state = 'buffering'

        resampler = av.AudioResampler(format='flt', layout='stereo', rate=self.samplerate)
        next_meta_check = time.monotonic()

        for frame in container.decode(stream):
            if self._stop.is_set():
                return
            for resampled in resampler.resample(frame):
                samples = resampled.to_ndarray().reshape(-1, self.channels)
                self.frames_decoded += len(samples)
                self._write(samples)
                if self._stop.is_set():
                    return
            now = time.monotonic()
            if now >= next_meta_check:
                next_meta_check = now + 0.5
                self._refresh_metadata()

    def _write(self, samples):
        """Pushes decoded audio into the ring, waiting when it is full."""
        offset = 0
        while offset < len(samples) and not self._stop.is_set():
            written = self.ring.write(samples[offset:])
            offset += written
            if offset < len(samples):
                # Buffer is full: we are ahead of playback, which is
                # exactly what we want. Idle until the callback drains it.
                time.sleep(0.02)


class NetworkSource(DecoderSource):
    """
    An internet radio stream.

    Plain Shoutcast/Icecast goes through our own HTTP reader so live track
    titles come through; HLS and anything else falls back to letting
    FFmpeg open the URL itself.
    """

    def __init__(self, engine, url, **kwargs):
        super().__init__(engine, label=url[:60], **kwargs)
        self.url = url
        self._icy = None
        self._container = None

    def _open(self):
        import av
        import requests

        try:
            self._icy = open_icy(self.url)
        except HlsStream:
            self._icy = None
        except (requests.ConnectionError, requests.Timeout) as e:
            # The host is unreachable, so FFmpeg would fail the same way,
            # only slower and without a way to interrupt it. Fail now.
            self._icy = None
            raise IOError('cannot reach %s: %s' % (self.url, e))
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (404, 410) or status >= 500:
                # Gone or broken at the source; retrying via FFmpeg only
                # costs a slow, uninterruptible connection attempt.
                self._icy = None
                raise IOError('%s returned HTTP %d' % (self.url, status))
            # 401/403 and friends are often just a header the server does
            # not like, which FFmpeg's own request may get past.
            print('NetworkSource: HTTP %d from %s, trying FFmpeg directly'
                  % (status, self.url))
            self._icy = None
        except Exception as e:
            # A protocol-level refusal is worth a second chance: some
            # servers answer FFmpeg's request but not ours, and vice versa.
            print('NetworkSource: ICY open failed (%s), trying FFmpeg directly' % e)
            self._icy = None

        if self._stop.is_set():
            # Scrubbing across the dial can retire a source while it is
            # still connecting. Drop it now rather than opening a decoder
            # nobody is listening to.
            self._unblock()
            raise IOError('stopped while connecting')

        if self._icy is not None:
            self.station_name = self._icy.station_name
            self._container = av.open(self._icy, mode='r', buffer_size=65536,
                                      metadata_errors='ignore')
        else:
            self._container = av.open(self.url, options=dict(_FFMPEG_OPTIONS),
                                      metadata_errors='ignore')
            meta = self._container.metadata or {}
            self.station_name = meta.get('icy-name') or self.station_name
            self.title = meta.get('StreamTitle') or self.title
        return self._container

    def _refresh_metadata(self):
        if self._icy is not None and self._icy.title != self.title:
            self.title = self._icy.title

    def _release(self):
        container, self._container = self._container, None
        if container is not None:
            try:
                container.close()
            except Exception:
                pass
        icy, self._icy = self._icy, None
        if icy is not None:
            try:
                icy.close()
            except Exception:
                pass

    def _unblock(self):
        # Dropping the HTTP response makes the decoder's next read return
        # empty, which unwinds it out of FFmpeg on its own thread.
        icy = self._icy
        if icy is not None:
            try:
                icy.close()
            except Exception:
                pass


class ProcessSource(DecoderSource):
    """
    Audio piped straight out of a helper process (KiwiSDR's recorder).

    The old build routed this through a local HTTP socket so VLC could
    open it; PyAV reads the pipe directly, so that bridge is gone.
    """

    def __init__(self, engine, command, cwd=None, input_format='wav', label='process',
                 **kwargs):
        super().__init__(engine, label=label, **kwargs)
        self.command = command
        self.cwd = cwd
        self.input_format = input_format
        self.process = None
        self._container = None
        self._stderr_thread = None

    def _open(self):
        import av

        if self._stop.is_set():
            raise IOError('stopped before launch')

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=self.cwd,
            bufsize=0,
            creationflags=creation_flags,
        )
        self._drain_stderr()
        self._container = av.open(self.process.stdout, mode='r',
                                  format=self.input_format, buffer_size=32768)
        return self._container

    def _drain_stderr(self):
        process = self.process
        if not process or not process.stderr:
            return

        def drain():
            try:
                for raw in iter(process.stderr.readline, b''):
                    text = raw.decode('utf-8', 'replace').strip()
                    if text:
                        self.last_error = text
            except Exception:
                pass

        self._stderr_thread = threading.Thread(target=drain, daemon=True)
        self._stderr_thread.start()

    def _release(self):
        container, self._container = self._container, None
        if container is not None:
            try:
                container.close()
            except Exception:
                pass
        self._kill_process()

    def _unblock(self):
        # Killing the recorder EOFs its stdout, which frees the decoder.
        self._kill_process()

    def _kill_process(self):
        process, self.process = self.process, None
        if process is None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


def python_executable():
    """The interpreter to spawn helper scripts with, PyInstaller aware."""
    if getattr(sys, 'frozen', False):
        return 'python'
    return sys.executable
