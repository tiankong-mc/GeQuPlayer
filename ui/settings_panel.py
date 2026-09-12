"""设置面板：下载目录 + 缓存管理"""
import os
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QApplication,
)

from config import DEFAULT_DOWNLOAD_DIR
from core.gequbao_api import get_cache_dir, get_default_cache_dir
from utils.helpers import load_config, save_config


# ---------- 工具函数 ----------
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


# ---------- 面板 ----------
class SettingsPanel(QWidget):
    set_download_dir = pyqtSignal(str)
    cache_cleared = pyqtSignal()
    cache_dir_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self._download_dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        title = QLabel("设置")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#ffffff;")
        layout.addWidget(title)

        # ========== 下载目录 ==========
        gb_dl = QGroupBox("下载目录")
        gb_dl.setStyleSheet(self._group_style())
        dl_layout = QVBoxLayout(gb_dl)
        dl_layout.setSpacing(10)

        dl_layout.addWidget(QLabel("音乐将下载到此目录（MP3 + LRC）："))
        self.lbl_download = QLabel(self._download_dir)
        self.lbl_download.setStyleSheet(self._path_style())
        self.lbl_download.setWordWrap(True)
        self.lbl_download.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dl_layout.addWidget(self.lbl_download)

        dl_btns = QHBoxLayout()
        btn_change_dl = QPushButton("更改目录")
        btn_change_dl.clicked.connect(self._change_download_dir)
        btn_open_dl = QPushButton("打开目录")
        btn_open_dl.clicked.connect(self._open_download_dir)
        dl_btns.addWidget(btn_change_dl)
        dl_btns.addWidget(btn_open_dl)
        dl_btns.addStretch(1)
        dl_layout.addLayout(dl_btns)
        layout.addWidget(gb_dl)

        # ========== 缓存管理 ==========
        gb_cache = QGroupBox("缓存管理")
        gb_cache.setStyleSheet(self._group_style())
        c_layout = QVBoxLayout(gb_cache)
        c_layout.setSpacing(10)

        c_layout.addWidget(QLabel("播放歌曲时的临时文件缓存目录："))
        self.lbl_cache_path = QLabel("")
        self.lbl_cache_path.setStyleSheet(self._path_style())
        self.lbl_cache_path.setWordWrap(True)
        self.lbl_cache_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        c_layout.addWidget(self.lbl_cache_path)

        self.lbl_cache_size = QLabel("缓存大小：计算中...")
        self.lbl_cache_size.setStyleSheet("color:#cfcfcf; font-size:14px;")
        c_layout.addWidget(self.lbl_cache_size)

        # 缓存目录操作按钮
        cache_btns = QHBoxLayout()
        btn_change_cache = QPushButton("更改缓存目录")
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

        # 缓存操作按钮
        ops_btns = QHBoxLayout()
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_cache_size)
        self.btn_clear_cache = QPushButton("清空缓存")
        self.btn_clear_cache.setObjectName("PrimaryButton")
        self.btn_clear_cache.clicked.connect(self._clear_cache)
        ops_btns.addWidget(btn_refresh)
        ops_btns.addStretch(1)
        ops_btns.addWidget(self.btn_clear_cache)
        c_layout.addLayout(ops_btns)

        hint = QLabel(
            "说明：缓存是你听过的歌曲的临时文件，用于下次秒开。\n"
            "清空缓存不会影响「下载目录」里的音乐，只影响已听歌曲的加载速度。\n"
            "更改缓存目录后，旧缓存不会自动迁移，可手动复制过去或让它自然过期。"
        )
        hint.setStyleSheet("color:#7a7a7a; font-size:12px; line-height:1.6;")
        hint.setWordWrap(True)
        c_layout.addWidget(hint)

        layout.addWidget(gb_cache)

        layout.addStretch(1)

        # 初始化显示
        self._refresh_cache_path()
        self.refresh_cache_size()

    # ---------- 样式 ----------
    def _group_style(self) -> str:
        return """
            QGroupBox {
                color: #e6e6e6;
                border: 1px solid #26272c;
                border-radius: 10px;
                margin-top: 12px;
                padding: 16px 14px 14px 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #ffffff;
            }
        """

    def _path_style(self) -> str:
        return (
            "color:#9a9a9a; background:#232428; border:1px solid #2e2f35;"
            "border-radius:6px; padding:8px 10px;"
        )

    # ---------- 缓存 ----------
    def _refresh_cache_path(self):
        self.lbl_cache_path.setText(str(get_cache_dir()))

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

    def _open_cache_dir(self):
        try:
            d = get_cache_dir()
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开失败: {e}")

    def _change_cache_dir(self):
        current = str(get_cache_dir())
        d = QFileDialog.getExistingDirectory(self, "选择缓存目录", current)
        if not d:
            return
        cfg = load_config()
        cfg["cache_dir"] = d
        save_config(cfg)
        self._refresh_cache_path()
        self.refresh_cache_size()
        self.cache_dir_changed.emit(d)
        QMessageBox.information(
            self, "已更改",
            f"缓存目录已设置为：\n{d}\n\n"
            "旧缓存不会自动迁移，可手动复制过去或让它自然过期。"
        )

    def _reset_cache_dir(self):
        cfg = load_config()
        if "cache_dir" in cfg:
            del cfg["cache_dir"]
            save_config(cfg)
        self._refresh_cache_path()
        self.refresh_cache_size()
        self.cache_dir_changed.emit(str(get_cache_dir()))
        QMessageBox.information(
            self, "已恢复默认",
            f"缓存目录已恢复为默认位置：\n{get_default_cache_dir()}"
        )

    def _clear_cache(self):
        ans = QMessageBox.question(
            self,
            "清空缓存",
            "确定要清空所有缓存文件吗？\n\n"
            "清空后下次播放同一首歌需要重新下载（约 5~10 秒），\n"
            "但不会影响下载目录里的音乐文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        cache_dir = get_cache_dir()
        deleted = 0
        failed = 0
        if cache_dir.exists():
            for f in list(cache_dir.iterdir()):
                try:
                    if f.is_file():
                        f.unlink()
                        deleted += 1
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                        deleted += 1
                except Exception:
                    failed += 1

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
        self._refresh_cache_path()
        self.refresh_cache_size()
