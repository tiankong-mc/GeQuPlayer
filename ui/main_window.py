"""主窗口"""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
)

from core.audio_engine import AudioEngine
from core.gequbao_api import Song, resolve_song
from core.lyrics_parser import load_lrc_file, parse_lrc
from core.playback_queue import (
    PlaybackQueue, PlaybackMode, QueueItem, MODE_NAMES,
)

from ui.search_panel import SearchPanel
from ui.playlist_panel import PlaylistPanel
from ui.local_panel import LocalPanel
from ui.download_panel import DownloadPanel
from ui.settings_panel import SettingsPanel
from ui.player_bar import PlayerBar
from ui.lyrics_window import LyricsWindow

from utils.helpers import run_async, load_config, save_config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicPlayer · gequbao 在线音乐")
        cfg = load_config()
        self.resize(int(cfg.get("win_w", 1200)), int(cfg.get("win_h", 780)))
        self.setMinimumSize(1080, 680)

        self._lyrics_visible = bool(cfg.get("lyrics_visible", False))
        self._lyrics_locked = bool(cfg.get("lyrics_locked", False))

        self.audio = AudioEngine(self)
        self.lyrics_window = LyricsWindow()
        self.queue = PlaybackQueue()
        # 恢复上次的播放模式
        self.queue.set_mode(cfg.get("playback_mode", PlaybackMode.LOOP_LIST))

        self._current_song_info = {}

        central = QWidget()
        central.setObjectName("RootWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab
        self.tabs = QTabWidget()
        self.search_panel = SearchPanel(self)
        self.playlist_panel = PlaylistPanel(self)
        self.local_panel = LocalPanel(self)
        self.download_panel = DownloadPanel(self)
        self.settings_panel = SettingsPanel(self)

        self.tabs.addTab(self.search_panel, "搜索")
        self.tabs.addTab(self.playlist_panel, "歌单")
        self.tabs.addTab(self.local_panel, "本地音乐")
        self.tabs.addTab(self.download_panel, "下载")
        self.tabs.addTab(self.settings_panel, "设置")
        layout.addWidget(self.tabs, 1)

        # 播放栏
        self.player_bar = PlayerBar(self.audio, self)
        self.player_bar.set_mode(self.queue.mode)
        self.player_bar.set_lyrics_checked(self._lyrics_visible)
        self.player_bar.set_lock_checked(self._lyrics_locked)
        layout.addWidget(self.player_bar)

        # 信号连接
        self.search_panel.play_list_requested.connect(self._play_search_list)
        self.search_panel.download_requested.connect(self._download_search_song)

        self.playlist_panel.play_list_requested.connect(self._play_playlist_list)
        self.playlist_panel.download_requested.connect(self._add_download_tasks)
        self.playlist_panel.download_single_requested.connect(self._download_playlist_song)

        self.local_panel.play_list_requested.connect(self._play_local_list)
        self.local_panel.set_download_dir.connect(self._on_dir_changed)

        self.download_panel.set_download_dir.connect(self._on_dir_changed)
        self.settings_panel.set_download_dir.connect(self._on_dir_changed)
        self.settings_panel.cache_cleared.connect(self._on_cache_cleared)
        self.settings_panel.cache_dir_changed.connect(self._on_cache_dir_changed)

        self.player_bar.toggle_lyrics.connect(self._on_toggle_lyrics)
        self.player_bar.toggle_lyric_lock.connect(self._on_toggle_lyric_lock)
        self.player_bar.prev_requested.connect(self._on_prev)
        self.player_bar.next_requested.connect(self._on_next)
        self.player_bar.mode_change_requested.connect(self._on_mode_change)

        self.audio.state_changed.connect(self._on_audio_state)
        self.audio.position_changed.connect(self._on_audio_position)
        self.audio.finished.connect(self._on_audio_finished)
        self.audio.error_occurred.connect(self._on_audio_error)
        self.audio.status_message.connect(self._on_audio_status_message)

        self.local_panel.refresh()

        self.lyrics_window.set_enabled(self._lyrics_visible)
        self.lyrics_window.set_locked(self._lyrics_locked)
        if self._lyrics_visible:
            self.lyrics_window.show()
        else:
            self.lyrics_window.hide()

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_window_size)

    # ---------- 播放队列 ----------
    def _play_search_list(self, songs, index):
        """搜索列表播放"""
        items = [QueueItem(title=s.title, artist=s.artist, song_id=s.song_id)
                 for s in songs]
        if not items:
            return
        self.queue.set_items(items, index)
        self._play_queue_current()

    def _play_playlist_list(self, songs, index):
        """在线歌单播放"""
        items = [QueueItem(title=s.title, artist=s.artist, song_id=None)
                 for s in songs]
        if not items:
            return
        self.queue.set_items(items, index)
        self._play_queue_current()

    def _play_local_list(self, songs, index):
        """本地列表播放"""
        items = [QueueItem(title=s.title, artist=s.artist,
                           song_id=None, file_path=s.path)
                 for s in songs]
        if not items:
            return
        self.queue.set_items(items, index)
        self._play_queue_current()

    def _play_queue_current(self):
        """播放队列当前项"""
        item = self.queue.current()
        if item is None:
            return
        self._play_item(item)

    def _play_item(self, item: QueueItem):
        """播放单个队列项（本地或在线）"""
        self.player_bar.set_song(item.title, item.artist)
        info = {"title": item.title, "artist": item.artist}
        if item.song_id:
            info["song_id"] = item.song_id

        if item.file_path:
            # 本地文件直接播
            info["path"] = item.file_path
            self._current_song_info = info
            self.audio.play_file(item.file_path, info=info)
            # 歌词优先用 item.lyrics，其次找同名 .lrc
            if item.lyrics:
                lyr = parse_lrc(item.lyrics)
                self.lyrics_window.set_lyrics(lyr)
            else:
                from pathlib import Path
                p = Path(item.file_path)
                lrc_path = p.with_suffix(".lrc")
                if lrc_path.exists():
                    lyr = load_lrc_file(str(lrc_path))
                    self.lyrics_window.set_lyrics(lyr)
                else:
                    self.lyrics_window.clear()
        else:
            # 在线歌曲
            if not item.song_id:
                # 需要先搜 song_id
                self._play_by_name_in_queue(item)
                return
            self._current_song_info = info

            def fetch():
                data = resolve_song(item.song_id, item.title, item.artist)
                data["song_id"] = item.song_id
                return data

            run_async(fetch, on_done=self._on_song_resolved,
                      on_error=self._on_play_error)

    def _play_by_name_in_queue(self, item: QueueItem):
        """队列项没有 song_id 时先搜索"""
        def fetch():
            from core.gequbao_api import search as gsearch
            results = gsearch(f"{item.title} {item.artist}".strip(), limit=20) or \
                      gsearch(item.title, limit=20)
            target = None
            for r in results:
                if r.title.strip() == item.title.strip() and r.artist.strip() == item.artist.strip():
                    target = r
                    break
            if target is None:
                for r in results:
                    if r.title.strip() == item.title.strip():
                        target = r
                        break
            if target is None and results:
                target = results[0]
            if target is None:
                raise RuntimeError("未找到匹配歌曲")
            item.song_id = target.song_id
            data = resolve_song(target.song_id, target.title or item.title,
                                 target.artist or item.artist)
            data["song_id"] = target.song_id
            return data

        run_async(fetch, on_done=self._on_song_resolved,
                  on_error=self._on_play_error)

    def _on_song_resolved(self, data: dict):
        info = self._current_song_info
        if data.get("song_id"):
            info["song_id"] = data["song_id"]

        file_path = data.get("file")
        url = data.get("url")
        lyrics_text = data.get("lyrics")

        if file_path:
            self.audio.play_file(file_path, info=info)
        elif url:
            self.audio.play_url(url, info=info)
        else:
            self._on_play_error("无法获取播放地址")
            return

        if lyrics_text:
            lyr = parse_lrc(lyrics_text)
            self.lyrics_window.set_lyrics(lyr)
        else:
            self.lyrics_window.clear()

        QTimer.singleShot(500, self.settings_panel.refresh_cache_size)

    # ---------- 上一首/下一首 ----------
    def _on_prev(self):
        if not self.queue.items:
            return
        item = self.queue.prev()
        if item:
            self._play_item(item)

    def _on_next(self):
        if not self.queue.items:
            return
        item = self.queue.next()
        if item:
            self._play_item(item)

    def _on_mode_change(self):
        new_mode = self.queue.next_mode()
        self.player_bar.set_mode(new_mode)
        cfg = load_config()
        cfg["playback_mode"] = new_mode
        save_config(cfg)
        self.statusBar().showMessage(f"播放模式：{MODE_NAMES[new_mode]}", 2500)

    # ---------- 播放完成 ----------
    def _on_audio_finished(self):
        """播放完成后按模式自动下一首"""
        if not self.queue.items:
            return

        if self.queue.mode == PlaybackMode.LOOP_ONE:
            # 单曲循环：重播当前
            item = self.queue.current()
            if item:
                self._play_item(item)
            return

        item = self.queue.next()
        if item is None:
            # 顺序播放到末尾
            self.player_bar.set_playing_ui(False)
            self.statusBar().showMessage("顺序播放结束", 3000)
            return
        self._play_item(item)

    # ---------- 音频状态 ----------
    def _on_audio_state(self, state):
        pass

    def _on_audio_position(self, cur, total):
        self.lyrics_window.set_time(cur)

    def _on_audio_error(self, err):
        self.statusBar().showMessage(err, 8000)

    def _on_audio_status_message(self, msg: str):
        if msg:
            self.statusBar().showMessage(msg, 0)
        else:
            self.statusBar().clearMessage()

    def _on_play_error(self, err: str):
        self.statusBar().showMessage(f"播放失败：{err}", 8000)

    # ---------- 歌词窗口 ----------
    def _on_toggle_lyrics(self, checked: bool):
        self._lyrics_visible = checked
        self.lyrics_window.set_enabled(checked)
        cfg = load_config()
        cfg["lyrics_visible"] = checked
        save_config(cfg)

    def _on_toggle_lyric_lock(self, locked: bool):
        self._lyrics_locked = locked
        self.lyrics_window.set_locked(locked)
        cfg = load_config()
        cfg["lyrics_locked"] = locked
        save_config(cfg)
        if locked:
            self.statusBar().showMessage("歌词已锁定：鼠标穿透", 2500)
        else:
            self.statusBar().showMessage("歌词可拖动：直接拖动；滚轮调字号", 3000)

    # ---------- 下载 ----------
    def _download_search_song(self, song: Song):
        self.download_panel.add_tasks([(song.title, song.artist, song.song_id)])
        self.tabs.setCurrentWidget(self.download_panel)

    def _download_playlist_song(self, title: str, artist: str):
        self.download_panel.add_tasks([(title, artist)])
        self.tabs.setCurrentWidget(self.download_panel)

    def _add_download_tasks(self, tasks, playlist_name=""):
        self.download_panel.add_tasks(tasks, playlist_name=playlist_name)
        self.tabs.setCurrentWidget(self.download_panel)

    # ---------- 目录 & 缓存 ----------
    def _on_dir_changed(self, d: str):
        self.local_panel._dir = d
        self.local_panel.lbl_dir.setText(f"目录：{d}")
        self.local_panel.refresh()
        try:
            self.download_panel._dir = d
            self.download_panel.lbl_dir.setText(f"下载目录：{d}")
            self.download_panel.downloader.set_download_dir(d)
        except Exception:
            pass
        try:
            self.settings_panel.on_dir_changed(d)
        except Exception:
            pass

    def _on_cache_cleared(self):
        self.statusBar().showMessage("缓存已清空", 3000)

    def _on_cache_dir_changed(self, d: str):
        self.statusBar().showMessage(f"缓存目录已更改：{d}", 4000)

    # ---------- 窗口 ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._save_timer.start(500)

    def _save_window_size(self):
        cfg = load_config()
        cfg["win_w"] = self.width()
        cfg["win_h"] = self.height()
        save_config(cfg)

    def closeEvent(self, event):
        try:
            self.audio.stop()
        except Exception:
            pass
        try:
            self.lyrics_window.close()
        except Exception:
            pass
        super().closeEvent(event)
