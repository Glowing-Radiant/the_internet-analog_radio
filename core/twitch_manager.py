import time
import requests


class TwitchManager:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.config = {
            "client_id": "",
            "client_secret": "",
            "category_query": "Music & Performing Arts",
            "max_streams": 50,
            "languages": ["en"],
            "channel_whitelist": []
        }
        if self.config_manager:
            loaded = self.config_manager.load_json("twitch.json", default=self.config)
            if isinstance(loaded, dict):
                self.config.update(loaded)
        
        self._app_token = None
        self._token_expires_at = 0

    def has_credentials(self):
        return bool(self.config.get("client_id") and self.config.get("client_secret"))

    def _get_app_token(self):
        if not self.has_credentials():
            return None
        
        now = time.time()
        if self._app_token and now < self._token_expires_at - 60:
            return self._app_token
        
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials"
        }
        try:
            resp = requests.post(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._app_token = data.get("access_token")
            expires_in = int(data.get("expires_in", 0))
            self._token_expires_at = now + expires_in
            return self._app_token
        except Exception as e:
            print(f"Twitch auth error: {e}")
            return None

    def _headers(self):
        token = self._get_app_token()
        if not token:
            return None
        return {
            "Client-ID": self.config["client_id"],
            "Authorization": f"Bearer {token}"
        }

    def _get(self, url, params=None):
        headers = self._headers()
        if not headers:
            return None
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Twitch API error: {e}")
            return None

    def _search_category_id(self, query):
        if not query:
            return None
        url = "https://api.twitch.tv/helix/search/categories"
        data = self._get(url, params={"query": query, "first": 1})
        if not data:
            return None
        items = data.get("data", [])
        if not items:
            return None
        return items[0].get("id")

    def _get_streams_by_game(self, game_id, max_streams=50, languages=None):
        if not game_id:
            return []
        url = "https://api.twitch.tv/helix/streams"
        results = []
        max_streams = max(1, min(100, max_streams))
        
        if not languages:
            data = self._get(url, params={"game_id": game_id, "first": max_streams})
            return data.get("data", []) if data else []
        
        for lang in languages:
            if len(results) >= max_streams:
                break
            remaining = max_streams - len(results)
            data = self._get(url, params={"game_id": game_id, "first": remaining, "language": lang})
            if data and data.get("data"):
                results.extend(data.get("data"))
        return results[:max_streams]

    def _get_streams_by_users(self, user_logins, max_streams=50):
        if not user_logins:
            return []
        url = "https://api.twitch.tv/helix/streams"
        results = []
        max_streams = max(1, min(100, max_streams))
        chunk = 100
        for i in range(0, len(user_logins), chunk):
            batch = user_logins[i:i + chunk]
            params = {"first": min(max_streams, 100)}
            for login in batch:
                params.setdefault("user_login", []).append(login)
            data = self._get(url, params=params)
            if data and data.get("data"):
                results.extend(data.get("data"))
            if len(results) >= max_streams:
                break
        return results[:max_streams]

    def fetch_streams(self):
        if not self.has_credentials():
            return []
        
        max_streams = int(self.config.get("max_streams", 50) or 50)
        languages = self.config.get("languages") or []
        whitelist = [c.strip().lower() for c in self.config.get("channel_whitelist") or [] if c.strip()]
        
        if whitelist:
            streams = self._get_streams_by_users(whitelist, max_streams=max_streams)
        else:
            category_query = self.config.get("category_query", "Music & Performing Arts")
            game_id = self._search_category_id(category_query)
            streams = self._get_streams_by_game(game_id, max_streams=max_streams, languages=languages)
        
        stations = []
        for s in streams:
            login = s.get("user_login")
            if not login:
                continue
            station = {
                "name": s.get("user_name", login),
                "url_resolved": f"twitch://{login}",
                "country": s.get("game_name", "Twitch"),
                "bitrate": 0,
                "title": s.get("title", ""),
                "category": s.get("game_name", ""),
                "viewers": s.get("viewer_count", 0),
                "language": s.get("language", "")
            }
            stations.append(station)
        return stations

    def fetch_streams_by_query(self, query):
        if not self.has_credentials():
            return []
        if not query:
            return []
        
        max_streams = int(self.config.get("max_streams", 50) or 50)
        languages = self.config.get("languages") or []
        
        q = query.strip()
        if q.lower().startswith("category:"):
            category_query = q.split(":", 1)[1].strip()
            game_id = self._search_category_id(category_query)
            streams = self._get_streams_by_game(game_id, max_streams=max_streams, languages=languages)
        else:
            if q.startswith("@"):
                q = q[1:].strip()
            if "channel:" in q.lower():
                q = q.split(":", 1)[1].strip()
            if "," in q:
                logins = [p.strip().lstrip("@").lower() for p in q.split(",") if p.strip()]
                streams = self._get_streams_by_users(logins, max_streams=max_streams)
            else:
                # Default to category search
                game_id = self._search_category_id(q)
                streams = self._get_streams_by_game(game_id, max_streams=max_streams, languages=languages)
        
        stations = []
        for s in streams:
            login = s.get("user_login")
            if not login:
                continue
            station = {
                "name": s.get("user_name", login),
                "url_resolved": f"twitch://{login}",
                "country": s.get("game_name", "Twitch"),
                "bitrate": 0,
                "title": s.get("title", ""),
                "category": s.get("game_name", ""),
                "viewers": s.get("viewer_count", 0),
                "language": s.get("language", "")
            }
            stations.append(station)
        return stations
