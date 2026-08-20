"""
Procedural between-stations static.

The old static was a one second loop of 8-bit white noise. This generates
it continuously instead, which lets the sound react to how far off the
dial you are: hiss shaped like a receiver's passband, sparse crackle, a
slow fading wobble, and the heterodyne whistle that slides down in pitch
as you close in on a carrier.
"""

import numpy as np

from core.audio.dsp import FirConvolver, design_fir_from_curve
from core.audio.engine import AudioSource

# Rough shape of a communications receiver's audio passband.
_HISS_CURVE_HZ = [20, 120, 300, 1200, 3500, 6000, 10000, 20000]
_HISS_CURVE_DB = [-30, -18, -4, 0, -1, -8, -20, -34]


class StaticSource(AudioSource):
    def __init__(self, engine, seed=None):
        super().__init__(samplerate=engine.samplerate, channels=engine.channels)
        self.blocksize = engine.blocksize
        self._rng = np.random.default_rng(seed)

        ir = design_fir_from_curve(_HISS_CURVE_HZ, _HISS_CURVE_DB, self.samplerate, taps=129)
        self._filter = FirConvolver(ir, self.blocksize, self.channels)

        # 0.0 = locked onto a station, 1.0 = nothing but noise.
        self.detune = 1.0
        self.crackle = 0.55
        self.whistle = 0.5
        self.wobble = 0.35

        self._whistle_phase = 0.0
        self._wobble_phase = 0.0
        self._vibrato_phase = 0.0

    def set_detune(self, value):
        self.detune = float(np.clip(value, 0.0, 1.0))

    def pull(self, frames):
        white = self._rng.standard_normal((frames, self.channels)) * 0.30
        block = self._filter.process(white)

        if self.crackle > 0.0:
            block += self._make_crackle(frames)
        if self.whistle > 0.0:
            block += self._make_whistle(frames)
        if self.wobble > 0.0:
            block *= self._make_wobble(frames)[:, None]
        return block

    def _make_crackle(self, frames):
        """Sparse impulses: atmospheric pops, denser when badly tuned."""
        density = 0.00025 + 0.0018 * self.detune
        hits = self._rng.random(frames) < density
        if not hits.any():
            return 0.0
        pops = np.zeros((frames, self.channels))
        count = int(hits.sum())
        amplitude = self._rng.random(count) * 0.7 * self.crackle
        # Pan each pop slightly so they scatter across the stereo field.
        pan = self._rng.random(count)
        pops[hits, 0] = amplitude * (1.0 - pan * 0.6)
        pops[hits, 1] = amplitude * (1.0 - (1.0 - pan) * 0.6)
        return pops

    def _make_whistle(self, frames):
        """
        Heterodyne beat note. Silent when locked (no offset to beat
        against) and when far away (the carrier is out of the passband),
        loudest in between -- the squeal you chase when tuning.
        """
        level = np.sin(np.pi * self.detune) ** 2 * 0.12 * self.whistle
        if level < 1e-4:
            return 0.0

        step = 2.0 * np.pi / self.samplerate
        self._vibrato_phase = (self._vibrato_phase + 5.5 * step * frames) % (2.0 * np.pi)
        vibrato = np.sin(self._vibrato_phase) * 30.0
        frequency = 180.0 + 4200.0 * self.detune + vibrato

        phases = self._whistle_phase + step * frequency * np.arange(frames)
        self._whistle_phase = float((phases[-1] + step * frequency) % (2.0 * np.pi))
        tone = np.sin(phases) * level
        return np.column_stack([tone, tone * 0.85])

    def _make_wobble(self, frames):
        """Slow amplitude drift, like a signal fading in and out."""
        step = 2.0 * np.pi / self.samplerate
        rate = 0.23
        phases = self._wobble_phase + step * rate * np.arange(frames)
        self._wobble_phase = float((phases[-1] + step * rate) % (2.0 * np.pi))
        depth = self.wobble * 0.5
        return 1.0 - depth + depth * (0.5 + 0.5 * np.sin(phases))
