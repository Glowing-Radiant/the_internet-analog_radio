from .config_manager import ConfigManager
import random

class FavoritesManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.favorites = self.config_manager.load_json("favorites.json", default=[])
        self._ensure_frequencies()
        self.current_index = 0

    def _ensure_frequencies(self):
        import random
        used_freqs = set(s.get('frequency') for s in self.favorites if s.get('frequency'))
        
        for station in self.favorites:
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

    def add_favorite(self, station):
        """
        Adds a station to favorites if not already present.
        Station must be a dict with at least 'url_resolved' and 'name'.
        """
        if not station or 'url_resolved' not in station:
            return False
        
        # Check for duplicates based on URL
        for fav in self.favorites:
            if fav['url_resolved'] == station['url_resolved']:
                return False
        
        self.favorites.append(station)
        self.save_favorites()
        return True

    def save_favorites(self):
        self.config_manager.save_json("favorites.json", self.favorites)

    def remove_favorite(self, station):
        # Remove by URL or Name
        initial_len = len(self.favorites)
        self.favorites = [s for s in self.favorites if s.get('url_resolved') != station.get('url_resolved')]
        
        if len(self.favorites) < initial_len:
            self.save_favorites()
            return True
        return False

    def get_favorites(self):
        return self.favorites

    def next_favorite(self):
        if not self.favorites:
            return None
        self.current_index = (self.current_index + 1) % len(self.favorites)
        return self.favorites[self.current_index]

    def previous_favorite(self):
        if not self.favorites:
            return None
        self.current_index = (self.current_index - 1) % len(self.favorites)
        return self.favorites[self.current_index]
    
    def get_current_favorite(self):
        if not self.favorites:
            return None
        if self.current_index >= len(self.favorites):
            self.current_index = 0
        return self.favorites[self.current_index]
