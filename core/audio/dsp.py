"""
Numpy DSP building blocks for the radio audio engine.

Everything here is block based and vectorised: `process(x)` takes a float
array shaped (frames, channels) and returns the same shape. Nothing
allocates unbounded memory and nothing blocks, so these are safe to run
inside the sounddevice callback.
"""

import numpy as np

# The ten bands the old VLC equalizer exposed, kept so existing presets
# (and saved user presets) keep meaning exactly the same thing.
EQ_BANDS_HZ = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]


def db_to_gain(db):
    return 10.0 ** (np.asarray(db, dtype=np.float64) / 20.0)


def _next_pow2(n):
    p = 1
    while p < n:
        p <<= 1
    return p


def design_fir_from_curve(freqs_hz, gains_db, samplerate, taps=257, design_size=1024):
    """
    Builds a linear-phase FIR whose magnitude response follows the given
    (frequency, gain) breakpoints, interpolated on a log-frequency axis.
    """
    taps = int(taps) | 1  # odd, so the delay is an exact integer
    bin_freqs = np.fft.rfftfreq(design_size, 1.0 / samplerate)

    log_f = np.log10(np.maximum(np.asarray(freqs_hz, dtype=np.float64), 1.0))
    log_bins = np.log10(np.maximum(bin_freqs, 1.0))
    gains = np.asarray(gains_db, dtype=np.float64)
    curve_db = np.interp(log_bins, log_f, gains, left=gains[0], right=gains[-1])

    magnitude = db_to_gain(curve_db)
    ir = np.fft.irfft(magnitude, n=design_size)
    ir = np.roll(ir, taps // 2)[:taps]
    ir *= np.hanning(taps)
    return ir.astype(np.float64)


class FirConvolver:
    """
    Overlap-add FFT convolution of a multichannel block stream with a FIR.
    Exact (no windowing artefacts) and cheap: two FFTs per block.
    """

    def __init__(self, ir, blocksize, channels=2):
        self.channels = channels
        self.blocksize = blocksize
        self._ir = None
        self._tail = None
        self.set_ir(ir)

    def set_ir(self, ir):
        ir = np.asarray(ir, dtype=np.float64)
        self._ir = ir
        self.taps = len(ir)
        self.nfft = _next_pow2(self.blocksize + self.taps - 1)
        self._spec = np.fft.rfft(ir, n=self.nfft)[:, None]

        tail_len = self.taps - 1
        old = self._tail
        self._tail = np.zeros((tail_len, self.channels), dtype=np.float64)
        if old is not None and len(old):
            keep = min(len(old), tail_len)
            self._tail[:keep] = old[:keep]

    def reset(self):
        self._tail[:] = 0.0

    @property
    def latency(self):
        """Group delay in frames (linear phase, so it is constant)."""
        return self.taps // 2

    def process(self, x):
        n = len(x)
        if n != self.blocksize:
            self.blocksize = n
            self.set_ir(self._ir)

        spectrum = np.fft.rfft(x, n=self.nfft, axis=0)
        y = np.fft.irfft(spectrum * self._spec, n=self.nfft, axis=0)

        tail_len = len(self._tail)
        if tail_len:
            y[:tail_len] += self._tail
            self._tail[:] = y[n:n + tail_len]
        return y[:n]


class Equalizer:
    """Ten band graphic EQ, implemented as a linear-phase FIR."""

    def __init__(self, samplerate, blocksize, channels=2, taps=257):
        self.samplerate = samplerate
        self.taps = taps
        self.gains_db = [0.0] * len(EQ_BANDS_HZ)
        self._conv = FirConvolver(self._design(), blocksize, channels)

    def _design(self):
        # Anchor the curve at both ends so the extremes do not flap around.
        freqs = [20.0] + list(EQ_BANDS_HZ) + [self.samplerate / 2.0]
        gains = [self.gains_db[0]] + list(self.gains_db) + [self.gains_db[-1]]
        return design_fir_from_curve(freqs, gains, self.samplerate, self.taps)

    def set_gains(self, gains_db):
        gains = [float(np.clip(g, -20.0, 20.0)) for g in gains_db]
        if len(gains) != len(EQ_BANDS_HZ):
            raise ValueError("expected %d band gains" % len(EQ_BANDS_HZ))
        if gains == self.gains_db:
            return
        self.gains_db = gains
        self._conv.set_ir(self._design())

    def set_band(self, index, gain_db):
        gains = list(self.gains_db)
        gains[index] = gain_db
        self.set_gains(gains)

    def reset(self):
        self._conv.reset()

    def process(self, x):
        return self._conv.process(x)


class Compressor:
    """
    Soft-knee compressor with an envelope evaluated on 64 sample
    sub-blocks and smoothly interpolated back to sample rate. Used as the
    loudness leveller so wildly different stations sit at a similar level.
    """

    SUB = 64

    def __init__(self, samplerate, threshold_db=-20.0, ratio=3.0,
                 attack_ms=15.0, release_ms=300.0, makeup_db=0.0):
        self.samplerate = samplerate
        self.threshold_db = threshold_db
        self.ratio = ratio
        self.knee_db = 6.0
        self.makeup_db = makeup_db
        self.set_times(attack_ms, release_ms)
        self._env = 1e-6
        self.gain_reduction_db = 0.0

    def set_times(self, attack_ms, release_ms):
        step_ms = self.SUB / float(self.samplerate) * 1000.0
        self._attack = float(np.exp(-step_ms / max(attack_ms, 0.1)))
        self._release = float(np.exp(-step_ms / max(release_ms, 1.0)))

    def reset(self):
        self._env = 1e-6

    def process(self, x):
        n = len(x)
        sub = self.SUB
        n_sub = max(1, (n + sub - 1) // sub)

        mono = np.abs(x).max(axis=1)
        peaks = np.empty(n_sub)
        for i in range(n_sub):
            chunk = mono[i * sub:(i + 1) * sub]
            peaks[i] = chunk.max() if len(chunk) else 0.0

        env = self._env
        for i in range(n_sub):
            target = peaks[i]
            coeff = self._attack if target > env else self._release
            env = target + (env - target) * coeff
            peaks[i] = env
        self._env = env

        env_db = 20.0 * np.log10(np.maximum(peaks, 1e-9))
        over = env_db - self.threshold_db
        knee = self.knee_db

        # Soft knee: quadratic blend across +/- knee/2 around the threshold.
        reduction = np.zeros_like(over)
        upper = over > knee / 2.0
        inside = (over > -knee / 2.0) & ~upper
        slope = 1.0 - 1.0 / max(self.ratio, 1.0)
        reduction[upper] = slope * over[upper]
        reduction[inside] = slope * (over[inside] + knee / 2.0) ** 2 / (2.0 * knee)

        self.gain_reduction_db = float(reduction.max()) if len(reduction) else 0.0
        gain_db = self.makeup_db - reduction

        if n_sub == 1:
            gain = np.full(n, float(db_to_gain(gain_db[0])))
        else:
            centres = np.arange(n_sub) * sub + sub / 2.0
            gain = db_to_gain(np.interp(np.arange(n), centres, gain_db))
        return x * gain[:, None]


class Limiter:
    """Output stage: fast peak limiter plus a tanh backstop."""

    SUB = 32

    def __init__(self, samplerate, ceiling=0.98, release_ms=120.0):
        self.samplerate = samplerate
        self.ceiling = ceiling
        step_ms = self.SUB / float(samplerate) * 1000.0
        self._release = float(np.exp(-step_ms / max(release_ms, 1.0)))
        self._gain = 1.0

    def reset(self):
        self._gain = 1.0

    def process(self, x):
        n = len(x)
        sub = self.SUB
        n_sub = max(1, (n + sub - 1) // sub)
        mono = np.abs(x).max(axis=1)

        gains = np.empty(n_sub)
        g = self._gain
        for i in range(n_sub):
            chunk = mono[i * sub:(i + 1) * sub]
            peak = chunk.max() if len(chunk) else 0.0
            needed = 1.0 if peak <= self.ceiling else self.ceiling / peak
            # Instant attack, smoothed release.
            g = needed if needed < g else needed + (g - needed) * self._release
            gains[i] = g
        self._gain = g

        if n_sub == 1:
            y = x * gains[0]
        else:
            centres = np.arange(n_sub) * sub + sub / 2.0
            y = x * np.interp(np.arange(n), centres, gains)[:, None]

        # Anything that still pokes through gets rounded off, not clipped.
        magnitude = np.abs(y)
        hot = magnitude > self.ceiling
        if hot.any():
            headroom = max(1.0 - self.ceiling, 1e-6)
            rounded = np.sign(y) * (self.ceiling + headroom *
                                    np.tanh((magnitude - self.ceiling) / headroom))
            y = np.where(hot, rounded, y)
        return y


class StereoWidth:
    """Mid/side width control. 0 = mono, 1 = untouched, above 1 = wider."""

    def __init__(self, width=1.0):
        self.width = width

    def process(self, x):
        if x.shape[1] < 2 or abs(self.width - 1.0) < 1e-3:
            return x
        mid = (x[:, 0] + x[:, 1]) * 0.5
        side = (x[:, 0] - x[:, 1]) * 0.5 * self.width
        out = np.empty_like(x)
        out[:, 0] = mid + side
        out[:, 1] = mid - side
        return out


class Saturator:
    """Tube/tape style soft saturation. Adds warmth and glues transients."""

    def __init__(self, drive=1.0, mix=1.0):
        self.drive = drive
        self.mix = mix

    def process(self, x):
        drive = max(self.drive, 1e-3)
        wet = np.tanh(x * drive) / np.tanh(drive)
        if self.mix >= 1.0:
            return wet
        return x * (1.0 - self.mix) + wet * self.mix


class Reverb:
    """
    Schroeder reverb: four parallel comb filters into two allpasses.
    Every delay line is longer than the audio blocksize, so each block is
    a plain array operation with no per-sample Python loop.
    """

    COMB_MS = [29.7, 37.1, 41.1, 43.7]
    ALLPASS_MS = [26.0, 30.5]

    def __init__(self, samplerate, room=0.6, damping=0.4, mix=0.2):
        self.samplerate = samplerate
        self.room = room
        self.damping = damping
        self.mix = mix
        self._combs = [self._make_line(ms) for ms in self.COMB_MS]
        self._allpass = [self._make_line(ms) for ms in self.ALLPASS_MS]
        self._lp_state = [np.zeros(2) for _ in self.COMB_MS]

    def _make_line(self, ms):
        length = int(self.samplerate * ms / 1000.0)
        return {'buf': np.zeros((length, 2)), 'pos': 0, 'len': length}

    def reset(self):
        for line in self._combs + self._allpass:
            line['buf'][:] = 0.0
        self._lp_state = [np.zeros(2) for _ in self.COMB_MS]

    @staticmethod
    def _indices(line, block_len):
        return (line['pos'] + np.arange(block_len)) % line['len']

    def process(self, x):
        if self.mix <= 0.001:
            return x
        n = len(x)
        feedback = 0.7 + 0.28 * float(np.clip(self.room, 0.0, 1.0))
        damp = float(np.clip(self.damping, 0.0, 0.95))

        wet = np.zeros_like(x)
        for i, line in enumerate(self._combs):
            if line['len'] <= n:
                continue
            idx = self._indices(line, n)
            delayed = line['buf'][idx]
            wet += delayed
            # One-pole damping in the feedback path, carried block to block.
            damped = delayed * (1.0 - damp) + self._lp_state[i] * damp
            self._lp_state[i] = damped[-1].copy()
            line['buf'][idx] = x + damped * feedback
            line['pos'] = (line['pos'] + n) % line['len']
        wet *= 0.25

        for line in self._allpass:
            if line['len'] <= n:
                continue
            idx = self._indices(line, n)
            delayed = line['buf'][idx]
            out = delayed - wet * 0.5
            line['buf'][idx] = wet + delayed * 0.5
            line['pos'] = (line['pos'] + n) % line['len']
            wet = out

        mix = float(np.clip(self.mix, 0.0, 1.0))
        return x * (1.0 - mix * 0.4) + wet * mix
