"""批量下载管理器"""
import os
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from config import DOWNLOAD_MP3_SUBDIR, DOWNLOAD_LRC_SUBDIR
from core.gequbao_api import (
    resolve_song, search as gequbao_search, _clean_song_cache,
    delete_cache_file, _pw_cache_path,
)
from utils.helpers import sanitize_filename


MAX_RETRY_PER_TASK = 1
COOLDOWN_SECONDS = 15
TOTAL_ROUNDS = 2

CONCURRENT_TASKS = 4


def _get_concurrent_tasks() -> int:
    try:
        from utils.helpers import load_config
        cfg = load_config()
        v = int(cfg.get("concurrent_tasks", 4))
        return max(1, min(v, 10))
    except Exception:
        return 4


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
        self._concurrent = CONCURRENT_TASKS

    def set_download_dir(self, path):
        self.download_dir = path

    def add_task(self, title, artist="", song_id=None):
        self.tasks.append(DownloadTask(title, artist, song_id))
        return len(self.tasks) - 1

    def start(self, download_dir, playlist_name=""):
        if self._thread and self._thread.is_alive():
            return
        self._concurrent = _get_concurrent_tasks()
        print(f"[downloader] 同时下载数：{self._concurrent}", flush=True)

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
    @staticmethod
    def _unique_path(directory: str, base: str, ext: str) -> str:
        p = os.path.join(directory, base + ext)
        if not os.path.exists(p):
            return p
        i = 1
        while i < 10000:
            p = os.path.join(directory, f"{base} ({i}){ext}")
            if not os.path.exists(p):
                return p
            i += 1
        import time as _t
        return os.path.join(directory, f"{base}_{int(_t.time())}{ext}")

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
                print(f"[downloader] 冷却 {COOLDOWN_SECONDS} 秒后开始第 {round_num} 轮"
                      f"（{len(tasks_to_run)} 首真正失败的任务）...", flush=True)
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
            with ThreadPoolExecutor(max_workers=self._concurrent) as pool:
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
        skipped = sum(1 for t in self.tasks if t.status == "skipped")
        failed = sum(1 for t in self.tasks if t.status == "failed")

        if self.playlist_name and not self._stop_flag.is_set():
            self._save_playlist_m3u()

        self._cleanup_done_cache()

        msg = f"[downloader] 完成，成功 {success}/{total}"
        if skipped:
            msg += f" / 跳过 {skipped}（搜不到）"
        if failed:
            msg += f" / 失败 {failed}"
        print(msg, flush=True)

        self.all_finished.emit(success, total)

    def _cleanup_done_cache(self):
        for t in self.tasks:
            if t.status == "done" and t.song_id:
                try:
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
                # LRC 现在在 {download_dir}/LRC/{base}.lrc
                base = os.path.splitext(os.path.basename(t.filepath))[0]
                lrc_path = os.path.join(self.download_dir,
                                        DOWNLOAD_LRC_SUBDIR, base + ".lrc")
                songs.append(LocalSong(
                    path=t.filepath,
                    lrc_path=lrc_path if os.path.exists(lrc_path) else None,
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

            if task.status == "skipped":
                print(f"[downloader] 「{task.display}」搜不到，跳过重试", flush=True)
                return

            if task.song_id:
                try:
                    _clean_song_cache(task.song_id)
                except Exception:
                    pass

        with self._lock:
            if task.status == "skipped":
                pass
            elif task.status == "stopped":
                pass
            else:
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
                print(f"[downloader] 「{title} - {artist}」gequbao 搜不到，标记为跳过",
                      flush=True)
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

        # ============ 分成 MP3/ 和 LRC/ 子目录 ============
        mp3_dir = os.path.join(self.download_dir, DOWNLOAD_MP3_SUBDIR)
        lrc_dir = os.path.join(self.download_dir, DOWNLOAD_LRC_SUBDIR)
        try:
            os.makedirs(mp3_dir, exist_ok=True)
            os.makedirs(lrc_dir, exist_ok=True)
        except Exception as e:
            task.error = f"创建目录失败: {e}"
            return False

        base = f"{artist} - {title}" if artist else title
        base = sanitize_filename(base)

        dest_mp3 = self._unique_path(mp3_dir, base, ".mp3")

        try:
            shutil.copy2(src_file, dest_mp3)
        except Exception as e:
            task.error = f"复制失败: {e}"
            return False

        if lyrics:
            dest_lrc = self._unique_path(lrc_dir, base, ".lrc")
            try:
                with open(dest_lrc, "w", encoding="utf-8") as f:
                    f.write(lyrics)
            except Exception:
                pass

        try:
            from data.database import add_download
            add_download(title, artist, dest_mp3)
        except Exception as e:
            print(f"[downloader] 记录历史失败: {e}", flush=True)

        delete_cache_file(src_file)

        with self._lock:
            task.filepath = dest_mp3
            task.status = "done"
        self.task_updated.emit(idx)
        return True
