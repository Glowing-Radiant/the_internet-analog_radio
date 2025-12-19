import json
import os

class ConfigManager:
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def load_json(self, filename, default=None):
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            return default if default is not None else {}
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default if default is not None else {}

    def save_json(self, filename, data):
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except IOError:
            return False
