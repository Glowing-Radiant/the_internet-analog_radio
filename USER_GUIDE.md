# The Internet Analog Radio — User Guide

**"Rediscover your music the old way"**

A radio you *tune* instead of click. Turn the dial through a band of static,
hear a station swim up out of the noise, and stop when it sounds right.
Behind the dial are thousands of real internet stations, live shortwave
receivers, and TV channels from around the world.

Everything is done from the keyboard, and everything is spoken aloud if you
use a screen reader.

---

## Getting started

1. Unzip the download anywhere you like — your Desktop or Documents is fine.
2. Open the folder and run **InternetAnalogRadio.exe**.
3. Wait a moment while it finds stations near you, then press
   **Right Arrow** to start tuning.

There is nothing to install. No media player, no codec pack, no setup wizard.

> **If Windows shows a "Windows protected your PC" box**, that is
> SmartScreen reacting to a new program it has not seen before, not a
> virus warning. Click **More info**, then **Run anyway**.

Keep the whole folder together. The program stores your favorites and
settings in a `config` folder next to the .exe, so if you move the program,
move the folder — not just the .exe.

---

## Your first two minutes

| Do this | And you get |
| :--- | :--- |
| Hold **Right Arrow** | The dial climbs. Static, then a station fading in. |
| **Up / Down Arrow** | Volume. |
| **Ctrl + Right Arrow** | Jump straight to the next station, skipping the empty air. |
| **Plus (+)** | Save the station you are on to Favorites. |
| **Tab** | Move to the next band — National, International, Favorites, History, Exploratory. |
| **S** | Search. Type "jazz", press Enter, and tune through what comes back. |
| **Q** | Quit. |

---

## The three modes

Press **Ctrl + Tab** to move between them. You can hide the ones you never
use in Settings.

**Digital Radio** — Internet stations laid out across an FM-style dial.
The dial moves in 0.1 steps. This is the mode most people live in.

**Analog Radio** — Real shortwave, received live by volunteer KiwiSDR
receivers around the world, tuned in kHz. Distant, atmospheric, and
genuinely live. This mode needs an optional extra download — see
[Turning on Analog Radio](#turning-on-analog-radio) at the end.

**TV Mode** — Channels, not frequencies. Left and Right move straight from
one channel to the next, with no static in between.

---

## Bands

**Tab** moves forward through bands, **Shift + Tab** moves back.

- **National** — the most popular stations in your country.
- **International** — the most popular stations worldwide.
- **Favorites** — everything you saved with **+**.
- **History** — the last 100 things you listened to, with how long you
  stayed.
- **Exploratory** — whatever your last search turned up.

**Make your own band.** Press **S**, search for something ("lofi",
"classical", "news"), then press **B** to keep those results as a permanent
band of their own. It joins the Tab rotation and stays there.

---

## How it sounds, and how to change it

This version has a proper audio engine of its own, which means the sound is
yours to shape. Press **O** for Settings, then **Up / Down** to pick a row
and **Left / Right / Enter** to change it. **O** or **Esc** closes it.

### Equalizer

Off by default. Turn it on in Settings, or press **E** at any time.
Press **P** to move to the next preset, **Shift + P** for the previous one.

| Preset | Good for |
| :--- | :--- |
| Flat | No change — the station as broadcast. |
| Rock, Pop, Jazz, Classical, Live | The usual genre shapes. |
| Bass Boost / Treble Boost | Small speakers / dull-sounding streams. |
| Speech, Vocal | Talk radio, news, podcasts. |
| Shortwave | Weak and noisy signals. Cuts the rumble and the hiss and leaves the voice. Try this one in Analog Radio mode. |

### Enhancements

Four switches in Settings, each on or off:

- **Volume Leveler** — *on by default.* Internet stations are mastered at
  wildly different levels; one is a whisper and the next takes your head
  off. This evens them out so you stop reaching for the volume every time
  you change station. Leave it on unless you want the raw broadcast.
- **Warmth** — a gentle valve-style softening. Takes the edge off harsh,
  low-bitrate streams.
- **Stereo Width** — opens the stereo image up. Nice on music, pointless on
  speech.
- **Spaciousness** — a light room reverb. A period effect, not a correction
  — try it on old recordings.

Your choices are remembered between sessions.

### The static

The noise between stations is generated live, and it listens to where the
dial is. Drift away from a station and the crackle thickens; drift closer
and a whistle slides down in pitch until it disappears at the moment you
lock on. It is the sound of actually finding something, and it is the
fastest way to tune by ear alone.

---

## All the controls

### Tuning and listening

| Key | Action |
| :--- | :--- |
| **Right / Left Arrow** | Tune up / down. In TV mode, next / previous channel. |
| **Ctrl + Right / Left** | Skip to the next / previous real station. |
| **Up / Down Arrow** | Volume up / down. |
| **M** | Mute and unmute. |
| **W** | Say what is playing right now. |
| **C** | Copy the current station's address to the clipboard. |

### Finding things

| Key | Action |
| :--- | :--- |
| **Tab** / **Shift + Tab** | Next / previous band. |
| **Ctrl + Tab** | Next mode (Digital Radio, Analog Radio, TV). |
| **S** | Search for a station, then Enter. |
| **B** | Keep the current search results as a permanent band. |
| **F** | Play a stream address you type in yourself. |
| **+** / **-** | Add / remove the current station from Favorites. |

### Sound and settings

| Key | Action |
| :--- | :--- |
| **O** | Open or close Settings. |
| **E** | Equalizer on / off. |
| **P** / **Shift + P** | Next / previous equalizer preset. |
| **T** | Sleep timer — type the minutes, press Enter. |
| **Shift + T** | Cancel the sleep timer. |
| **Q** | Quit. |

Inside Settings: **Up / Down** to move, **Left / Right / Enter** to change,
**O** or **Esc** to close.

---

## Sleep timer

Press **T**, type a number of minutes, press **Enter**. The radio plays on
and then fades away gently over the last ten seconds rather than cutting
out. **Shift + T** cancels it.

---

## Using a screen reader

The whole program is built to be used without looking at it. NVDA, JAWS and
Narrator are all supported and are detected automatically — there is
nothing to switch on.

Station names, bands, modes, settings rows and their values are all spoken
as you move. **W** repeats what is currently playing at any time.

---

## When something does not sound right

**A station is silent, or you hear only hiss.**
The station's own server is down or refusing connections — this is common
and has nothing to do with your computer. The radio keeps the hiss going
while it tries, gives up after a moment, and leaves you on the dial. Tune
on, or press **Ctrl + Right** to jump to the next one.

**It says "Buffering..." for a few seconds.**
Normal. Slow or distant stations take a moment to start. If it never
clears, that station is unreachable.

**The sound stutters.**
Usually the station or your connection, not the program. The radio keeps a
few seconds of audio in hand and quietly refills it after a hiccup, so
short interruptions should pass without you noticing.

**No sound at all, from anything.**
Check that Windows is playing to the device you expect. If the sound device
changes while the radio is open — headphones plugged in, a speaker switched
off — it notices and reconnects to the new one within a few seconds.

**Everything is too loud, or too quiet, station to station.**
Turn on **Volume Leveler** in Settings. That is exactly what it is for.

---

## Where your things are kept

In the `config` folder next to the program:

| File | What it holds |
| :--- | :--- |
| `favorites.json` | Your saved stations. |
| `custom_bands.json` | Bands you made with **B**. |
| `history.json` | What you have listened to. |
| `ui_settings.json` | Equalizer, enhancements, which modes are shown. |
| `audio_presets.json` | Your own equalizer presets. |

To move the radio to another computer, copy this folder across and your
favorites come with you.

---

## Turning on Analog Radio

Analog Radio mode listens to real shortwave through public **KiwiSDR**
receivers. Those receivers need a small helper program that is not included
here, because it belongs to another project.

1. Install Python from [python.org](https://www.python.org/downloads/) if
   you do not have it.
2. Download [KiwiClient](https://github.com/jks-prv/kiwiclient) and unzip it.
3. Create a file called `analog_radio.json` inside the `config` folder next
   to the radio, containing:

   ```json
   {
       "kiwi_client_dir": "C:\\path\\to\\kiwiclient"
   }
   ```

   Use the real path to where you unzipped it, with doubled backslashes.

Digital Radio and TV mode work perfectly without any of this. If you never
set it up, just turn Analog Radio off in Settings and forget about it.

---

## Credits and license

Station listings come from [Radio-Browser](https://www.radio-browser.info/).
Shortwave reception is provided by volunteers running
[KiwiSDR](http://kiwisdr.com/) receivers, reached with
[KiwiClient](https://github.com/jks-prv/kiwiclient).

Released under the MIT License. See `LICENSE` for the full text.
