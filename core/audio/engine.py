"""
The audio engine: a single output stream that mixes every source and
runs the master effect chain.

This replaces libVLC. Instead of handing a URL to an opaque player we
own the whole path -- decode, mix, process, output -- so the tuning
crossfade is sample accurate and any effect we want can sit in the chain.
"""

import queue
import threading
import time

import numpy as np

from core.audio import dsp

DEFAULT_SAMPLERATE = 48000
DEFAULT_BLOCKSIZE = 1024
CHANNELS = 2

# Retired sources are closed on one long-lived worker rather than a fresh
# thread each time: scrubbing the dial spawns them faster than they finish,
# and thread creation under that much contention is what stalls the UI.
_reaper_queue = queue.Queue()
_reaper_thread = None
_reaper_lock = threading.Lock()


def _reap_forever():
    while True:
        source = _reaper_queue.get()
        try:
            source.close()
        except Exception:
            pass


def close_async(source):
    global _reaper_thread
    with _reaper_lock:
        if _reaper_thread is None:
            _reaper_thread = threading.Thread(target=_reap_forever, daemon=True,
                                              name='source-reaper')
            _reaper_thread.start()
    _reaper_queue.put(source)


class AudioSource:
    """
    Base class for anything that can feed the mixer.

    `gain` may be written from any thread; the engine ramps towards it
    across a block so volume changes never click.
    """

    def __init__(self, samplerate=DEFAULT_SAMPLERATE, channels=CHANNELS):
        self.samplerate = samplerate
        self.channels = channels
        self.gain = 0.0
        self._current_gain = 0.0

    def pull(self, frames):
        """Returns a (frames, channels) float array. Subclasses override."""
        return np.zeros((frames, self.channels))

    def render(self, frames):
        block = self.pull(frames)
        target = float(np.clip(self.gain, 0.0, 4.0))
        current = self._current_gain

        if abs(target - current) < 1e-5:
            self._current_gain = target
            if target == 0.0:
                return None
            return block * target

        ramp = np.linspace(current, target, frames, endpoint=False)
        self._current_gain = target
        return block * ramp[:, None]

    def close(self):
        pass


class MasterChain:
    """Ordered effect chain applied to the summed mix."""

    def __init__(self, samplerate, blocksize, channels=CHANNELS):
        self.samplerate = samplerate
        self.equalizer = dsp.Equalizer(samplerate, blocksize, channels)
        self.saturator = dsp.Saturator(drive=2.0, mix=0.35)
        self.compressor = dsp.Compressor(samplerate, threshold_db=-20.0, ratio=3.0,
                                         attack_ms=15.0, release_ms=280.0, makeup_db=4.0)
        self.width = dsp.StereoWidth(1.25)
        self.reverb = dsp.Reverb(samplerate, room=0.6, damping=0.45, mix=0.18)
        self.limiter = dsp.Limiter(samplerate, ceiling=0.97)

        # The leveller is on by default: internet stations differ wildly in
        # loudness and evening that out is the single biggest listening win.
        self.enabled = {
            'equalizer': False,
            'warmth': False,
            'leveler': True,
            'width': False,
            'space': False,
        }
        self.output_gain = 1.0

    def set_enabled(self, name, value):
        if name not in self.enabled:
            return False
        self.enabled[name] = bool(value)
        if not value:
            stage = getattr(self, {'space': 'reverb', 'leveler': 'compressor'}.get(name, name), None)
            if stage is not None and hasattr(stage, 'reset'):
                stage.reset()
        return True

    def is_enabled(self, name):
        return self.enabled.get(name, False)

    def reset(self):
        for stage in (self.equalizer, self.compressor, self.reverb, self.limiter):
            stage.reset()

    def process(self, block):
        if self.enabled['equalizer']:
            block = self.equalizer.process(block)
        if self.enabled['warmth']:
            block = self.saturator.process(block)
        if self.enabled['leveler']:
            block = self.compressor.process(block)
        if self.enabled['width']:
            block = self.width.process(block)
        if self.enabled['space']:
            block = self.reverb.process(block)
        if self.output_gain != 1.0:
            block = block * self.output_gain
        return self.limiter.process(block)


class AudioEngine:
    """
    Owns the output device. Sources are pulled, summed, processed and
    written every callback; if the device is unavailable the engine runs
    in silent mode so the rest of the app keeps working.
    """

    def __init__(self, samplerate=None, blocksize=DEFAULT_BLOCKSIZE, device=None):
        self.blocksize = blocksize
        self.channels = CHANNELS
        self.device = device
        self.samplerate = samplerate or self._preferred_samplerate(device)

        self.chain = MasterChain(self.samplerate, blocksize, self.channels)
        self._sources = ()
        self._lock = threading.Lock()
        self._stream = None
        self._running = False
        self.silent = False
        self.last_error = None

        # Meters for the UI: updated every callback, read from any thread.
        self.peak = 0.0
        self.rms = 0.0
        self.spectrum = np.zeros(32)
        self._spectrum_window = np.hanning(blocksize)
        self._spectrum_bins = self._build_spectrum_bins()
        self._block_counter = 0
        self._underruns = 0
        self._last_restart = 0.0

    @staticmethod
    def _preferred_samplerate(device):
        try:
            import sounddevice as sd
            info = sd.query_devices(device, 'output')
            rate = int(info.get('default_samplerate') or DEFAULT_SAMPLERATE)
            return rate if rate >= 8000 else DEFAULT_SAMPLERATE
        except Exception:
            return DEFAULT_SAMPLERATE

    def _build_spectrum_bins(self):
        """Log spaced band edges (as rfft bin indices) for the visualiser."""
        freqs = np.fft.rfftfreq(self.blocksize, 1.0 / self.samplerate)
        edges = np.logspace(np.log10(40.0), np.log10(min(16000.0, self.samplerate / 2.2)), 33)
        return np.clip(np.searchsorted(freqs, edges), 0, len(freqs) - 1)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self):
        if self._stream is not None:
            return True
        self._running = True
        try:
            import sounddevice as sd
            self._stream = sd.OutputStream(
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                channels=self.channels,
                dtype='float32',
                device=self.device,
                callback=self._callback,
                finished_callback=self._on_finished,
            )
            self._stream.start()
            self.silent = False
            print("AudioEngine: %d Hz, %d frame blocks, device=%s"
                  % (self.samplerate, self.blocksize, self.device or 'default'))
            return True
        except Exception as e:
            self._stream = None
            self.silent = True
            self.last_error = "Audio output unavailable: %s" % e
            print("AudioEngine: %s" % self.last_error)
            return False

    def stop(self):
        self._running = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        sources, self._sources = self._sources, ()
        for source in sources:
            try:
                source.close()
            except Exception:
                pass

    def _on_finished(self):
        # PortAudio aborted the stream (device removed, format change...).
        # Flag it so the next update() call brings audio back.
        self._stream = None

    def update(self):
        """
        Called from the UI loop: brings audio back if the device dropped
        out, and keeps looking for one if there was none at startup (a
        headset plugged in later should just start working).
        """
        if self._stream is not None or not self._running:
            return
        now = time.monotonic()
        if now - self._last_restart < (10.0 if self.silent else 2.0):
            return
        self._last_restart = now
        if not self.silent:
            print("AudioEngine: output stream lost, restarting")
        self.chain.reset()
        self.start()

    # ------------------------------------------------------------------ #
    # Sources
    # ------------------------------------------------------------------ #

    def add_source(self, source):
        with self._lock:
            if source not in self._sources:
                self._sources = self._sources + (source,)
        return source

    def remove_source(self, source, wait=False):
        """
        Detaches a source from the mix.

        Tearing a decoder down can take a moment (a socket may need to
        time out), so by default that happens on a throwaway thread and
        the UI loop never stalls. Shutdown passes wait=True.
        """
        with self._lock:
            self._sources = tuple(s for s in self._sources if s is not source)
        if wait:
            source.close()
        else:
            close_async(source)

    # ------------------------------------------------------------------ #
    # Audio callback
    # ------------------------------------------------------------------ #

    def _callback(self, outdata, frames, time_info, status):
        if status:
            self._underruns += 1

        mix = np.zeros((frames, self.channels), dtype=np.float64)
        for source in self._sources:  # tuple snapshot: safe without a lock
            try:
                block = source.render(frames)
            except Exception:
                continue
            if block is not None:
                mix += block

        try:
            mix = self.chain.process(mix)
        except Exception as e:
            self.last_error = "Effect chain error: %s" % e

        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:] = mix.astype(np.float32)
        self._update_meters(mix)

    def _update_meters(self, mix):
        mono = mix.mean(axis=1)
        self.peak = float(np.abs(mono).max())
        self.rms = float(np.sqrt(np.mean(mono * mono)))

        # The spectrum only feeds visuals, so a third of the rate is plenty.
        self._block_counter += 1
        if self._block_counter % 3:
            return
        if len(mono) != len(self._spectrum_window):
            return
        magnitude = np.abs(np.fft.rfft(mono * self._spectrum_window))
        edges = self._spectrum_bins
        bands = np.empty(len(edges) - 1)
        for i in range(len(bands)):
            lo, hi = edges[i], max(edges[i + 1], edges[i] + 1)
            bands[i] = magnitude[lo:hi].mean()
        # Smooth the decay so bars fall instead of flickering.
        self.spectrum = np.maximum(bands / (len(mono) * 0.25), self.spectrum * 0.72)
