try:
    from cytolk import tolk
except ImportError:
    tolk = None

class AccessibilityManager:
    def __init__(self):
        self.available = False
        if tolk:
            try:
                tolk.load()
                self.available = True
                print(f"Screen reader loaded: {tolk.detect_screen_reader()}")
                tolk.speak("Internet Analog Radio Ready")
            except Exception as e:
                print(f"Error initializing cytolk: {e}")
                self.available = False
        else:
            print("cytolk module not found. Accessibility disabled.")

    def speak(self, text):
        if self.available and text:
            try:
                tolk.speak(text)
            except Exception:
                pass
