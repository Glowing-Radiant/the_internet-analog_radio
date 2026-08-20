from core.audio import get_engine
from core.audio.noise import StaticSource


class StaticGenerator:
    """
    Between-stations noise.

    Same interface as before, but the noise is now generated live inside
    the audio engine rather than looped through the pygame mixer. Because
    it shares the engine's clock with the station audio, the crossfade
    while tuning is sample accurate instead of two mixers guessing.
    """

    def __init__(self):
        self.engine = get_engine()
        self.source = StaticSource(self.engine)
        self.volume = 0.0
        self._playing = False

    def play(self):
        if not self._playing:
            self.engine.add_source(self.source)
            self._playing = True
        self.set_volume(self.volume)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, float(volume)))
        self.source.gain = self.volume

    def set_detune(self, amount):
        """
        0.0 = locked onto a station, 1.0 = nothing there.
        Drives the crackle density and the heterodyne whistle.
        """
        self.source.set_detune(amount)

    def stop(self):
        self.source.gain = 0.0
        self.volume = 0.0
        if self._playing:
            self.engine.remove_source(self.source)
            self._playing = False
