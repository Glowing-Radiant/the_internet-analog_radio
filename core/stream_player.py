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
            # Reset volume tracking so next set_volume works effectively
            self._last_set_volume = 0
            
        except Exception as e:
            print(f"Error creating stream for {url}: {e}")

    def set_volume(self, volume):
        """
        Sets volume for the current stream. 
        Volume 0.0 to 1.0.
        """
        vol = int(max(0.0, min(1.0, volume)) * 100)
        
        # Optimization: Don't spam VLC if volume hasn't effectively changed
        if hasattr(self, '_last_set_volume') and self._last_set_volume == vol:
            return
            
        self._last_set_volume = vol

        # Use mute for 0
        if vol == 0:
            if not self.player.audio_get_mute():
                self.player.audio_set_mute(True)
        else:
            if self.player.audio_get_mute():
                self.player.audio_set_mute(False)
            
            # Update only if changed (double check against VLC internal state occasionally?)
            # Actually trusting our cache is better for perf, VLC calls are C-types overhead.
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

    def get_now_playing(self):
        """
        Returns the current metadata (Now Playing) if available.
        """
        if not self.player.get_media():
            return "Unknown"
            
        media = self.player.get_media()
        # vlc.Meta.NowPlaying is enum 12
        now_playing = media.get_meta(12) 
        if now_playing:
            return now_playing
            
        # Fallback to Title/Artist
        title = media.get_meta(0) # Title
        artist = media.get_meta(1) # Artist
        
        if title and artist:
            return f"{artist} - {title}"
        if title:
            return title
            
        return "Unknown"

    def update(self):
        pass
    
    # Helper for legacy calls if any
    def cleanup_except(self, keep_urls):
        pass
