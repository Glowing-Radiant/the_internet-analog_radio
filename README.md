# The Internet Analog Radio

**"Rediscover your music the old way"**

The Internet Analog Radio is a minimalist, keyboard-driven internet radio player designed to simulate the tactile experience of an analog radio. It features static noise effects during tuning, a retro-style interface, and full screen reader accessibility.

## Features

*   **Analog Feel**: Simulates static noise and tuning delays for a nostalgic experience.
*   **Global Station Database**: Powered by the [Radio-Browser API](https://www.radio-browser.info/), giving access to thousands of stations worldwide.
*   **Intelligent Bands**:
    *   **Local**: Automatically detects your location (via IP) to find nearby stations (using Geo-Coordinates).
    *   **National**: Top stations from your country.
    *   **International**: Top voted stations globally.
    *   **Favorites**: Your saved stations.
    *   **🆕 History**: Your recently played stations (up to 100 entries).
    *   **Exploratory**: Search for specific genres or names.
*   **Custom Bands**: Save your search results as permanent bands (e.g., "Jazz", "News").
*   **Accessibility First**: Fully accessible with screen readers (NVDA, JAWS, Narrator) via `cytolk`.
*   **Keyboard Control**: Designed for completely mouse-free operation.
*   **Dual Mode**: Switch between **Radio Mode** (Analog tuning) and **TV Mode** (Direct Channel Indexing).
*   **🆕 Playback History**: Automatically tracks your listening history with timestamps and duration. Access via the History band.
*   **🆕 Sleep Timer**: Set a timer to automatically stop playback after a specified duration with smooth fade-out.
*   **🆕 Audio Equalizer**: Built-in equalizer with 10 preset modes (Rock, Jazz, Classical, Speech, Bass Boost, etc.) for enhanced audio.

## TV Mode Features
*   **Direct Navigation**: Left/Right keys switch channels immediately (CH 1 -> CH 2).
*   **Clean Audio**: No static noise simulation in TV mode.
*   **Auto-Country**: Automatically finds National TV channels for your location.

## Requirements

*   Python 3.8+
*   **VLC Media Player**: Must be installed on your system (used for audio decoding).
    *   Windows: [Download VLC](https://www.videolan.org/vlc/download-windows.html)
    *   macOS: [Download VLC](https://www.videolan.org/vlc/download-macosx.html)
    *   Linux: `sudo apt install vlc` (or equivalent)

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

## Usage

Run the application:
```bash
python main.py
```

### Controls

| Key | Action |
| :--- | :--- |
| **Right Arrow** | Radio: Tune Up (+0.1 MHz). Hold for smooth tuning. <br> TV/History: Next Channel/Station. |
| **Left Arrow** | Radio: Tune Down (-0.1 MHz). Hold for smooth tuning. <br> TV/History: Prev Channel/Station. |
| **Ctrl + Arrows** | Radio: Scan to next station (Debounced). |
| **Up / Down** | Volume Control (Time-based smooth adjustment) |
| **Tab** | Cycle Bands Forward (Local -> National -> International -> Favorites -> History -> Exploratory) |
| **Shift + Tab** | Cycle Bands Backward |
| **Ctrl + Tab** | **Switch Mode (Radio / TV)** |
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
*   `favorites.json`: Stores your favorite stations.
*   `custom_bands.json`: Stores your saved custom bands.
*   `user_region.json`: Caches your detected location.
*   **🆕** `history.json`: Stores your playback history (up to 100 entries per mode).
*   **🆕** `audio_presets.json`: Stores your custom audio equalizer presets.

## License

MIT License. See `LICENSE` for details.
