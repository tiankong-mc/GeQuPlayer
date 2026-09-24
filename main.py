"""GeQuPlayer 入口"""
import os
import sys
import subprocess

# ============ 确保项目根目录在 sys.path 里 ============
if getattr(sys, "frozen", False):
    _BASE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
# ====================================================

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtGui import QFont, QIcon

from ui.styles import apply_style
from ui.main_window import MainWindow
from data.database import init_db


def _get_resource_path(name: str) -> str:
    """获取资源文件的绝对路径（兼容源码运行与打包运行）"""
    if getattr(sys, "frozen", False):
        # 打包后：优先 exe 同级目录，其次 _MEIPASS
        exe_dir = os.path.dirname(sys.executable)
        cand = os.path.join(exe_dir, name)
        if os.path.exists(cand):
            return cand
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return os.path.join(meipass, name)
        return cand
    else:
        return os.path.join(_BASE, name)


def _set_app_icon(app: QApplication):
    """设置应用窗口/任务栏图标"""
    try:
        icon_path = _get_resource_path("myicon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            print(f"[main] 窗口图标: {icon_path}", flush=True)
        else:
            print(f"[main] 找不到图标文件: {icon_path}", flush=True)
    except Exception as e:
        print(f"[main] 设置图标失败: {e}", flush=True)


def _read_registry_config():
    """从注册表读取安装程序写入的配置（仅 Windows）"""
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\GeQuPlayer", 0, winreg.KEY_READ)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"[main] 读取注册表失败: {e}", flush=True)
        return

    values = {}
    for name in ("InstallPath", "CacheDir", "DownloadDir"):
        try:
            v, _ = winreg.QueryValueEx(key, name)
            if v and isinstance(v, str):
                values[name] = v
        except FileNotFoundError:
            continue
        except Exception:
            continue
    winreg.CloseKey(key)

    if not values:
        return

    from utils.helpers import load_config, save_config
    cfg = load_config()
    changed = False

    if "download_dir" not in cfg and "DownloadDir" in values:
        cfg["download_dir"] = values["DownloadDir"]
        changed = True
        print(f"[main] 采用注册表下载目录: {values['DownloadDir']}", flush=True)

    if "cache_dir" not in cfg and "CacheDir" in values:
        cfg["cache_dir"] = values["CacheDir"]
        changed = True
        print(f"[main] 采用注册表缓存目录: {values['CacheDir']}", flush=True)

    if changed:
        save_config(cfg)


def setup_playwright_env():
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


def _download_chromium_subprocess():
    if getattr(sys, "frozen", False):
        try:
            from playwright.__main__ import main as pw_main
            sys.argv = ["playwright", "install", "chromium"]
            pw_main()
            return
        except SystemExit:
            return
        except Exception as e:
            print(f"[main] 内置调用失败: {e}，尝试系统 python", flush=True)
            import shutil
            python_exe = shutil.which("python") or shutil.which("python3")
            if python_exe:
                subprocess.run(
                    [python_exe, "-m", "playwright", "install", "chromium"],
                    check=True)
                return
            raise
    else:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True)


def ensure_playwright_chromium(parent=None) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        QMessageBox.warning(
            parent, "缺少依赖",
            "Playwright 未安装。请运行：\n"
            "pip install playwright")
        return False

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        print("[main] Chromium 已就绪", flush=True)
        return True
    except Exception as e:
        print(f"[main] Chromium 未安装或启动失败: {e}", flush=True)

    ret = QMessageBox.question(
        parent, "首次运行准备",
        "首次使用需要下载 Chromium 内核（约 150MB），用于解析音乐链接。\n\n"
        "是否现在下载？下载过程可能需要 1-3 分钟。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if ret != QMessageBox.StandardButton.Yes:
        QMessageBox.information(
            parent, "跳过",
            "你可以稍后手动下载。打开 PowerShell 执行：\n\n"
            "$env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright'\n"
            "python -m playwright install chromium")
        return False

    env_backup = os.environ.get("PLAYWRIGHT_DOWNLOAD_HOST")
    os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = \
        "https://npmmirror.com/mirrors/playwright"

    progress = QProgressDialog(
        "正在下载 Chromium 内核（约 150MB）...\n"
        "下载期间请勿关闭窗口，可能需要 1-3 分钟。",
        None, 0, 0, parent)
    progress.setWindowTitle("下载 Chromium")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)
    progress.show()
    QApplication.processEvents()

    success = False
    try:
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
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                b.close()
            QMessageBox.information(parent, "完成", "Chromium 内核下载完成！")
            return True
        except Exception as e:
            QMessageBox.critical(parent, "下载后仍无法启动",
                                 f"{e}\n\n请手动执行 playwright install chromium")
            return False
    else:
        QMessageBox.critical(parent, "下载失败",
                             "请手动执行：\n"
                             "playwright install chromium")
        return False


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    setup_playwright_env()

    # 必须在 QApplication 创建之前设置 AppUserModelID，
    # 否则任务栏图标不会生效（Windows 特有）
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "tiankong.GeQuPlayer.1")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("GeQuPlayer")
    app.setApplicationDisplayName("GeQuPlayer")
    app.setOrganizationName("tiankong")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    # ============ 设置窗口/任务栏图标 ============
    _set_app_icon(app)
    # =============================================

    try:
        from utils.log_capture import LogCapture
        LogCapture.instance().install()
        print("[main] 日志捕获已启用", flush=True)
    except Exception as e:
        print(f"[main] 日志捕获安装失败: {e}", flush=True)

    apply_style(app)
    init_db()

    _read_registry_config()

    ensure_playwright_chromium()

    w = MainWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
