# What's New

## v2.0.0

**The radio now makes its own sound.**

Everything you hear used to be handled by VLC Media Player, which you had to
install separately. That is gone. The radio has its own audio engine built
in, and this release is mostly about what that lets it do.

### You no longer need to install anything

Unzip, run. No VLC, no codec pack, no setup. If VLC was the reason the radio
would not start for you before, it will start now.

### New sound controls

Press **O** for Settings. Four new switches, each on or off:

- **Volume Leveler** — *on by default.* Internet stations are broadcast at
  wildly different volumes; one is a whisper and the next takes your head
  off. This evens them out so you stop reaching for the volume knob every
  time you change station.
- **Warmth** — a gentle valve-style softening that takes the edge off
  harsh, low-bitrate streams.
- **Stereo Width** — opens the stereo image up.
- **Spaciousness** — a light room reverb.

Your settings are remembered between sessions.

### The equalizer got better, and gained a preset

The equalizer is rebuilt and now runs on the radio's own engine. Every
preset you already had works exactly as before, including any you saved
yourself — nothing to redo.

New **Shortwave** preset: cuts the rumble and the hiss and leaves the voice.
Made for weak, noisy signals. Try it in Analog Radio mode.

### Station names, live

The radio now shows the actual song or programme playing, updating as it
changes, on stations that broadcast it. Press **W** at any time to hear it.
Previously this only worked sometimes.

### The static listens to your tuning

The noise between stations is generated fresh as you turn the dial instead
of being a short recording on loop. Drift away from a station and the
crackle thickens; drift closer and a whistle slides down in pitch until it
vanishes at the moment you lock on. You can find stations by ear now,
without looking at the frequency at all.

The crossfade between static and station is also handled properly, so
stations swim in and out smoothly instead of stepping.

### Dead stations get out of your way

Some stations in the public listings simply do not work any more. Before,
tuning onto one left you in silence with no clue why. Now:

- The static keeps going while the radio connects, so the dial never falls
  silent on you.
- A station that cannot be reached gives up in about a second instead of
  hanging, and you carry on tuning.
- Brief network hiccups are ridden out from a few seconds of stored audio
  rather than becoming a stutter.
- If your sound device changes while the radio is open — headphones plugged
  in, a speaker switched off — it finds the new one on its own.

### Also

- Switching stations fades instead of clicking.
- The Settings panel grows to fit its contents, so nothing is cut off.
- Analog Radio (KiwiSDR) plays through the same engine and starts a little
  faster.
- The download is bigger than before, because the audio decoding that VLC
  used to provide is now included in the box.

---

## Earlier releases

**v1.0** — Analog Radio mode added, tuning live shortwave through public
KiwiSDR receivers. Search added to TV mode. A Settings panel for turning
modes on and off. Sound effects for menus and controls. Downloads changed
from a single .exe to a zip so those sounds ship with the program.

Before that: playback History as its own band, the Sleep Timer, and the
first version of the audio equalizer. TV mode. Custom bands you build from
your own searches. Screen reader support throughout.
