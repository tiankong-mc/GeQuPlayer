"""各大音乐网站歌单解析（酷狗 / QQ音乐）"""
import json
import re
import html as html_lib
from typing import List, Optional, Tuple

from utils.http_client import get


# ---------- 数据结构 ----------
class PlaylistItem:
    __slots__ = ("name", "playlist_id", "cover", "platform", "song_count")

    def __init__(self, name, playlist_id, cover="", platform="", song_count=0):
        self.name = name
        self.playlist_id = str(playlist_id)
        self.cover = cover
        self.platform = platform
        self.song_count = song_count

    def __repr__(self):
        return f"<Playlist {self.platform} {self.name} ({self.song_count})>"


class PlaylistSong:
    __slots__ = ("title", "artist")

    def __init__(self, title: str, artist: str):
        self.title = title
        self.artist = artist

    def __repr__(self):
        return f"<PListSong {self.title} - {self.artist}>"


# ---------- 分享链接解析 ----------
def parse_playlist_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    url = (url or "").strip()
    if not url:
        return None, None

    m = re.search(r"kugou\.com/songlist/(gcid_[a-z0-9]+)", url, re.I)
    if m:
        return "kugou_gcid", m.group(1)

    m = re.search(r"kugou\.com/yy/special/single/(\d+)", url, re.I)
    if m:
        return "kugou", m.group(1)
    m = re.search(r"kugou\.com/[^\s?]*\?[^\s]*?\blistid=(\d+)", url, re.I)
    if m:
        return "kugou", m.group(1)
    m = re.search(r"kugou\.com/[^\s?]*\?[^\s]*?\b(?:specialid|special|id)=(\d+)", url, re.I)
    if m:
        return "kugou", m.group(1)

    m = re.search(r"y\.qq\.com/[^\s]*?/playlist/(\d+)", url, re.I)
    if m:
        return "qq", m.group(1)
    m = re.search(r"y\.qq\.com/[^\s?]*\?[^\s]*?\bid=(\d+)", url, re.I)
    if m:
        return "qq", m.group(1)
    m = re.search(r"y\.qq\.com/[^\s]*?/play(?:square|list)/(\d+)", url, re.I)
    if m:
        return "qq", m.group(1)

    if re.fullmatch(r"\d+", url):
        return "kugou_code", url

    return None, None


# ---------- 酷狗常量 ----------
KUGOU_RANK_LIST = "http://mobilecdn.kugou.com/api/v3/rank/list"
KUGOU_RANK_SONG = "http://mobilecdn.kugou.com/api/v3/rank/song"
KUGOU_SPECIAL_SONG = "http://mobilecdn.kugou.com/api/v3/special/song"
KUGOU_SEARCH_SONG = "http://mobilecdn.kugou.com/api/v3/search/song"

KUGOU_SEARCH_SPECIAL_ENDPOINTS = [
    "http://msearchcdn.kugou.com/api/v3/search/special",
    "http://mobilecdn.kugou.com/api/v3/search/special",
    "http://searchcdn.kugou.com/api/v3/search/special",
]


# ---------- 酷狗 热门榜单 ----------
def kugou_hot_playlists(limit: int = 30) -> List[PlaylistItem]:
    try:
        r = get(KUGOU_RANK_LIST, params={"json": "true", "page": 1, "pagesize": limit},
                referer="https://www.kugou.com/")
        data = r.json()
        items = data.get("data", {}).get("info", []) or []
        result = []
        for it in items:
            result.append(PlaylistItem(
                name=it.get("rankname", "").strip(),
                playlist_id=it.get("rankid", ""),
                cover=it.get("imgurl", "").replace("{size}", "400"),
                platform="kugou",
                song_count=it.get("songcount", 0),
            ))
        return result
    except Exception as e:
        print(f"[kugou] hot playlists error: {e}")
        return []


def kugou_playlist_songs(rank_id: str, limit: int = 500) -> List[PlaylistSong]:
    songs = _kugou_fetch(KUGOU_SPECIAL_SONG, {"specialid": rank_id}, limit)
    if songs:
        return songs
    return _kugou_fetch(KUGOU_RANK_SONG, {"rankid": rank_id}, limit)


def _kugou_fetch(api: str, id_param: dict, limit: int) -> List[PlaylistSong]:
    try:
        params = {**id_param, "page": 1, "pagesize": limit, "json": "true"}
        r = get(api, params=params, referer="https://www.kugou.com/")
        data = r.json()
        items = data.get("data", {}).get("info", []) or []
        songs = []
        for it in items:
            filename = it.get("filename", "")
            if " - " in filename:
                a, b = filename.split(" - ", 1)
                songs.append(PlaylistSong(title=b.strip(), artist=a.strip()))
            else:
                songs.append(PlaylistSong(
                    title=filename.strip(),
                    artist=it.get("singername", "").strip(),
                ))
        return songs
    except Exception as e:
        print(f"[kugou] fetch {api} error: {e}")
        return []


# ---------- 酷狗 歌单搜索 ----------
def search_kugou_playlists(keyword: str, limit: int = 30) -> List[PlaylistItem]:
    for api in KUGOU_SEARCH_SPECIAL_ENDPOINTS:
        try:
            params = {
                "keyword": keyword,
                "page": 1,
                "pagesize": limit,
                "showtype": 1,
                "format": "json",
            }
            r = get(api, params=params, referer="https://www.kugou.com/")
            data = r.json()
            items = data.get("data", {}).get("info", []) or []
            if not items:
                continue

            result = []
            for it in items:
                specialid = (it.get("specialid") or it.get("special_id")
                             or it.get("gid") or it.get("id"))
                name = (it.get("specialname") or it.get("name")
                        or it.get("songlistname") or "").strip()
                song_count = (it.get("songcount") or it.get("song_count")
                              or it.get("total") or 0)
                imgurl = (it.get("imgurl") or it.get("img_url")
                          or it.get("cover") or "")
                if specialid and name:
                    result.append(PlaylistItem(
                        name=name,
                        playlist_id=str(specialid),
                        cover=imgurl,
                        platform="kugou",
                        song_count=song_count,
                    ))
            if result:
                print(f"[kugou] 歌单搜索 '{keyword}' → {len(result)} 个结果（via {api}）",
                      flush=True)
                return result
        except Exception as e:
            print(f"[kugou] search playlists {api} 失败: {e}", flush=True)
    return []


# ---------- 酷狗 gcid ----------
def kugou_gcid_songs(gcid: str, limit: int = 500) -> List[PlaylistSong]:
    songs = []
    try:
        url = f"https://m.kugou.com/songlist/{gcid}/"
        r = get(
            url,
            referer="https://m.kugou.com/",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                                   "Mobile/15E148 Safari/604.1"},
        )
        text = r.text
        for pattern in [
            r'window\.\$output\s*=\s*(\{.*?\})\s*;',
            r'var\s+nData\s*=\s*(\{.*?\})\s*;',
        ]:
            m = re.search(pattern, text, re.S)
            if not m:
                continue
            try:
                data = json.loads(m.group(1))
                for path in ["info.list", "list", "songs", "data.list"]:
                    nodes = data
                    for key in path.split("."):
                        if isinstance(nodes, dict):
                            nodes = nodes.get(key)
                        else:
                            nodes = None
                            break
                    if isinstance(nodes, list) and nodes:
                        for it in nodes[:limit]:
                            name = it.get("name") or it.get("songname") or ""
                            singer = it.get("singer") or it.get("singername") or ""
                            if name:
                                songs.append(PlaylistSong(
                                    title=str(name).strip(),
                                    artist=str(singer).strip(),
                                ))
                        if songs:
                            return songs[:limit]
            except Exception:
                continue

        for m in re.finditer(r'title="([^"]+)"[^>]*class="[^"]*song[^"]*"', text, re.I):
            raw = html_lib.unescape(m.group(1))
            if " - " in raw:
                a, b = raw.split(" - ", 1)
                songs.append(PlaylistSong(title=b.strip(), artist=a.strip()))
            if len(songs) >= limit:
                break
    except Exception as e:
        print(f"[kugou] gcid parse error: {e}", flush=True)
    return songs[:limit]


# ---------- 酷狗 酷狗码 ----------
def kugou_code_songs(code: str, limit: int = 500) -> List[PlaylistSong]:
    try:
        r = get(
            KUGOU_SEARCH_SONG,
            params={"format": "json", "keyword": code, "page": 1,
                    "pagesize": 10, "showtype": 1},
            referer="https://www.kugou.com/",
        )
        data = r.json()
        items = data.get("data", {}).get("info", []) or []
        if not items:
            return []
        specialid = None
        for it in items:
            specialid = it.get("specialid") or it.get("album_id")
            if specialid:
                break
        if not specialid:
            return []
        return _kugou_fetch(KUGOU_SPECIAL_SONG, {"specialid": specialid}, limit)
    except Exception as e:
        print(f"[kugou] code parse error: {e}")
        return []


# ---------- QQ音乐 ----------
QQ_RECOMMEND = "https://c.y.qq.com/splcloud/fcgi-bin/fcg_get_diss_by_tag.fcg"
QQ_PLAYLIST_DETAIL = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
QQ_SEARCH_PLAYLIST = "https://c.y.qq.com/soso/fcgi-bin/client_music_search_songlist"


def qq_hot_playlists(limit: int = 30) -> List[PlaylistItem]:
    try:
        params = {
            "picmid": 1, "rnd": 0.123456, "g_tk": 5381,
            "loginUin": 0, "hostUin": 0, "format": "json",
            "inCharset": "utf8", "outCharset": "utf-8",
            "notice": 0, "platform": "yqq.json", "needNewCode": 0,
            "categoryId": 10000000, "sortId": 5, "sin": 0, "ein": limit - 1,
        }
        r = get(QQ_RECOMMEND, params=params, referer="https://y.qq.com/")
        data = r.json()
        items = data.get("data", {}).get("list", []) or []
        result = []
        for it in items:
            result.append(PlaylistItem(
                name=it.get("dissname", "").strip(),
                playlist_id=it.get("dissid", ""),
                cover=it.get("imgurl", ""),
                platform="qq",
                song_count=it.get("song_count", 0),
            ))
        return result
    except Exception as e:
        print(f"[qq] hot playlists error: {e}")
        return []


def qq_playlist_songs(disstid: str, limit: int = 500) -> List[PlaylistSong]:
    try:
        params = {
            "type": 1, "json": 1, "utf8": 1, "onlysong": 0,
            "disstid": disstid, "format": "json", "g_tk": 5381,
            "loginUin": 0, "hostUin": 0, "inCharset": "utf8",
            "outCharset": "utf-8", "notice": 0,
            "platform": "yqq.json", "needNewCode": 0,
        }
        r = get(QQ_PLAYLIST_DETAIL, params=params,
                referer=f"https://y.qq.com/n/yqq/playlist/{disstid}.html")
        data = r.json()
        cdlist = data.get("cdlist", []) or []
        songs = []
        if cdlist:
            for it in cdlist[0].get("songlist", [])[:limit]:
                singers = "、".join(
                    s.get("name", "") for s in it.get("singer", []) if s.get("name")
                )
                songs.append(PlaylistSong(
                    title=it.get("name", "").strip(),
                    artist=singers.strip(),
                ))
        return songs
    except Exception as e:
        print(f"[qq] playlist songs error: {e}")
        return []


def search_qq_playlists(keyword: str, limit: int = 30) -> List[PlaylistItem]:
    try:
        params = {
            "query": keyword,
            "num": limit,
            "page": 0,
            "flag": 1,
            "remoteplace": "txt.yqq.playlist",
            "format": "json",
        }
        r = get(QQ_SEARCH_PLAYLIST, params=params, referer="https://y.qq.com/")
        data = r.json()
        items = data.get("data", {}).get("list", []) or []
        result = []
        for it in items:
            disstid = it.get("dissid") or it.get("diss_id")
            name = it.get("dissname") or it.get("diss_name") or ""
            song_count = it.get("song_count") or it.get("songnum") or 0
            imgurl = it.get("imgurl") or it.get("cover") or ""
            if disstid and name:
                result.append(PlaylistItem(
                    name=name.strip(),
                    playlist_id=str(disstid),
                    cover=imgurl,
                    platform="qq",
                    song_count=song_count,
                ))
        if result:
            print(f"[qq] 歌单搜索 '{keyword}' → {len(result)} 个结果", flush=True)
        return result
    except Exception as e:
        print(f"[qq] search playlists error: {e}", flush=True)
        return []


# ---------- 统一入口 ----------
def get_hot_playlists(platform: str, limit: int = 30) -> List[PlaylistItem]:
    platform = platform.lower()
    if platform == "kugou":
        return kugou_hot_playlists(limit)
    if platform == "qq":
        return qq_hot_playlists(limit)
    return []


def search_playlists(platform: str, keyword: str, limit: int = 30) -> List[PlaylistItem]:
    platform = platform.lower()
    if platform == "kugou":
        return search_kugou_playlists(keyword, limit)
    if platform == "qq":
        return search_qq_playlists(keyword, limit)
    return []


def get_playlist_songs(platform: str, playlist_id: str) -> List[PlaylistSong]:
    platform = platform.lower()
    if platform == "kugou":
        return kugou_playlist_songs(playlist_id)
    if platform == "kugou_gcid":
        return kugou_gcid_songs(playlist_id)
    if platform == "kugou_code":
        return kugou_code_songs(playlist_id)
    if platform == "qq":
        return qq_playlist_songs(playlist_id)
    return []


def get_playlist_by_url(url: str) -> List[PlaylistSong]:
    platform, playlist_id = parse_playlist_url(url)
    if not platform or not playlist_id:
        return []
    return get_playlist_songs(platform, playlist_id)
