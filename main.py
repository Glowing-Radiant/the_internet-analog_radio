import pygame
import sys
import os
import ctypes

from core.config_manager import ConfigManager
from core.region_detector import RegionDetector
from core.station_manager import StationManager
from core.favorites_manager import FavoritesManager
from core.stream_player import StreamPlayer
from core.history_manager import HistoryManager
from core.timer_manager import TimerManager
from core.audio_presets import AudioPresetsManager
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
    
    station_manager = StationManager(config_manager, region_detector)
    
    # Threaded Fetch
    import threading
    def fetch_async():
        print("Fetching stations in background...")
        station_manager.fetch_all(country_code)
        print("Stations fetched.")
        
    fetch_thread = threading.Thread(target=fetch_async, daemon=True)
    fetch_thread.start()
    
    favorites_manager = FavoritesManager(config_manager)
    stream_player = StreamPlayer(config_manager)
    
    # NEW: Initialize new managers
    history_manager = HistoryManager(config_manager, max_entries=100)
    timer_manager = TimerManager()
    audio_presets_manager = AudioPresetsManager(config_manager)
    
    # Initialize equalizer
    audio_presets_manager.initialize_equalizer(stream_player.instance)
    
    # 2. Initialize UI
    renderer = PygameRenderer()
    
    # 3. Initialize Controller
    controller = EventController(
        station_manager=station_manager,
        favorites_manager=favorites_manager,
        stream_player=stream_player,
        renderer=renderer,
        accessibility_manager=accessibility_manager,
        history_manager=history_manager,
        timer_manager=timer_manager,
        audio_presets_manager=audio_presets_manager,
        config_manager=config_manager
    )
    
    # 4. Run
    controller.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("CRITICAL ERROR IN MAIN:")
        import traceback
        traceback.print_exc()
        
        # Keep window open if console
        print("Press Enter to Exit...")
        input()
