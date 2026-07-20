import os
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

import vlc


class KiwiClientPlayer:
    """
    Plays KiwiSDR audio through the upstream jks-prv/kiwiclient recorder.

    The adapter expects a local clone/download of KiwiClient and uses
    kiwirecorder.py in netcat WAV mode. Set KIWI_CLIENT_DIR or configure
    kiwi_client_dir in config/analog_radio.json.
    """

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.instance = vlc.Instance("--no-video", "--quiet")
        self.player = self.instance.media_player_new()
        self.process = None
        self.current_key = None
        self.current_station = None
        self.last_error = None
        self.master_volume = 1.0
        self._last_set_volume = None
        self._stderr_thread = None
        self._bridge_socket = None
        self._bridge_thread = None
        self._failed_key = None
        self._failed_until = 0
        self._last_play_attempt_at = 0

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
        parsed = urlparse(kiwi_url if has_scheme else f"http://{kiwi_url}")
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
            sys.executable,
            recorder,
            "--server-host", host,
            "--server-port", str(port),
            "--freq", str(freq),
            "--mode", str(mode),
            "--nc",
            "--nc-wav",
            "--quiet",
        ]

    def play_station(self, station):
        key = self._station_key(station)
        now = time.monotonic()
        if key and key == self._failed_key and now < self._failed_until:
            return False

        if key and key == self.current_key:
            state = self.player.get_state()
            active_states = {vlc.State.Opening, vlc.State.Buffering, vlc.State.Playing}
            if state in active_states:
                return True
            if state in {vlc.State.Error, vlc.State.Ended}:
                self._mark_failed(key)
                return False
            if now - self._last_play_attempt_at >= 2.0 and not self.player.is_playing():
                self._last_play_attempt_at = now
                self.player.play()
            return True

        self.stop()
        command = self._build_command(station)
        if not command:
            self._mark_failed(key)
            return False

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=os.path.dirname(command[1]),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            bridge_url = self._start_http_bridge()
            media = self.instance.media_new(bridge_url)
            self.player.set_media(media)
            self.player.audio_set_volume(0)
            self.player.play()
            self._last_play_attempt_at = time.monotonic()
            self.current_key = key
            self.current_station = station
            self.last_error = None
            self._last_set_volume = 0
            self._start_stderr_drain()
            return True
        except Exception as e:
            self.last_error = f"Unable to start Kiwi audio: {e}"
            self._mark_failed(key)
            self.stop()
            return False

    def _start_http_bridge(self):
        self._close_http_bridge()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(10)
        self._bridge_socket = server
        host, port = server.getsockname()

        def bridge():
            client = None
            try:
                client, _ = server.accept()
                client.settimeout(5)
                try:
                    client.recv(4096)
                except Exception:
                    pass
                client.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: audio/wav\r\n"
                    b"Cache-Control: no-store\r\n"
                    b"Connection: close\r\n\r\n"
                )
                while self.process and self.process.stdout:
                    chunk = self.process.stdout.read(4096)
                    if not chunk:
                        break
                    client.sendall(chunk)
            except Exception as e:
                if self.process and self.process.poll() is None:
                    self.last_error = f"Kiwi audio bridge stopped: {e}"
            finally:
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
                try:
                    server.close()
                except Exception:
                    pass

        self._bridge_thread = threading.Thread(target=bridge, daemon=True)
        self._bridge_thread.start()
        return f"http://{host}:{port}/kiwi.wav"

    def _close_http_bridge(self):
        if self._bridge_socket:
            try:
                self._bridge_socket.close()
            except Exception:
                pass
        self._bridge_socket = None

    def _mark_failed(self, key):
        if not key:
            return
        self._failed_key = key
        self._failed_until = time.monotonic() + 5.0

    def _start_stderr_drain(self):
        if not self.process or not self.process.stderr:
            return

        def drain():
            try:
                for raw in iter(self.process.stderr.readline, b""):
                    text = raw.decode(errors="replace").strip()
                    if text:
                        self.last_error = text
            except Exception:
                pass

        self._stderr_thread = threading.Thread(target=drain, daemon=True)
        self._stderr_thread.start()

    def set_volume(self, volume):
        vol = int(max(0.0, min(1.0, volume)) * 100)
        if self._last_set_volume == vol:
            return
        self._last_set_volume = vol
        if vol == 0:
            if not self.player.audio_get_mute():
                self.player.audio_set_mute(True)
        else:
            if self.player.audio_get_mute():
                self.player.audio_set_mute(False)
            self.player.audio_set_volume(vol)

    def stop(self):
        if not self.process and not self.current_key and not self.current_station:
            return
        try:
            self.player.stop()
        except Exception:
            pass
        self._close_http_bridge()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None
        self.current_key = None
        self.current_station = None

    def is_playing(self):
        return self.player.is_playing()

    def get_now_playing(self):
        if self.current_station:
            freq = self.current_station.get("kiwi_frequency_khz")
            mode = self.current_station.get("kiwi_mode", "am").upper()
            name = self.current_station.get("name", "KiwiSDR")
            if freq:
                return f"{name} - {freq} kHz {mode}"
            return name
        return self.last_error or "Unknown"

    def update(self):
        if self.process and self.process.poll() is not None:
            key = self.current_key
            exit_code = self.process.returncode
            self.last_error = self.last_error or f"Kiwi client stopped ({exit_code})"
            self._mark_failed(key)
            self.stop()
