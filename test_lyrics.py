import sys
print("[1] start", flush=True)
from PyQt6.QtWidgets import QApplication
print("[2] QApplication imported", flush=True)
app = QApplication(sys.argv)
print("[3] app created", flush=True)

from ui.lyrics_window import LyricsWindow
print("[4] LyricsWindow class imported", flush=True)

w = LyricsWindow()
print("[5] LyricsWindow instance created", flush=True)

w.show()
print("[6] shown", flush=True)

sys.exit(app.exec())
