"""音频播放引擎，基于 just_playback + requests 下载缓存

酷我 CDN 防盗链需要完整的浏览器请求特征，这里模拟完整请求头。
"""
import hashlib
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import requests
from just_playback import Playback
from PyQt6.QtCore import QObject, pyqtSignal

from config import USER_AGENT


_CACHE_DIR = Path(tempfile.gettempdir()) / "musicplayer_cache"
_CACHE_DIR.mkdir(exist_ok=True)

MIN_VALID_SIZE = 400 * 1024   # 400 KB 以下视为占位音频

# 按优先级尝试的完整请求头组合
HEADER_VARIANTS = [
    # 1. 最接近浏览器的请求
    {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.kuwo.cn/",
        "Origin": "https://www.kuwo.cn",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "identity",
    },
    # 2. 带 kw_token cookie
    {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.kuwo.cn/",
        "Origin": "https://www.kuwo.cn",
        "Cookie": "kw_token=GY3EWHPDHD",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    },
    # 3. gequbao 来源
    {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.gequbao.com/",
        "Origin": "https://www.gequbao.com",
        "Accept": "*/*",
    },
    # 4. 无 Referer 但带 Origin
    {
        "User-Agent": USER_AGENT,
        "Origin": "https://www.kuwo.cn",
        "Accept": "*/*",
    },
]


class AudioEngine(QObject):
    state_changed = pyqtSignal(str)
    position_changed = pyqtSignal(float, float)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_message = pyqtSignal(str)

    _play_local_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playback: Optional[Playback] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._loader_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._current_url: Optional[str] = None
        self._current_info: dict = {}
        self._duration = 0.0

        self._play_local_signal.connect(self._do_play_local)

    @property
    def current_info(self) -> dict:
        return self._current_info

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        if self._playback and self._playback.active:
            return self._playback.curr_pos
        return 0.0

    @property
    def is_paused(self) -> bool:
        return self._playback is not None and self._playback.paused

    @property
    def is_playing(self) -> bool:
        return self._playback is not None and self._playback.playing

    # ---------- 对外接口 ----------
    def play_url(self, url: str, info: dict = None):
        self.stop()
        self._current_url = url
        self._current_info = info or {}
        self._stop_flag.clear()
        self.state_changed.emit("loading")
        self.status_message.emit("正在下载音频...")

        self._loader_thread = threading.Thread(
            target=self._download_and_play, args=(url,), daemon=True
        )
        self._loader_thread.start()

    def play_file(self, path: str, info: dict = None):
        self.stop()
        self._current_url = path
        self._current_info = info or {}
        self._stop_flag.clear()
        self._do_play_local(str(path))

    # ---------- 内部 ----------
    def _cache_path_for(self, url: str) -> Path:
        h = hashlib.md5(url.encode("utf-8")).hexdigest()
        return _CACHE_DIR / f"{h}.mp3"

    def _download_and_play(self, url: str):
        try:
            cache = self._cache_path_for(url)

            if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE:
                self._play_local_signal.emit(str(cache))
                return
            if cache.exists():
                try:
                    cache.unlink()
                except Exception:
                    pass

            tmp = cache.with_suffix(".part")
            last_err = ""

            for idx, headers in enumerate(HEADER_VARIANTS):
                if self._stop_flag.is_set():
                    return
                try:
                    self.status_message.emit(
                        f"正在下载音频... (尝试 {idx + 1}/{len(HEADER_VARIANTS)})"
                    )
                    r = requests.get(url, headers=headers, stream=True, timeout=30)
                    r.raise_for_status()

                    size = 0
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(64 * 1024):
                            if self._stop_flag.is_set():
                                try:
                                    tmp.unlink()
                                except Exception:
                                    pass
                                return
                            if chunk:
                                f.write(chunk)
                                size += len(chunk)

                    ref = headers.get("Referer", "无")
                    if size >= MIN_VALID_SIZE:
                        os.replace(tmp, cache)
                        print(f"[audio] ✓ 下载成功 size={size} headers变体={idx+1} Referer={ref}", flush=True)
                        self._play_local_signal.emit(str(cache))
                        return
                    else:
                        last_err = f"文件过小 ({size} 字节)"
                        print(f"[audio] ✗ 变体{idx+1} Referer={ref} 失败: {last_err}", flush=True)
                        try:
                            tmp.unlink()
                        except Exception:
                            pass
                except Exception as e:
                    last_err = str(e)
                    print(f"[audio] ✗ 变体{idx+1} 异常: {e}", flush=True)
                    try:
                        if tmp.exists():
                            tmp.unlink()
                    except Exception:
                        pass
                    continue

            self.error_occurred.emit(
                f"下载失败（已尝试 {len(HEADER_VARIANTS)} 种请求头）: {last_err}"
            )
            self.status_message.emit("")
            self.state_changed.emit("stopped")

        except Exception as e:
            if not self._stop_flag.is_set():
                self.error_occurred.emit(f"播放失败: {e}")
                self.status_message.emit("")
                self.state_changed.emit("stopped")

    def _do_play_local(self, path: str):
        try:
            self._playback = Playback()
            self._playback.load_file(path)
            self._duration = self._playback.duration or 0.0
            self._playback.play()
            self.state_changed.emit("playing")
            self.status_message.emit("")
            self._start_monitor()
        except Exception as e:
            self.error_occurred.emit(f"播放失败: {e}")
            self.status_message.emit("")
            self.state_changed.emit("stopped")

    def _start_monitor(self):
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()

    def _monitor(self):
        while not self._stop_flag.is_set():
            if self._playback is None:
                break
            try:
                if not self._playback.active:
                    if not self._stop_flag.is_set():
                        self.position_changed.emit(self._duration, self._duration)
                        self.state_changed.emit("stopped")
                        self.finished.emit()
                    break
                cur = self._playback.curr_pos
                self.position_changed.emit(cur, self._duration)
            except Exception:
                break
            time.sleep(0.25)

    # ---------- 控制 ----------
    def toggle_pause(self):
        if self._playback is None or not self._playback.active:
            return
        if self._playback.paused:
            self._playback.resume()
            self.state_changed.emit("playing")
        else:
            self._playback.pause()
            self.state_changed.emit("paused")

    def pause(self):
        if self._playback and self._playback.playing:
            self._playback.pause()
            self.state_changed.emit("paused")

    def resume(self):
        if self._playback and self._playback.paused:
            self._playback.resume()
            self.state_changed.emit("playing")

    def stop(self):
        self._stop_flag.set()
        if self._playback:
            try:
                self._playback.stop()
            except Exception:
                pass
        self._playback = None
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=0.5)
        self._monitor_thread = None
        if self._loader_thread and self._loader_thread.is_alive():
            self._loader_thread.join(timeout=0.5)
        self._loader_thread = None
        self.state_changed.emit("stopped")

    def seek(self, seconds: float):
        if self._playback and self._playback.active:
            self._playback.seek(max(0.0, seconds))
