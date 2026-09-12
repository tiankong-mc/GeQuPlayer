import sys
print("[1] start", flush=True)
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print("[2] app created", flush=True)

from core.audio_engine import AudioEngine
print("[3] AudioEngine class imported", flush=True)

e = AudioEngine()
print("[4] AudioEngine instance created", flush=True)
print("done")
