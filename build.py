import PyInstaller.__main__
import os
import shutil
import cytolk

# Get cytolk path to include its DLLs/so files
cytolk_path = os.path.dirname(cytolk.__file__)

# Define build arguments
args = [
    'main.py',
    '--name=InternetAnalogRadio',
    '--onefile',
    '--noconsole',  # Hidden by default, main.py allocates if needed
    '--clean',
    # Add cytolk package data (includes DLLs usually)
    f'--add-data={cytolk_path}{os.pathsep}cytolk',
    # Hidden imports that might be missed
    '--hidden-import=vlc',
    '--hidden-import=cytolk',
    '--hidden-import=requests',
    '--hidden-import=pygame',
    '--hidden-import=tkinter',
]


# Redirect output to file for debugging
import sys
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("build_log.txt", "w")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.log.flush()

sys.stdout = Logger()
sys.stderr = sys.stdout

print("Starting build process...")
print("Building with args:", args)

try:
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    print("Build finished successfully.")
except Exception as e:
    print(f"Build failed with error: {e}")

