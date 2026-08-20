"""
Lock-free single-producer/single-consumer ring buffer for audio frames.

The decoder thread is the only writer, the audio callback is the only
reader, so the CPython GIL is enough to keep the index updates atomic.
The callback never blocks or allocates.
"""

import numpy as np


class RingBuffer:
    def __init__(self, capacity_frames, channels=2, dtype=np.float32):
        # One slot is always kept empty so full/empty are distinguishable.
        self.capacity = int(capacity_frames) + 1
        self.channels = channels
        self._buf = np.zeros((self.capacity, channels), dtype=dtype)
        self._read = 0
        self._write = 0

    @property
    def available(self):
        """Frames ready to be read."""
        return (self._write - self._read) % self.capacity

    @property
    def space(self):
        """Frames that can still be written."""
        return self.capacity - 1 - self.available

    def clear(self):
        self._read = self._write

    def write(self, data):
        """
        Writes as many frames of `data` as fit. Returns the count written.
        Called from the producer thread only.
        """
        n = min(len(data), self.space)
        if n <= 0:
            return 0

        w = self._write
        first = min(n, self.capacity - w)
        self._buf[w:w + first] = data[:first]
        if n > first:
            self._buf[:n - first] = data[first:n]

        self._write = (w + n) % self.capacity
        return n

    def read_into(self, out):
        """
        Fills `out` with up to len(out) frames, zero-padding any shortfall.
        Returns the number of real frames read. Consumer thread only.
        """
        n = min(len(out), self.available)
        if n <= 0:
            out[:] = 0.0
            return 0

        r = self._read
        first = min(n, self.capacity - r)
        out[:first] = self._buf[r:r + first]
        if n > first:
            out[first:n] = self._buf[:n - first]
        if n < len(out):
            out[n:] = 0.0

        self._read = (r + n) % self.capacity
        return n
