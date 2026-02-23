import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class HistoryManager:
    """
    Manages playback history for both radio and TV modes.
    Tracks stations with timestamps and provides replay functionality.
    """
    
    def __init__(self, config_manager, max_entries: int = 100):
        self.config_manager = config_manager
        self.max_entries = max_entries
        
        # Load history from config
        # Format: {'radio': [...], 'tv': [...]}
        # Each entry: {'station': {...}, 'timestamp': '...', 'duration': seconds}
        raw_data = self.config_manager.load_json("history.json", default={'radio': [], 'tv': [], 'twitch': [], 'soundcloud': []})
        
        # Ensure both modes exist
        if isinstance(raw_data, list):
            # Migration from old format if needed
            self.history = {'radio': raw_data, 'tv': [], 'twitch': [], 'soundcloud': []}
        else:
            self.history = raw_data
            
        if 'radio' not in self.history:
            self.history['radio'] = []
        if 'tv' not in self.history:
            self.history['tv'] = []
        if 'twitch' not in self.history:
            self.history['twitch'] = []
        if 'soundcloud' not in self.history:
            self.history['soundcloud'] = []
            
        # Track current playing station to calculate duration
        self.current_playing = {'radio': None, 'tv': None, 'twitch': None, 'soundcloud': None}
        self.current_start_time = {'radio': None, 'tv': None, 'twitch': None, 'soundcloud': None}
        
    def start_tracking(self, station: Dict, mode: str = 'radio'):
        """
        Start tracking a station. Called when playback begins.
        """
        if not station or 'url_resolved' not in station:
            return
            
        # If same station, don't restart tracking
        if self.current_playing.get(mode) == station.get('url_resolved'):
            return
            
        # Save previous station if exists
        if self.current_playing.get(mode):
            self._save_current_session(mode)
        
        # Start new session
        self.current_playing[mode] = station.get('url_resolved')
        self.current_start_time[mode] = datetime.now()
        self._current_station_data = {mode: station.copy()}
        
    def _save_current_session(self, mode: str):
        """
        Save the current playing session to history.
        """
        if not self.current_playing.get(mode) or not self.current_start_time.get(mode):
            return
            
        # Calculate duration
        duration = (datetime.now() - self.current_start_time[mode]).total_seconds()
        
        # Only save if played for at least 5 seconds
        if duration < 5:
            return
            
        # Get station data
        station_data = getattr(self, '_current_station_data', {}).get(mode)
        if not station_data:
            return
            
        # Create history entry
        entry = {
            'station': station_data,
            'timestamp': self.current_start_time[mode].isoformat(),
            'duration': int(duration)
        }
        
        # Add to history (most recent first)
        history_list = self.history[mode]
        history_list.insert(0, entry)
        
        # Remove duplicates (keep most recent)
        seen_urls = set()
        unique_history = []
        for item in history_list:
            url = item['station'].get('url_resolved')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_history.append(item)
                
        # Limit size
        self.history[mode] = unique_history[:self.max_entries]
        
        # Save to disk
        self._save_history()
        
    def stop_tracking(self, mode: str = 'radio'):
        """
        Stop tracking current station. Called when playback stops.
        """
        self._save_current_session(mode)
        self.current_playing[mode] = None
        self.current_start_time[mode] = None
        
    def get_history(self, mode: str = 'radio', limit: Optional[int] = None) -> List[Dict]:
        """
        Get history entries for a mode.
        Returns list of entries sorted by most recent first.
        """
        history = self.history.get(mode, [])
        if limit:
            return history[:limit]
        return history
        
    def get_recent_stations(self, mode: str = 'radio', limit: int = 10) -> List[Dict]:
        """
        Get just the station data from recent history.
        """
        history = self.get_history(mode, limit)
        return [entry['station'] for entry in history if 'station' in entry]
        
    def clear_history(self, mode: str = 'radio'):
        """
        Clear all history for a mode.
        """
        self.history[mode] = []
        self._save_history()
        
    def _save_history(self):
        """
        Save history to disk.
        """
        if self.config_manager:
            self.config_manager.save_json("history.json", self.history)
            
    def format_history_entry(self, entry: Dict) -> str:
        """
        Format a history entry for display.
        """
        station = entry.get('station', {})
        timestamp = entry.get('timestamp', '')
        duration = entry.get('duration', 0)
        
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = "Unknown"
            
        # Format duration
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        station_name = station.get('name', 'Unknown')
        
        return f"{station_name} - {time_str} ({duration_str})"
