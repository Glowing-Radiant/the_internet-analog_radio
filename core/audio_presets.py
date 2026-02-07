import vlc
from typing import Dict, List, Optional

class AudioPresetsManager:
    """
    Manages VLC audio equalizer presets.
    Provides built-in and custom presets for audio enhancement.
    """
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.equalizer = None
        self.enabled = False
        
        # VLC equalizer has 10 bands (frequencies in Hz):
        # 60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000
        
        # Built-in presets (values in dB, range typically -20 to +20)
        self.builtin_presets = {
            'Flat': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'Rock': [5, 3, -3, -5, -2, 2, 5, 7, 7, 7],
            'Jazz': [4, 3, 1, 1, -1, -1, 0, 1, 2, 3],
            'Classical': [5, 4, 3, 2, -1, -1, 0, 2, 3, 4],
            'Pop': [-2, -1, 0, 1, 3, 3, 1, 0, -1, -2],
            'Bass Boost': [8, 6, 4, 2, 0, -1, -2, -3, -3, -3],
            'Treble Boost': [-3, -3, -2, -1, 0, 2, 4, 6, 8, 9],
            'Speech': [-1, -1, 0, 2, 4, 4, 3, 1, 0, -1],
            'Vocal': [-2, -1, 1, 3, 3, 2, 0, -1, -2, -3],
            'Live': [-2, 0, 2, 3, 3, 3, 2, 1, 1, 1]
        }
        
        # Load custom presets from config
        self.custom_presets = {}
        if self.config_manager:
            self.custom_presets = self.config_manager.load_json("audio_presets.json", {})
            
        self.current_preset_name = 'Flat'
        self.preset_names = list(self.builtin_presets.keys()) + list(self.custom_presets.keys())
        self.current_preset_index = 0
        
    def initialize_equalizer(self, vlc_instance):
        """
        Initialize the VLC equalizer object.
        Must be called with a VLC instance.
        """
        try:
            self.equalizer = vlc.AudioEqualizer()
            if self.equalizer:
                print("VLC Equalizer initialized")
                return True
        except Exception as e:
            print(f"Failed to initialize equalizer: {e}")
            self.equalizer = None
            return False
            
    def set_preset(self, preset_name: str) -> bool:
        """
        Apply a preset by name.
        """
        if not self.equalizer:
            return False
            
        # Get preset values
        preset_values = None
        if preset_name in self.builtin_presets:
            preset_values = self.builtin_presets[preset_name]
        elif preset_name in self.custom_presets:
            preset_values = self.custom_presets[preset_name]
        else:
            print(f"Preset '{preset_name}' not found")
            return False
            
        # Apply preset
        try:
            for band_index, value in enumerate(preset_values):
                # VLC expects values in range, clamp to -20 to +20
                clamped_value = max(-20.0, min(20.0, float(value)))
                self.equalizer.set_amp_at_index(clamped_value, band_index)
                
            self.current_preset_name = preset_name
            print(f"Applied equalizer preset: {preset_name}")
            return True
        except Exception as e:
            print(f"Error applying preset: {e}")
            return False
            
    def cycle_preset(self, direction: int = 1) -> str:
        """
        Cycle to next/previous preset.
        Returns the new preset name.
        """
        self.preset_names = list(self.builtin_presets.keys()) + list(self.custom_presets.keys())
        
        if not self.preset_names:
            return 'Flat'
            
        # Find current index
        if self.current_preset_name in self.preset_names:
            self.current_preset_index = self.preset_names.index(self.current_preset_name)
        else:
            self.current_preset_index = 0
            
        # Cycle
        self.current_preset_index = (self.current_preset_index + direction) % len(self.preset_names)
        new_preset = self.preset_names[self.current_preset_index]
        
        self.set_preset(new_preset)
        return new_preset
        
    def toggle_equalizer(self, player) -> bool:
        """
        Toggle equalizer on/off for a VLC player.
        Returns new enabled state.
        """
        if not self.equalizer:
            return False
            
        try:
            if self.enabled:
                # Disable
                player.set_equalizer(None)
                self.enabled = False
                print("Equalizer disabled")
            else:
                # Enable
                player.set_equalizer(self.equalizer)
                self.enabled = True
                print(f"Equalizer enabled with preset: {self.current_preset_name}")
                
            return self.enabled
        except Exception as e:
            print(f"Error toggling equalizer: {e}")
            return self.enabled
            
    def apply_to_player(self, player):
        """
        Apply current equalizer settings to a VLC player.
        """
        if not self.equalizer or not self.enabled:
            return False
            
        try:
            player.set_equalizer(self.equalizer)
            return True
        except Exception as e:
            print(f"Error applying equalizer to player: {e}")
            return False
            
    def save_custom_preset(self, name: str, values: List[float]) -> bool:
        """
        Save a custom preset.
        """
        if len(values) != 10:
            print("Preset must have exactly 10 band values")
            return False
            
        # Validate values
        clamped_values = [max(-20.0, min(20.0, float(v))) for v in values]
        
        self.custom_presets[name] = clamped_values
        
        if self.config_manager:
            self.config_manager.save_json("audio_presets.json", self.custom_presets)
            
        # Update preset names list
        self.preset_names = list(self.builtin_presets.keys()) + list(self.custom_presets.keys())
        
        print(f"Saved custom preset: {name}")
        return True
        
    def delete_custom_preset(self, name: str) -> bool:
        """
        Delete a custom preset.
        """
        if name in self.custom_presets:
            del self.custom_presets[name]
            
            if self.config_manager:
                self.config_manager.save_json("audio_presets.json", self.custom_presets)
                
            # Update preset names list
            self.preset_names = list(self.builtin_presets.keys()) + list(self.custom_presets.keys())
            
            print(f"Deleted custom preset: {name}")
            return True
        return False
        
    def get_current_preset_info(self) -> Dict:
        """
        Get information about the current preset.
        """
        return {
            'name': self.current_preset_name,
            'enabled': self.enabled,
            'values': self.builtin_presets.get(self.current_preset_name) or self.custom_presets.get(self.current_preset_name, [0]*10)
        }
