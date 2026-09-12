"""本地音乐库扫描 + .m3u 歌单读取"""
from pathlib import Path
from typing import List, Optional


class LocalSong:
    __slots__ = ("title", "artist", "path", "lrc_path")

    def __init__(self, path: str, lrc_path: str = None,
                 title: str = None, artist: str = None):
        self.path = path
        self.lrc_path = lrc_path
        if title is None:
            stem = Path(path).stem
            if " - " in stem:
                a, b = stem.split(" - ", 1)
                self.title = b.strip()
                self.artist = a.strip()
            else:
                self.title = stem
                self.artist = ""
        else:
            self.title = title
            self.artist = artist or ""

    @property
    def display(self) -> str:
        return f"{self.title} - {self.artist}" if self.artist else self.title

    def __repr__(self):
        return f"<LocalSong {self.display}>"


class LocalPlaylist:
    def __init__(self, name: str, m3u_path: str, songs: List[LocalSong]):
        self.name = name
        self.m3u_path = m3u_path
        self.songs = songs

    @property
    def count(self) -> int:
        return len(self.songs)

    def __repr__(self):
        return f"<LocalPlaylist {self.name} ({len(self.songs)})>"


def scan_directory(path: str) -> List[LocalSong]:
    """扫描目录下所有 mp3"""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return []
    songs: List[LocalSong] = []
    for f in p.rglob("*.mp3"):
        lrc = f.with_suffix(".lrc")
        songs.append(LocalSong(
            path=str(f),
            lrc_path=str(lrc) if lrc.exists() else None,
        ))
    songs.sort(key=lambda s: s.title.lower())
    return songs


def scan_playlists(path: str) -> List[LocalPlaylist]:
    """扫描目录下的所有 .m3u 歌单"""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return []
    playlists: List[LocalPlaylist] = []
    for f in p.glob("*.m3u"):
        pl = load_m3u(str(f))
        if pl is not None and pl.songs:
            playlists.append(pl)
    playlists.sort(key=lambda x: x.name.lower())
    return playlists


def load_m3u(m3u_path: str) -> Optional[LocalPlaylist]:
    """读取 .m3u 文件"""
    lines = None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            with open(m3u_path, "r", encoding=enc) as f:
                lines = f.readlines()
            break
        except Exception:
            continue
    if lines is None:
        return None

    base_dir = Path(m3u_path).parent
    name = Path(m3u_path).stem
    songs: List[LocalSong] = []
    pending_title = None
    pending_artist = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#PLAYLIST:"):
            name = line[len("#PLAYLIST:"):].strip()
            continue
        if line.startswith("#EXTINF:"):
            try:
                meta = line.split(",", 1)[1].strip()
                if " - " in meta:
                    a, b = meta.split(" - ", 1)
                    pending_artist = a.strip()
                    pending_title = b.strip()
                else:
                    pending_title = meta
                    pending_artist = ""
            except Exception:
                pass
            continue
        if line.startswith("#"):
            continue

        full = Path(line)
        if not full.is_absolute():
            full = (base_dir / line).resolve()
        if not full.exists():
            continue
        lrc = full.with_suffix(".lrc")
        songs.append(LocalSong(
            path=str(full),
            lrc_path=str(lrc) if lrc.exists() else None,
            title=pending_title,
            artist=pending_artist,
        ))
        pending_title = None
        pending_artist = None

    return LocalPlaylist(name=name, m3u_path=m3u_path, songs=songs)


def save_m3u(m3u_path: str, name: str, songs: List[LocalSong]):
    """保存 .m3u 文件"""
    try:
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:{name}\n")
            for s in songs:
                f.write(f"#EXTINF:-1,{s.artist} - {s.title}\n")
                f.write(Path(s.path).name + "\n")
        return True
    except Exception as e:
        print(f"[local_library] save_m3u error: {e}", flush=True)
        return False
