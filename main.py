"""MusicPlayer 入口"""
import os
import sys
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QProgressDialog,
)
from PyQt6.QtGui import QFont

from ui.styles import apply_style
from ui.main_window import MainWindow
from data.database import init_db


# ---------- Playwright 环境 ----------
def setup_playwright_env():
    """打包后，把 Playwright 的浏览器目录指向打包位置"""
    if getattr(sys, "frozen", False):
        candidates = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "ms-playwright"))
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "ms-playwright"))
        candidates.append(os.path.join(exe_dir, "_internal", "ms-playwright"))

        for c in candidates:
            if os.path.isdir(c):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = c
                print(f"[main] Playwright 浏览器目录: {c}", flush=True)
                return


def ensure_playwright_chromium(parent=None) -> bool:
    """确保 Playwright Chromium 已安装"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        QMessageBox.warning(
            parent, "缺少依赖",
            "Playwright 未安装。请运行：\n"
            "pip install playwright"
        )
        return False

    # 尝试启动一次
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        print("[main] Chromium 已就绪", flush=True)
        return True
    except Exception as e:
        print(f"[main] Chromium 未安装或启动失败: {e}", flush=True)

    # 询问用户
    ret = QMessageBox.question(
        parent, "首次运行准备",
        "首次使用需要下载 Chromium 内核（约 150MB），用于解析音乐链接。\n\n"
        "是否现在下载？下载过程可能需要 1-3 分钟。\n"
        "（下载源已切换到国内镜像，速度较快）",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if ret != QMessageBox.StandardButton.Yes:
        QMessageBox.information(
            parent, "跳过",
            "你可以稍后手动下载。打开 PowerShell 执行：\n\n"
            "$env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright'\n"
            "python -m playwright install chromium"
        )
        return False

    # 打包后无法通过 subprocess 调用 playwright CLI，
    # 改为直接调用 Playwright 的 Python 下载 API
    env_backup = os.environ.get("PLAYWRIGHT_DOWNLOAD_HOST")
    os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = (
        "https://npmmirror.com/mirrors/playwright"
    )

    progress = QProgressDialog(
        "正在下载 Chromium 内核（约 150MB）...\n"
        "下载期间请勿关闭窗口，可能需要 1-3 分钟。",
        None, 0, 0, parent,
    )
    progress.setWindowTitle("下载 Chromium")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)
    progress.show()
    QApplication.processEvents()

    success = False
    try:
        if getattr(sys, "frozen", False):
            # 打包后：用 subprocess 调 Playwright 的 driver（exe 内置）
            _download_chromium_subprocess()
        else:
            # 源码运行：用 subprocess 调 python -m playwright
            _download_chromium_subprocess()
        success = True
    except Exception as e:
        print(f"[main] 下载失败: {e}", flush=True)

    progress.close()
    if env_backup is None:
        os.environ.pop("PLAYWRIGHT_DOWNLOAD_HOST", None)
    else:
        os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = env_backup

    if success:
        # 验证是否可启动
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                b.close()
            QMessageBox.information(parent, "完成", "Chromium 内核下载完成！")
            return True
        except Exception as e:
            QMessageBox.critical(
                parent, "下载后仍无法启动",
                f"下载可能未完成：\n{e}\n\n"
                "请手动执行：\n"
                "  $env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright'\n"
                "  python -m playwright install chromium"
            )
            return False
    else:
        QMessageBox.critical(
            parent, "下载失败",
            "Chromium 下载失败。请手动执行：\n\n"
            "$env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright'\n"
            "python -m playwright install chromium"
        )
        return False


def _download_chromium_subprocess():
    """用 subprocess 调 playwright install chromium"""
    if getattr(sys, "frozen", False):
        # 打包后：尝试从 exe 所在环境找 playwright 的 driver
        # PyInstaller 会把 playwright 的 __main__ 打包进去
        try:
            from playwright.__main__ import main as pw_main
            sys.argv = ["playwright", "install", "chromium"]
            pw_main()
            return
        except SystemExit:
            return
        except Exception as e:
            # 兜底：用系统 python
            print(f"[main] 内置调用失败: {e}，尝试系统 python", flush=True)
            import shutil
            python_exe = shutil.which("python") or shutil.which("python3")
            if python_exe:
                subprocess.run(
                    [python_exe, "-m", "playwright", "install", "chromium"],
                    check=True,
                )
                return
            raise
    else:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )


# ---------- 主函数 ----------
def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 打包后先配置 Playwright 环境变量（必须在导入 playwright 前设置）
    setup_playwright_env()

    app = QApplication(sys.argv)
    app.setApplicationName("MusicPlayer")
    app.setApplicationDisplayName("MusicPlayer")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    apply_style(app)
    init_db()

    # 检查 Chromium 是否就绪
    ensure_playwright_chromium()

    w = MainWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
