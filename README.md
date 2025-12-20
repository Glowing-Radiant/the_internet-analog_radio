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
    *   **Exploratory**: Search for specific genres or names.
*   **Custom Bands**: Save your search results as permanent bands (e.g., "Jazz", "News").
*   **Accessibility First**: Fully accessible with screen readers (NVDA, JAWS, Narrator) via `cytolk`.
*   **Keyboard Control**: Designed for completely mouse-free operation.

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
| **Left / Right** | Tune Station (Hold for fast seek) |
| **Up / Down** | Volume Control |
| **Tab** | Cycle Bands Forward (Local -> National -> ...) |
| **Shift + Tab** | Cycle Bands Backward |
| **+ (Plus)** | Add current station to Favorites |
| **- (Minus)** | Remove current station from Favorites |
| **M** | Toggle Mute |
| **S** | Search for a station (activates Exploratory band) |
| **F** | Enter a custom Stream URL |
| **B** | Save current Exploratory search as a Custom Band |
| **W** | Announce "Now Playing" metadata |
| **C** | Copy current Station URL to Clipboard |
| **Q** | Quit Application |

### Search & Custom Bands
1.  Press **S** and type a query (e.g., "LoFi").
2.  Press **Enter**. The radio switches to the "Exploratory" band with your results.
3.  If you like this collection, press **B** to save it as a permanent band named "LoFi".

## Configuration

Configuration files are stored in the `config/` directory:
*   `favorites.json`: Stores your favorite stations.
*   `custom_bands.json`: Stores your saved custom bands.
*   `user_region.json`: Caches your detected location.

## License

MIT License. See `LICENSE` for details.
