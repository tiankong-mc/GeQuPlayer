"""播放队列 + 播放模式"""
from enum import Enum
from typing import List, Optional


class PlaybackMode:
    LOOP_LIST = "loop_list"   # 列表循环
    LOOP_ONE = "loop_one"     # 单曲循环
    SEQUENCE = "sequence"     # 顺序播放（末尾停止）
    SHUFFLE = "shuffle"       # 随机播放


MODE_NAMES = {
    PlaybackMode.LOOP_LIST: "列表循环",
    PlaybackMode.LOOP_ONE: "单曲循环",
    PlaybackMode.SEQUENCE: "顺序播放",
    PlaybackMode.SHUFFLE: "随机播放",
}

MODE_ICONS = {
    PlaybackMode.LOOP_LIST: "🔁",
    PlaybackMode.LOOP_ONE: "🔂",
    PlaybackMode.SEQUENCE: "➡",
    PlaybackMode.SHUFFLE: "🔀",
}

MODE_ORDER = [
    PlaybackMode.LOOP_LIST,
    PlaybackMode.LOOP_ONE,
    PlaybackMode.SEQUENCE,
    PlaybackMode.SHUFFLE,
]


class QueueItem:
    __slots__ = ("title", "artist", "song_id", "file_path", "lyrics")

    def __init__(self, title, artist="", song_id=None, file_path=None, lyrics=None):
        self.title = title
        self.artist = artist
        self.song_id = song_id
        self.file_path = file_path
        self.lyrics = lyrics

    @property
    def display(self):
        return f"{self.title} - {self.artist}" if self.artist else self.title


class PlaybackQueue:
    def __init__(self):
        self.items: List[QueueItem] = []
        self.current_index = -1
        self.mode = PlaybackMode.LOOP_LIST
        self._shuffle_pool: List[int] = []

    def clear(self):
        self.items = []
        self.current_index = -1
        self._shuffle_pool = []

    def set_items(self, items: List[QueueItem], start_index: int = 0):
        self.items = list(items)
        if not self.items:
            self.current_index = -1
            return
        start_index = max(0, min(start_index, len(self.items) - 1))
        self.current_index = start_index
        self._rebuild_shuffle()

    def append(self, item: QueueItem):
        self.items.append(item)
        self._rebuild_shuffle()

    def current(self) -> Optional[QueueItem]:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def set_mode(self, mode: str):
        self.mode = mode
        self._rebuild_shuffle()

    def next_mode(self) -> str:
        try:
            i = MODE_ORDER.index(self.mode)
        except ValueError:
            i = 0
        self.mode = MODE_ORDER[(i + 1) % len(MODE_ORDER)]
        self._rebuild_shuffle()
        return self.mode

    def _rebuild_shuffle(self):
        import random
        n = len(self.items)
        self._shuffle_pool = list(range(n))
        if 0 <= self.current_index < n:
            try:
                self._shuffle_pool.remove(self.current_index)
            except ValueError:
                pass
        random.shuffle(self._shuffle_pool)

    def next(self) -> Optional[QueueItem]:
        """返回下一首；顺序播放到末尾返回 None"""
        n = len(self.items)
        if n == 0:
            return None

        # 单曲循环：不动索引
        if self.mode == PlaybackMode.LOOP_ONE:
            if self.current_index < 0:
                self.current_index = 0
            return self.current()

        # 随机
        if self.mode == PlaybackMode.SHUFFLE:
            if not self._shuffle_pool:
                self._rebuild_shuffle()
                if not self._shuffle_pool:
                    return self.items[0] if self.items else None
            next_idx = self._shuffle_pool.pop(0)
            self.current_index = next_idx
            return self.current()

        # 顺序 / 列表循环
        next_idx = self.current_index + 1
        if next_idx >= n:
            if self.mode == PlaybackMode.LOOP_LIST:
                next_idx = 0
            else:
                return None
        self.current_index = next_idx
        return self.current()

    def prev(self) -> Optional[QueueItem]:
        n = len(self.items)
        if n == 0:
            return None

        if self.mode == PlaybackMode.LOOP_ONE:
            if self.current_index < 0:
                self.current_index = 0
            return self.current()

        if self.mode == PlaybackMode.SHUFFLE:
            next_idx = (self.current_index - 1 + n) % n
            self.current_index = next_idx
            return self.current()

        next_idx = self.current_index - 1
        if next_idx < 0:
            if self.mode == PlaybackMode.LOOP_LIST:
                next_idx = n - 1
            else:
                next_idx = 0
        self.current_index = next_idx
        return self.current()
