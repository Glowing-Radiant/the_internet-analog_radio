import time
import requests


class SoundCloudResolver:
    def __init__(self, client_id, cache_ttl=300):
        self.client_id = client_id or ""
        self.cache_ttl = cache_ttl
        self._cache = {}

    def _cache_get(self, key):
        item = self._cache.get(key)
        if not item:
            return None
        url, expires_at = item
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return url

    def _cache_set(self, key, url):
        self._cache[key] = (url, time.time() + self.cache_ttl)

    def resolve(self, station):
        if not self.client_id:
            return None
        if not station:
            return None
        
        cache_key = station.get("url_resolved") or station.get("permalink_url")
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        
        stream_url = station.get("stream_url")
        if stream_url:
            play_url = f"{stream_url}?client_id={self.client_id}"
            self._cache_set(cache_key, play_url)
            return play_url
        
        # Try progressive transcoding
        transcodings = station.get("transcodings") or []
        for t in transcodings:
            fmt = t.get("format") or {}
            if fmt.get("protocol") != "progressive":
                continue
            trans_url = t.get("url")
            if not trans_url:
                continue
            try:
                resp = requests.get(trans_url, params={"client_id": self.client_id}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                play_url = data.get("url")
                if play_url:
                    self._cache_set(cache_key, play_url)
                    return play_url
            except Exception:
                continue
        
        return None
