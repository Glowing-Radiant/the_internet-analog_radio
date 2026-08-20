"""
The radio's audio stack.

    engine   - output device, mixer, master effect chain
    dsp      - the effect building blocks
    decoder  - PyAV based stream/pipe sources
    noise    - procedural between-stations static
    icy      - Shoutcast metadata aware HTTP reader
    ring     - lock free buffer shared by decoder and callback

One engine is shared by the whole app so every sound goes through the
same mixer and the same effects.
"""

from core.audio.engine import AudioEngine, AudioSource, MasterChain  # noqa: F401

_engine = None


def get_engine():
    """Returns the process-wide engine, starting the output device once."""
    global _engine
    if _engine is None:
        _engine = AudioEngine()
        _engine.start()
    return _engine


def shutdown_engine():
    global _engine
    if _engine is not None:
        _engine.stop()
        _engine = None
