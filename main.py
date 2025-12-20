import pygame
import sys
import os
import ctypes

from core.config_manager import ConfigManager
from core.region_detector import RegionDetector
from core.station_manager import StationManager
from core.favorites_manager import FavoritesManager
from core.stream_player import StreamPlayer
from ui.pygame_renderer import PygameRenderer
from ui.event_controller import EventController
from core.accessibility import AccessibilityManager

def setup_console():
    """
    Allocates a console if frozen and --debug flag is present.
    """
    if getattr(sys, 'frozen', False):
        if '--debug' in sys.argv:
            try:
                # Detach from any existing console first just in case
                ctypes.windll.kernel32.FreeConsole()
                # Create a new console
                if ctypes.windll.kernel32.AllocConsole():
                    # Re-open stdout and stderr to point to the new console
                    sys.stdout = open("CONOUT$", "w")
                    sys.stderr = open("CONOUT$", "w")
                    print("Debug Console Attached")
            except Exception as e:
                pass # Fail silently if console creation fails

def main():
    setup_console()
    pygame.init()
    
    # Play Intro
    try:
        pygame.mixer.init()
        intro_path = os.path.join("sounds", "intro.mp3")
        if os.path.exists(intro_path):
            pygame.mixer.music.load(intro_path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing intro: {e}")
    
    # 1. Initialize Core
    config_manager = ConfigManager()
    accessibility_manager = AccessibilityManager()
    
    region_detector = RegionDetector()
    region_info = region_detector.get_region()
    print(f"Detected Region Info: {region_info}")
    
    country_code = region_info.get('countryCode') if region_info else None
    city = region_info.get('city') if region_info else None
    
    lat = region_info.get('lat') if region_info else None
    lon = region_info.get('lon') if region_info else None
    
    station_manager = StationManager(config_manager)
    station_manager = StationManager(config_manager)
    
    # Threaded Fetch
    import threading
    def fetch_async():
        print("Fetching stations in background...")
        station_manager.fetch_all(country_code, city, lat, lon)
        print("Stations fetched.")
        
    fetch_thread = threading.Thread(target=fetch_async, daemon=True)
    fetch_thread.start()
    
    favorites_manager = FavoritesManager(config_manager)
    stream_player = StreamPlayer()
    
    # 2. Initialize UI
    renderer = PygameRenderer()
    
    # 3. Initialize Controller
    controller = EventController(
        station_manager=station_manager,
        favorites_manager=favorites_manager,
        stream_player=stream_player,
        renderer=renderer,
        accessibility_manager=accessibility_manager
    )
    
    # 4. Run
    controller.run()

if __name__ == "__main__":
    main()
