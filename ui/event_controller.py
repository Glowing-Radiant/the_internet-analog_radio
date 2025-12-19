import pygame
import sys
import os
import random
from core.static_generator import StaticGenerator


class EventController:
    def __init__(self, station_manager, favorites_manager, stream_player, renderer, accessibility_manager=None):
        self.station_manager = station_manager
        self.favorites_manager = favorites_manager
        self.stream_player = stream_player
        self.renderer = renderer
        self.accessibility_manager = accessibility_manager
        
        self.bands = ['local', 'national', 'international', 'favorites', 'exploratory']
        # Append custom bands
        self.bands.extend(self.station_manager.custom_bands.keys())
        
        self.current_band_index = 1 # Default to National
        self.band_indices = {b: 0 for b in self.bands}
        
        self.current_frequency = 88.0
        self.current_frequency = 88.0
        # Widen bandwidth to 0.4 MHz (radius)
        # This gives a zero-crossing at +/- 0.4
        # At +/- 0.2 (2 steps away), signal is 0.5 (50/50 mix) -- Desired Edge
        # Total "hearing" width is 0.8, but "good" range is ~0.5
        self.tuning_bandwidth = 0.4 
        self.static_generator = StaticGenerator()
        self.static_generator = StaticGenerator()
        
        self.is_muted = False
        self.input_mode = None # 'search' or 'url'
        self.input_text = ""
        self.last_search_query = ""
        
        self.running = True

        # Play Intro Sound - Moved to main.py
        self._play_intro()

    def _play_intro(self):
        # Intro played in main.py
        # Just start static at 0 volume so it's ready
        self.static_generator.play()
        self.static_generator.set_volume(0.0)

    def run(self):
        clock = pygame.time.Clock()
        
        # Initial play handled by storage/scanning loop
        # self._play_current_station()

        while self.running:
            self._handle_events()
            if not self.input_mode:
                self._handle_continuous_input()
            
            self._update_audio_mixing()
            self.stream_player.update()
            self._render()
            clock.tick(30)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.input_mode:
                    self._handle_input(event)
                else:
                    self._handle_keydown(event.key)
            elif event.type == pygame.TEXTINPUT and self.input_mode:
                self.input_text += event.text
                if self.accessibility_manager:
                    self.accessibility_manager.speak(event.text)

    def _handle_input(self, event):
        if event.key == pygame.K_RETURN:
            if self.input_mode == 'search':
                self._submit_search()
            elif self.input_mode == 'url':
                self._submit_url()
            self.input_mode = None
            self.input_text = ""
        elif event.key == pygame.K_ESCAPE:
            self.input_mode = None
            self.input_text = ""
            if self.accessibility_manager:
                self.accessibility_manager.speak("Cancelled")
        elif event.key == pygame.K_BACKSPACE:
            if self.input_text:
                deleted = self.input_text[-1]
                self.input_text = self.input_text[:-1]
                if self.accessibility_manager:
                    self.accessibility_manager.speak(f"Deleted {deleted}")
        elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
            # Paste support
            try:
                import tkinter
                text = tkinter.Tk().clipboard_get()
                self.input_text += text
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Pasted")
            except Exception:
                pass

    def _handle_keydown(self, key):
        if key == pygame.K_q:
            self.running = False
        elif key == pygame.K_TAB:
            mods = pygame.key.get_mods()
            direction = -1 if (mods & pygame.KMOD_SHIFT) else 1
            self._cycle_band(direction)
        elif key == pygame.K_m:
            self._toggle_mute()
        elif key == pygame.K_PLUS or key == pygame.K_EQUALS:
            self._add_favorite()
        elif key == pygame.K_MINUS:
            self._remove_favorite()
        elif key == pygame.K_b:
            self._save_custom_band()
        elif key == pygame.K_s:
            # Clear buffer before entering mode to prevent ghosting
            pygame.event.clear() 
            self.input_mode = 'search'
            self.input_text = ""
            if self.accessibility_manager:
                self.accessibility_manager.speak("Search Station")
        elif key == pygame.K_f:
            pygame.event.clear()
            self.input_mode = 'url'
            self.input_text = ""
            if self.accessibility_manager:
                self.accessibility_manager.speak("Enter Stream URL")

    def _submit_search(self):
        print(f"Searching for: {self.input_text}")
        if self.accessibility_manager:
            self.accessibility_manager.speak(f"Searching for {self.input_text}")
        
        self.last_search_query = self.input_text
        self.station_manager.search_stations(self.input_text)
        
        # Check if results found
        if not self.station_manager.get_station_list('exploratory'):
             print("Nothing found.")
             if self.accessibility_manager:
                 self.accessibility_manager.speak("Nothing found")
             return

        # Switch to exploratory band
        if 'exploratory' in self.bands:
            self.current_band_index = self.bands.index('exploratory')
            self.band_indices['exploratory'] = 0
            self._play_current_station()
            if self.accessibility_manager:
                self.accessibility_manager.speak("Exploratory Band")

    def _save_custom_band(self):
        # Only allow saving from exploratory band if it has stations
        if self.bands[self.current_band_index] == 'exploratory':
            stations = self.station_manager.get_station_list('exploratory')
            if stations and self.last_search_query:
                name = self.last_search_query
                self.station_manager.save_custom_band(name, stations)
                
                if name not in self.bands:
                    self.bands.append(name)
                    self.band_indices[name] = 0
                    
                if self.accessibility_manager:
                    self.accessibility_manager.speak(f"Band {name} Saved")
                print(f"Saved custom band: {name}")

    def _update_audio_mixing(self):
        # 1. Get Closest Station
        closest_station, distance = self._get_closest_station()
        
        # 2. Calculate Volumes
        station_vol = 0.0
        static_vol = 1.0
        
        # Update Drift Logic (Global now)
        if not hasattr(self, '_last_freq'): self._last_freq = self.current_frequency
        if not hasattr(self, '_drift_level'): self._drift_level = 0.0
        
        if abs(self.current_frequency - self._last_freq) > 0.01:
            self._drift_level = 0.0
            self._last_freq = self.current_frequency
        else:
             if distance < 0.05:
                if random.random() < 0.01:
                     self._drift_level = min(0.3, self._drift_level + 0.05)

        band_width = self.tuning_bandwidth # 0.4
        
        if closest_station and distance < band_width:
            url = closest_station.get('url_resolved')
            
            # ZONES
            if distance < 0.05:
                # CENTER
                drift_static = 0.0
                if random.random() < 0.05: drift_static = self._drift_level
                station_vol = 1.0
                static_vol = drift_static
                
            elif distance < 0.2:
                # NEAR
                station_vol = 1.0
                static_vol = 0.0
                if random.random() < 0.05:
                     static_vol = random.uniform(0.05, 0.2)
                     
            elif distance < 0.4:
                # EDGE (0.2 - 0.4)
                # Linear fade
                norm = (distance - 0.2) / 0.2
                station_vol = 1.0 - norm
                static_vol = norm
                if 0.35 < distance < 0.45:
                    static_vol = max(static_vol, 0.5)
            
            # Apply Master / Mute
            if not hasattr(self, 'user_volume'): self.user_volume = 0.5
            
            final_station_vol = station_vol * self.user_volume
            final_static_vol = static_vol * self.user_volume * 0.15
            
            if self.is_muted:
                final_station_vol = 0.0
                final_static_vol = 0.0
            
            if pygame.mixer.music.get_busy():
                 final_static_vol = 0.0

            # 3. Control Stream Player
            if url:
                self.stream_player.play(url)
                self.stream_player.set_volume(final_station_vol)

            # Announce
            if station_vol > 0.5:
                 if self.accessibility_manager:
                     name = closest_station.get('name')
                     if getattr(self, '_last_spoken_station', None) != name:
                         self.accessibility_manager.speak(name)
                         self._last_spoken_station = name
        else:
            # No station in range
            self.stream_player.stop()
            self._last_spoken_station = None
            
            # Full static if not muted/intro
            if self.is_muted or pygame.mixer.music.get_busy():
                 final_static_vol = 0.0
            else:
                 final_static_vol = 1.0 * getattr(self, 'user_volume', 0.5) * 0.15

        self.static_generator.set_volume(final_static_vol)

    def _get_closest_station(self):
        stations = self._get_current_station_list()
        if not stations: return None, 999.0
        
        closest = None
        min_dist = 999.0
        
        for s in stations:
            freq = s.get('frequency')
            if freq is None: continue
            
            dist = abs(freq - self.current_frequency)
            # Handle wrapping if we used a circular dial
            # But FM 87-108 usually hard stops. We can wrap.
            # Let's handle wrapping: distance on a circle of (108-87.5) = 20.5
            band_range = 108.0 - 87.5
            dist = min(dist, band_range - dist) # Shortest path on circle? 
            # actually circular logic might be confusing if UI is linear.
            # Let's stick to linear distance for now.
            dist = abs(freq - self.current_frequency)

            if dist < min_dist:
                min_dist = dist
                closest = s
                
        return closest, min_dist

    def _submit_url(self):
        url = self.input_text.strip()
        if url:
            print(f"Adding custom URL: {url}")
            # Create a dummy station object
            station = {
                'name': 'Custom Stream',
                'url_resolved': url,
                'country': 'Custom',
                'bitrate': 0
            }
            self.favorites_manager.add_favorite(station)
            if self.accessibility_manager:
                self.accessibility_manager.speak("Added to favorites")
            # Switch to favorites
            if 'favorites' in self.bands:
                self.current_band_index = self.bands.index('favorites')
                # Set index to the last item (newly added)
                favs = self.favorites_manager.get_favorites()
                self.band_indices['favorites'] = len(favs) - 1
                self._play_current_station()

    def _handle_continuous_input(self):
        keys = pygame.key.get_pressed()
        
        # Initialize user volume if not present
        if not hasattr(self, 'user_volume'):
            self.user_volume = 0.5

        if keys[pygame.K_UP]:
            self.user_volume = min(1.0, self.user_volume + 0.01)
            # volume update happens in mixing loop
        if keys[pygame.K_DOWN]:
            self.user_volume = max(0.0, self.user_volume - 0.01)
            
        if not hasattr(self, '_tuning_delay'):
            self._tuning_delay = 0
            
        # Define tuning speed/delay
        # We want to be able to "tap" for 0.1 step, or hold to scan slowly.
        # If we update every frame (30fps), 0.1 * 30 = 3MHz/sec. Too fast to hear static fade.
        # Let's update every 5 frames (~6 times/sec) = 0.6MHz/sec.
        # Or use a timer.
        
        REPEAT_DELAY = 5
        tuning_speed = 0.1 # 0.1 MHz step
        
        if keys[pygame.K_RIGHT]:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if self._tuning_delay == 0:
                    self._scan_station(1)
                    self._tuning_delay = 10
                else:
                    self._tuning_delay -= 1
            else:
                 if self._tuning_delay == 0:
                     self.current_frequency += tuning_speed
                     self.current_frequency = round(self.current_frequency, 1) # Keep clean
                     self._tuning_delay = REPEAT_DELAY
                 else:
                     self._tuning_delay -= 1

                 if self.current_frequency > 108.0: self.current_frequency = 87.5
        
        elif keys[pygame.K_LEFT]:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if self._tuning_delay == 0:
                    self._scan_station(-1)
                    self._tuning_delay = 10
                else:
                    self._tuning_delay -= 1
            else:
                if self._tuning_delay == 0:
                     self.current_frequency -= tuning_speed
                     self.current_frequency = round(self.current_frequency, 1) # Keep clean
                     self._tuning_delay = REPEAT_DELAY
                else:
                     self._tuning_delay -= 1

                if self.current_frequency < 87.5: self.current_frequency = 108.0
        
        else:
            # Reset delay when key released so next tap is immediate
            self._tuning_delay = 0

    def _scan_station(self, direction):
        # Jump to next closest station freq in direction
        stations = self._get_current_station_list()
        if not stations: return
        
        # Collect all freqs
        freqs = sorted([s.get('frequency', 0) for s in stations if s.get('frequency')])
        if not freqs: return
        
        # Find position
        # If we are at 90.0, and freqs are [88, 92, 95]
        # Next is 92.
        
        target = None
        
        if direction > 0:
            for f in freqs:
                if f > self.current_frequency + 0.1: # Threshold to avoid sticking
                    target = f
                    break
            if target is None: target = freqs[0] # Wrap
        else:
            for f in reversed(freqs):
                if f < self.current_frequency - 0.1:
                    target = f
                    break
            if target is None: target = freqs[-1] # Wrap
            
        self.current_frequency = target

    def _cycle_band(self, direction=1):
        self.current_band_index = (self.current_band_index + direction) % len(self.bands)
        # Skip exploratory if empty and not current
        if self.bands[self.current_band_index] == 'exploratory':
             if not self.station_manager.get_station_list('exploratory'):
                 self.current_band_index = (self.current_band_index + direction) % len(self.bands)
        
        band_name = self.bands[self.current_band_index]
        
        # Debug log
        # Use helper method to ensure we get favorites if that's the current band
        stations = self._get_current_station_list()
        print(f"Switched to band: {band_name}, Stations: {len(stations)}")
        
        if self.accessibility_manager:
            self.accessibility_manager.speak(f"{band_name}, {len(stations)} stations")
        
        # When changing bands, we might want to tune to the first station?
        # Or just keep the frequency?
        # "let the user reach that frequency manually"
        # Keeping frequency simulates real radio where bands share frequency space?
        # Actually FM is one band. 'Local', 'National' are virtual bands.
        # But if we change 'band', we change the set of available stations.
        # So we stay at 88.0, but now check checking Local stations at 88.0.
        # This is cool.
        
        # self._play_current_station() # Removed

    def _get_current_station_list(self):
        band = self.bands[self.current_band_index]
        if band == 'favorites':
            return self.favorites_manager.get_favorites()
        return self.station_manager.get_station_list(band)

    def _get_current_station(self):
        stations = self._get_current_station_list()
        if not stations: return None
        
        band = self.bands[self.current_band_index]
        idx = self.band_indices.get(band, 0)
        
        if idx >= len(stations):
            idx = 0
            self.band_indices[band] = 0
            
        return stations[idx]

    def _change_station(self, direction):
        stations = self._get_current_station_list()
        if not stations: return

        band = self.bands[self.current_band_index]
        idx = self.band_indices.get(band, 0)
        idx = (idx + direction) % len(stations)
        self.band_indices[band] = idx
        
        self._play_current_station()
        
        # Announce station name
        station = stations[idx]
        if self.accessibility_manager:
            self.accessibility_manager.speak(station.get('name', 'Unknown Station'))

    def _play_current_station(self):
        # Legacy method kept if something calls it, but updated to effectively do nothing 
        # or just force update mixing
        pass
        
        # station = self._get_current_station()
        # if station:
        #     self.stream_player.play(station['url_resolved'])
        # else:
        #     self.stream_player.stop()

    def _toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            if self.accessibility_manager:
                self.accessibility_manager.speak("Muted")
        else:
            if self.accessibility_manager:
                self.accessibility_manager.speak("Unmuted")
                
        # Force update mixing immediately
        self._update_audio_mixing()

    def _add_favorite(self):
        station = self._get_current_station()
        if station:
            self.favorites_manager.add_favorite(station)
            print(f"Added to favorites: {station.get('name')}")
            if self.accessibility_manager:
                self.accessibility_manager.speak("Added to favorites")

    def _remove_favorite(self):
        station = self._get_current_station()
        if station and self.bands[self.current_band_index] == 'favorites':
            if self.favorites_manager.remove_favorite(station):
                print(f"Removed from favorites: {station.get('name')}")
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Removed from favorites")
                # Refresh playback/index
                self._change_station(0)
            else:
                 if self.accessibility_manager:
                    self.accessibility_manager.speak("Could not remove")

    def _render(self):
        state = {
            'current_station': self._get_closest_station()[0], # Just show closest
            'frequency': self.current_frequency,
            'volume': getattr(self, 'user_volume', 0.5), # Show user volume
            'active_panel': self.bands[self.current_band_index],
            'is_muted': self.is_muted, 
            'input_mode': self.input_mode,
            'input_text': self.input_text
        }
        self.renderer.render(state)
