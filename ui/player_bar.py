"""底部播放控制栏（SVG 图标版）"""
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider,
)

from core.audio_engine import AudioEngine
from core.playback_queue import MODE_NAMES
from utils.helpers import format_time
from utils.icon_helper import get_icon


MODE_ICON_MAP = {
    "loop_list": "repeat_all",
    "loop_one": "repeat_one",
    "sequence": "sequential",
    "shuffle": "shuffle",
}

ICON_SIZE = 20
PLAY_ICON_SIZE = 24


class PlayerBar(QWidget):
    toggle_lyrics = pyqtSignal(bool)
    toggle_lyric_lock = pyqtSignal(bool)
    prev_requested = pyqtSignal()
    next_requested = pyqtSignal()
    mode_change_requested = pyqtSignal()

    def __init__(self, audio: AudioEngine, parent=None):
        super().__init__(parent)
        self.audio = audio
        self.setFixedHeight(72)
        self.setObjectName("PlayerBar")
        self.setStyleSheet(
            "#PlayerBar { background-color: #1b1c20; border-top: 1px solid #26272c; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(10)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        self.lbl_title = QLabel("未播放")
        self.lbl_title.setObjectName("TitleLabel")
        self.lbl_artist = QLabel("")
        self.lbl_artist.setStyleSheet("color:#9a9a9a; font-size:12px;")
        info_box.addWidget(self.lbl_title)
        info_box.addWidget(self.lbl_artist)

        info_wrap = QWidget()
        info_wrap.setLayout(info_box)
        info_wrap.setFixedWidth(220)
        layout.addWidget(info_wrap)

        self.btn_mode = QPushButton()
        self.btn_mode.setObjectName("IconButton")
        self.btn_mode.setFixedSize(38, 38)
        self.btn_mode.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btn_mode.setToolTip("列表循环")
        self.btn_mode.clicked.connect(lambda: self.mode_change_requested.emit())
        layout.addWidget(self.btn_mode)

        self.btn_prev = QPushButton()
        self.btn_prev.setObjectName("IconButton")
        self.btn_prev.setFixedSize(38, 38)
        self.btn_prev.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btn_prev.setIcon(get_icon("prev", ICON_SIZE))
        self.btn_prev.setToolTip("上一首")
        self.btn_prev.clicked.connect(lambda: self.prev_requested.emit())
        layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        self.btn_play.setObjectName("PrimaryButton")
        self.btn_play.setFixedSize(48, 48)
        self.btn_play.setIconSize(QSize(PLAY_ICON_SIZE, PLAY_ICON_SIZE))
        self.btn_play.setIcon(get_icon("play", PLAY_ICON_SIZE, color="#0e0f12"))
        self.btn_play.setToolTip("播放/暂停")
        layout.addWidget(self.btn_play)

        self.btn_next = QPushButton()
        self.btn_next.setObjectName("IconButton")
        self.btn_next.setFixedSize(38, 38)
        self.btn_next.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btn_next.setIcon(get_icon("next", ICON_SIZE))
        self.btn_next.setToolTip("下一首")
        self.btn_next.clicked.connect(lambda: self.next_requested.emit())
        layout.addWidget(self.btn_next)

        self.lbl_cur = QLabel("00:00")
        self.lbl_cur.setFixedWidth(46)
        self.lbl_cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderReleased.connect(self._on_seek)
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setFixedWidth(46)
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lbl_cur)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.lbl_total)

        self.btn_lyrics = QPushButton("词")
        self.btn_lyrics.setObjectName("IconButton")
        self.btn_lyrics.setCheckable(True)
        self.btn_lyrics.setChecked(False)
        self.btn_lyrics.setToolTip("显示/隐藏桌面歌词")
        self.btn_lyrics.clicked.connect(self._on_lyrics_btn)
        layout.addWidget(self.btn_lyrics)

        self.btn_lock = QPushButton("锁")
        self.btn_lock.setObjectName("IconButton")
        self.btn_lock.setCheckable(True)
        self.btn_lock.setChecked(False)
        self.btn_lock.setToolTip("锁定歌词：鼠标穿透，不可拖动")
        self.btn_lock.clicked.connect(self._on_lock_btn)
        layout.addWidget(self.btn_lock)

        self.btn_play.clicked.connect(self.audio.toggle_pause)
        self.audio.state_changed.connect(self._on_state)
        self.audio.position_changed.connect(self._on_position)
        self.audio.finished.connect(self._on_finished)

        self._is_slider_dragging = False
        self.slider.sliderPressed.connect(lambda: setattr(self, "_is_slider_dragging", True))
        self.slider.sliderReleased.connect(lambda: setattr(self, "_is_slider_dragging", False))

        self.set_mode("loop_list")

    def set_song(self, title: str, artist: str = ""):
        self.lbl_title.setText(title or "未播放")
        self.lbl_artist.setText(artist or "")

    def set_lyrics_checked(self, checked: bool):
        self.btn_lyrics.blockSignals(True)
        self.btn_lyrics.setChecked(checked)
        self.btn_lyrics.blockSignals(False)

    def set_lock_checked(self, checked: bool):
        self.btn_lock.blockSignals(True)
        self.btn_lock.setChecked(checked)
        self.btn_lock.blockSignals(False)

    def set_mode(self, mode: str):
        icon_name = MODE_ICON_MAP.get(mode, "repeat_all")
        self.btn_mode.setIcon(get_icon(icon_name, ICON_SIZE))
        self.btn_mode.setToolTip(MODE_NAMES.get(mode, "列表循环"))

    def set_playing_ui(self, playing: bool):
        self._update_play_icon(playing)

    def _update_play_icon(self, playing: bool):
        if playing:
            self.btn_play.setIcon(get_icon("pause", PLAY_ICON_SIZE, color="#0e0f12"))
        else:
            self.btn_play.setIcon(get_icon("play", PLAY_ICON_SIZE, color="#0e0f12"))

    def _on_state(self, state: str):
        if state == "loading":
            # 加载中：禁用按钮避免误点
            self.btn_play.setEnabled(False)
        else:
            self.btn_play.setEnabled(True)
            self._update_play_icon(state == "playing")

    def _on_position(self, cur: float, total: float):
        self.lbl_cur.setText(format_time(cur))
        self.lbl_total.setText(format_time(total))
        if total > 0 and not self._is_slider_dragging:
            self.slider.setValue(int(cur / total * 1000))

    def _on_finished(self):
        self._update_play_icon(False)
        self.slider.setValue(0)

    def _on_seek(self):
        if self.audio.duration > 0:
            self.audio.seek(self.slider.value() / 1000.0 * self.audio.duration)

    def _on_lyrics_btn(self):
        self.toggle_lyrics.emit(self.btn_lyrics.isChecked())

    def _on_lock_btn(self):
        self.toggle_lyric_lock.emit(self.btn_lock.isChecked())
