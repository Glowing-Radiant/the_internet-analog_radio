import pygame
import os

class StaticGenerator:
    def __init__(self):
        try:
            pygame.mixer.init()
        except pygame.error:
            pass # Might already be initialized
            
        self.sound = self._generate_white_noise()
        self.channel = None
        self.volume = 0.5
        
    def _generate_white_noise(self):
        # Generate 1 second of white noise
        duration = 1.0 
        sample_rate = 44100
        
        # Use os.urandom which is standard library
        # Generate random bytes
        n_samples = int(duration * sample_rate)
        buffer = os.urandom(n_samples)
        
        # Convert to numpy array for manipulation if we had numpy, but
        # standard pygame can take raw bytes for Sound if formatted correctly.
        # Actually simplest is just to use the raw bytes.
        # 8-bit unsigned audio is 0-255. White noise is random values.
        
        return pygame.mixer.Sound(buffer=buffer)

    def play(self):
        if not self.channel:
            self.channel = self.sound.play(loops=-1) # Loop forever
        
        # Ensure it's playing
        if self.channel and not self.channel.get_busy():
             self.channel = self.sound.play(loops=-1)
             
        self.set_volume(self.volume)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.channel:
            self.channel.set_volume(self.volume)

    def stop(self):
        if self.channel:
            self.channel.stop()
            self.channel = None
