MODE_DIGITAL_RADIO = "digital_radio"
MODE_ANALOG_RADIO = "analog_radio"
MODE_TV = "tv"

MODE_ALIASES = {
    "radio": MODE_DIGITAL_RADIO,
    "digital": MODE_DIGITAL_RADIO,
    "digital radio": MODE_DIGITAL_RADIO,
    "analog": MODE_ANALOG_RADIO,
    "analog radio": MODE_ANALOG_RADIO,
}

ALL_MODES = [MODE_DIGITAL_RADIO, MODE_ANALOG_RADIO, MODE_TV]
FREQUENCY_MODES = {MODE_DIGITAL_RADIO, MODE_ANALOG_RADIO}

MODE_LABELS = {
    MODE_DIGITAL_RADIO: "Digital Radio",
    MODE_ANALOG_RADIO: "Analog Radio",
    MODE_TV: "TV",
}


def normalize_mode(mode):
    if not isinstance(mode, str):
        return MODE_DIGITAL_RADIO
    key = mode.strip().lower()
    return MODE_ALIASES.get(key, key)


def mode_label(mode):
    return MODE_LABELS.get(normalize_mode(mode), str(mode).replace("_", " ").title())
