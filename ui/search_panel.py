"""搜索面板：列表每行带下载按钮"""
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel,
)

from core.gequbao_api import Song, search
from utils.helpers import run_async


class _ClickableLabel(QLabel):
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class SongRowWidget(QWidget):
    play_requested = pyqtSignal()
    download_requested = pyqtSignal()

    def __init__(self, song: Song, parent=None):
        super().__init__(parent)
        self.song = song

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 6, 2)
        layout.setSpacing(8)

        self.label = _ClickableLabel(song.display)
        self.label.setStyleSheet("color: #e6e6e6; background: transparent;")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setToolTip("双击播放")
        self.label.double_clicked.connect(self.play_requested)
        layout.addWidget(self.label, 1)

        self.btn_dl = QPushButton("下载")
        self.btn_dl.setFixedSize(60, 26)
        self.btn_dl.setObjectName("IconButton")
        self.btn_dl.clicked.connect(self.download_requested)
        layout.addWidget(self.btn_dl)

        self.setStyleSheet("background: transparent;")


class SearchPanel(QWidget):
    # (歌曲列表, 起始索引)
    play_list_requested = pyqtSignal(list, int)
    download_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._songs = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("搜索歌曲 / 歌手 / 关键词（回车确认）")
        self.input.returnPressed.connect(self.do_search)
        self.btn_search = QPushButton("搜索")
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_search.setFixedWidth(90)
        self.btn_search.clicked.connect(self.do_search)
        bar.addWidget(self.input, 1)
        bar.addWidget(self.btn_search)
        layout.addLayout(bar)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)

        self.status = QLabel("输入关键词后回车搜索")
        self.status.setStyleSheet("color:#8b8b8b;")
        layout.addWidget(self.status)

    def do_search(self):
        keyword = self.input.text().strip()
        if not keyword:
            return
        self.btn_search.setEnabled(False)
        self.status.setText("搜索中...")
        self.list.clear()
        self._songs = []

        run_async(
            lambda: search(keyword),
            on_done=self._on_results,
            on_error=self._on_error,
        )

    def _on_results(self, songs):
        self._songs = songs
        self.list.clear()
        for i, s in enumerate(songs):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 38))
            self.list.addItem(item)

            row = SongRowWidget(s, self.list)
            row.play_requested.connect(lambda idx=i: self.play_list_requested.emit(self._songs, idx))
            row.download_requested.connect(lambda s=s: self.download_requested.emit(s))
            self.list.setItemWidget(item, row)

        self.status.setText(f"共找到 {len(songs)} 条结果 · 双击播放（自动顺序播放下一首）/ 点下载按钮加入队列")
        self.btn_search.setEnabled(True)

    def _on_error(self, err):
        self.status.setText(f"搜索失败：{err}")
        self.btn_search.setEnabled(True)
