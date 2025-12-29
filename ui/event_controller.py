import pygame
import sys
import os
import random
from core.static_generator import StaticGenerator
import threading

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
        # Widen bandwidth to 0.8 MHz (radius) for smoother fading
        # This gives a zero-crossing at +/- 0.8
        self.tuning_bandwidth = 0.8
        self.static_generator = StaticGenerator()
        
        self.user_volume = 0.5 
        
        self.is_muted = False
        self.input_mode = None # 'search' or 'url'
        self.input_text = ""
        self.last_search_query = ""
        
        self.running = True

        # Mode: 'radio' or 'tv'
        self.mode = 'radio'
        
        # Cache for closest station to avoid recalculating every frame
        self._cached_closest = None
        self._cached_freq = None
        self._cached_band_idx = None

        self._cached_band_idx = None
        
        self.last_scan_time = 0

        # Play Intro Sound - Moved to main.py
        self._play_intro()

    def _play_intro(self):
        # Intro played in main.py
        # Just start static at 0 volume so it's ready
        self.static_generator.play()
        self.static_generator.set_volume(0.0)

    def run(self):
        clock = pygame.time.Clock()
        
    def run(self):
        clock = pygame.time.Clock()
        
        while self.running:
            try:
                self._handle_events()
                if not self.input_mode:
                    self._handle_continuous_input()
                
                self._update_audio_mixing()
                self.stream_player.update()
                self._render()
                clock.tick(30)
            except Exception as e:
                # print(f"Error in Event Loop: {e}") 
                # import traceback
                # traceback.print_exc()
                # Do not wait, just continue to keep UI responsive
                # Maybe print only once per second?
                pass

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.input_mode:
                    self._handle_input(event)
                else:
                    self._handle_keydown(event)
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

    def _handle_keydown(self, event):
        key = event.key
        mods = event.mod
        
        if key == pygame.K_q:
            self.running = False
        elif key == pygame.K_TAB:
            # Check for Ctrl+Tab for Mode Switch
            if mods & pygame.KMOD_CTRL:
                self._toggle_mode()
            else:
                direction = -1 if (mods & pygame.KMOD_SHIFT) else 1
                self._cycle_band(direction)
        elif key == pygame.K_RIGHT and (mods & pygame.KMOD_CTRL):
            # Scan Forward (Discrete)
            self._scan_station(1)
        elif key == pygame.K_LEFT and (mods & pygame.KMOD_CTRL):
            # Scan Backward (Discrete)
            self._scan_station(-1)
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
        elif key == pygame.K_w:
            # Now Playing
            meta = self.stream_player.get_now_playing()
            print(f"Now Playing: {meta}")
            if self.accessibility_manager:
                self.accessibility_manager.speak(f"Now Playing: {meta}")
        elif key == pygame.K_c:
            # Copy URL
            closest_station, _ = self._get_closest_station()
            if closest_station:
                url = closest_station.get('url_resolved', '')
                if url:
                    try:
                        import tkinter
                        r = tkinter.Tk()
                        r.withdraw()
                        r.clipboard_clear()
                        r.clipboard_append(url)
                        r.update() # Enable clipboard update
                        r.destroy()
                        print(f"Copied to clipboard: {url}")
                        if self.accessibility_manager:
                            self.accessibility_manager.speak("URL Copied")
                    except Exception as e:
                        print(f"Clipboard error: {e}")
                        if self.accessibility_manager:
                            self.accessibility_manager.speak("Copy Failed")

    def _submit_search(self):
        print(f"Searching for: {self.input_text}")
        if self.accessibility_manager:
            self.accessibility_manager.speak(f"Searching for {self.input_text}")
        
        self.last_search_query = self.input_text
        query = self.input_text

        def search_thread():
            self.station_manager.search_stations(query)
            
            # Post-search checks
            stations = self.station_manager.get_station_list('exploratory')
            if not stations:
                 print("Nothing found.")
                 if self.accessibility_manager:
                     self.accessibility_manager.speak("Nothing found")
                 return

            # Switch to exploratory band
            if 'exploratory' in self.bands:
                self.current_band_index = self.bands.index('exploratory')
                self.band_indices['exploratory'] = 0
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Exploratory Band")
        
        threading.Thread(target=search_thread, daemon=True).start()

    def _save_custom_band(self):
        # Only allow saving from exploratory band if it has stations
        if self.bands[self.current_band_index] == 'exploratory':
            stations = self.station_manager.get_station_list('exploratory', self.mode) # Should return from radio stations anyway
            if stations and self.last_search_query:
                name = self.last_search_query
                self.station_manager.save_custom_band(name, stations, self.mode)
                
                # Add to bands if not present
                # Note: We need to ensure self.bands reflects current mode.
                # If we are in Radio, we add to self.bands.
                # If we are in TV, can we search? Currently TV search not implemented fully, 
                # but if we add it, we want it there.
                
                if name not in self.bands:
                    self.bands.append(name)
                    self.band_indices[name] = 0
                    
                if self.accessibility_manager:
                    self.accessibility_manager.speak(f"Band {name} Saved")
                print(f"Saved custom band: {name} in {self.mode}")

    def _update_audio_mixing(self):
        # TV MODE: Direct Index Playback
        if self.mode == 'tv':
            station = self._get_current_station()
            
            # Reset Static
            self.static_generator.set_volume(0.0)
            
            if station:
                url = station.get('url_resolved')
                # Play if valid
                if url:
                    # Volume management
                    if not hasattr(self, 'user_volume'): self.user_volume = 0.5
                    
                    final_vol = self.user_volume
                    if self.is_muted: final_vol = 0.0
                    
                    self.stream_player.play(url)
                    self.stream_player.set_volume(final_vol)
                    
                    # Announce if new
                    if final_vol > 0:
                         if self.accessibility_manager:
                             name = station.get('name')
                             if getattr(self, '_last_spoken_station', None) != name:
                                 self.accessibility_manager.speak(name)
                                 self._last_spoken_station = name
            else:
                self.stream_player.stop()
            return

        # RADIO MODE: Frequency Logic
        # 1. Get Closest Station
        closest_station, distance = self._get_closest_station()
        
        # 2. Calculate Volumes
        station_vol = 0.0
        static_vol = 1.0
        
        # systematic static logic:
        # < 0.1: Locked (Clear Signal)
        # 0.1 - 0.4: Fading
        # > 0.4: Lost (Static)
        
        band_width = self.tuning_bandwidth # 0.4
        current_station_url = None
        
        if closest_station and distance < band_width:
            current_station_url = closest_station.get('url_resolved')
            
            if distance < 0.1:
                # LOCKED - Perfect Signal
                station_vol = 1.0
                static_vol = 0.0
                
            elif distance < band_width:
                # FADING - Linear Crossfade
                # Normalize distance from 0.1 to band_width -> 0.0 to 1.0
                # 0.1 maps to 0.0 (full vol)
                # band_width maps to 1.0 (no vol)
                fade_range = band_width - 0.1
                if fade_range <= 0: fade_range = 0.1 # Safety
                
                norm = (distance - 0.1) / fade_range
                station_vol = 1.0 - norm
                static_vol = norm
            
            else:
                # Should not happen given outer if, but safety
                station_vol = 0.0
                static_vol = 1.0

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
            # Only play if URL is valid and volume is audible
            if current_station_url and final_station_vol > 0:
                self.stream_player.play(current_station_url)
                self.stream_player.set_volume(final_station_vol)
            else:
                 if current_station_url:
                     self.stream_player.play(current_station_url)
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
        # Check cache
        if (self._cached_closest and 
            self._cached_freq == self.current_frequency and 
            self._cached_band_idx == self.current_band_index):
            return self._cached_closest

        stations = self._get_current_station_list()
        if not stations: return None, 999.0
        
        closest = None
        min_dist = 999.0
        
        # Hysteresis: Favor the last played station slightly to prevent flip-flopping
        last_url = self.stream_player.current_url
        
        for s in stations:
            freq = s.get('frequency')
            if freq is None: continue
            
            dist = abs(freq - self.current_frequency)
            
            # Hysteresis bonus
            if last_url and s.get('url_resolved') == last_url:
                 dist -= 0.001 
                 
            if dist < min_dist:
                min_dist = dist
                closest = s
                
        # Update cache
        self._cached_closest = (closest, min_dist)
        self._cached_freq = self.current_frequency
        self._cached_band_idx = self.current_band_index
        
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
            if self.favorites_manager.add_favorite(station, self.mode):
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Added to favorites")
                # Switch to favorites
                if 'favorites' in self.bands:
                    self.current_band_index = self.bands.index('favorites')
                    # Set index to the last item (newly added)
                    favs = self.favorites_manager.get_favorites(self.mode)
                    self.band_indices['favorites'] = len(favs) - 1
                    self._play_current_station()

    def _handle_continuous_input(self):
        keys = pygame.key.get_pressed()
        
        # Initialize user volume if not present
        # Initialize user volume if not present
        if not hasattr(self, 'user_volume'):
            self.user_volume = 0.5
            
        current_time = pygame.time.get_ticks()
        if not hasattr(self, '_vol_update_time'):
             self._vol_update_time = 0
             
        if current_time - self._vol_update_time > 50: # Update every 50ms
            if keys[pygame.K_UP]:
                self.user_volume = min(1.0, self.user_volume + 0.02) # slightly larger step, slower rate
                self._vol_update_time = current_time
                # print(f"Vol Up: {self.user_volume:.2f}") 
            if keys[pygame.K_DOWN]:
                self.user_volume = max(0.0, self.user_volume - 0.02)
                self._vol_update_time = current_time
                # print(f"Vol Down: {self.user_volume:.2f}")
            
        if not hasattr(self, '_tuning_delay'):
            self._tuning_delay = 0
            
        # Define tuning speed/delay
        # Radio: 0.1 MHz step
        # TV: 1 Channel step
        
        if self.mode == 'tv':
             # TV NAVIGATION
             REPEAT_DELAY = 8 # Slightly slower for channel surfing
             
             if keys[pygame.K_RIGHT]:
                 if self._tuning_delay == 0:
                     self._change_station(1)
                     self._tuning_delay = REPEAT_DELAY
                 else:
                     self._tuning_delay -= 1
             elif keys[pygame.K_LEFT]:
                 if self._tuning_delay == 0:
                     self._change_station(-1)
                     self._tuning_delay = REPEAT_DELAY
                 else:
                     self._tuning_delay -= 1
             else:
                 self._tuning_delay = 0

        else:
            # RADIO NAVIGATION (Frequency)
            tuning_speed = 0.1 
            current_time = pygame.time.get_ticks()

            if not hasattr(self, '_tuning_next_time'):
                 self._tuning_next_time = 0
            
            is_turning = False
            
            if keys[pygame.K_RIGHT]:
                 if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                     is_turning = True
                     if hasattr(self, '_tuning_key') and self._tuning_key == 'RIGHT':
                         # Continued Press
                         if current_time >= self._tuning_next_time:
                             self.current_frequency += tuning_speed
                             self.current_frequency = round(self.current_frequency, 1)
                             self._tuning_next_time = current_time + 100 # Repeat every 100ms
                             # Wrap
                             if self.current_frequency > 108.0: self.current_frequency = 87.5
                     else:
                         # New Press (Tap)
                         self._tuning_key = 'RIGHT'
                         self.current_frequency += tuning_speed
                         self.current_frequency = round(self.current_frequency, 1)
                         self._tuning_next_time = current_time + 500 # Initial delay 500ms
                         if self.current_frequency > 108.0: self.current_frequency = 87.5
            
            elif keys[pygame.K_LEFT]:
                 if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                     is_turning = True
                     if hasattr(self, '_tuning_key') and self._tuning_key == 'LEFT':
                         # Continued
                         if current_time >= self._tuning_next_time:
                             self.current_frequency -= tuning_speed
                             self.current_frequency = round(self.current_frequency, 1)
                             self._tuning_next_time = current_time + 100
                             if self.current_frequency < 87.5: self.current_frequency = 108.0
                     else:
                         # New
                         self._tuning_key = 'LEFT'
                         self.current_frequency -= tuning_speed
                         self.current_frequency = round(self.current_frequency, 1)
                         self._tuning_next_time = current_time + 500
                         if self.current_frequency < 87.5: self.current_frequency = 108.0
            
            if not is_turning:
                # Reset state
                if hasattr(self, '_tuning_key'):
                    del self._tuning_key

    def _scan_station(self, direction):
        # Debounce to prevent rapid skipping
        current_time = pygame.time.get_ticks()
        if current_time - self.last_scan_time < 300: # 300ms cooldown
             return
        self.last_scan_time = current_time

        # Jump to next closest station freq in direction
        stations = self._get_current_station_list()
        if not stations: return
        
        # Collect all freqs
        freqs = sorted([s.get('frequency', 0) for s in stations if s.get('frequency')])
        if not freqs: return
        
        # Find position
        target = None
        
        # Use smaller epsilon (0.05) to catch 88.1 if at 88.0
        epsilon = 0.05
        
        if direction > 0:
            for f in freqs:
                if f > self.current_frequency + epsilon: 
                    target = f
                    break
            if target is None: target = freqs[0] # Wrap
        else:
            for f in reversed(freqs):
                if f < self.current_frequency - epsilon:
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
            return self.favorites_manager.get_favorites(self.mode)
        return self.station_manager.get_station_list(band, self.mode)

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
            if self.favorites_manager.add_favorite(station, self.mode):
                print(f"Added to favorites ({self.mode}): {station.get('name')}")
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Added to favorites")
            else:
                 if self.accessibility_manager:
                    self.accessibility_manager.speak("Already in favorites")

    def _remove_favorite(self):
        # 1. Identify valid station to remove via frequency (not index)
        station, dist = self._get_closest_station()
        
        # Ensure we are in favorites band and locked on signal
        if self.bands[self.current_band_index] != 'favorites':
            return
            
        if not station or dist > self.tuning_bandwidth:
            if self.accessibility_manager:
                self.accessibility_manager.speak("No station selected")
            return

        # 2. Calculate "Left" station frequency BEFORE removal
        current_freq = station.get('frequency', 0)
        target_freq = current_freq # Default to current (will be static after removal)
        
        # Get all favorites sorted by frequency
        favs = self.favorites_manager.get_favorites(self.mode)
        sorted_favs = sorted(favs, key=lambda s: s.get('frequency', 0))
        
        # Find current index in this sorted list
        # We match by URL or Name to be safe, frequency should handle it though
        found_idx = -1
        for i, s in enumerate(sorted_favs):
            if s.get('url_resolved') == station.get('url_resolved'):
                found_idx = i
                break
        
        if found_idx != -1:
            # Logic: Focus user position to either static left of it, or the left radio station
            # "Left radio station" = index - 1
            if found_idx > 0:
                target_freq = sorted_favs[found_idx - 1].get('frequency', 88.0)
            elif len(sorted_favs) > 1:
                # If we are removing the first one, maybe go to 87.5 or stay?
                # "static left of it" - imply just go down a bit? 
                # Let's go to the next available one if we are at 0? 
                # Request said: "or the left radio station of it".
                # If there's no left station, maybe just static immediately to the left?
                # Let's just create a gap.
                target_freq = max(87.5, current_freq - 0.5)
            else:
                 # Removing the last valid station
                 target_freq = current_freq # Becomes static
        
        # 3. Perform Removal
        if self.favorites_manager.remove_favorite(station, self.mode):
            print(f"Removed from favorites: {station.get('name')}")
            
            # 4. Tune to target
            self.current_frequency = target_freq
            
            # Determine reaction
            if self.accessibility_manager:
                self.accessibility_manager.speak("Removed")
            
            # Force update to stop playing removed station immediately
            self._update_audio_mixing()
            
        else:
             if self.accessibility_manager:
                self.accessibility_manager.speak("Could not remove")

    def _toggle_mode(self):
        self.mode = 'tv' if self.mode == 'radio' else 'radio'
        print(f"Switched to Mode: {self.mode.upper()}")
        
        if self.accessibility_manager:
            self.accessibility_manager.speak(f"{self.mode} mode")
            
        # Lazy load TV data
        if self.mode == 'tv':
            # Check if we have stations, if not, fetch (threaded)
            # Just trigger fetch generally
            if not self.station_manager.tv_stations['national']:
                print("First time TV init: Fetching stations...")
                if self.accessibility_manager:
                    self.accessibility_manager.speak("Fetching T V channels")
                    
                def fetch_tv():
                    # Use StationManager's auto detection or fallback
                    self.station_manager.fetch_tv_all() 
                    
                threading.Thread(target=fetch_tv, daemon=True).start()
                
        # Rebuild Bands for the new Mode
        standard_bands = ['local', 'national', 'international', 'favorites', 'exploratory']
        
        # Get custom bands for this mode
        custom = self.station_manager.custom_bands.get(self.mode, {})
        
        self.bands = standard_bands + list(custom.keys())
        
        # Initialize indices for new bands if missing
        for b in self.bands:
            if b not in self.band_indices:
                self.band_indices[b] = 0

        # Reset band index to National (1) or 0
        self.current_band_index = 1 
        if self.current_band_index >= len(self.bands):
             self.current_band_index = 0 
        
    def _render(self):
        # Get channel info
        stations = self._get_current_station_list()
        total_channels = len(stations) if stations else 0
        band = self.bands[self.current_band_index]
        channel_index = self.band_indices.get(band, 0) + 1 # 1-based index
        
        state = {
            'mode': self.mode,
            'current_station': self._get_current_station()[0] if self.mode == 'radio' else self._get_current_station(), # TV uses _get_current_station directly which returns the station object
            'frequency': self.current_frequency,
            'volume': getattr(self, 'user_volume', 0.5), # Show user volume
            'active_panel': self.bands[self.current_band_index],
            'is_muted': self.is_muted, 
            'input_mode': self.input_mode,
            'input_text': self.input_text,
            'channel_index': channel_index,
            'total_channels': total_channels
        }
        
        # fix: _get_closest_station returns (station, dist)
        # _get_current_station returns (station)
        if self.mode == 'radio':
             state['current_station'] = self._get_closest_station()[0]
        else:
             state['current_station'] = self._get_current_station()

        self.renderer.render(state)
