"""通用工具函数"""
import json
import re
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from config import CONFIG_PATH


def sanitize_filename(name: str) -> str:
    """去掉文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip().strip(".")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def format_time(seconds: float) -> str:
    if not seconds or seconds < 0:
        seconds = 0
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


class _AsyncRunner(QObject):
    """用于把后台线程的结果通过 Qt 信号安全地送回主线程"""
    done = pyqtSignal(object)
    error = pyqtSignal(str)


def run_async(fn, on_done=None, on_error=None):
    """
    在后台线程执行 fn()，
    结果通过 Qt 信号发回主线程，on_done / on_error 会在主线程中被调用。
    """
    # 每次调用使用独立的 runner，避免并发冲突
    runner = _AsyncRunner()

    if on_done:
        runner.done.connect(on_done)
    if on_error:
        runner.error.connect(on_error)

    def worker():
        try:
            result = fn()
            runner.done.emit(result)
        except Exception as e:
            runner.error.emit(str(e))

    t = threading.Thread(target=worker, daemon=True)
    # 把 runner 挂在线程对象上，避免被垃圾回收
    t._runner = runner
    t.start()
