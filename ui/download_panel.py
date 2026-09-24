"""下载面板：带实时日志显示"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QSplitter,
    QPlainTextEdit,
)

from core.downloader import Downloader
from utils.helpers import load_config, save_config
from utils.log_capture import LogCapture
from config import DEFAULT_DOWNLOAD_DIR


MAX_LOG_LINES = 3000


class DownloadPanel(QWidget):
    set_download_dir = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self._dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)
        self._playlist_name = ""
        self._current_round = 0
        self._log_visible = False

        self.downloader = Downloader(self)
        self.downloader.set_download_dir(self._dir)
        self.downloader.task_updated.connect(self._on_task_updated)
        self.downloader.all_finished.connect(self._on_all_finished)
        self.downloader.round_changed.connect(self._on_round_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(12)

        # ============ 顶部按钮栏 ============
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.lbl_dir = QLabel(f"下载目录：{self._dir}")
        self.lbl_dir.setStyleSheet("color:#9a9a9a;")

        # 查看实时进度（可勾选），位置在"更换目录"左边
        self.btn_log = QPushButton("查看实时进度")
        self.btn_log.setCheckable(True)
        self.btn_log.setChecked(False)
        self.btn_log.setToolTip("显示/隐藏后台运行日志（打开链接、下载进度等）")
        self.btn_log.clicked.connect(self._toggle_log)

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
        bar.addWidget(self.btn_log)
        bar.addWidget(btn_dir)
        bar.addWidget(self.btn_start)
        bar.addWidget(self.btn_stop)
        bar.addWidget(self.btn_clear)
        layout.addLayout(bar)

        # ============ 主体：左右分栏 ============
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # 左：下载列表
        self.list = QListWidget()
        self.splitter.addWidget(self.list)

        # 右：日志视图（默认隐藏）
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color:#0e0f12; color:#c8c8c8; "
            "border:1px solid #26272c; border-radius:10px; padding:6px;"
        )
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setMaximumBlockCount(MAX_LOG_LINES)
        self.log_view.setPlaceholderText(
            "后台运行日志将显示在这里...\n\n"
            "例如：\n"
            "  [pw] 会话1 打开 https://...\n"
            "  [pw] 步骤1：点击下载\n"
            "  [download] ✓ 成功 5127719"
        )
        self.log_view.hide()
        self.splitter.addWidget(self.log_view)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter, 1)

        self.status = QLabel("等待任务...")
        self.status.setStyleSheet("color:#8b8b8b;")
        layout.addWidget(self.status)

        # 连接日志捕获信号
        try:
            LogCapture.instance().message_written.connect(self._on_log_message)
        except Exception as e:
            print(f"[download_panel] 日志信号连接失败: {e}", flush=True)

    # ============ 日志切换 ============
    def _toggle_log(self, checked: bool):
        self._log_visible = checked
        if checked:
            self.log_view.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self.btn_log.setText("隐藏实时进度")
        else:
            self.log_view.hide()
            self.btn_log.setText("查看实时进度")

    def _on_log_message(self, text: str):
        if not self._log_visible:
            return
        try:
            self.log_view.appendPlainText(text)
        except Exception:
            pass

    # ============ 任务管理 ============
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

    # ============ 状态更新 ============
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
