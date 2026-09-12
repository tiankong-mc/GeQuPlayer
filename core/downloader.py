"""批量下载管理器"""
import os
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core.gequbao_api import (
    resolve_song, search as gequbao_search, _clean_song_cache,
    delete_cache_file,
)
from utils.helpers import sanitize_filename


MAX_RETRY_PER_TASK = 1
CONCURRENT_TASKS = 4
COOLDOWN_SECONDS = 15
TOTAL_ROUNDS = 2


class DownloadTask:
    __slots__ = ("title", "artist", "song_id", "status", "error",
                 "filepath", "retry_count")

    def __init__(self, title, artist="", song_id=None):
        self.title = title
        self.artist = artist
        self.song_id = song_id
        self.status = "pending"
        self.error = ""
        self.filepath = ""
        self.retry_count = 0

    @property
    def display(self):
        return f"{self.title} - {self.artist}" if self.artist else self.title


class Downloader(QObject):
    task_updated = pyqtSignal(int)
    all_finished = pyqtSignal(int, int)
    round_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks: List[DownloadTask] = []
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.download_dir = ""
        self.playlist_name = ""
        self._lock = threading.Lock()

    def set_download_dir(self, path):
        self.download_dir = path

    def add_task(self, title, artist="", song_id=None):
        self.tasks.append(DownloadTask(title, artist, song_id))
        return len(self.tasks) - 1

    def start(self, download_dir, playlist_name=""):
        if self._thread and self._thread.is_alive():
            return
        self.download_dir = download_dir
        self.playlist_name = playlist_name or ""
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._stop_flag.is_set():
            print("[downloader] 收到停止信号", flush=True)
            self._stop_flag.set()

    def clear(self):
        self.tasks.clear()
        self.playlist_name = ""

    # ---------- 内部 ----------
    def _interruptible_sleep(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            if self._stop_flag.is_set():
                return False
            time.sleep(0.2)
        return True

    def _match_song(self, title, artist):
        try:
            results = gequbao_search(f"{title} {artist}".strip(), limit=20)
        except Exception:
            results = []
        if not results:
            try:
                results = gequbao_search(title, limit=20)
            except Exception:
                results = []
        for r in results:
            if r.title.strip() == title.strip() and r.artist.strip() == artist.strip():
                return r
        for r in results:
            if r.title.strip() == title.strip():
                return r
        return results[0] if results else None

    def _run(self):
        total = len(self.tasks)

        for round_num in range(1, TOTAL_ROUNDS + 1):
            if self._stop_flag.is_set():
                break

            if round_num == 1:
                tasks_to_run = [(i, t) for i, t in enumerate(self.tasks)
                                if t.status != "done"]
            else:
                tasks_to_run = [(i, t) for i, t in enumerate(self.tasks)
                                if t.status == "failed"]

            if not tasks_to_run:
                if round_num > 1:
                    print(f"[downloader] 第 {round_num} 轮无需重试", flush=True)
                break

            if round_num > 1:
                print(f"[downloader] 冷却 {COOLDOWN_SECONDS} 秒后开始第 {round_num} 轮...",
                      flush=True)
                if not self._interruptible_sleep(COOLDOWN_SECONDS):
                    break

                for idx, t in tasks_to_run:
                    with self._lock:
                        t.status = "pending"
                        t.error = ""
                        t.retry_count = 0
                    self.task_updated.emit(idx)

            self.round_changed.emit(round_num)
            print(f"[downloader] 第 {round_num} 轮：{len(tasks_to_run)} 首", flush=True)
            self._run_round(tasks_to_run)

        self._finish()

    def _run_round(self, tasks_with_idx):
        if not tasks_with_idx:
            return

        try:
            with ThreadPoolExecutor(max_workers=CONCURRENT_TASKS) as pool:
                futures = {}
                for idx, task in tasks_with_idx:
                    if self._stop_flag.is_set():
                        break
                    fut = pool.submit(self._process_task_with_retry, idx, task)
                    futures[fut] = idx

                for fut in as_completed(futures):
                    if self._stop_flag.is_set():
                        for f in futures:
                            f.cancel()
                        break
                    try:
                        fut.result()
                    except Exception as e:
                        idx = futures[fut]
                        if 0 <= idx < len(self.tasks):
                            self.tasks[idx].status = "failed"
                            self.tasks[idx].error = str(e)
                            self.task_updated.emit(idx)
        except Exception as e:
            print(f"[downloader] 线程池异常: {e}", flush=True)

    def _finish(self):
        total = len(self.tasks)
        success = sum(1 for t in self.tasks if t.status == "done")

        if self.playlist_name and not self._stop_flag.is_set():
            self._save_playlist_m3u()

        # 最后清理：删掉所有已完成任务的缓存（如果还没删的话）
        self._cleanup_done_cache()

        print(f"[downloader] 完成，成功 {success}/{total}", flush=True)
        self.all_finished.emit(success, total)

    def _cleanup_done_cache(self):
        """兜底清理：把已完成任务对应的缓存文件删掉"""
        for t in self.tasks:
            if t.status == "done" and t.song_id:
                try:
                    from core.gequbao_api import _pw_cache_path
                    cache = _pw_cache_path(t.song_id)
                    if cache.exists():
                        delete_cache_file(str(cache), verbose=False)
                except Exception:
                    pass

    def _save_playlist_m3u(self):
        try:
            from core.local_library import LocalSong, save_m3u
            done_tasks = [t for t in self.tasks if t.status == "done" and t.filepath]
            if not done_tasks:
                return
            songs = []
            for t in done_tasks:
                lrc = os.path.splitext(t.filepath)[0] + ".lrc"
                songs.append(LocalSong(
                    path=t.filepath,
                    lrc_path=lrc if os.path.exists(lrc) else None,
                    title=t.title,
                    artist=t.artist,
                ))
            name = sanitize_filename(self.playlist_name)
            m3u_path = os.path.join(self.download_dir, name + ".m3u")
            save_m3u(m3u_path, self.playlist_name, songs)
            print(f"[downloader] 生成歌单：{m3u_path}", flush=True)
        except Exception as e:
            print(f"[downloader] m3u 失败: {e}", flush=True)

    def _process_task_with_retry(self, idx, task):
        last_err = ""
        for attempt in range(1, MAX_RETRY_PER_TASK + 1):
            if self._stop_flag.is_set():
                with self._lock:
                    if task.status not in ("done", "failed", "skipped", "stopped"):
                        task.status = "stopped"
                        task.error = "已停止"
                self.task_updated.emit(idx)
                return

            if attempt > 1:
                with self._lock:
                    task.status = "retry"
                    task.retry_count = attempt - 1
                self.task_updated.emit(idx)
                delay = 2.0 + random.uniform(0.5, 2.0)
                if not self._interruptible_sleep(delay):
                    return

            try:
                ok = self._process_task(idx, task)
                if ok:
                    return
                last_err = task.error or "未知错误"
            except Exception as e:
                last_err = str(e)

            if self._stop_flag.is_set():
                return

            if task.song_id:
                try:
                    _clean_song_cache(task.song_id)
                except Exception:
                    pass

        with self._lock:
            task.status = "failed"
            task.error = last_err or "未知错误"
        self.task_updated.emit(idx)

    def _process_task(self, idx, task):
        if self._stop_flag.is_set():
            return False

        title, artist = task.title, task.artist

        song_id = task.song_id
        if not song_id:
            with self._lock:
                task.status = "searching"
            self.task_updated.emit(idx)

            target = self._match_song(title, artist)
            if target is None:
                with self._lock:
                    task.status = "skipped"
                    task.error = "gequbao 未找到匹配"
                self.task_updated.emit(idx)
                return False
            song_id = target.song_id
            title = target.title or title
            artist = target.artist or artist
            task.title = title
            task.artist = artist
            task.song_id = song_id

        if self._stop_flag.is_set():
            return False

        with self._lock:
            task.status = "downloading"
        self.task_updated.emit(idx)

        data = resolve_song(song_id, title, artist, max_retry=1,
                            stop_flag=self._stop_flag)
        src_file = data.get("file")
        lyrics = data.get("lyrics")

        if self._stop_flag.is_set():
            return False

        if not src_file or not os.path.exists(src_file):
            task.error = "下载失败"
            return False

        os.makedirs(self.download_dir, exist_ok=True)
        base = f"{artist} - {title}" if artist else title
        base = sanitize_filename(base)
        dest_mp3 = os.path.join(self.download_dir, base + ".mp3")

        try:
            shutil.copy2(src_file, dest_mp3)
        except Exception as e:
            task.error = f"复制失败: {e}"
            return False

        if lyrics:
            try:
                with open(os.path.join(self.download_dir, base + ".lrc"),
                          "w", encoding="utf-8") as f:
                    f.write(lyrics)
            except Exception:
                pass

        # ============ 关键：下载完成后删缓存 ============
        # 复制成功，缓存副本现在冗余，删除它释放空间
        # （如果这首歌正在被播放，delete_cache_file 会自动跳过）
        delete_cache_file(src_file)

        with self._lock:
            task.filepath = dest_mp3
            task.status = "done"
        self.task_updated.emit(idx)
        return True
