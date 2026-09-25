"""本地音乐面板：左歌单 / 右歌曲 + 搜索"""
import os
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QFileDialog, QMenu, QSplitter, QLineEdit,
)

from core.local_library import (
    scan_directory, scan_playlists, LocalSong, LocalPlaylist,
)
from utils.helpers import load_config, save_config
from config import DEFAULT_DOWNLOAD_DIR


class _ClickableLabel(QLabel):
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class PlaylistRowWidget(QWidget):
    play_all_requested = pyqtSignal()
    selected_requested = pyqtSignal()

    def __init__(self, name: str, count: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(6)

        self.label = _ClickableLabel(f"{name}  ({count})")
        self.label.setStyleSheet("color: #e6e6e6; background: transparent;")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.double_clicked.connect(self.selected_requested)
        layout.addWidget(self.label, 1)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(28, 24)
        self.btn_play.setObjectName("IconButton")
        self.btn_play.setToolTip("一键播放此歌单")
        self.btn_play.clicked.connect(self.play_all_requested)
        layout.addWidget(self.btn_play)

        self.setStyleSheet("background: transparent;")


class LocalPanel(QWidget):
    play_list_requested = pyqtSignal(list, int)
    set_download_dir = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_songs = []
        self._playlists = []
        self._current_list = []
        self._displayed_list = []

        cfg = load_config()
        self._dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.lbl_dir = QLabel(f"目录：{self._dir}")
        self.lbl_dir.setStyleSheet("color:#9a9a9a;")
        self.lbl_dir.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        btn_change = QPushButton("更换目录")
        btn_change.clicked.connect(self._change_dir)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh)
        bar.addWidget(self.lbl_dir, 1)
        bar.addWidget(btn_change)
        bar.addWidget(btn_refresh)
        layout.addLayout(bar)

        search_bar = QHBoxLayout()
        search_bar.setSpacing(8)
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("搜索本地歌曲：输入歌名或歌手（实时过滤）")
        self.input_search.setClearButtonEnabled(True)
        self.input_search.textChanged.connect(self._on_search_changed)
        self.btn_clear_search = QPushButton("清空")
        self.btn_clear_search.setFixedWidth(60)
        self.btn_clear_search.clicked.connect(lambda: self.input_search.clear())
        search_bar.addWidget(self.input_search, 1)
        search_bar.addWidget(self.btn_clear_search)
        layout.addLayout(search_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)
        ll.addWidget(QLabel("本地歌单"))
        self.list_pl = QListWidget()
        self.list_pl.itemClicked.connect(self._on_playlist_clicked)
        self.list_pl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_pl.customContextMenuRequested.connect(self._on_playlist_menu)
        ll.addWidget(self.list_pl, 1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        top2 = QHBoxLayout()
        self.lbl_right_title = QLabel("全部歌曲")
        top2.addWidget(self.lbl_right_title)
        top2.addStretch(1)
        self.btn_play_all = QPushButton("▶ 一键播放")
        self.btn_play_all.setObjectName("PrimaryButton")
        self.btn_play_all.clicked.connect(self._play_current_list_all)
        top2.addWidget(self.btn_play_all)
        rl.addLayout(top2)
        self.list_songs = QListWidget()
        self.list_songs.itemDoubleClicked.connect(self._on_song_double_click)
        self.list_songs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_songs.customContextMenuRequested.connect(self._on_song_menu)
        rl.addWidget(self.list_songs, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#8b8b8b;")
        layout.addWidget(self.status)

    # ---------- 搜索 ----------
    def _on_search_changed(self, text: str):
        keyword = (text or "").strip().lower()
        if not keyword:
            self._render_songs(self._current_list)
            total = len(self._current_list)
            if total:
                self.status.setText(f"共 {total} 首歌曲")
            return
        filtered = [
            s for s in self._current_list
            if keyword in s.title.lower() or keyword in s.artist.lower()
        ]
        self._render_songs(filtered)
        self.status.setText(
            f"搜索「{keyword}」：找到 {len(filtered)} / {len(self._current_list)} 首"
        )

    # ---------- 刷新 ----------
    def refresh(self):
        self._all_songs = scan_directory(self._dir)
        self._playlists = scan_playlists(self._dir)

        self.list_pl.clear()

        item_all = QListWidgetItem()
        item_all.setSizeHint(QSize(0, 32))
        self.list_pl.addItem(item_all)
        lbl_all = _ClickableLabel(f"全部歌曲  ({len(self._all_songs)})")
        lbl_all.setStyleSheet("color: #a0e0a0; background: transparent; font-weight: bold;")
        lbl_all.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_all.double_clicked.connect(lambda: self._show_all_songs())
        self.list_pl.setItemWidget(item_all, lbl_all)

        for pl in self._playlists:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 32))
            self.list_pl.addItem(item)
            row = PlaylistRowWidget(pl.name, pl.count, self.list_pl)
            row.selected_requested.connect(lambda _pl=pl: self._show_playlist(_pl))
            row.play_all_requested.connect(lambda _pl=pl: self._play_playlist(_pl))
            self.list_pl.setItemWidget(item, row)

        self._show_all_songs()

        self.status.setText(
            f"共 {len(self._all_songs)} 首歌曲 / {len(self._playlists)} 个歌单"
        )

    def _show_all_songs(self):
        # 清空搜索框，避免旧关键词过滤新列表
        if self.input_search.text():
            self.input_search.blockSignals(True)
            self.input_search.clear()
            self.input_search.blockSignals(False)

        self._current_list = list(self._all_songs)
        self.lbl_right_title.setText(f"全部歌曲（{len(self._current_list)}）")
        self._render_songs(self._current_list)

    def _show_playlist(self, pl: LocalPlaylist):
        # 清空搜索框，避免旧关键词过滤新列表
        if self.input_search.text():
            self.input_search.blockSignals(True)
            self.input_search.clear()
            self.input_search.blockSignals(False)

        self._current_list = list(pl.songs)
        self.lbl_right_title.setText(f"{pl.name}（{len(self._current_list)}）")
        self._render_songs(self._current_list)

    def _render_songs(self, songs):
        self._displayed_list = list(songs)
        self.list_songs.clear()
        for s in songs:
            item = QListWidgetItem(s.display)
            item.setToolTip(s.path)
            self.list_songs.addItem(item)

    # ---------- 播放 ----------
    def _on_song_double_click(self, item):
        idx = self.list_songs.row(item)
        if 0 <= idx < len(self._displayed_list):
            self.play_list_requested.emit(self._displayed_list, idx)

    def _play_current_list_all(self):
        lst = self._displayed_list if self._displayed_list else self._current_list
        if not lst:
            self.status.setText("列表为空")
            return
        self.play_list_requested.emit(list(lst), 0)

    def _play_playlist(self, pl: LocalPlaylist):
        if not pl.songs:
            self.status.setText(f"歌单「{pl.name}」为空")
            return
        self.play_list_requested.emit(list(pl.songs), 0)
        self.status.setText(f"正在播放歌单：{pl.name}")

    def _on_playlist_clicked(self, item):
        idx = self.list_pl.row(item)
        if idx == 0:
            self._show_all_songs()
        elif 0 < idx <= len(self._playlists):
            pl = self._playlists[idx - 1]
            self._show_playlist(pl)

    # ---------- 菜单 ----------
    def _on_song_menu(self, pos):
        item = self.list_songs.itemAt(pos)
        if not item:
            return
        idx = self.list_songs.row(item)
        if not (0 <= idx < len(self._displayed_list)):
            return
        s = self._displayed_list[idx]
        menu = QMenu(self)
        act_play = menu.addAction("播放")
        act_folder = menu.addAction("打开所在文件夹")
        act = menu.exec(self.list_songs.mapToGlobal(pos))
        if act == act_play:
            self.play_list_requested.emit(self._displayed_list, idx)
        elif act == act_folder:
            os.startfile(os.path.dirname(s.path))

    def _on_playlist_menu(self, pos):
        item = self.list_pl.itemAt(pos)
        if not item:
            return
        idx = self.list_pl.row(item)
        if idx <= 0 or idx > len(self._playlists):
            return
        pl = self._playlists[idx - 1]
        menu = QMenu(self)
        act_play = menu.addAction("一键播放")
        act_open = menu.addAction("打开 .m3u 文件位置")
        act_delete = menu.addAction("删除歌单")
        act = menu.exec(self.list_pl.mapToGlobal(pos))
        if act == act_play:
            self._play_playlist(pl)
        elif act == act_open:
            os.startfile(os.path.dirname(pl.m3u_path))
        elif act == act_delete:
            try:
                os.remove(pl.m3u_path)
                self.refresh()
            except Exception as e:
                self.status.setText(f"删除失败: {e}")

    # ---------- 目录 ----------
    def _change_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择音乐目录", self._dir)
        if d:
            self._dir = d
            self.lbl_dir.setText(f"目录：{d}")
            cfg = load_config()
            cfg["download_dir"] = d
            save_config(cfg)
            self.set_download_dir.emit(d)
            self.refresh()
