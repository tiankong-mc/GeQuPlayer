"""音频播放引擎：基于 just_playback

修复：
- 使用 generation ID 避免旧线程覆盖新播放（快速切歌不再播错）
- 缓存目录从 gequbao_api.get_cache_dir() 动态获取
- 播放时保护文件不被删除
"""
import os
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

from just_playback import Playback
from PyQt6.QtCore import QObject, pyqtSignal

from core.gequbao_api import protect_file, unprotect_file, get_cache_dir


class AudioEngine(QObject):
    state_changed = pyqtSignal(str)
    position_changed = pyqtSignal(float, float)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_message = pyqtSignal(str)

    # 内部信号：携带 (path, generation)
    _play_local_signal = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playback: Optional[Playback] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._loader_thread: Optional[threading.Thread] = None

        # 用 generation 代替共享的 stop_flag，避免竞态
        self._generation = 0
        self._gen_lock = threading.Lock()

        self._current_url: Optional[str] = None
        self._current_info: dict = {}
        self._duration = 0.0
        self._playing_path: Optional[str] = None

        self._play_local_signal.connect(self._do_play_local)

    # ---------- 属性 ----------
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

    # ---------- generation ----------
    def _bump_generation(self) -> int:
        with self._gen_lock:
            self._generation += 1
            return self._generation

    def _is_current(self, gen: int) -> bool:
        with self._gen_lock:
            return gen == self._generation

    # ---------- 对外接口 ----------
    def play_url(self, url: str, info: dict = None):
        # 使旧线程失效
        self.stop()

        my_gen = self._bump_generation()
        self._current_url = url
        self._current_info = info or {}
        self.state_changed.emit("loading")
        self.status_message.emit("正在下载音频...")

        self._loader_thread = threading.Thread(
            target=self._download_and_play, args=(url, my_gen), daemon=True
        )
        self._loader_thread.start()

    def play_file(self, path: str, info: dict = None):
        self.stop()

        my_gen = self._bump_generation()
        self._current_url = path
        self._current_info = info or {}

        # 直接在主线程调用（通过信号）
        self._play_local_signal.emit(str(path), my_gen)

    # ---------- 内部 ----------
    def _cache_path_for(self, url: str) -> Path:
        import hashlib
        h = hashlib.md5(url.encode("utf-8")).hexdigest()
        return get_cache_dir() / f"{h}.mp3"

    def _download_and_play(self, url: str, my_gen: int):
        tmp_file: Optional[Path] = None
        try:
            if not self._is_current(my_gen):
                return

            cache = self._cache_path_for(url)
            if cache.exists() and cache.stat().st_size > 1024:
                if self._is_current(my_gen):
                    self._play_local_signal.emit(str(cache), my_gen)
                return

            import requests
            from config import USER_AGENT, GEQUBAO_BASE

            headers = {"User-Agent": USER_AGENT, "Referer": GEQUBAO_BASE + "/"}
            r = requests.get(url, headers=headers, stream=True, timeout=30)
            r.raise_for_status()

            tmp_file = cache.with_suffix(".part")
            with open(tmp_file, "wb") as f:
                for chunk in r.iter_content(64 * 1024):
                    if not self._is_current(my_gen):
                        return
                    if chunk:
                        f.write(chunk)

            if not self._is_current(my_gen):
                return

            os.replace(tmp_file, cache)
            self._play_local_signal.emit(str(cache), my_gen)

        except Exception as e:
            if self._is_current(my_gen):
                self.error_occurred.emit(f"播放失败: {e}")
                self.state_changed.emit("stopped")
        finally:
            if tmp_file and tmp_file.exists() and not self._is_current(my_gen):
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    def _do_play_local(self, path: str, my_gen: int):
        """主线程中调用"""
        if not self._is_current(my_gen):
            print(f"[audio] 忽略过期播放请求", flush=True)
            return

        try:
            # 解除上一个文件的保护
            if self._playing_path and self._playing_path != path:
                unprotect_file(self._playing_path)

            protect_file(path)
            self._playing_path = path

            self._playback = Playback()
            self._playback.load_file(path)
            self._duration = self._playback.duration or 0.0
            self._playback.play()
            self.state_changed.emit("playing")
            self.status_message.emit("")
            self._start_monitor(my_gen)
        except Exception as e:
            unprotect_file(path)
            self._playing_path = None
            self.error_occurred.emit(f"播放失败: {e}")
            self.status_message.emit("")
            self.state_changed.emit("stopped")

    def _start_monitor(self, my_gen: int):
        self._monitor_thread = threading.Thread(
            target=self._monitor, args=(my_gen,), daemon=True)
        self._monitor_thread.start()

    def _monitor(self, my_gen: int):
        last_pos = 0.0
        while self._is_current(my_gen):
            if self._playback is None:
                break
            try:
                if not self._playback.active:
                    if self._is_current(my_gen):
                        self.position_changed.emit(self._duration, self._duration)
                        self.state_changed.emit("stopped")
                        self.finished.emit()
                    break
                cur = self._playback.curr_pos
                if abs(cur - last_pos) > 0.05:
                    self.position_changed.emit(cur, self._duration)
                    last_pos = cur
            except Exception:
                break
            time.sleep(0.25)

        # 播放结束，解除保护
        if self._is_current(my_gen) and self._playing_path:
            unprotect_file(self._playing_path)
            self._playing_path = None

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
        # 使所有旧线程失效
        self._bump_generation()

        if self._playback:
            try:
                self._playback.stop()
            except Exception:
                pass
        self._playback = None

        if self._playing_path:
            unprotect_file(self._playing_path)
            self._playing_path = None

        # 不等待线程结束（线程会自己检查 generation 退出）
        self._monitor_thread = None
        self._loader_thread = None

        self.state_changed.emit("stopped")

    def seek(self, seconds: float):
        if self._playback and self._playback.active:
            self._playback.seek(max(0.0, seconds))
