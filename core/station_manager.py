import requests
import random

class StationManager:
    def __init__(self, config_manager=None):
        self.base_url = self._find_server()
        print(f"Using API Server: {self.base_url}")
        
        self.config_manager = config_manager
        self.stations = {
            'local': [],
            'national': [],
            'international': [],
            'exploratory': []
        }
        self.config_manager = config_manager
        
        # Load Cache
        self.cache_file = "stations_cache.json"
        self._load_cache()

        self.custom_bands = {}
        if self.config_manager:
            self.config_manager.load_json("custom_bands.json", {})

    def _find_server(self):
        # List of known servers
        mirrors = [
            "at1.api.radio-browser.info",
            "de1.api.radio-browser.info",
            "fr1.api.radio-browser.info",
            "nl1.api.radio-browser.info"
        ]
        random.shuffle(mirrors)
        
        # Fast check to find a working one
        for host in mirrors:
            try:
                url = f"https://{host}/json"
                # Timeout short for checking
                requests.get(f"{url}/stats", timeout=2)
                return f"{url}/stations"
            except Exception as e:
                print(f"Server {host} unreachable: {e}")
                continue
                
        # Fallback
        return "https://de1.api.radio-browser.info/json/stations"


    def fetch_all(self, country_code=None, city=None, lat=None, lon=None):
        if lat and lon:
            self.fetch_local(lat, lon)
        elif city:
             # Fallback to city search if no lat/lon
             self.stations['local'] = self._fetch(f"{self.base_url}/bycity/{city}", 20)
             
        if country_code:
            self.fetch_national(country_code)
            
        self.fetch_international()

    def fetch_national(self, country_code, limit=50):
        if not country_code: return
        data = self._fetch(f"{self.base_url}/bycountrycodeexact/{country_code}", limit)
        if data:
            self.stations['national'] = data
            self._save_cache()

    def fetch_local(self, lat, lon):
        # Fetch by geo, radius 50km
        url = f"{self.base_url}/bygeo/{lat}/{lon}/50"
        data = self._fetch(url, 20)
        if data:
            self.stations['local'] = data
            self._save_cache()

    def fetch_international(self, limit=50):
        # Fetch top voted stations, retry a few times if empty
        data = []
        for _ in range(3):
            data = self._fetch(f"{self.base_url}/topvote", limit)
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

    def search_stations(self, query, limit=50):
        if not query: return
        
        # Search by name
        url_name = f"{self.base_url}/search"
        params_name = {'name': query, 'limit': limit}
        
        # Search by tag
        url_tag = f"{self.base_url}/search"
        params_tag = {'tag': query, 'limit': limit}
        
        stations_name = self._fetch(url_name, limit, params=params_name)
        stations_tag = self._fetch(url_tag, limit, params=params_tag)
        
        # Combine and deduplicate by UUID
        seen_uuids = set()
        combined = []
        
        for s in stations_name + stations_tag:
            uuid = s.get('stationuuid')
            if uuid not in seen_uuids:
                seen_uuids.add(uuid)
                combined.append(s)
                
        self.stations['exploratory'] = combined[:limit]

    def save_custom_band(self, name, stations):
        if not name or not stations: return
        self.custom_bands[name] = stations
        if self.config_manager:
            self.config_manager.save_json("custom_bands.json", self.custom_bands)

    def get_station_list(self, band):
        if band in self.stations:
            return self.stations[band]
        if band in self.custom_bands:
            return self.custom_bands[band]
        return []

    def _fetch(self, url, limit, params=None):
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            valid_stations = [s for s in data if s.get('url_resolved') and s.get('lastcheckok') == 1]
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

        # Sort by frequency for easier navigation if we were traversing list,
        # but we are tuning. However, the station list structure in 'local' etc 
        # is just a list. The Controller will need to find the "closest" station.
        # So order in the list doesn't matter for the tuning logic I planned.

