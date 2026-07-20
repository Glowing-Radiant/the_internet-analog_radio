# The Internet Analog Radio

**"Rediscover your music the old way"**

The Internet Analog Radio is a minimalist, keyboard-driven radio player designed to simulate the tactile experience of tuning a physical receiver. It has a digital internet-station mode, a live analog KiwiSDR mode, static noise effects during tuning, a retro-style interface, and full screen reader accessibility.

## Features

*   **Digital Radio Mode**: Powered by the [Radio-Browser API](https://www.radio-browser.info/), giving access to thousands of internet stations worldwide through the existing analog-style dial.
*   **Analog Radio Mode**: Uses live KiwiSDR receivers through the upstream [jks-prv/kiwiclient](https://github.com/jks-prv/kiwiclient) tools.
*   **Analog Feel**: Simulates static noise and tuning delays for a nostalgic experience in frequency-based modes.
*   **Intelligent Bands**:
    *   **National**: Top stations from your country.
    *   **International**: Top voted stations globally.
    *   **Favorites**: Your saved stations.
    *   **🆕 History**: Your recently played stations (up to 100 entries).
    *   **Exploratory**: Search for specific genres or names.
*   **Custom Bands**: Save your search results as permanent bands (e.g., "Jazz", "News"). Custom bands are stored per mode (Radio/TV).
*   **Accessibility First**: Fully accessible with screen readers (NVDA, JAWS, Narrator) via `cytolk`.
*   **Keyboard Control**: Designed for completely mouse-free operation.
*   **Multi Mode**: Switch between **Digital Radio**, **Analog Radio**, and **TV Mode**.
*   **🆕 Playback History**: Automatically tracks your listening history with timestamps and duration. Access via the History band.
*   **🆕 Sleep Timer**: Set a timer to automatically stop playback after a specified duration with smooth fade-out.
*   **🆕 Audio Equalizer**: Built-in equalizer with 10 preset modes (Rock, Jazz, Classical, Speech, Bass Boost, etc.) for enhanced audio.

## TV Mode Features
*   **Direct Navigation**: Left/Right keys switch channels immediately (CH 1 -> CH 2).
*   **Clean Audio**: No static noise simulation in TV mode.
*   **Auto-Country**: Automatically finds National TV channels for your location.

## Analog Radio Mode Features
*   **KiwiSDR Support**: Fetches public KiwiSDR receivers and exposes shortwave tuning targets.
*   **Real Frequency Display**: Analog mode tunes in kHz across the HF range.
*   **External Client Playback**: Playback uses `kiwirecorder.py` from the upstream KiwiClient project.

## Requirements

*   Python 3.8+
*   **VLC Media Player**: Must be installed on your system (used for audio decoding).
    *   Windows: [Download VLC](https://www.videolan.org/vlc/download-windows.html)
    *   macOS: [Download VLC](https://www.videolan.org/vlc/download-macosx.html)
    *   Linux: `sudo apt install vlc` (or equivalent)
*   **Optional for Analog Radio**: A local clone or download of [jks-prv/kiwiclient](https://github.com/jks-prv/kiwiclient) with its dependencies installed.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/glowing-radiant/the-internet-analog-radio.git
    cd the-internet-analog-radio
    ```

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  To enable Analog Radio playback, install KiwiClient and point this app at it:
    ```bash
    git clone https://github.com/jks-prv/kiwiclient.git
    set KIWI_CLIENT_DIR=C:\path\to\kiwiclient
    ```

    You can also create `config/analog_radio.json`:
    ```json
    {
        "kiwi_client_dir": "C:\\path\\to\\kiwiclient",
        "refresh_public_receivers": false,
        "receivers": [
            {
                "name": "My KiwiSDR",
                "url": "http://example.com:8073",
                "country": "Local"
            }
        ]
    }
    ```
    The app does not contact the public KiwiSDR directory by default. Set `refresh_public_receivers` to `true` only if you want to refresh from `kiwisdr.com/.public/`. The `receivers` list is optional. Use it when the public KiwiSDR directory is unreachable or you want known-good receivers.

## Usage

Run the application:
```bash
python main.py
```

### Controls

| Key | Action |
| :--- | :--- |
| **Right Arrow** | Digital Radio: Tune Up (+0.1 MHz). Analog Radio: Tune Up (+1 kHz). <br> TV/History: Next Channel/Station. |
| **Left Arrow** | Digital Radio: Tune Down (-0.1 MHz). Analog Radio: Tune Down (-1 kHz). <br> TV/History: Prev Channel/Station. |
| **Ctrl + Arrows** | Frequency modes: Scan to next station (Debounced). |
| **Up / Down** | Volume Control (Time-based smooth adjustment) |
| **Tab** | Cycle Bands Forward (National -> International -> Favorites -> History -> Exploratory) |
| **Shift + Tab** | Cycle Bands Backward |
| **Ctrl + Tab** | **Switch Mode (Digital Radio / Analog Radio / TV)** |
| **+ (Plus)** | Add current station to Favorites |
| **- (Minus)** | Remove current station from Favorites |
| **M** | Toggle Mute |
| **S** | Search for a station (activates Exploratory band) |
| **F** | Enter a custom Stream URL |
| **B** | Save current Exploratory search as a Custom Band |
| **W** | Announce "Now Playing" metadata |
| **C** | Copy current Station URL to Clipboard |
| **🆕 T** | **Set Sleep Timer** - Enter duration in minutes |
| **🆕 Shift + T** | **Cancel Sleep Timer** |
| **🆕 E** | **Toggle Audio Equalizer** - Enable/disable equalizer |
| **🆕 P** | **Cycle Audio Presets** - Switch between EQ presets (forward) |
| **🆕 Shift + P** | **Cycle Audio Presets** - Switch between EQ presets (backward) |
| **Q** | Quit Application |

### Search & Custom Bands
1.  Press **S** and type a query (e.g., "LoFi").
2.  Press **Enter**. The radio switches to the "Exploratory" band with your results.
3.  If you like this collection, press **B** to save it as a permanent band named "LoFi".

### 🆕 Using Playback History
1.  Press **Tab** to cycle through bands until you reach the **History** band.
2.  Use **Left/Right Arrow** keys to navigate through your listening history.
3.  The currently selected station will play automatically (in Radio mode, you may need to tune to the station's frequency).

### 🆕 Using Sleep Timer
1.  Press **T** to open the sleep timer dialog.
2.  Enter the duration in minutes (e.g., "30" for 30 minutes).
3.  Press **Enter** to activate the timer.
4.  The audio will gradually fade out in the last 10 seconds before stopping.
5.  Press **Shift + T** to cancel an active timer.

### 🆕 Using Audio Equalizer
1.  Press **E** to toggle the equalizer on/off.
2.  Press **P** to cycle through available presets:
    *   Flat (neutral)
    *   Rock
    *   Jazz
    *   Classical
    *   Pop
    *   Bass Boost
    *   Treble Boost
    *   Speech
    *   Vocal
    *   Live
3.  The current preset is displayed in the status bar at the bottom of the screen.

## Configuration

Configuration files are stored in the `config/` directory:
*   `favorites.json`: Stores your favorite stations per mode.
*   `custom_bands.json`: Stores your saved custom bands per mode.
*   `analog_radio.json`: Optional KiwiClient path configuration.
*   `kiwi_receivers_cache.json`: Last successful public KiwiSDR receiver list.
*   `user_region.json`: Caches your detected location.
*   **🆕** `history.json`: Stores your playback history (up to 100 entries per mode).
*   **🆕** `audio_presets.json`: Stores your custom audio equalizer presets.


## License

MIT License. See `LICENSE` for details.
