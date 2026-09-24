"""设置面板"""
import os
import shutil
import subprocess
import tempfile
import webbrowser
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QApplication, QSpinBox,
    QRadioButton, QButtonGroup, QProgressBar, QScrollArea,
    QFrame, QSizePolicy,
)

from config import (
    DEFAULT_DOWNLOAD_DIR, APP_NAME, APP_VERSION,
    DEFAULT_CONCURRENT_TASKS, DEFAULT_LYRICS_MODE,
)
from core.gequbao_api import (
    get_cache_dir, get_default_cache_dir, is_valid_cache_dir,
)
from utils.helpers import load_config, save_config, run_async


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _format_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / 1024 / 1024:.2f} MB"
    return f"{b / 1024 / 1024 / 1024:.2f} GB"


def _path_label_style() -> str:
    return """
        QLabel {
            color: #cfcfcf;
            background-color: #232428;
            border: 1px solid #2e2f35;
            border-radius: 6px;
            padding: 8px 12px;
        }
    """


def _primary_btn_style() -> str:
    """主按钮内联样式（双保险，避免 QSS 全局失效）"""
    return """
        QPushButton {
            background-color: #1db954;
            color: #0e0f12;
            border: none;
            border-radius: 8px;
            padding: 7px 16px;
            font-weight: bold;
            min-height: 20px;
        }
        QPushButton:hover { background-color: #24d162; }
        QPushButton:pressed { background-color: #17a349; }
        QPushButton:disabled {
            background-color: #2e4d3a;
            color: #7c8a80;
        }
    """


class SettingsPanel(QWidget):
    set_download_dir = pyqtSignal(str)
    cache_cleared = pyqtSignal()
    cache_dir_changed = pyqtSignal(str)
    concurrent_changed = pyqtSignal(int)
    lyrics_mode_changed = pyqtSignal(str)

    _download_progress = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self._download_dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)
        self._updating = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("设置")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#ffffff;")
        layout.addWidget(title)

        # ============ 下载设置 ============
        gb_dl = QGroupBox("下载设置")
        dl_layout = QVBoxLayout(gb_dl)
        dl_layout.setSpacing(10)

        lbl_dl_hint = QLabel("音乐将下载到此目录（MP3 + LRC）：")
        lbl_dl_hint.setStyleSheet("color:#cfcfcf;")
        dl_layout.addWidget(lbl_dl_hint)

        self.lbl_download = QLabel(self._download_dir)
        self.lbl_download.setStyleSheet(_path_label_style())
        self.lbl_download.setWordWrap(True)
        self.lbl_download.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_download.setMinimumHeight(36)
        dl_layout.addWidget(self.lbl_download)

        dl_btns = QHBoxLayout()
        dl_btns.setSpacing(8)
        btn_change_dl = QPushButton("更改目录")
        btn_change_dl.clicked.connect(self._change_download_dir)
        btn_open_dl = QPushButton("打开目录")
        btn_open_dl.clicked.connect(self._open_download_dir)
        dl_btns.addWidget(btn_change_dl)
        dl_btns.addWidget(btn_open_dl)
        dl_btns.addStretch(1)
        dl_layout.addLayout(dl_btns)

        conc_row = QHBoxLayout()
        conc_row.setSpacing(8)
        conc_label = QLabel("同时下载数：")
        conc_label.setStyleSheet("color:#cfcfcf;")
        conc_row.addWidget(conc_label)

        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 10)
        self.spin_concurrent.setValue(
            int(cfg.get("concurrent_tasks", DEFAULT_CONCURRENT_TASKS)))
        self.spin_concurrent.setFixedWidth(90)
        self.spin_concurrent.valueChanged.connect(self._on_concurrent_changed)
        conc_row.addWidget(self.spin_concurrent)

        hint = QLabel("（1-10，太大容易被限流，建议 3-5）")
        hint.setStyleSheet("color:#7a7a7a; font-size:11px;")
        conc_row.addWidget(hint)
        conc_row.addStretch(1)
        dl_layout.addLayout(conc_row)

        layout.addWidget(gb_dl)

        # ============ 歌词设置 ============
        gb_lyrics = QGroupBox("歌词设置")
        ll = QVBoxLayout(gb_lyrics)
        ll.setSpacing(8)

        lyric_hint = QLabel("歌词显示方式：")
        lyric_hint.setStyleSheet("color:#cfcfcf;")
        ll.addWidget(lyric_hint)

        self.rb_line = QRadioButton("逐行显示（推荐）")
        self.rb_word = QRadioButton("逐字显示（卡拉 OK 效果）")

        self.lyric_mode_group = QButtonGroup(self)
        self.lyric_mode_group.addButton(self.rb_line)
        self.lyric_mode_group.addButton(self.rb_word)

        current_mode = cfg.get("lyrics_mode", DEFAULT_LYRICS_MODE)
        if current_mode == "word":
            self.rb_word.setChecked(True)
        else:
            self.rb_line.setChecked(True)

        self.rb_line.toggled.connect(self._on_lyrics_mode_changed)

        radio_wrap = QVBoxLayout()
        radio_wrap.setContentsMargins(12, 0, 0, 0)
        radio_wrap.setSpacing(4)
        radio_wrap.addWidget(self.rb_line)
        radio_wrap.addWidget(self.rb_word)
        ll.addLayout(radio_wrap)

        hint2 = QLabel(
            "说明：由于 gequbao 平台下载的歌词大多没有逐字时间戳，"
            "选择「逐字」时可能会有偏差（按行平均分配时间）。"
        )
        hint2.setStyleSheet("color:#7a7a7a; font-size:11px; line-height:1.6;")
        hint2.setWordWrap(True)
        hint2.setContentsMargins(12, 4, 0, 0)
        ll.addWidget(hint2)

        layout.addWidget(gb_lyrics)

        # ============ 缓存管理 ============
        gb_cache = QGroupBox("缓存管理")
        c_layout = QVBoxLayout(gb_cache)
        c_layout.setSpacing(10)

        self.lbl_cache_path = QLabel(str(get_cache_dir()))
        self.lbl_cache_path.setStyleSheet(_path_label_style())
        self.lbl_cache_path.setWordWrap(True)
        self.lbl_cache_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_cache_path.setMinimumHeight(36)
        c_layout.addWidget(self.lbl_cache_path)

        self.lbl_cache_size = QLabel("缓存大小：计算中...")
        self.lbl_cache_size.setStyleSheet("color:#cfcfcf; font-size:13px;")
        c_layout.addWidget(self.lbl_cache_size)

        cache_btns = QHBoxLayout()
        cache_btns.setSpacing(8)
        btn_change_cache = QPushButton("更改缓存根目录")
        btn_change_cache.clicked.connect(self._change_cache_dir)
        btn_reset_cache = QPushButton("恢复默认位置")
        btn_reset_cache.clicked.connect(self._reset_cache_dir)
        btn_open_cache = QPushButton("打开缓存目录")
        btn_open_cache.clicked.connect(self._open_cache_dir)
        cache_btns.addWidget(btn_change_cache)
        cache_btns.addWidget(btn_reset_cache)
        cache_btns.addWidget(btn_open_cache)
        cache_btns.addStretch(1)
        c_layout.addLayout(cache_btns)

        ops_btns = QHBoxLayout()
        ops_btns.setSpacing(8)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_cache_size)

        # ============ 清空缓存：用内联样式双保险 ============
        self.btn_clear_cache = QPushButton("清空缓存")
        self.btn_clear_cache.setObjectName("PrimaryButton")
        self.btn_clear_cache.setFixedWidth(120)
        self.btn_clear_cache.setStyleSheet(_primary_btn_style())
        self.btn_clear_cache.clicked.connect(self._clear_cache)
        # ===================================================

        ops_btns.addWidget(btn_refresh)
        ops_btns.addStretch(1)
        ops_btns.addWidget(self.btn_clear_cache)
        c_layout.addLayout(ops_btns)

        layout.addWidget(gb_cache)

        # ============ 关于 ============
        gb_about = QGroupBox("关于")
        a_layout = QVBoxLayout(gb_about)
        a_layout.setSpacing(10)

        # ---- 第一行：检查更新按钮（左对齐） ----
        self.btn_check_update = QPushButton("检查更新")
        self.btn_check_update.setFixedWidth(120)
        self.btn_check_update.clicked.connect(self._on_check_update)
        a_layout.addWidget(self.btn_check_update, alignment=Qt.AlignmentFlag.AlignLeft)

        # ---- 第二行：进度条（默认隐藏，下载时显示） ----
        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.setValue(0)
        self.update_progress.setFixedHeight(8)
        self.update_progress.setVisible(False)
        a_layout.addWidget(self.update_progress)

        # ---- 第三行：反馈 + 关于 ----
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        btn_feedback = QPushButton("反馈问题")
        btn_feedback.setFixedWidth(120)
        btn_feedback.clicked.connect(self._open_feedback)
        btn_about = QPushButton("关于 GeQuPlayer")
        btn_about.setFixedWidth(140)
        btn_about.clicked.connect(self._open_about)
        row2.addWidget(btn_feedback)
        row2.addWidget(btn_about)
        row2.addStretch(1)
        a_layout.addLayout(row2)

        layout.addWidget(gb_about)
        layout.addStretch(1)

        self.refresh_cache_size()
        self._download_progress.connect(self._on_download_progress)

    # ---------- 事件 ----------
    def _on_concurrent_changed(self, value: int):
        cfg = load_config()
        cfg["concurrent_tasks"] = value
        save_config(cfg)
        self.concurrent_changed.emit(value)
        print(f"[settings] 同时下载数设为 {value}", flush=True)

    def _on_lyrics_mode_changed(self, _):
        mode = "word" if self.rb_word.isChecked() else "line"
        cfg = load_config()
        cfg["lyrics_mode"] = mode
        save_config(cfg)
        self.lyrics_mode_changed.emit(mode)
        print(f"[settings] 歌词模式：{mode}", flush=True)

    def _open_feedback(self):
        webbrowser.open("https://github.com/tiankong-mc/GeQuPlayer/issues")

    def _open_about(self):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec()

    # ---------- 检查更新 ----------
    def _on_check_update(self):
        if self._updating:
            return

        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("检查中...")

        def work():
            from utils.updater import check_update
            return check_update(APP_VERSION)

        def on_done(result):
            self.btn_check_update.setEnabled(True)
            self.btn_check_update.setText("检查更新")
            if result.get("has_update"):
                self._show_update_dialog(result)
            else:
                QMessageBox.information(
                    self, "检查更新",
                    f"当前已是最新版本（v{APP_VERSION}）。"
                )

        def on_error(err):
            self.btn_check_update.setEnabled(True)
            self.btn_check_update.setText("检查更新")
            QMessageBox.warning(
                self, "检查更新失败",
                f"无法连接到更新服务器：\n{err}\n\n"
                "由于 GitHub 在国内访问不稳定，请稍后重试。"
            )

        run_async(work, on_done=on_done, on_error=on_error)

    def _show_update_dialog(self, info: dict):
        from ui.update_dialog import UpdateDialog
        dlg = UpdateDialog(info, self)
        if dlg.exec() == UpdateDialog.DialogCode.Accepted:
            self._start_download(info)

    def _start_download(self, info: dict):
        url = info.get("download_url")
        if not url:
            QMessageBox.warning(
                self, "无法下载",
                "未找到安装包下载链接，请手动前往 GitHub Releases 下载。")
            webbrowser.open(info.get("html_url") or
                            "https://github.com/tiankong-mc/GeQuPlayer/releases")
            return

        version = info.get("latest_version", "latest")
        dest = os.path.join(tempfile.gettempdir(),
                            f"GeQuPlayer_Setup_v{version}.exe")

        self._updating = True
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("下载中 0%")
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)

        def work():
            from utils.updater import download_installer

            def progress(done, total):
                pct = int(done * 100 / total) if total > 0 else 0
                self._download_progress.emit(pct)

            ok = download_installer(url, dest, progress)
            return ok, dest

        def on_done(result):
            ok, path = result
            self._updating = False
            self.btn_check_update.setEnabled(True)
            self.btn_check_update.setText("检查更新")
            self.update_progress.setVisible(False)

            if not ok:
                QMessageBox.warning(
                    self, "下载失败",
                    "安装包下载失败，请稍后重试或手动下载。")
                webbrowser.open(info.get("html_url") or
                                "https://github.com/tiankong-mc/GeQuPlayer/releases")
                return

            ret = QMessageBox.question(
                self, "下载完成",
                f"安装包已下载到：\n{path}\n\n"
                f"是否现在运行安装程序？\n"
                f"（安装过程会自动覆盖旧版本，保留你的设置和下载记录）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ret == QMessageBox.StandardButton.Yes:
                try:
                    subprocess.Popen([path], shell=True)
                except Exception as e:
                    QMessageBox.warning(self, "启动失败", f"{e}")

        def on_error(err):
            self._updating = False
            self.btn_check_update.setEnabled(True)
            self.btn_check_update.setText("检查更新")
            self.update_progress.setVisible(False)
            QMessageBox.warning(self, "下载失败", f"{err}")

        run_async(work, on_done=on_done, on_error=on_error)

    def _on_download_progress(self, pct: int):
        self.update_progress.setValue(pct)
        self.btn_check_update.setText(f"下载中 {pct}%")

    # ---------- 缓存 ----------
    def refresh_cache_size(self):
        self.lbl_cache_size.setText("缓存大小：计算中...")
        QApplication.processEvents()

        cache_dir = get_cache_dir()
        size = _dir_size(cache_dir)
        file_count = 0
        if cache_dir.exists():
            try:
                file_count = sum(1 for f in cache_dir.iterdir() if f.is_file())
            except Exception:
                pass

        self.lbl_cache_size.setText(
            f"缓存大小：{_format_size(size)}（{file_count} 个文件）"
        )
        self.lbl_cache_path.setText(str(cache_dir))

    def _open_cache_dir(self):
        try:
            d = get_cache_dir()
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开失败: {e}")

    def _change_cache_dir(self):
        cfg = load_config()
        current = cfg.get("cache_dir") or str(get_default_cache_dir().parent)
        d = QFileDialog.getExistingDirectory(self, "选择缓存根目录", current)
        if not d:
            return
        cfg["cache_dir"] = d
        save_config(cfg)
        self.refresh_cache_size()
        self.cache_dir_changed.emit(str(get_cache_dir()))
        QMessageBox.information(
            self, "已更改",
            f"缓存根目录已设置为：\n{d}\n\n"
            f"程序会在其中创建 {APP_NAME}Cache 子目录存放缓存，"
            "不会污染该根目录的其他文件。"
        )

    def _reset_cache_dir(self):
        cfg = load_config()
        if "cache_dir" in cfg:
            del cfg["cache_dir"]
            save_config(cfg)
        self.refresh_cache_size()
        self.cache_dir_changed.emit(str(get_cache_dir()))
        QMessageBox.information(
            self, "已恢复默认",
            f"缓存目录已恢复为默认位置：\n{get_default_cache_dir()}"
        )

    def _clear_cache(self):
        cache_dir = get_cache_dir()

        if not is_valid_cache_dir(cache_dir):
            QMessageBox.critical(
                self, "拒绝清空",
                f"缓存标识文件不存在或无效：\n{cache_dir}\n\n"
                "为防止误删用户文件，已拒绝清空操作。")
            return

        ans = QMessageBox.question(
            self, "清空缓存",
            f"确定要清空以下目录中的所有缓存文件吗？\n\n{cache_dir}\n\n"
            f"（只删除文件，不会递归删除子目录）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        failed = 0
        try:
            for f in list(cache_dir.iterdir()):
                if f.name.startswith("."):
                    continue
                try:
                    if f.is_file() or f.is_symlink():
                        f.unlink()
                        deleted += 1
                    elif f.is_dir():
                        if f.name.startswith(".") and f.name.endswith("_chunks"):
                            shutil.rmtree(f, ignore_errors=True)
                            deleted += 1
                except Exception:
                    failed += 1
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清理过程中出错: {e}")

        self.refresh_cache_size()
        self.cache_cleared.emit()

        msg = f"已删除 {deleted} 个缓存文件。"
        if failed:
            msg += f"\n{failed} 个文件删除失败（可能正在被占用）。"
        QMessageBox.information(self, "完成", msg)

    # ---------- 下载目录 ----------
    def _change_download_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self._download_dir)
        if not d:
            return
        self._download_dir = d
        self.lbl_download.setText(d)
        cfg = load_config()
        cfg["download_dir"] = d
        save_config(cfg)
        self.set_download_dir.emit(d)

    def _open_download_dir(self):
        try:
            os.makedirs(self._download_dir, exist_ok=True)
            os.startfile(self._download_dir)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开失败: {e}")

    def on_dir_changed(self, d: str):
        self._download_dir = d
        self.lbl_download.setText(d)

    def on_cache_changed(self):
        self.refresh_cache_size()
