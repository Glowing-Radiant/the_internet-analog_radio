import time


class TwitchResolver:
    def __init__(self, cache_ttl=300, preferred_quality="audio_only"):
        self.cache_ttl = cache_ttl
        self.preferred_quality = preferred_quality
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

    def resolve(self, channel_login):
        if not channel_login:
            return None
        
        cached = self._cache_get(channel_login)
        if cached:
            return cached
        
        try:
            import streamlink
        except Exception:
            return None
        
        try:
            session = streamlink.Streamlink()
            url = f"https://www.twitch.tv/{channel_login}"
            streams = session.streams(url)
            if not streams:
                return None
            stream = streams.get(self.preferred_quality) or streams.get("best")
            if not stream:
                return None
            play_url = stream.to_url()
            if play_url:
                self._cache_set(channel_login, play_url)
            return play_url
        except Exception:
            return None
