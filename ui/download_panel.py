"""下载面板"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog,
)

from core.downloader import Downloader
from utils.helpers import load_config, save_config
from config import DEFAULT_DOWNLOAD_DIR


class DownloadPanel(QWidget):
    set_download_dir = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self._dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)
        self._playlist_name = ""
        self._current_round = 0

        self.downloader = Downloader(self)
        self.downloader.set_download_dir(self._dir)
        self.downloader.task_updated.connect(self._on_task_updated)
        self.downloader.all_finished.connect(self._on_all_finished)
        self.downloader.round_changed.connect(self._on_round_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        self.lbl_dir = QLabel(f"下载目录：{self._dir}")
        self.lbl_dir.setStyleSheet("color:#9a9a9a;")
        btn_dir = QPushButton("更换目录")
        btn_dir.clicked.connect(self._change_dir)
        self.btn_start = QPushButton("开始下载")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._clear)
        bar.addWidget(self.lbl_dir, 1)
        bar.addWidget(btn_dir)
        bar.addWidget(self.btn_start)
        bar.addWidget(self.btn_stop)
        bar.addWidget(self.btn_clear)
        layout.addLayout(bar)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)

        self.status = QLabel("等待任务...")
        self.status.setStyleSheet("color:#8b8b8b;")
        layout.addWidget(self.status)

    def add_tasks(self, tasks, playlist_name: str = ""):
        added = 0
        for t in tasks:
            if not t:
                continue
            if len(t) >= 3:
                title, artist, song_id = t[0], t[1], t[2]
            elif len(t) == 2:
                title, artist = t
                song_id = None
            else:
                title, artist, song_id = t[0], "", None

            self.downloader.add_task(title, artist, song_id)
            display = f"{title} - {artist}" if artist else title
            item = QListWidgetItem(f"[待下载] {display}")
            self.list.addItem(item)
            added += 1

        if playlist_name:
            self._playlist_name = playlist_name
            self.status.setText(
                f"新增 {added} 个任务，共 {self.list.count()} 个（完成后生成 {playlist_name}.m3u）"
            )
        elif added:
            self.status.setText(f"新增 {added} 个任务，共 {self.list.count()} 个")

    def _start(self):
        if not self.downloader.tasks:
            self.status.setText("没有任务")
            return
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._current_round = 0
        self.status.setText("下载中...（两轮调度，失败任务会在冷却后重跑）")
        self.downloader.start(self._dir, self._playlist_name)

    def _stop(self):
        self.downloader.stop()
        self.status.setText("正在停止...等待当前任务退出")
        self.btn_stop.setEnabled(False)

    def _clear(self):
        if self.downloader._thread and self.downloader._thread.is_alive():
            self.status.setText("下载进行中，请先停止")
            return
        self.downloader.clear()
        self.list.clear()
        self._playlist_name = ""
        self.status.setText("已清空")

    def _change_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self._dir)
        if d:
            self._dir = d
            self.lbl_dir.setText(f"下载目录：{d}")
            self.downloader.set_download_dir(d)
            cfg = load_config()
            cfg["download_dir"] = d
            save_config(cfg)
            self.set_download_dir.emit(d)

    def _on_round_changed(self, round_num: int):
        self._current_round = round_num
        if round_num == 1:
            self.status.setText("第 1 轮下载中...")
        elif round_num == 2:
            self.status.setText("第 2 轮：重试失败任务中...")

    def _on_task_updated(self, idx: int):
        if not (0 <= idx < len(self.downloader.tasks)):
            return
        t = self.downloader.tasks[idx]
        if idx < self.list.count():
            item = self.list.item(idx)
            display = t.display
            if t.status == "pending":
                text = f"[待下载] {display}"
            elif t.status == "searching":
                text = f"[搜索中] {display}"
            elif t.status == "downloading":
                prefix = f"第{self._current_round}轮" if self._current_round else ""
                text = f"[{prefix}下载中] {display}"
            elif t.status == "retry":
                text = f"[重试中] {display}"
            elif t.status == "done":
                text = f"[完成] {display}"
            elif t.status == "stopped":
                text = f"[已停止] {display}"
            elif t.status == "skipped":
                text = f"[跳过] {display}  ({t.error})"
            else:
                text = f"[失败] {display}  ({t.error})"
            item.setText(text)

    def _on_all_finished(self, success: int, total: int):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        msg = f"全部完成：成功 {success} / 共 {total}"
        if self._playlist_name:
            msg += f"（已生成 {self._playlist_name}.m3u）"
        self.status.setText(msg)
