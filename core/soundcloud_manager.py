import requests


class SoundCloudManager:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.config = {
            "client_id": "",
            "max_tracks": 50,
            "streamable_only": True
        }
        if self.config_manager:
            loaded = self.config_manager.load_json("soundcloud.json", default=self.config)
            if isinstance(loaded, dict):
                self.config.update(loaded)

    def has_credentials(self):
        return bool(self.config.get("client_id"))

    def _get(self, url, params=None):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"SoundCloud API error: {e}")
            return None

    def fetch_tracks(self, query):
        if not self.has_credentials():
            return []
        if not query:
            return []
        
        max_tracks = int(self.config.get("max_tracks", 50) or 50)
        params = {
            "client_id": self.config["client_id"],
            "q": query,
            "limit": max_tracks
        }
        if self.config.get("streamable_only", True):
            params["streamable"] = "true"
        
        data = self._get("https://api.soundcloud.com/tracks", params=params)
        if not data:
            return []
        
        stations = []
        for t in data:
            title = t.get("title") or "Unknown Track"
            user = t.get("user") or {}
            username = user.get("username") or "Unknown Artist"
            genre = t.get("genre") or ""
            duration_ms = t.get("duration") or 0
            duration_sec = int(duration_ms / 1000) if duration_ms else 0
            
            station = {
                "name": title,
                "artist": username,
                "genre": genre,
                "duration": duration_sec,
                "playback_count": t.get("playback_count", 0),
                "url_resolved": f"soundcloud://track/{t.get('id') or t.get('urn')}",
                "stream_url": t.get("stream_url"),
                "permalink_url": t.get("permalink_url"),
                "transcodings": (t.get("media") or {}).get("transcodings", [])
            }
            stations.append(station)
        
        return stations
