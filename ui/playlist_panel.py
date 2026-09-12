"""歌单面板：热门歌单 + 搜索歌单 + 粘贴分享链接 + 勾选下载 + 每首歌下载按钮"""
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QSplitter, QInputDialog,
    QMessageBox, QLineEdit, QCheckBox,
)

from core.playlist_parser import (
    get_hot_playlists, get_playlist_songs, parse_playlist_url,
    search_playlists,
)
from utils.helpers import run_async


class _ClickableLabel(QLabel):
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class PlaylistSongRow(QWidget):
    play_requested = pyqtSignal()
    download_requested = pyqtSignal()
    checked_changed = pyqtSignal()

    def __init__(self, title: str, artist: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.artist = artist

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(22)
        self.checkbox.stateChanged.connect(lambda _: self.checked_changed.emit())
        layout.addWidget(self.checkbox)

        # 歌名+歌手（双击播放）
        text = f"{title} - {artist}" if artist else title
        self.label = _ClickableLabel(text)
        self.label.setStyleSheet("color: #e6e6e6; background: transparent;")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setToolTip("双击播放")
        self.label.double_clicked.connect(self.play_requested)
        layout.addWidget(self.label, 1)

        # 单曲下载按钮
        self.btn_dl = QPushButton("下载")
        self.btn_dl.setFixedSize(60, 26)
        self.btn_dl.setObjectName("IconButton")
        self.btn_dl.setToolTip("只下载这一首")
        self.btn_dl.clicked.connect(self.download_requested)
        layout.addWidget(self.btn_dl)

        self.setStyleSheet("background: transparent;")

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(checked)
        self.checkbox.blockSignals(False)


class PlaylistPanel(QWidget):
    play_list_requested = pyqtSignal(list, int)         # (PlaylistSong 列表, 起始索引)
    download_requested = pyqtSignal(list, str)          # (tasks[(title, artist)], playlist_name)
    download_single_requested = pyqtSignal(str, str)    # (title, artist)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(10)

        # ---------- 第一行：平台 + 热门 + 分享 ----------
        bar1 = QHBoxLayout()
        bar1.setSpacing(10)
        self.platform = QComboBox()
        self.platform.addItem("酷狗音乐", "kugou")
        self.platform.addItem("QQ音乐", "qq")

        self.btn_load = QPushButton("加载热门歌单")
        self.btn_load.setObjectName("PrimaryButton")
        self.btn_load.clicked.connect(self.load_playlists)

        self.btn_paste = QPushButton("粘贴歌单链接")
        self.btn_paste.setToolTip("粘贴酷狗或QQ音乐的分享链接/酷狗码")
        self.btn_paste.clicked.connect(self.paste_share_link)

        bar1.addWidget(QLabel("平台："))
        bar1.addWidget(self.platform)
        bar1.addWidget(self.btn_load)
        bar1.addWidget(self.btn_paste)
        bar1.addStretch(1)
        layout.addLayout(bar1)

        # ---------- 第二行：搜索歌单 ----------
        bar2 = QHBoxLayout()
        bar2.setSpacing(10)
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText(
            "搜索歌单：输入关键词，如「深夜 emo」「抖音热歌」（回车确认）"
        )
        self.input_search.returnPressed.connect(self.search_playlists)
        self.btn_search = QPushButton("搜索歌单")
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_search.setFixedWidth(100)
        self.btn_search.clicked.connect(self.search_playlists)
        bar2.addWidget(self.input_search, 1)
        bar2.addWidget(self.btn_search)
        layout.addLayout(bar2)

        # ---------- 左右分栏 ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左：歌单列表
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)
        self.lbl_left_title = QLabel("歌单列表")
        ll.addWidget(self.lbl_left_title)
        self.list_pl = QListWidget()
        self.list_pl.itemClicked.connect(self._on_playlist_selected)
        ll.addWidget(self.list_pl, 1)

        # 右：歌曲列表 + 操作按钮
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)

        # 操作栏
        top2 = QHBoxLayout()
        top2.setSpacing(8)
        top2.addWidget(QLabel("歌曲列表"))
        top2.addStretch(1)

        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setObjectName("IconButton")
        self.btn_select_all.clicked.connect(self._select_all)
        top2.addWidget(self.btn_select_all)

        self.btn_unselect_all = QPushButton("全不选")
        self.btn_unselect_all.setObjectName("IconButton")
        self.btn_unselect_all.clicked.connect(self._unselect_all)
        top2.addWidget(self.btn_unselect_all)

        self.btn_download_checked = QPushButton("下载勾选")
        self.btn_download_checked.setObjectName("PrimaryButton")
        self.btn_download_checked.clicked.connect(self._download_checked)
        top2.addWidget(self.btn_download_checked)

        rl.addLayout(top2)

        self.list_songs = QListWidget()
        rl.addWidget(self.list_songs, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#8b8b8b;")
        layout.addWidget(self.status)

        self._playlists = []
        self._songs = []
        self._current_playlist_name = ""

    # ---------- 加载热门歌单 ----------
    def load_playlists(self):
        platform = self.platform.currentData()
        self.btn_load.setEnabled(False)
        self.status.setText(f"加载 {self.platform.currentText()} 热门歌单中...")
        self.list_pl.clear()
        self.list_songs.clear()
        self.lbl_left_title.setText("歌单列表（热门榜单）")

        run_async(
            lambda: get_hot_playlists(platform, limit=30),
            on_done=self._on_playlists,
            on_error=lambda e: (
                self.status.setText(f"加载失败：{e}"),
                self.btn_load.setEnabled(True),
            ),
        )

    def _on_playlists(self, playlists):
        self._playlists = playlists
        self.list_pl.clear()
        for p in playlists:
            it = QListWidgetItem(f"{p.name}  ({p.song_count})")
            it.setToolTip(p.name)
            self.list_pl.addItem(it)
        self.status.setText(f"共 {len(playlists)} 个歌单 · 点击查看歌曲")
        self.btn_load.setEnabled(True)

    # ---------- 搜索歌单 ----------
    def search_playlists(self):
        keyword = self.input_search.text().strip()
        if not keyword:
            return
        platform = self.platform.currentData()

        self.btn_search.setEnabled(False)
        self.status.setText(f"搜索歌单「{keyword}」中...")
        self.list_pl.clear()
        self.list_songs.clear()
        self.lbl_left_title.setText(f"歌单列表（搜索：{keyword}）")

        run_async(
            lambda: search_playlists(platform, keyword, limit=30),
            on_done=self._on_search_results,
            on_error=lambda e: (
                self.status.setText(f"搜索失败：{e}"),
                self.btn_search.setEnabled(True),
            ),
        )

    def _on_search_results(self, playlists):
        self._playlists = playlists
        self.list_pl.clear()
        if not playlists:
            self.status.setText("没有找到歌单，换个关键词试试")
            self.btn_search.setEnabled(True)
            return
        for p in playlists:
            it = QListWidgetItem(f"{p.name}  ({p.song_count} 首)")
            it.setToolTip(p.name)
            self.list_pl.addItem(it)
        self.status.setText(f"找到 {len(playlists)} 个歌单 · 点击查看歌曲")
        self.btn_search.setEnabled(True)

    # ---------- 粘贴分享链接 ----------
    def paste_share_link(self):
        url, ok = QInputDialog.getText(
            self, "粘贴歌单分享链接",
            "支持酷狗 / QQ音乐的分享链接、酷狗码：\n\n"
            "示例：\n"
            "  酷狗码： 17960538\n"
            "  酷狗分享名片： https://www.kugou.com/songlist/gcid_xxx/\n"
            "  酷狗网页分享： https://www.kugou.com/yy/special/single/xxx.html\n"
            "  QQ音乐： https://y.qq.com/n/ryqq/playlist/xxx",
            QLineEdit.EchoMode.Normal, "",
        )
        if not ok:
            return
        url = (url or "").strip()
        if not url:
            return

        platform, playlist_id = parse_playlist_url(url)
        if not platform or not playlist_id:
            QMessageBox.warning(self, "无法识别", "无法从该链接识别平台或歌单 ID。")
            return

        label = {"kugou": "酷狗音乐",
                 "kugou_gcid": "酷狗音乐（分享名片）",
                 "kugou_code": "酷狗音乐（酷狗码）",
                 "qq": "QQ音乐"}.get(platform, platform)
        self.status.setText(f"正在解析 {label} 歌单（{playlist_id}）...")
        self.list_songs.clear()
        self.lbl_left_title.setText("歌单列表（分享链接）")

        run_async(
            lambda: get_playlist_songs(platform, playlist_id),
            on_done=self._on_pasted_songs,
            on_error=lambda e: self.status.setText(f"解析失败：{e}"),
        )

    def _on_pasted_songs(self, songs):
        if not songs:
            self.status.setText("未获取到歌曲")
            self.list_songs.clear()
            self._songs = []
            return
        self._on_songs(songs)
        self.status.setText(f"从分享链接获取到 {len(songs)} 首")

    # ---------- 选择歌单 ----------
    def _on_playlist_selected(self, item):
        idx = self.list_pl.row(item)
        if not (0 <= idx < len(self._playlists)):
            return
        pl = self._playlists[idx]
        self._current_playlist_name = pl.name
        self.status.setText(f"正在解析歌单：{pl.name}")
        self.list_songs.clear()

        run_async(
            lambda: get_playlist_songs(pl.platform, pl.playlist_id),
            on_done=self._on_songs,
            on_error=lambda e: self.status.setText(f"解析失败：{e}"),
        )

    def _on_songs(self, songs):
        self._songs = songs
        self.list_songs.clear()

        for i, s in enumerate(songs):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 38))
            self.list_songs.addItem(item)

            row = PlaylistSongRow(s.title, s.artist, self.list_songs)
            row.play_requested.connect(
                lambda idx=i: self.play_list_requested.emit(self._songs, idx)
            )
            row.download_requested.connect(
                lambda t=s.title, a=s.artist: self.download_single_requested.emit(t, a)
            )
            row.checked_changed.connect(self._on_check_changed)
            self.list_songs.setItemWidget(item, row)

        self._update_status()

    # ---------- 勾选 ----------
    def _on_check_changed(self):
        self._update_status()

    def _update_status(self):
        checked = self._get_checked_count()
        total = len(self._songs)
        if total == 0:
            self.status.setText("")
            return
        if checked == 0:
            self.status.setText(
                f"歌单共 {total} 首 · 勾选后点「下载勾选」，或双击歌名播放、"
                f"点行尾「下载」单曲下载"
            )
        else:
            self.status.setText(
                f"歌单共 {total} 首 · 已勾选 {checked} 首 · 点「下载勾选」批量下载"
            )

    def _get_checked_count(self) -> int:
        count = 0
        for i in range(self.list_songs.count()):
            item = self.list_songs.item(i)
            widget = self.list_songs.itemWidget(item)
            if widget and hasattr(widget, "is_checked") and widget.is_checked():
                count += 1
        return count

    def _get_checked_tasks(self):
        """返回 [(title, artist), ...]"""
        tasks = []
        for i in range(self.list_songs.count()):
            item = self.list_songs.item(i)
            widget = self.list_songs.itemWidget(item)
            if widget and hasattr(widget, "is_checked") and widget.is_checked():
                if 0 <= i < len(self._songs):
                    s = self._songs[i]
                    tasks.append((s.title, s.artist))
        return tasks

    def _select_all(self):
        for i in range(self.list_songs.count()):
            item = self.list_songs.item(i)
            widget = self.list_songs.itemWidget(item)
            if widget and hasattr(widget, "set_checked"):
                widget.set_checked(True)
        self._update_status()

    def _unselect_all(self):
        for i in range(self.list_songs.count()):
            item = self.list_songs.item(i)
            widget = self.list_songs.itemWidget(item)
            if widget and hasattr(widget, "set_checked"):
                widget.set_checked(False)
        self._update_status()

    def _download_checked(self):
        tasks = self._get_checked_tasks()
        if not tasks:
            self.status.setText("请先勾选要下载的歌曲")
            return
        name = self._current_playlist_name or "歌单"
        self.download_requested.emit(tasks, name)
        self.status.setText(
            f"已加入下载队列：{len(tasks)} 首（完成后会在下载目录生成 {name}.m3u）"
        )
