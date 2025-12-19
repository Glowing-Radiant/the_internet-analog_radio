import pygame
import math
import os

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
        
        # Draw Header
        self._draw_text("The Internet Analog Radio", self.font_large, self.colors['accent'], (20, 20))
        self._draw_text("Rediscover your music the old way", self.font_tagline, self.colors['text_dim'], (20, 60))
        
        # Draw Main Display (Adjusted Y position)
        self._draw_main_display(state)
        
        # Draw Panel Indicator
        self._draw_panel_indicator(state)
        
        # Draw Volume
        self._draw_volume(state)
        
        # Draw Dial (Visual flair)
        self._draw_dial(state)

        # Draw Input Modal if active
        if state.get('input_mode'):
            self._draw_input_modal(state['input_mode'], state.get('input_text', ''))

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
        title = "SEARCH STATION" if mode == 'search' else "ENTER STREAM URL"
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
        frequency = state.get('frequency', 88.0)
        
        # Shifted down slightly to accommodate tagline
        y_offset = 30 
        
        freq_text = f"{frequency:.1f} MHz"
        self._draw_text(freq_text, self.font_large, self.colors['accent'], (50, 60 + y_offset))
        
        if station:
            name = station.get('name', 'Unknown Station')
            country = station.get('country', 'Unknown Region')
            bitrate = str(station.get('bitrate', '?')) + " kbps"
            
            self._draw_text(name, self.font_medium, self.colors['text_main'], (50, 110 + y_offset))
            self._draw_text(f"{country} | {bitrate}", self.font_small, self.colors['text_dim'], (50, 150 + y_offset))
        else:
            self._draw_text("Static...", self.font_medium, self.colors['text_dim'], (50, 110 + y_offset))

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
        # Range 87.5 to 108.0
        # Map to -135 to +135 degrees (3/4 circle)
        freq = state.get('frequency', 88.0)
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
