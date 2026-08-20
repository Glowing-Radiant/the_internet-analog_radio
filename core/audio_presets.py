from typing import Dict, List

from core.audio.dsp import EQ_BANDS_HZ

# Effects that sit after the equalizer in the engine's master chain.
# Keys match core.audio.engine.MasterChain.enabled.
EFFECTS = {
    'warmth': 'Warmth',
    'leveler': 'Volume Leveler',
    'width': 'Stereo Width',
    'space': 'Spaciousness',
}


class AudioPresetsManager:
    """
    Manages the engine's equalizer presets and enhancement effects.

    The ten band layout matches what the old VLC equalizer used, so
    presets saved by earlier versions keep working unchanged.
    """

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.engine = None
        self.equalizer = None
        self.enabled = False

        # Band centres in Hz: 60, 170, 310, 600, 1000, 3000, 6000, 12000,
        # 14000, 16000. Values are dB, clamped to -20..+20.
        self.bands_hz = list(EQ_BANDS_HZ)

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
            'Live': [-2, 0, 2, 3, 3, 3, 2, 1, 1, 1],
            # Shortwave-style narrow band: cuts rumble and hiss so weak or
            # noisy stations stay intelligible.
            'Shortwave': [-12, -8, 0, 4, 5, 3, -4, -12, -15, -18],
        }

        self.custom_presets = {}
        if self.config_manager:
            self.custom_presets = self.config_manager.load_json("audio_presets.json", {})

        self.current_preset_name = 'Flat'
        self.preset_names = self._all_preset_names()
        self.current_preset_index = 0

    def _all_preset_names(self):
        return list(self.builtin_presets.keys()) + list(self.custom_presets.keys())

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def initialize_equalizer(self, engine=None):
        """
        Binds this manager to the audio engine's equalizer.

        Args:
            engine: an AudioEngine. Defaults to the shared one.
        """
        try:
            if engine is None:
                from core.audio import get_engine
                engine = get_engine()
            self.engine = engine
            self.equalizer = engine.chain.equalizer
            self.enabled = engine.chain.is_enabled('equalizer')
            print("Equalizer initialized (%d bands)" % len(self.bands_hz))
            return True
        except Exception as e:
            print("Failed to initialize equalizer: %s: %s" % (type(e).__name__, e))
            self.equalizer = None
            return False

    # ------------------------------------------------------------------ #
    # Presets
    # ------------------------------------------------------------------ #

    def get_preset_values(self, preset_name: str):
        if preset_name in self.builtin_presets:
            return self.builtin_presets[preset_name]
        return self.custom_presets.get(preset_name)

    def set_preset(self, preset_name: str) -> bool:
        """Applies a preset by name."""
        if not self.equalizer:
            return False

        preset_values = self.get_preset_values(preset_name)
        if preset_values is None:
            print("Preset '%s' not found" % preset_name)
            return False

        try:
            self.equalizer.set_gains(preset_values)
            self.current_preset_name = preset_name
            print("Applied equalizer preset: %s" % preset_name)
            return True
        except Exception as e:
            print("Error applying preset: %s" % e)
            return False

    def cycle_preset(self, direction: int = 1) -> str:
        """Cycles to the next/previous preset and returns its name."""
        self.preset_names = self._all_preset_names()
        if not self.preset_names:
            return 'Flat'

        if self.current_preset_name in self.preset_names:
            self.current_preset_index = self.preset_names.index(self.current_preset_name)
        else:
            self.current_preset_index = 0

        self.current_preset_index = (self.current_preset_index + direction) % len(self.preset_names)
        new_preset = self.preset_names[self.current_preset_index]

        self.set_preset(new_preset)
        return new_preset

    def toggle_equalizer(self, player=None) -> bool:
        """Turns the equalizer stage on or off. Returns the new state."""
        if not self.equalizer or not self.engine:
            return False

        try:
            self.enabled = not self.enabled
            self.engine.chain.set_enabled('equalizer', self.enabled)
            if self.enabled:
                print("Equalizer enabled with preset: %s" % self.current_preset_name)
            else:
                print("Equalizer disabled")
            return self.enabled
        except Exception as e:
            print("Error toggling equalizer: %s" % e)
            return self.enabled

    def apply_to_player(self, player=None):
        """
        Re-asserts the current equalizer state on the engine. Kept for
        callers that used to re-apply the EQ after switching streams; the
        engine keeps the chain across stream changes, so this is cheap.
        """
        if not self.equalizer or not self.engine:
            return False
        self.engine.chain.set_enabled('equalizer', self.enabled)
        return True

    def save_custom_preset(self, name: str, values: List[float]) -> bool:
        if len(values) != len(self.bands_hz):
            print("Preset must have exactly %d band values" % len(self.bands_hz))
            return False

        clamped_values = [max(-20.0, min(20.0, float(v))) for v in values]
        self.custom_presets[name] = clamped_values

        if self.config_manager:
            self.config_manager.save_json("audio_presets.json", self.custom_presets)

        self.preset_names = self._all_preset_names()
        print("Saved custom preset: %s" % name)
        return True

    def delete_custom_preset(self, name: str) -> bool:
        if name in self.custom_presets:
            del self.custom_presets[name]

            if self.config_manager:
                self.config_manager.save_json("audio_presets.json", self.custom_presets)

            self.preset_names = self._all_preset_names()
            print("Deleted custom preset: %s" % name)
            return True
        return False

    def get_current_preset_info(self) -> Dict:
        return {
            'name': self.current_preset_name,
            'enabled': self.enabled,
            'values': self.get_preset_values(self.current_preset_name) or [0] * len(self.bands_hz),
        }

    # ------------------------------------------------------------------ #
    # Enhancement effects
    # ------------------------------------------------------------------ #

    def set_effect(self, name: str, enabled: bool) -> bool:
        """Turns one of the master chain enhancements on or off."""
        if not self.engine or name not in EFFECTS:
            return False
        return self.engine.chain.set_enabled(name, enabled)

    def toggle_effect(self, name: str) -> bool:
        if not self.engine or name not in EFFECTS:
            return False
        new_state = not self.engine.chain.is_enabled(name)
        self.engine.chain.set_enabled(name, new_state)
        return new_state

    def is_effect_enabled(self, name: str) -> bool:
        if not self.engine:
            return False
        return self.engine.chain.is_enabled(name)

    def get_effects_state(self) -> Dict[str, bool]:
        return {key: self.is_effect_enabled(key) for key in EFFECTS}
