import pygame
import math
import os
from core.modes import MODE_ANALOG_RADIO, MODE_DIGITAL_RADIO, MODE_TV, mode_label, normalize_mode

class PygameRenderer:
    def __init__(self, width=800, height=450): # Increased height slightly for tagline
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("The Internet Analog Radio")
        
        # Load Icon
        try:
            icon_path = os.path.join("assets", "icon.png")
            if os.path.exists(icon_path):
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Failed to load icon: {e}")

        self.font_large = pygame.font.SysFont("Arial", 36)
        self.font_medium = pygame.font.SysFont("Arial", 24)
        self.font_small = pygame.font.SysFont("Arial", 16)
        self.font_tagline = pygame.font.SysFont("Arial", 14, italic=True)
        
        self.colors = {
            'bg': (20, 20, 20),
            'text_main': (200, 200, 200),
            'text_dim': (100, 100, 100),
            'accent': (255, 165, 0),  # Orange
            'panel_bg': (30, 30, 30)
        }

    def render(self, state):
        self.screen.fill(self.colors['bg'])
        
        # Mode Logic
        mode = normalize_mode(state.get('mode', MODE_DIGITAL_RADIO))
        if mode == MODE_TV:
            self.colors['accent'] = (0, 200, 255) # Cyan for TV
        elif mode == MODE_ANALOG_RADIO:
            self.colors['accent'] = (120, 220, 120) # Green for live SDR
        else:
            self.colors['accent'] = (255, 165, 0) # Orange for Radio
            
        # Draw Header
        self._draw_text("The Internet Analog Radio", self.font_large, self.colors['accent'], (20, 20))
        if mode == MODE_DIGITAL_RADIO:
            tagline = "Internet stations with classic dial tuning"
        elif mode == MODE_ANALOG_RADIO:
            tagline = "Live shortwave through KiwiSDR receivers"
        else:
            tagline = "Broadcast Television (Audio Only)"
        self._draw_text(tagline, self.font_tagline, self.colors['text_dim'], (20, 60))
        
        # Draw Mode Indicator
        self._draw_text(f"MODE: {mode_label(mode).upper()}", self.font_small, self.colors['accent'], (610, 20))
        
        # Draw Main Display (Adjusted Y position)
        self._draw_main_display(state)
        
        # Draw Panel Indicator
        self._draw_panel_indicator(state)
        
        # Draw Volume
        self._draw_volume(state)
        
        # Draw Dial (Visual flair) - Only for frequency modes
        if mode in (MODE_DIGITAL_RADIO, MODE_ANALOG_RADIO):
            self._draw_dial(state)

        # NEW: Draw Feature Status Bar
        self._draw_feature_status(state)

        # Draw transient UI message if present
        if state.get('ui_message'):
            self._draw_ui_message(state['ui_message'])

        # Draw Input Modal if active
        if state.get('input_mode'):
            self._draw_input_modal(state['input_mode'], state.get('input_text', ''))

        # Settings is a true modal and must stay on top.
        if state.get('settings_open'):
            self._draw_settings_panel(state)

        pygame.display.flip()

    def _draw_input_modal(self, mode, text):
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Modal Box
        box_width, box_height = 600, 150
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2
        
        pygame.draw.rect(self.screen, self.colors['panel_bg'], (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, self.colors['accent'], (box_x, box_y, box_width, box_height), 2)
        
        # Title
        if mode == 'search':
            title = "SEARCH STATION"
        elif mode == 'url':
            title = "ENTER STREAM URL"
        elif mode == 'timer':
            title = "SET SLEEP TIMER (MINUTES)"
        else:
            title = "INPUT"
            
        self._draw_text(title, self.font_medium, self.colors['accent'], (box_x + 20, box_y + 20))
        
        # Input Text
        self._draw_text(text + "_", self.font_medium, self.colors['text_main'], (box_x + 20, box_y + 70))
        
        # Hint
        hint = "Press ENTER to submit, ESC to cancel"
        self._draw_text(hint, self.font_small, self.colors['text_dim'], (box_x + 20, box_y + 110))

    def _draw_text(self, text, font, color, pos):
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def _draw_main_display(self, state):
        station = state.get('current_station')
        mode = normalize_mode(state.get('mode', MODE_DIGITAL_RADIO))
        
        # Shifted down slightly to accommodate tagline
        y_offset = 30 
        
        if mode == MODE_DIGITAL_RADIO:
            frequency = state.get('frequency', 88.0)
            main_text = f"{frequency:.1f} MHz"
        elif mode == MODE_ANALOG_RADIO:
            frequency = state.get('frequency', 10000.0)
            main_text = f"{frequency:.0f} kHz"
        elif mode == MODE_TV:
            # TV Mode
            idx = state.get('channel_index', 1)
            total = state.get('total_channels', 0)
            if total > 0:
                main_text = f"CH {idx} / {total}"
            else:
                 main_text = "Scanning..."
        else:
            idx = state.get('channel_index', 1)
            total = state.get('total_channels', 0)
            if total > 0:
                main_text = f"CH {idx} / {total}"
            else:
                main_text = "Scanning..."
        
        self._draw_text(main_text, self.font_large, self.colors['accent'], (50, 60 + y_offset))
        
        if station:
            name = station.get('name', 'Unknown Station')
            country = station.get('country', 'Unknown Region')
            if station.get('source') == 'kiwi':
                detail = f"{station.get('kiwi_mode', 'am').upper()} | {station.get('kiwi_frequency_khz', '?')} kHz"
            else:
                detail = str(station.get('bitrate', '?')) + " kbps"
            
            self._draw_text(name, self.font_medium, self.colors['text_main'], (50, 110 + y_offset))
            self._draw_text(f"{country} | {detail}", self.font_small, self.colors['text_dim'], (50, 150 + y_offset))
        else:
            if mode in (MODE_DIGITAL_RADIO, MODE_ANALOG_RADIO):
                self._draw_text("Static...", self.font_medium, self.colors['text_dim'], (50, 110 + y_offset))
            else:
                 self._draw_text("No Signal / Loading...", self.font_medium, self.colors['text_dim'], (50, 110 + y_offset))

    def _draw_panel_indicator(self, state):
        panel = state.get('active_panel', 'explore')
        text = f"BAND: {panel.upper()}"
        self._draw_text(text, self.font_small, self.colors['accent'], (50, 370)) # Adjusted Y

    def _draw_volume(self, state):
        volume = state.get('volume', 0.5)
        is_muted = state.get('is_muted', False)
        
        if is_muted or volume == 0:
            vol_str = "VOL: MUTED"
            color = (255, 50, 50) # Red for muted
        else:
            vol_str = f"VOL: {int(volume * 100)}%"
            color = self.colors['text_main']
            
        self._draw_text(vol_str, self.font_small, color, (650, 370))  # Adjusted Y

    def _draw_dial(self, state):
        # Visual representation of a dial
        center = (600, 220) # Adjusted Y
        radius = 80
        pygame.draw.circle(self.screen, self.colors['panel_bg'], center, radius)
        pygame.draw.circle(self.screen, self.colors['text_dim'], center, radius, 2)
        
        # Calculate angle based on frequency
        freq = state.get('frequency', 88.0)
        mode = normalize_mode(state.get('mode', MODE_DIGITAL_RADIO))
        if mode == MODE_ANALOG_RADIO:
            min_freq = 10.0
            max_freq = 30000.0
        else:
            min_freq = 87.5
            max_freq = 108.0
        
        pct = (freq - min_freq) / (max_freq - min_freq)
        pct = max(0.0, min(1.0, pct))
        
        # Radians
        start_angle = -0.75 * math.pi # -135 deg
        total_angle = 1.5 * math.pi   # 270 deg range
        angle = start_angle + (pct * total_angle)
        
        # Draw ticks
        for i in range(11):
            t_pct = i / 10.0
            t_angle = start_angle + (t_pct * total_angle)
            t_start = (center[0] + radius * 0.7 * math.cos(t_angle), center[1] + radius * 0.7 * math.sin(t_angle))
            t_end = (center[0] + radius * 0.9 * math.cos(t_angle), center[1] + radius * 0.9 * math.sin(t_angle))
            pygame.draw.line(self.screen, self.colors['text_dim'], t_start, t_end, 1)

        end_pos = (center[0] + radius * 0.8 * math.cos(angle), center[1] + radius * 0.8 * math.sin(angle))
        pygame.draw.line(self.screen, self.colors['accent'], center, end_pos, 3)
        pygame.draw.circle(self.screen, self.colors['accent'], center, 5)
    
    def _draw_feature_status(self, state):
        """Draw status bar for new features at the bottom of the screen."""
        y_pos = self.height - 50
        status_items = []
        
        # Sleep timer
        if state.get('timer_active'):
            timer_text = state.get('timer_remaining', 'Timer Active')
            status_items.append(f"⏱ {timer_text}")
        
        # Equalizer
        if state.get('equalizer_enabled'):
            preset_name = state.get('equalizer_preset', 'EQ')
            status_items.append(f"♪ EQ: {preset_name}")
        
        # Draw status items
        if status_items:
            status_text = " | ".join(status_items)
            # Draw background bar
            bar_height = 40
            pygame.draw.rect(self.screen, self.colors['panel_bg'], 
                           (0, y_pos - 10, self.width, bar_height))
            # Draw text
            self._draw_text(status_text, self.font_small, self.colors['accent'], 
                          (20, y_pos))

    def _draw_ui_message(self, text):
        # Simple toast at bottom center
        pad_x = 16
        pad_y = 8
        surface = self.font_small.render(text, True, self.colors['text_main'])
        text_w, text_h = surface.get_size()
        box_w = text_w + (pad_x * 2)
        box_h = text_h + (pad_y * 2)
        box_x = (self.width - box_w) // 2
        box_y = self.height - box_h - 8
        
        pygame.draw.rect(self.screen, self.colors['panel_bg'], (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, self.colors['accent'], (box_x, box_y, box_w, box_h), 1)
        self.screen.blit(surface, (box_x + pad_x, box_y + pad_y))

    def _draw_settings_panel(self, state):
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        box_width, box_height = 520, 320
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2

        pygame.draw.rect(self.screen, self.colors['panel_bg'], (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, self.colors['accent'], (box_x, box_y, box_width, box_height), 2)

        self._draw_text("SETTINGS", self.font_medium, self.colors['accent'], (box_x + 20, box_y + 16))

        items = state.get('settings_items', [])
        cursor = state.get('settings_cursor', 0)

        row_y = box_y + 56
        for i, item in enumerate(items):
            label = item.get('label', '')
            value = item.get('value', '')
            color = self.colors['text_main']
            if i == cursor:
                pygame.draw.rect(self.screen, (55, 55, 55), (box_x + 14, row_y - 3, box_width - 28, 28))
                color = self.colors['accent']
            self._draw_text(label, self.font_small, color, (box_x + 24, row_y))
            self._draw_text(value, self.font_small, color, (box_x + box_width - 120, row_y))
            row_y += 32

        hint = "UP/DOWN select  LEFT/RIGHT/ENTER change  O/ESC close"
        self._draw_text(hint, self.font_small, self.colors['text_dim'], (box_x + 20, box_y + box_height - 28))
