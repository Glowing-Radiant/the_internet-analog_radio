import requests
import random
import re

class StationManager:
    def __init__(self, config_manager=None, region_detector=None):
        # Default server to avoid blocking start
        self.base_url = "https://de1.api.radio-browser.info/json/stations"
        print(f"Using default API Server: {self.base_url}")
        
        self.config_manager = config_manager
        self.region_detector = region_detector
        self.stations = {
            'national': [],
            'international': [],
            'exploratory': []
        }
        self.tv_stations = {
            'national': [],
            'international': [],
            'exploratory': [],
            'favorites': [] # Shared or separate? Plan said separate keys maybe?
        }
        
        # Load Cache
        self.cache_file = "stations_cache.json"
        self._load_cache()

        self.custom_bands = {}
        self.custom_bands_migrated = False
        if self.config_manager:
            # Load and migrate custom bands to per-mode format
            loaded = self.config_manager.load_json("custom_bands.json", {})
            migrated = self._migrate_custom_bands(loaded)
            self.custom_bands = migrated
            if migrated is not loaded:
                self.config_manager.save_json("custom_bands.json", migrated)
                self.custom_bands_migrated = True

    def _migrate_custom_bands(self, data):
        if not isinstance(data, dict):
            return {'radio': {}, 'tv': {}}
        
        # If already per-mode
        if any(k in data for k in ('radio', 'tv')):
            for k in ('radio', 'tv'):
                data.setdefault(k, {})
            return {k: data.get(k, {}) for k in ('radio', 'tv')}
        
        # Legacy flat dict: assume radio
        return {
            'radio': data,
            'tv': {}
        }

    def _ensure_server(self):
        """
        Ensures we have a working server. Called from threaded fetch.
        """
        # Try current first
        try:
             # Construct stats URL correctly
             # base_url is typically .../json/stations
             # we want .../json/stats
             stats_url = self.base_url.replace('/stations', '/stats')
             requests.get(stats_url, timeout=2)
             return # Current is good
        except:
             print("Current server unreachable, finding new one...")
             self.base_url = self._find_server()
             print(f"Switched to: {self.base_url}")

    def _find_server(self):
        # List of known servers
        mirrors = [
            "at1.api.radio-browser.info",
            "de1.api.radio-browser.info",
            "fr1.api.radio-browser.info",
            "nl1.api.radio-browser.info",
            "all.api.radio-browser.info"
        ]
        random.shuffle(mirrors)
        
        for host in mirrors:
            try:
                url = f"https://{host}/json"
                requests.get(f"{url}/stats", timeout=2)
                return f"{url}/stations"
            except Exception as e:
                print(f"Server {host} unreachable: {e}")
                continue
                
        return "https://de1.api.radio-browser.info/json/stations"

    def fetch_all(self, country_code=None):
        # This runs in thread, so we can block to find server
        self._ensure_server()
        
        # If no country was provided, try region detector if available.
        if not country_code and self.region_detector:
             region = self.region_detector.get_region()
             country_code = region.get('countryCode')
             
        if country_code:
            self.fetch_national(country_code)
            
        self.fetch_international()

    def fetch_national(self, country_code, limit=50):
        if not country_code: return
        data = self._fetch(f"{self.base_url}/bycountrycodeexact/{country_code}", limit)
        if data:
            self.stations['national'] = data
            self._save_cache()

    def fetch_international(self, limit=50):
        # Fetch RANDOM stations for exploration (instead of topvote)
        data = []
        for _ in range(3):
            # API endpoint for search with random order
            url = f"{self.base_url}/search"
            # Tag list to ensure variety? Or just completely random?
            # Completely random sometimes gives weird stuff. Let's try general random.
            # Adding has_geo_info=false to avoid biasing (default).
            params = {
                'limit': limit,
                'order': 'random',
                'hidebroken': 'true'
            }
            data = self._fetch(url, limit, params=params)
            if data:
                break
            print("Retrying International fetch...")
        
        # Save if found
        if data:
            self.stations['international'] = data
            self._save_cache()
        
        # Fallback if still empty (and cache was empty)
        if not self.stations['international']:
            print("Using fallback International stations")
            self.stations['international'] = [
                {'name': 'BBC World Service', 'url_resolved': 'http://stream.live.vc.bbcmedia.co.uk/bbc_world_service', 'country': 'UK', 'bitrate': 128},
                {'name': 'KEXP 90.3 FM', 'url_resolved': 'http://live-aacplus-64.kexp.org/kexp64.aac', 'country': 'USA', 'bitrate': 64},
                {'name': 'Radio Paradise', 'url_resolved': 'http://stream.radioparadise.com/aac-128', 'country': 'USA', 'bitrate': 128},
                {'name': 'SomaFM Groove Salad', 'url_resolved': 'http://ice1.somafm.com/groovesalad-128-mp3', 'country': 'USA', 'bitrate': 128},
                {'name': 'Classic FM', 'url_resolved': 'http://media-ice.musicradio.com/ClassicFMMP3', 'country': 'UK', 'bitrate': 128}
            ]
            self._assign_frequencies(self.stations['international'])

    def _load_cache(self):
        if self.config_manager:
            cached = self.config_manager.load_json(self.cache_file, {})
            if cached:
                # Merge cache
                for k, v in cached.items():
                    if k in self.stations:
                        self.stations[k] = v
                print(f"Loaded {sum(len(v) for v in cached.values())} stations from cache.")

    def _save_cache(self):
        if self.config_manager:
            self.config_manager.save_json(self.cache_file, self.stations)

    def search_stations(self, query, limit=50, mode='radio'):
        if not query:
            return

        if mode == 'tv':
            self.search_tv_stations(query, limit)
            return
        
        # Search by name
        url_name = f"{self.base_url}/search"
        params_name = {'name': query, 'limit': limit, 'hidebroken': 'true'}
        
        # Search by tag
        url_tag = f"{self.base_url}/search"
        params_tag = {'tag': query, 'limit': limit, 'hidebroken': 'true'}
        
        stations_name = self._fetch(url_name, limit, params=params_name)
        stations_tag = self._fetch(url_tag, limit, params=params_tag)
        
        combined = self._dedupe_stations(stations_name + stations_tag)
        self.stations['exploratory'] = combined[:limit]

    def search_tv_stations(self, query, limit=100):
        if not query:
            self.tv_stations['exploratory'] = []
            return []

        # Reuse the same TV API-backed bands already fetched for TV mode.
        if not self.tv_stations['national'] and not self.tv_stations['international']:
            self.fetch_tv_all()

        pool = self.tv_stations.get('national', []) + self.tv_stations.get('international', [])
        if not pool:
            self.tv_stations['exploratory'] = []
            return []

        terms = [term.strip().lower() for term in query.split() if term.strip()]
        matches = []
        for station in pool:
            haystack = " ".join([
                str(station.get('name', '')),
                str(station.get('country', '')),
                str(station.get('group', '')),
                str(station.get('tvg_id', '')),
                str(station.get('tvg_name', ''))
            ]).lower()
            if all(term in haystack for term in terms):
                matches.append(station)

        self.tv_stations['exploratory'] = self._dedupe_stations(matches)[:limit]
        return self.tv_stations['exploratory']

    def _dedupe_stations(self, stations):
        seen = set()
        deduped = []
        for station in stations:
            key = (
                station.get('stationuuid')
                or station.get('url_resolved')
                or f"{station.get('name', '')}|{station.get('country', '')}"
            )
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(station)
        return deduped

    def save_custom_band(self, name, stations, mode='radio'):
        if not name or not stations: 
            return
        if mode not in self.custom_bands:
            self.custom_bands[mode] = {}
        self.custom_bands[mode][name] = stations
        if self.config_manager:
            self.config_manager.save_json("custom_bands.json", self.custom_bands)

    def get_station_list(self, band, mode='radio'):
        if mode == 'tv':
            # TV Logic
            if band in self.tv_stations:
                return self.tv_stations[band]
            if mode in self.custom_bands and band in self.custom_bands[mode]:
                return self.custom_bands[mode][band]
            return []
            
        # Radio Logic
        if band in self.stations:
            return self.stations[band]
        if mode in self.custom_bands and band in self.custom_bands[mode]:
            return self.custom_bands[mode][band]
        return []

    def _fetch(self, url, limit, params=None):
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Relaxed check: some valid stations have null lastcheckok or 0 explicitly but work.
            # We strictly need url_resolved. 
            # Only filter out if lastcheckok is explicitly 0 (failed check), 
            # but maybe that's too aggressive if the check itself is old.
            # Let's trust url_resolved presence mostly.
            
            valid_stations = []
            for s in data:
                if not s.get('url_resolved'): continue
                
                # If lastcheckok is missing, assume OK. If 0, maybe skip. 
                # But let's be generous for now to fix empty lists.
                if 'lastcheckok' in s and s['lastcheckok'] == 0:
                     continue
                     
                valid_stations.append(s)
                
            random.shuffle(valid_stations)
            
            # Assign frequencies to the selected stations
            selected = valid_stations[:limit]
            self._assign_frequencies(selected)
            return selected
        except requests.RequestException:
            return []

    def _assign_frequencies(self, stations):
        # Range 87.5 - 108.0
        # Divide range into slots to avoid overlap if we wanted perfect distribution,
        # but random is fine for now as long as we check collisions or just accept them.
        # User said "assign a frequency... let user reach that frequency".
        
        used_freqs = set()
        
        for station in stations:
            # Try to find a unique frequency with spacing
            # We'll use 1 decimal place for simplicity in UI, e.g. 104.5
            # Enforce minimal spacing of 0.4 MHz to avoid overlapping signals
            MAX_RETRIES = 50
            for _ in range(MAX_RETRIES): 
                cand_freq = round(random.uniform(87.5, 108.0), 1)
                
                # Check collision with existing freqs
                collision = False
                for f in used_freqs:
                    if abs(f - cand_freq) < 0.4: # Spacing check
                        collision = True
                        break
                
                if not collision:
                    used_freqs.add(cand_freq)
                    station['frequency'] = cand_freq
                    break
            
            # Fallback if crowded (unlikely with float/limit=50)
            if 'frequency' not in station:
                # Just pick one even if it overlaps, best effort
                station['frequency'] = round(random.uniform(87.5, 108.0), 1)

    # --- TV MODE SUPPORT ---
    
    def fetch_tv_all(self, country_code=None):
        """Fetch all necessary TV bands."""
        if not country_code and self.region_detector:
             region = self.region_detector.get_region()
             country_code = region.get('countryCode')
             print(f"Detected Country for TV: {country_code}")

        if country_code:
            self.fetch_tv_national(country_code)
        self.fetch_tv_international()
        
    def fetch_tv_national(self, country_code):
        # Using iptv-org country playlists
        # URL format: https://iptv-org.github.io/iptv/countries/{code}.m3u
        # Code is usually ISO 2 letter lower case? iptv-org uses 2 letter lowercase.
        if not country_code: return
        
        url = f"https://iptv-org.github.io/iptv/countries/{country_code.lower()}.m3u"
        print(f"Fetching TV National: {url}")
        
        stations = self._fetch_m3u(url)
        if stations:
            self.tv_stations['national'] = stations
            # Cache?
            
    def fetch_tv_international(self):
        # Provide a curated list of international news/music TV channels
        # Or just fetch a category like 'music' or 'news' from iptv-org
        # Let's fetch 'music' category as international band equivalent
        
        url = "https://iptv-org.github.io/iptv/categories/music.m3u"
        print(f"Fetching TV International (Music): {url}")
        
        stations = self._fetch_m3u(url)
        if stations:
            # Preservation of order: No shuffle.
            # Limit to reasonable amount? Maybe 100? Or just all?
            # User said "respect list order".
            self.tv_stations['international'] = stations[:100]
            
    def _fetch_m3u(self, url):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            content = response.text
            return self._parse_m3u(content)
        except Exception as e:
            print(f"Error fetching M3U {url}: {e}")
            return []
            
    def _parse_m3u(self, content):
        """
        Simple M3U parser.
        Expected format:
        #EXTINF:-1 tvg-id="..." tvg-name="..." ... ,Channel Name
        http://stream.url
        """
        lines = content.splitlines()
        stations = []
        
        current_station = {}
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF:"):
                # Parse metadata
                # Format: #EXTINF:-1 key="value",Name
                # We mainly want the Name and maybe logo/group
                
                # Split by comma for name
                parts = line.split(',', 1)
                name = "Unknown TV"
                if len(parts) > 1:
                    name = parts[1].strip()

                attrs = self._parse_m3u_attrs(parts[0])
                
                # We could parse other tags but Name is most important
                current_station = {
                    'name': name,
                    'bitrate': 0, # TV usually high
                    'country': attrs.get('tvg-country', 'TV'),
                    'group': attrs.get('group-title', ''),
                    'tvg_id': attrs.get('tvg-id', ''),
                    'tvg_name': attrs.get('tvg-name', '')
                }
            elif not line.startswith("#"):
                # URL
                if current_station:
                    current_station['url_resolved'] = line
                    stations.append(current_station)
                    current_station = {}
                    
        # Assign frequencies
        # Removed for TV as per new requirement: Direct Indexing
        # if stations:
        #    self._assign_frequencies(stations)
            
        return stations

    def _parse_m3u_attrs(self, extinf_head):
        return dict(re.findall(r'([a-zA-Z0-9_-]+)="([^"]*)"', extinf_head))
