import vlc
import time
import threading

class StreamPlayer:
    def __init__(self):
        self.instance = vlc.Instance('--no-video')
        self.player = self.instance.media_player_new()
        self.current_url = None
        self.master_volume = 1.0

    def play(self, url):
        """
        Plays the given URL. 
        Stops previous stream automatically.
        """
        if not url: return

        # Optimization: If already playing this URL, do nothing
        if self.current_url == url:
             if not self.player.is_playing():
                 # Valid states to resume/play from
                 state = self.player.get_state()
                 active_states = {vlc.State.Opening, vlc.State.Buffering, vlc.State.Playing}
                 if state not in active_states:
                     self.player.play()
             return

        # New URL
        self.stop()
        
        try:
            print(f"StreamPlayer: Playing {url}")
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.audio_set_volume(0) # Start silent
            self.player.play()
            self.current_url = url
            
        except Exception as e:
            print(f"Error creating stream for {url}: {e}")

    def set_volume(self, volume):
        """
        Sets volume for the current stream. 
        Volume 0.0 to 1.0.
        """
        vol = int(max(0.0, min(1.0, volume)) * 100)
        
        # Use mute for 0
        if vol == 0:
            if not self.player.audio_get_mute():
                self.player.audio_set_mute(True)
        else:
            if self.player.audio_get_mute():
                self.player.audio_set_mute(False)
            
            # Update only if changed
            if self.player.audio_get_volume() != vol:
                self.player.audio_set_volume(vol)

    def stop(self):
        """
        Stops playback.
        """
        self.player.stop()
        self.current_url = None

    def is_playing(self):
        return self.player.is_playing()

    def update(self):
        pass
    
    # Helper for legacy calls if any
    def cleanup_except(self, keep_urls):
        pass
