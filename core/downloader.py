"""批量下载管理器

- 每个任务失败自动重试最多 2 次
- 支持歌单名：全部完成后生成 .m3u 播放列表
"""
import os
import shutil
import threading
import time
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core.gequbao_api import (
    resolve_song, search as gequbao_search, _clean_song_cache,
)
from core.local_library import LocalSong, save_m3u
from utils.helpers import sanitize_filename


MAX_RETRY = 2


class DownloadTask:
    __slots__ = ("title", "artist", "song_id", "status", "error",
                 "filepath", "retry_count")

    def __init__(self, title: str, artist: str = "", song_id: Optional[str] = None):
        self.title = title
        self.artist = artist
        self.song_id = song_id
        self.status = "pending"
        self.error = ""
        self.filepath = ""
        self.retry_count = 0

    @property
    def display(self) -> str:
        return f"{self.title} - {self.artist}" if self.artist else self.title


class Downloader(QObject):
    task_updated = pyqtSignal(int)
    all_finished = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks: List[DownloadTask] = []
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.download_dir = ""
        self.playlist_name = ""

    def set_download_dir(self, path: str):
        self.download_dir = path

    def add_task(self, title: str, artist: str = "", song_id: Optional[str] = None) -> int:
        self.tasks.append(DownloadTask(title, artist, song_id))
        return len(self.tasks) - 1

    def start(self, download_dir: str, playlist_name: str = ""):
        if self._thread and self._thread.is_alive():
            return
        self.download_dir = download_dir
        self.playlist_name = playlist_name or ""
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()

    def clear(self):
        self.tasks.clear()
        self.playlist_name = ""

    # ---------- 内部 ----------
    def _match_song(self, title: str, artist: str):
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
        success = 0
        for i, task in enumerate(self.tasks):
            if self._stop_flag.is_set():
                break
            if task.status == "done":
                success += 1
                continue
            try:
                self._process_task_with_retry(i, task)
                if task.status == "done":
                    success += 1
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            self.task_updated.emit(i)

        # 全部完成，生成 .m3u
        if self.playlist_name and not self._stop_flag.is_set():
            self._save_playlist_m3u()

        self.all_finished.emit(success, total)

    def _save_playlist_m3u(self):
        """把成功下载的歌曲保存为一个 .m3u"""
        try:
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
            print(f"[downloader] 生成歌单文件：{m3u_path}", flush=True)
        except Exception as e:
            print(f"[downloader] 生成 m3u 失败: {e}", flush=True)

    def _process_task_with_retry(self, idx: int, task: DownloadTask):
        last_err = ""
        for attempt in range(1, MAX_RETRY + 1):
            if self._stop_flag.is_set():
                return

            if attempt > 1:
                task.status = "retry"
                task.retry_count = attempt - 1
                self.task_updated.emit(idx)
                time.sleep(1.5)

            try:
                ok = self._process_task(idx, task)
                if ok:
                    return
                last_err = task.error or "未知错误"
            except Exception as e:
                last_err = str(e)

            if task.song_id:
                try:
                    _clean_song_cache(task.song_id)
                except Exception:
                    pass

        task.status = "failed"
        task.error = f"{last_err}（已重试 {MAX_RETRY} 次）"
        self.task_updated.emit(idx)

    def _process_task(self, idx: int, task: DownloadTask) -> bool:
        title, artist = task.title, task.artist

        song_id = task.song_id
        if not song_id:
            task.status = "searching"
            self.task_updated.emit(idx)

            target = self._match_song(title, artist)
            if target is None:
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

        task.status = "downloading"
        self.task_updated.emit(idx)

        data = resolve_song(song_id, title, artist, max_retry=1)
        src_file = data.get("file")
        lyrics = data.get("lyrics")

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
                with open(os.path.join(self.download_dir, base + ".lrc"), "w", encoding="utf-8") as f:
                    f.write(lyrics)
            except Exception:
                pass

        task.filepath = dest_mp3
        task.status = "done"
        self.task_updated.emit(idx)
        return True
