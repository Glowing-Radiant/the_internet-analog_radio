import PyInstaller.__main__
import os
import shutil
import cytolk

# Get cytolk path to include its DLLs/so files
cytolk_path = os.path.dirname(cytolk.__file__)

APP_NAME = 'InternetAnalogRadio'
DIST_DIR = os.path.join('dist', APP_NAME)

# Docs that go into the zip alongside the exe.
DOCS = ['USER_GUIDE.md', 'CHANGELOG.md', 'LICENSE']

# Define build arguments
# NOTE: sounds are intentionally NOT passed via --add-data. The app loads
# sounds from a relative "sounds" path next to the executable, so the
# directory is copied into the onedir output after the build instead (see
# below). --onefile bundles data into a temp extraction dir at runtime
# (not next to the exe), and PyInstaller's --add-data for onedir builds
# nests it under _internal, so neither location matches what the code expects.
args = [
    'main.py',
    f'--name={APP_NAME}',
    '--noconsole',  # Hidden by default, main.py allocates if needed
    '--clean',
    '--noconfirm',  # Never stop to ask about wiping the old dist output
    # Add cytolk package data (includes DLLs usually)
    f'--add-data={cytolk_path}{os.pathsep}cytolk',
    # Hidden imports that might be missed
    '--hidden-import=av',
    '--hidden-import=sounddevice',
    '--hidden-import=_sounddevice_data',
    '--hidden-import=numpy',
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
    # PyInstaller probes the stream before writing to it, so pass the
    # questions through to the real stdout instead of blowing up.
    def isatty(self):
        return getattr(self.terminal, 'isatty', lambda: False)()
    def fileno(self):
        return self.terminal.fileno()
    @property
    def encoding(self):
        return getattr(self.terminal, 'encoding', 'utf-8')

sys.stdout = Logger()
sys.stderr = sys.stdout

print("Starting build process...")
print("Building with args:", args)

try:
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    print("Build finished successfully.")

    # Copy the sounds directory next to the exe (top level of the onedir
    # output), matching the relative "sounds" path the app looks for at runtime.
    dist_sounds_dir = os.path.join(DIST_DIR, 'sounds')
    if os.path.exists(dist_sounds_dir):
        shutil.rmtree(dist_sounds_dir)
    shutil.copytree('sounds', dist_sounds_dir)
    print(f"Copied sounds directory to {dist_sounds_dir}")

    # Ship the reader-facing docs beside the exe. README.md is deliberately
    # left out: it documents running from source, which nobody downloading
    # the zip is doing.
    for doc in DOCS:
        if os.path.exists(doc):
            shutil.copy2(doc, os.path.join(DIST_DIR, doc))
            print(f"Copied {doc} to {DIST_DIR}")
        else:
            print(f"WARNING: {doc} not found, not shipping it")

    # Zip up the onedir output for distribution.
    zip_base_name = os.path.join('dist', f'{APP_NAME}-windows')
    archive_path = shutil.make_archive(zip_base_name, 'zip', root_dir='dist', base_dir=APP_NAME)
    print(f"Created release archive: {archive_path}")
except Exception as e:
    print(f"Build failed with error: {e}")
    sys.exit(1)

