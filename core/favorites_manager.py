from .config_manager import ConfigManager
import random

class FavoritesManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        
        # Load raw data
        raw_data = self.config_manager.load_json("favorites.json", default={'radio': [], 'tv': []})
        
        # Migration: If it's a list, it's the old format (radio only)
        if isinstance(raw_data, list):
            self.favorites = {
                'radio': raw_data,
                'tv': []
            }
        else:
            self.favorites = raw_data
            
        # Ensure keys exist if partial dict loaded
        if 'radio' not in self.favorites: self.favorites['radio'] = []
        if 'tv' not in self.favorites: self.favorites['tv'] = []
            
        self._ensure_frequencies_all()
        self.current_indices = {'radio': 0, 'tv': 0}

    def _ensure_frequencies_all(self):
        for mode in self.favorites:
            self._ensure_frequencies(mode)

    def _ensure_frequencies(self, mode):
        import random
        fav_list = self.favorites[mode]
        used_freqs = set(s.get('frequency') for s in fav_list if s.get('frequency'))
        
        for station in fav_list:
            if 'frequency' not in station:
                # Assign unique freq with spacing
                for _ in range(50):
                     cand_freq = round(random.uniform(87.5, 108.0), 1)
                     
                     collision = False
                     for f in used_freqs:
                         if abs(f - cand_freq) < 0.4:
                             collision = True
                             break
                             
                     if not collision:
                         used_freqs.add(cand_freq)
                         station['frequency'] = cand_freq
                         break
                if 'frequency' not in station:
                     station['frequency'] = round(random.uniform(87.5, 108.0), 1)
        
        # Save back to ensure persistence
        self.save_favorites()

    def add_favorite(self, station, mode='radio'):
        """
        Adds a station to favorites if not already present.
        Station must be a dict with at least 'url_resolved' and 'name'.
        """
        if not station or 'url_resolved' not in station:
            return False
            
        target_list = self.favorites.get(mode)
        if target_list is None: return False
        
        # Check for duplicates based on URL
        for fav in target_list:
            if fav['url_resolved'] == station['url_resolved']:
                return False
        
        target_list.append(station)
        self._ensure_frequencies(mode) # Ensure freq assigned immediately
        self.save_favorites()
        return True

    def save_favorites(self):
        self.config_manager.save_json("favorites.json", self.favorites)

    def remove_favorite(self, station, mode='radio'):
        target_list = self.favorites.get(mode)
        if target_list is None: return False

        # Remove by URL or Name
        initial_len = len(target_list)
        self.favorites[mode] = [s for s in target_list if s.get('url_resolved') != station.get('url_resolved')]
        
        if len(self.favorites[mode]) < initial_len:
            self.save_favorites()
            return True
        return False

    def get_favorites(self, mode='radio'):
        return self.favorites.get(mode, [])

