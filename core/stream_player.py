import time

from core.audio import get_engine
from core.audio.decoder import NetworkSource
from core.kiwi_player import KiwiClientPlayer

# How long a station that refuses to play is left alone before we retry.
FAILED_URL_COOLDOWN = 5.0
# A retiring stream is faded rather than cut, so switching stations does
# not click. It keeps mixing for this long at falling gain.
RETIRE_SECONDS = 0.25
# Scrubbing across the dial can outrun the fades. Past this many, the
# oldest gets dropped immediately rather than holding a connection open.
MAX_RETIRING = 2


class StreamPlayer:
    """
    Plays internet radio through the shared audio engine.

    The engine mixes and processes everything, so this class only has to
    decide which source should exist and how loud it should be.
    """

    def __init__(self, config_manager=None):
        self.engine = get_engine()
        self.kiwi_player = KiwiClientPlayer(config_manager, engine=self.engine)
        self.current_url = None
        self.master_volume = 1.0

        self._source = None
        self._retiring = []
        self._volume = 0.0
        self._failed_url = None
        self._failed_url_until = 0.0

    # The equalizer used to be applied to a VLC media player; now it lives
    # on the engine. Kept as properties so callers do not have to care.
    @property
    def player(self):
        return self.engine

    @property
    def instance(self):
        return self.engine

    # ------------------------------------------------------------------ #
    # Playback
    # ------------------------------------------------------------------ #

    def play_station(self, station):
        if not station:
            return False

        if station.get('source') == 'kiwi':
            if self._source is not None:
                self._retire_source()
                self.current_url = None
            return self.kiwi_player.play_station(station)

        if self.kiwi_player.is_active():
            self.kiwi_player.stop()
        self.play(station.get('url_resolved'))
        return True

    def play(self, url):
        """
        Plays the given URL, replacing whatever was playing. Safe to call
        every frame: repeat calls for the URL already playing do nothing.
        """
        if not url:
            return
        if self.kiwi_player.is_active():
            self.kiwi_player.stop()

        if url == self.current_url and self._source is not None:
            if self._source.failed:
                self._mark_failed(url)
                self.stop()
            return

        now = time.monotonic()
        if url == self._failed_url and now < self._failed_url_until:
            return

        self._retire_source()
        print("StreamPlayer: Playing %s" % url)
        source = NetworkSource(self.engine, url)
        source.gain = self._volume
        self.engine.add_source(source)
        source.start()

        self._source = source
        self.current_url = url
        self._failed_url = None
        self._failed_url_until = 0.0

    def stop(self):
        self._retire_source()
        self.current_url = None
        if self.kiwi_player.is_active():
            self.kiwi_player.stop()

    def _retire_source(self):
        """Fades the current source out instead of cutting it dead."""
        source, self._source = self._source, None
        if source is None:
            return
        source.gain = 0.0
        self._retiring.append((source, time.monotonic() + RETIRE_SECONDS))
        while len(self._retiring) > MAX_RETIRING:
            oldest, _ = self._retiring.pop(0)
            self.engine.remove_source(oldest)

    def _mark_failed(self, url):
        self._failed_url = url
        self._failed_url_until = time.monotonic() + FAILED_URL_COOLDOWN

    # ------------------------------------------------------------------ #
    # Volume and state
    # ------------------------------------------------------------------ #

    def set_volume(self, volume):
        """Volume is 0.0 to 1.0; the engine ramps to it without clicking."""
        volume = max(0.0, min(1.0, float(volume)))
        if self.kiwi_player.is_active():
            self.kiwi_player.set_volume(volume)
            return
        self._volume = volume
        if self._source is not None:
            self._source.gain = volume

    def is_playing(self):
        if self.kiwi_player.is_active():
            return self.kiwi_player.is_playing()
        return self._source is not None and self._source.state == 'playing'

    def get_now_playing(self):
        """Live track title when the station sends one, else its status."""
        if self.kiwi_player.is_active():
            return self.kiwi_player.get_now_playing()
        source = self._source
        if source is None:
            return "Unknown"
        if source.title:
            return source.title
        if source.state in ('connecting', 'buffering'):
            return "Buffering..."
        if source.state == 'error':
            return source.last_error or "Stream unavailable"
        return source.station_name or "Unknown"

    def get_status(self):
        """Diagnostics for the UI: engine meters plus stream health."""
        source = self._source
        return {
            'state': source.state if source else 'idle',
            'codec': source.codec if source else None,
            'underruns': source.underruns if source else 0,
            'error': source.last_error if source else self.engine.last_error,
            'peak': self.engine.peak,
            'rms': self.engine.rms,
        }

    def update(self):
        """Called once per UI frame: retires faded sources, watches health."""
        if self._retiring:
            now = time.monotonic()
            still_fading = []
            for source, deadline in self._retiring:
                if now >= deadline:
                    self.engine.remove_source(source)
                else:
                    still_fading.append((source, deadline))
            self._retiring = still_fading

        if self._source is not None and self._source.failed:
            print("StreamPlayer: %s failed (%s)"
                  % (self.current_url, self._source.last_error))
            self._mark_failed(self.current_url)
            self.stop()

        self.engine.update()
        self.kiwi_player.update()

    def cleanup_except(self, keep_urls):
        pass
