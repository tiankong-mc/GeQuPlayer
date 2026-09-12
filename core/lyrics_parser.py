"""LRC 歌词解析（行级 + 逐字）"""
import re
from typing import List, Tuple

# 普通 LRC 时间标签：[00:12.34] 或 [00:12.340] 或 [00:12]
_LINE_TAG = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")
# 逐字标签：<00:12.34>
_WORD_TAG = re.compile(r"<(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?>")


def _to_seconds(mm: str, ss: str, frac: str = "") -> float:
    t = int(mm) * 60 + int(ss)
    if frac:
        if len(frac) == 1:
            t += int(frac) / 10.0
        elif len(frac) == 2:
            t += int(frac) / 100.0
        else:
            t += int(frac) / 1000.0
    return t


class LyricLine:
    __slots__ = ("time", "text", "words")

    def __init__(self, time: float, text: str, words=None):
        self.time = time
        self.text = text
        # words: List[(abs_time, text_chunk)]  用于逐字染色
        self.words: List[Tuple[float, str]] = words or []

    def __repr__(self):
        return f"<Line {self.time:.2f} {self.text!r}>"


class Lyrics:
    def __init__(self):
        self.lines: List[LyricLine] = []
        self.offset: float = 0.0
        self.title: str = ""
        self.artist: str = ""

    def is_empty(self) -> bool:
        return not self.lines

    def index_at(self, t: float) -> int:
        """返回时间 t 对应的歌词行索引；未到第一行返回 -1"""
        if not self.lines:
            return -1
        lo, hi, res = 0, len(self.lines) - 1, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.lines[mid].time <= t:
                res = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return res


def parse_lrc(text: str) -> Lyrics:
    lyrics = Lyrics()
    if not text:
        return lyrics

    offset = 0.0
    # 解析元信息
    for raw in text.splitlines():
        m = re.match(r"\[offset:([+-]?\d+)\]", raw.strip(), re.I)
        if m:
            offset = int(m.group(1)) / 1000.0
        m = re.match(r"\[ti:(.*?)\]", raw.strip(), re.I)
        if m:
            lyrics.title = m.group(1).strip()
        m = re.match(r"\[ar:(.*?)\]", raw.strip(), re.I)
        if m:
            lyrics.artist = m.group(1).strip()

    entries = []  # (time, text, words)

    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("["):
            # 跳过 offset / ti / ar / al / by 等元信息行
            if not re.match(r"^\[\d", raw):
                if not _LINE_TAG.search(raw):
                    continue

        line_tags = list(_LINE_TAG.finditer(raw))
        if not line_tags:
            continue

        body = raw[line_tags[-1].end():]

        # 解析逐字
        words: List[Tuple[float, str]] = []
        if _WORD_TAG.search(body):
            cursor = 0
            cur_time = None
            for wm in _WORD_TAG.finditer(body):
                chunk = body[cursor:wm.start()]
                if cur_time is not None and chunk:
                    words.append((cur_time, chunk))
                t = _to_seconds(wm.group(1), wm.group(2), wm.group(3) or "")
                cur_time = t
                cursor = wm.end()
            tail = body[cursor:]
            if cur_time is not None and tail:
                words.append((cur_time, tail))
            plain = "".join(w[1] for w in words)
        else:
            plain = _WORD_TAG.sub("", body).strip()

        for tag in line_tags:
            t = _to_seconds(tag.group(1), tag.group(2), tag.group(3) or "")
            entries.append((t, plain, list(words)))

    entries.sort(key=lambda x: x[0])
    lyrics.offset = offset
    for t, plain, words in entries:
        adj_t = t + offset
        adj_words = [(wt + offset, txt) for wt, txt in words]
        lyrics.lines.append(LyricLine(adj_t, plain, adj_words))
    return lyrics


def load_lrc_file(path: str) -> Lyrics:
    """从本地文件加载 .lrc 歌词"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return parse_lrc(f.read())
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        except Exception:
            break
    return Lyrics()
