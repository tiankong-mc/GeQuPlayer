"""底部播放控制栏"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider,
)

from core.audio_engine import AudioEngine
from core.playback_queue import MODE_ICONS, MODE_NAMES
from utils.helpers import format_time


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

        # 歌曲信息
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

        # 播放模式按钮
        self.btn_mode = QPushButton(MODE_ICONS["loop_list"])
        self.btn_mode.setObjectName("IconButton")
        self.btn_mode.setFixedWidth(38)
        self.btn_mode.setToolTip("列表循环")
        self.btn_mode.clicked.connect(lambda: self.mode_change_requested.emit())
        layout.addWidget(self.btn_mode)

        # 控制按钮
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setObjectName("IconButton")
        self.btn_prev.setToolTip("上一首")
        self.btn_prev.clicked.connect(lambda: self.prev_requested.emit())

        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PrimaryButton")
        self.btn_play.setFixedWidth(52)
        self.btn_play.setToolTip("播放/暂停")

        self.btn_next = QPushButton("⏭")
        self.btn_next.setObjectName("IconButton")
        self.btn_next.setToolTip("下一首")
        self.btn_next.clicked.connect(lambda: self.next_requested.emit())

        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_next)

        # 进度
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

        # 歌词显示开关
        self.btn_lyrics = QPushButton("词")
        self.btn_lyrics.setObjectName("IconButton")
        self.btn_lyrics.setCheckable(True)
        self.btn_lyrics.setChecked(False)
        self.btn_lyrics.setToolTip("显示/隐藏桌面歌词")
        self.btn_lyrics.clicked.connect(self._on_lyrics_btn)
        layout.addWidget(self.btn_lyrics)

        # 歌词锁定开关
        self.btn_lock = QPushButton("锁")
        self.btn_lock.setObjectName("IconButton")
        self.btn_lock.setCheckable(True)
        self.btn_lock.setChecked(False)
        self.btn_lock.setToolTip("锁定歌词：鼠标穿透，不可拖动")
        self.btn_lock.clicked.connect(self._on_lock_btn)
        layout.addWidget(self.btn_lock)

        # 连接
        self.btn_play.clicked.connect(self.audio.toggle_pause)
        self.audio.state_changed.connect(self._on_state)
        self.audio.position_changed.connect(self._on_position)
        self.audio.finished.connect(self._on_finished)

        self._is_slider_dragging = False
        self.slider.sliderPressed.connect(lambda: setattr(self, "_is_slider_dragging", True))
        self.slider.sliderReleased.connect(lambda: setattr(self, "_is_slider_dragging", False))

    # ---------- 接口 ----------
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
        self.btn_mode.setText(MODE_ICONS.get(mode, "🔁"))
        self.btn_mode.setToolTip(MODE_NAMES.get(mode, "列表循环"))

    def set_playing_ui(self, playing: bool):
        """外部改变播放状态时的 UI 同步"""
        self.btn_play.setText("⏸" if playing else "▶")

    # ---------- 内部 ----------
    def _on_state(self, state: str):
        if state == "playing":
            self.btn_play.setText("⏸")
        elif state == "paused":
            self.btn_play.setText("▶")
        else:
            self.btn_play.setText("▶")

    def _on_position(self, cur: float, total: float):
        self.lbl_cur.setText(format_time(cur))
        self.lbl_total.setText(format_time(total))
        if total > 0 and not self._is_slider_dragging:
            self.slider.setValue(int(cur / total * 1000))

    def _on_finished(self):
        self.btn_play.setText("▶")
        self.slider.setValue(0)

    def _on_seek(self):
        if self.audio.duration > 0:
            self.audio.seek(self.slider.value() / 1000.0 * self.audio.duration)

    def _on_lyrics_btn(self):
        self.toggle_lyrics.emit(self.btn_lyrics.isChecked())

    def _on_lock_btn(self):
        self.toggle_lyric_lock.emit(self.btn_lock.isChecked())
