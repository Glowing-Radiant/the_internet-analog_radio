import time
from datetime import datetime, timedelta
from typing import Optional, Callable

class TimerManager:
    """
    Manages sleep timer and scheduling functionality.
    Provides countdown timer that can gracefully stop playback.
    """
    
    def __init__(self):
        self.timer_end_time = None
        self.timer_duration = 0  # in seconds
        self.timer_active = False
        self.fade_duration = 10  # Fade out over 10 seconds before stopping
        self.on_timer_expired = None  # Callback when timer expires
        
    def set_timer(self, minutes: int, callback: Optional[Callable] = None):
        """
        Set a sleep timer for the specified number of minutes.
        
        Args:
            minutes: Duration in minutes
            callback: Optional callback to execute when timer expires
        """
        if minutes <= 0:
            self.cancel_timer()
            return False
            
        self.timer_duration = minutes * 60
        self.timer_end_time = datetime.now() + timedelta(seconds=self.timer_duration)
        self.timer_active = True
        self.on_timer_expired = callback
        
        print(f"Sleep timer set for {minutes} minutes (until {self.timer_end_time.strftime('%H:%M:%S')})")
        return True
        
    def cancel_timer(self):
        """
        Cancel the active timer.
        """
        self.timer_active = False
        self.timer_end_time = None
        self.timer_duration = 0
        self.on_timer_expired = None
        print("Sleep timer cancelled")
        
    def get_remaining_time(self) -> Optional[int]:
        """
        Get remaining time in seconds.
        Returns None if no timer is active.
        """
        if not self.timer_active or not self.timer_end_time:
            return None
            
        remaining = (self.timer_end_time - datetime.now()).total_seconds()
        
        if remaining <= 0:
            return 0
            
        return int(remaining)
        
    def get_fade_volume_multiplier(self) -> float:
        """
        Get volume multiplier for fade effect.
        Returns 1.0 if not in fade period, or a value between 0.0-1.0 during fade.
        """
        if not self.timer_active:
            return 1.0
            
        remaining = self.get_remaining_time()
        
        if remaining is None or remaining > self.fade_duration:
            return 1.0
            
        if remaining <= 0:
            return 0.0
            
        # Linear fade from 1.0 to 0.0
        return remaining / self.fade_duration
        
    def check_timer(self) -> bool:
        """
        Check if timer has expired.
        Returns True if timer expired this check.
        """
        if not self.timer_active:
            return False
            
        remaining = self.get_remaining_time()
        
        if remaining is not None and remaining <= 0:
            # Timer expired
            self.timer_active = False
            
            # Execute callback if set
            if self.on_timer_expired:
                self.on_timer_expired()
                
            print("Sleep timer expired - stopping playback")
            return True
            
        return False
        
    def format_remaining_time(self) -> str:
        """
        Format remaining time as a human-readable string.
        """
        remaining = self.get_remaining_time()
        
        if remaining is None:
            return "No timer"
            
        if remaining <= 0:
            return "Timer expired"
            
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
            
    def is_active(self) -> bool:
        """
        Check if timer is currently active.
        """
        return self.timer_active and self.timer_end_time is not None
