import os
import time
from urllib.parse import urlparse

from core.audio.decoder import ProcessSource, python_executable

RETRY_COOLDOWN = 5.0


class KiwiClientPlayer:
    """
    Plays KiwiSDR audio through the upstream jks-prv/kiwiclient recorder.

    The adapter expects a local clone/download of KiwiClient and uses
    kiwirecorder.py in netcat WAV mode. Set KIWI_CLIENT_DIR or configure
    kiwi_client_dir in config/analog_radio.json.

    The recorder's WAV output is decoded straight off its stdout pipe, so
    there is no local HTTP bridge in the path any more.
    """

    def __init__(self, config_manager=None, engine=None):
        from core.audio import get_engine

        self.config_manager = config_manager
        self.engine = engine or get_engine()
        self.current_key = None
        self.current_station = None
        self.last_error = None
        self.master_volume = 1.0

        self._source = None
        self._volume = 0.0
        self._failed_key = None
        self._failed_until = 0.0

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #

    def _load_config(self):
        if not self.config_manager:
            return {}
        data = self.config_manager.load_json("analog_radio.json", {})
        return data if isinstance(data, dict) else {}

    def _find_kiwirecorder(self):
        config = self._load_config()
        candidates = []
        configured_dir = config.get("kiwi_client_dir")
        if configured_dir:
            candidates.append(configured_dir)
        env_dir = os.environ.get("KIWI_CLIENT_DIR")
        if env_dir:
            candidates.append(env_dir)
        candidates.extend([
            os.path.join(os.getcwd(), "kiwiclient"),
            os.path.join(os.getcwd(), "vendor", "kiwiclient"),
        ])

        for base in candidates:
            path = os.path.join(base, "kiwirecorder.py")
            if os.path.exists(path):
                return os.path.abspath(path)
        return None

    def _station_key(self, station):
        if not station:
            return None
        return (
            station.get("kiwi_url"),
            station.get("kiwi_frequency_khz"),
            station.get("kiwi_mode", "am"),
        )

    def _build_command(self, station):
        recorder = self._find_kiwirecorder()
        if not recorder:
            self.last_error = "Kiwi client not configured"
            return None

        kiwi_url = station.get("kiwi_url", "")
        has_scheme = "://" in kiwi_url
        parsed = urlparse(kiwi_url if has_scheme else "http://%s" % kiwi_url)
        host = parsed.hostname
        if parsed.port:
            port = parsed.port
        elif not has_scheme:
            port = 8073
        else:
            port = 443 if parsed.scheme == "https" else 80
        if not host:
            self.last_error = "Invalid KiwiSDR URL"
            return None

        freq = station.get("kiwi_frequency_khz") or station.get("frequency")
        mode = station.get("kiwi_mode", "am")
        if not freq:
            self.last_error = "Analog station has no frequency"
            return None

        return [
            python_executable(),
            recorder,
            "--server-host", host,
            "--server-port", str(port),
            "--freq", str(freq),
            "--mode", str(mode),
            "--nc",
            "--nc-wav",
            "--quiet",
        ]

    # ------------------------------------------------------------------ #
    # Playback
    # ------------------------------------------------------------------ #

    def play_station(self, station):
        key = self._station_key(station)
        now = time.monotonic()
        if key and key == self._failed_key and now < self._failed_until:
            return False

        if key and key == self.current_key and self._source is not None:
            if self._source.failed:
                self.last_error = self._source.last_error or self.last_error
                self._mark_failed(key)
                self.stop()
                return False
            return True

        self.stop()
        command = self._build_command(station)
        if not command:
            self._mark_failed(key)
            return False

        try:
            source = ProcessSource(
                self.engine,
                command,
                cwd=os.path.dirname(command[1]),
                input_format='wav',
                label='kiwi',
                # The recorder needs a moment to connect to the SDR, so be
                # patient before declaring the station dead.
                prebuffer_seconds=1.0,
                connect_attempts=2,
                reconnect_attempts=2,
            )
            source.gain = self._volume
            self.engine.add_source(source)
            source.start()

            self._source = source
            self.current_key = key
            self.current_station = station
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = "Unable to start Kiwi audio: %s" % e
            self._mark_failed(key)
            self.stop()
            return False

    def _mark_failed(self, key):
        if not key:
            return
        self._failed_key = key
        self._failed_until = time.monotonic() + RETRY_COOLDOWN

    def stop(self):
        source, self._source = self._source, None
        if source is not None:
            self.engine.remove_source(source)
        self.current_key = None
        self.current_station = None

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    def is_active(self):
        """True while a Kiwi station is claimed, playing or not yet."""
        return self.current_station is not None or self._source is not None

    def is_playing(self):
        return self._source is not None and self._source.state == 'playing'

    def set_volume(self, volume):
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._source is not None:
            self._source.gain = self._volume

    def get_now_playing(self):
        if self.current_station:
            freq = self.current_station.get("kiwi_frequency_khz")
            mode = self.current_station.get("kiwi_mode", "am").upper()
            name = self.current_station.get("name", "KiwiSDR")
            if self._source is not None and self._source.state in ('connecting', 'buffering'):
                return "%s - tuning..." % name
            if freq:
                return "%s - %s kHz %s" % (name, freq, mode)
            return name
        return self.last_error or "Unknown"

    def update(self):
        if self._source is not None and self._source.failed:
            self.last_error = self._source.last_error or "Kiwi client stopped"
            self._mark_failed(self.current_key)
            self.stop()
