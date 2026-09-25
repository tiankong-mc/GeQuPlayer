"""各大音乐网站歌单解析（酷狗 / QQ音乐 / 网易云）

关键：
- 酷狗部分域名只有 HTTP（无有效证书），HTTP / HTTPS 混着放候选列表
- QQ 音乐优先用 u.y.qq.com 新接口，老接口兜底
- 网易云使用官方 API，分批拉取全量歌曲（每批 3 次重试）
- 所有解析都做类型防御，避免 'str' object has no attribute 'get'
"""
import json
import re
import time
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

    m = re.search(r"music\.163\.com/[^\s]*?[?&#]id=(\d+)", url, re.I)
    if m:
        return "netease", m.group(1)

    if re.fullmatch(r"\d+", url):
        return "kugou_code", url

    return None, None


# ============================================================
#  酷狗
# ============================================================
KUGOU_RANK_LIST_CANDIDATES = [
    "https://mobiles.kugou.com/api/v3/rank/list",
    "http://mobilecdn.kugou.com/api/v3/rank/list",
]

KUGOU_SEARCH_SPECIAL_CANDIDATES = [
    "http://msearchcdn.kugou.com/api/v3/search/special",
    "http://mobilecdn.kugou.com/api/v3/search/special",
    "https://mobiles.kugou.com/api/v3/search/special",
]

KUGOU_SPECIAL_SONG_CANDIDATES = [
    "http://mobilecdn.kugou.com/api/v3/special/song",
    "https://mobiles.kugou.com/api/v3/special/song",
]

KUGOU_RANK_SONG_CANDIDATES = [
    "http://mobilecdn.kugou.com/api/v3/rank/song",
    "https://mobiles.kugou.com/api/v3/rank/song",
]

KUGOU_SEARCH_SONG_URL = "http://mobilecdn.kugou.com/api/v3/search/song"


def _try_json(url: str, params: dict, referer: str = "https://www.kugou.com/",
              timeout: int = 12) -> Optional[dict]:
    try:
        r = get(url, params=params, referer=referer, timeout=timeout)
        if r.status_code != 200:
            print(f"[kugou] {url} -> HTTP {r.status_code}", flush=True)
            return None
        try:
            return r.json()
        except Exception:
            print(f"[kugou] {url} 非 JSON: {r.text[:80]!r}", flush=True)
            return None
    except Exception as e:
        print(f"[kugou] {url} 异常: {str(e)[:80]}", flush=True)
        return None


def kugou_hot_playlists(limit: int = 30) -> List[PlaylistItem]:
    params = {"json": "true", "page": 1, "pagesize": limit}
    for api in KUGOU_RANK_LIST_CANDIDATES:
        data = _try_json(api, params)
        if not data:
            continue
        items = (data.get("data", {}).get("info", [])
                 or data.get("info", [])
                 or data.get("data", {}).get("list", []))
        if not items:
            continue
        result = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = (it.get("rankname") or it.get("name") or "").strip()
            rid = it.get("rankid") or it.get("id") or ""
            cover = (it.get("imgurl") or it.get("img_url") or "").replace("{size}", "400")
            count = it.get("songcount") or it.get("song_count") or 0
            if name and rid:
                result.append(PlaylistItem(
                    name=name, playlist_id=str(rid), cover=cover,
                    platform="kugou", song_count=count,
                ))
        if result:
            print(f"[kugou] 热榜 {len(result)} 个（via {api}）", flush=True)
            return result
    print("[kugou] 所有热榜接口均失败", flush=True)
    return []


def search_kugou_playlists(keyword: str, limit: int = 30) -> List[PlaylistItem]:
    params = {"keyword": keyword, "page": 1, "pagesize": limit,
              "showtype": 1, "format": "json"}
    for api in KUGOU_SEARCH_SPECIAL_CANDIDATES:
        data = _try_json(api, params)
        if not data:
            continue
        items = (data.get("data", {}).get("info", [])
                 or data.get("data", {}).get("list", [])
                 or data.get("info", []))
        if not items:
            continue
        result = []
        for it in items:
            if not isinstance(it, dict):
                continue
            specialid = (it.get("specialid") or it.get("special_id")
                         or it.get("gid") or it.get("id"))
            name = (it.get("specialname") or it.get("name")
                    or it.get("songlistname") or it.get("title") or "").strip()
            if not name:
                name = re.sub(r"<[^>]+>", "", it.get("specialname", "")).strip()
            song_count = (it.get("songcount") or it.get("song_count")
                          or it.get("total") or it.get("songnum") or 0)
            cover = (it.get("imgurl") or it.get("img_url")
                     or it.get("cover") or it.get("pic") or "")
            if specialid and name:
                result.append(PlaylistItem(
                    name=name, playlist_id=str(specialid), cover=cover,
                    platform="kugou", song_count=song_count,
                ))
        if result:
            print(f"[kugou] 搜歌单 '{keyword}' → {len(result)} 个", flush=True)
            return result
    print(f"[kugou] 所有搜歌单接口均失败: {keyword}", flush=True)
    return []


def kugou_playlist_songs(rank_id: str, limit: int = 500) -> List[PlaylistSong]:
    songs = _kugou_fetch_multi(KUGOU_SPECIAL_SONG_CANDIDATES,
                               {"specialid": rank_id}, limit)
    if songs:
        return songs
    return _kugou_fetch_multi(KUGOU_RANK_SONG_CANDIDATES,
                              {"rankid": rank_id}, limit)


def _kugou_fetch_multi(apis: List[str], id_param: dict, limit: int) -> List[PlaylistSong]:
    for api in apis:
        params = {**id_param, "page": 1, "pagesize": limit, "json": "true"}
        data = _try_json(api, params)
        if not data:
            continue
        items = (data.get("data", {}).get("info", [])
                 or data.get("data", {}).get("list", []))
        if not items:
            continue
        songs = []
        for it in items:
            if not isinstance(it, dict):
                continue
            filename = (it.get("filename") or it.get("name")
                        or it.get("songname") or "")
            if not filename:
                continue
            if " - " in filename:
                a, b = filename.split(" - ", 1)
                songs.append(PlaylistSong(title=b.strip(), artist=a.strip()))
            else:
                singer = it.get("singername") or it.get("author") or ""
                songs.append(PlaylistSong(title=filename.strip(),
                                          artist=singer.strip()))
        if songs:
            print(f"[kugou] 歌单 {id_param} → {len(songs)} 首", flush=True)
            return songs
    return []


def kugou_gcid_songs(gcid: str, limit: int = 500) -> List[PlaylistSong]:
    songs = []
    try:
        r = get(f"https://m.kugou.com/songlist/{gcid}/",
                referer="https://m.kugou.com/",
                headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                                       "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                                       "Mobile/15E148 Safari/604.1"},
                timeout=20)
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
                            if not isinstance(it, dict):
                                continue
                            name = it.get("name") or it.get("songname") or ""
                            singer = it.get("singer") or it.get("singername") or ""
                            if name:
                                songs.append(PlaylistSong(
                                    title=str(name).strip(),
                                    artist=str(singer).strip()))
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
        print(f"[kugou] gcid 异常: {e}", flush=True)
    return songs[:limit]


def kugou_code_songs(code: str, limit: int = 500) -> List[PlaylistSong]:
    data = _try_json(KUGOU_SEARCH_SONG_URL,
                     {"format": "json", "keyword": code, "page": 1,
                      "pagesize": 10, "showtype": 1})
    if not data:
        return []
    items = data.get("data", {}).get("info", []) or []
    if not items:
        return []
    specialid = None
    for it in items:
        if not isinstance(it, dict):
            continue
        specialid = it.get("specialid") or it.get("album_id")
        if specialid:
            break
    if not specialid:
        return []
    return _kugou_fetch_multi(KUGOU_SPECIAL_SONG_CANDIDATES,
                              {"specialid": specialid}, limit)


# ============================================================
#  QQ 音乐
# ============================================================
QQ_U_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"
QQ_HOT_REFERER = "https://y.qq.com/n/ryqq/playlist"


def _qq_post(payload: dict) -> Optional[dict]:
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": QQ_HOT_REFERER,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        r = requests.post(QQ_U_URL, json=payload, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        print(f"[qq] u.y.qq.com 异常: {str(e)[:80]}", flush=True)
        return None


def qq_hot_playlists(limit: int = 30) -> List[PlaylistItem]:
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "playlist": {
            "method": "GetPlaylistByCategory",
            "module": "music.playlist.PlayListCategory",
            "param": {"categoryId": 10000000, "sortId": 5,
                      "sin": 0, "ein": limit - 1},
        },
    }
    data = _qq_post(payload)
    if not data:
        return _qq_hot_playlists_legacy(limit)

    items = []
    try:
        playlist_node = data.get("playlist")
        if isinstance(playlist_node, dict):
            inner = playlist_node.get("data")
            if isinstance(inner, dict):
                for k in ("v_playlist", "list"):
                    v = inner.get(k)
                    if isinstance(v, list):
                        items = v
                        break
    except Exception:
        items = []

    if not items:
        return _qq_hot_playlists_legacy(limit)

    result = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = (it.get("title") or it.get("dissname") or "").strip()
        pid = it.get("dissid") or it.get("content_id") or it.get("id")
        cover = it.get("cover") or it.get("imgurl") or ""
        count = it.get("song_cnt") or it.get("song_count") or 0
        if name and pid:
            result.append(PlaylistItem(
                name=name, playlist_id=str(pid), cover=cover,
                platform="qq", song_count=count,
            ))
    if result:
        print(f"[qq] 热榜 {len(result)} 个", flush=True)
    return result


def _qq_hot_playlists_legacy(limit: int = 30) -> List[PlaylistItem]:
    try:
        r = get("https://c.y.qq.com/splcloud/fcgi-bin/fcg_get_diss_by_tag.fcg",
                params={"picmid": 1, "rnd": 0.123456, "g_tk": 5381,
                        "loginUin": 0, "hostUin": 0, "format": "json",
                        "inCharset": "utf8", "outCharset": "utf-8",
                        "notice": 0, "platform": "yqq.json", "needNewCode": 0,
                        "categoryId": 10000000, "sortId": 5,
                        "sin": 0, "ein": limit - 1},
                referer="https://y.qq.com/", timeout=15)
        data = r.json()
        inner = data.get("data")
        if not isinstance(inner, dict):
            inner = {}
        items = inner.get("list")
        if not isinstance(items, list):
            items = []
        result = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = (it.get("dissname") or "").strip()
            pid = it.get("dissid", "")
            if name and pid:
                result.append(PlaylistItem(
                    name=name, playlist_id=str(pid),
                    cover=it.get("imgurl", ""), platform="qq",
                    song_count=it.get("song_count", 0),
                ))
        return result
    except Exception as e:
        print(f"[qq] legacy 热榜异常: {str(e)[:80]}", flush=True)
        return []


def qq_playlist_songs(disstid: str, limit: int = 500) -> List[PlaylistSong]:
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "req_0": {
            "module": "music.srfDissInfo.aiDissInfo",
            "method": "uniform_get_Dissinfo",
            "param": {
                "disstid": int(disstid) if str(disstid).isdigit() else disstid,
                "enc_host_uin": "", "tag": 1, "userinfo": 1,
                "song_begin": 0, "song_num": limit,
            },
        },
    }
    data = _qq_post(payload)
    if data:
        try:
            req0 = data.get("req_0")
            if not isinstance(req0, dict):
                req0 = {}
            inner = req0.get("data")
            if not isinstance(inner, dict):
                inner = {}
            songlist = inner.get("songlist")
            if not isinstance(songlist, list):
                songlist = []
            songs = []
            for it in songlist[:limit]:
                if not isinstance(it, dict):
                    continue
                name = (it.get("name") or it.get("songname") or "")
                if not isinstance(name, str):
                    name = str(name)
                name = name.strip()
                singers = it.get("singer") or []
                if isinstance(singers, list):
                    parts = []
                    for s in singers:
                        if isinstance(s, dict):
                            n = s.get("name", "")
                            if isinstance(n, str) and n:
                                parts.append(n)
                        elif isinstance(s, str):
                            parts.append(s)
                    artist = "、".join(parts)
                elif isinstance(singers, str):
                    artist = singers
                else:
                    artist = ""
                if name:
                    songs.append(PlaylistSong(title=name, artist=artist.strip()))
            if songs:
                print(f"[qq] 歌单 {disstid} → {len(songs)} 首", flush=True)
                return songs
        except Exception as e:
            print(f"[qq] 解析异常: {str(e)[:100]}", flush=True)

    return _qq_playlist_songs_legacy(disstid, limit)


def _qq_playlist_songs_legacy(disstid: str, limit: int = 500) -> List[PlaylistSong]:
    try:
        r = get("https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg",
                params={"type": 1, "json": 1, "utf8": 1, "onlysong": 0,
                        "disstid": disstid, "format": "json", "g_tk": 5381,
                        "loginUin": 0, "hostUin": 0, "inCharset": "utf8",
                        "outCharset": "utf-8", "notice": 0,
                        "platform": "yqq.json", "needNewCode": 0},
                referer=f"https://y.qq.com/n/yqq/playlist/{disstid}.html",
                timeout=15)
        data = r.json()
        cdlist = data.get("cdlist")
        if not isinstance(cdlist, list) or not cdlist:
            return []
        first = cdlist[0]
        if not isinstance(first, dict):
            return []
        songs = []
        for it in first.get("songlist", [])[:limit]:
            if not isinstance(it, dict):
                continue
            name = (it.get("name") or "").strip()
            singers_field = it.get("singer") or []
            if isinstance(singers_field, list):
                singers = "、".join(
                    s.get("name", "") for s in singers_field
                    if isinstance(s, dict) and s.get("name")
                )
            else:
                singers = ""
            if name:
                songs.append(PlaylistSong(title=name, artist=singers.strip()))
        return songs
    except Exception as e:
        print(f"[qq] legacy 异常: {str(e)[:80]}", flush=True)
        return []


def search_qq_playlists(keyword: str, limit: int = 30) -> List[PlaylistItem]:
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "req_0": {
            "module": "music.search.SearchCgiService",
            "method": "DoSearchForQQMusicDesktop",
            "param": {"query": keyword, "num_per_page": limit,
                      "page_num": 1, "search_type": 3},
        },
    }
    data = _qq_post(payload)
    if data:
        try:
            req0 = data.get("req_0")
            if not isinstance(req0, dict):
                req0 = {}
            inner = req0.get("data")
            if not isinstance(inner, dict):
                inner = {}
            body = inner.get("body")
            if not isinstance(body, dict):
                body = {}
            items = []
            for key in ("songlist", "list", "playlist"):
                v = body.get(key)
                if isinstance(v, list) and v:
                    items = v
                    break
            if not items:
                for key in ("songlist", "list", "playlist"):
                    v = inner.get(key)
                    if isinstance(v, list) and v:
                        items = v
                        break
            result = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = (it.get("dissname") or it.get("title") or "")
                if not isinstance(name, str):
                    name = str(name)
                name = name.strip()
                pid = it.get("dissid") or it.get("id") or it.get("content_id")
                if pid is None:
                    continue
                pid = str(pid)
                cover = it.get("imgurl") or it.get("cover") or ""
                if not isinstance(cover, str):
                    cover = str(cover)
                count = it.get("song_count") or it.get("songnum") or 0
                try:
                    count = int(count)
                except Exception:
                    count = 0
                if name and pid:
                    result.append(PlaylistItem(
                        name=name, playlist_id=pid, cover=cover,
                        platform="qq", song_count=count,
                    ))
            if result:
                print(f"[qq] 搜歌单 '{keyword}' → {len(result)} 个", flush=True)
                return result
        except Exception as e:
            print(f"[qq] 搜歌单异常: {str(e)[:100]}", flush=True)

    try:
        r = get("https://c.y.qq.com/soso/fcgi-bin/client_music_search_songlist",
                params={"query": keyword, "num": limit, "page": 0, "flag": 1,
                        "remoteplace": "txt.yqq.playlist", "format": "json"},
                referer="https://y.qq.com/", timeout=15)
        data = r.json()
        inner = data.get("data")
        if not isinstance(inner, dict):
            inner = {}
        items = inner.get("list")
        if not isinstance(items, list):
            items = []
        result = []
        for it in items:
            if not isinstance(it, dict):
                continue
            disstid = it.get("dissid") or it.get("diss_id")
            name = it.get("dissname") or it.get("diss_name") or ""
            if not isinstance(name, str):
                name = str(name)
            if disstid and name:
                count = it.get("song_count") or it.get("songnum") or 0
                try:
                    count = int(count)
                except Exception:
                    count = 0
                result.append(PlaylistItem(
                    name=name.strip(), playlist_id=str(disstid),
                    cover=it.get("imgurl", "") or "", platform="qq",
                    song_count=count,
                ))
        return result
    except Exception as e:
        print(f"[qq] legacy 搜歌单异常: {str(e)[:80]}", flush=True)
        return []


# ============================================================
#  网易云音乐
# ============================================================
NETEASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://music.163.com/",
    "Accept": "application/json, text/plain, */*",
}


def search_netease_playlists(keyword: str, limit: int = 30) -> List[PlaylistItem]:
    try:
        import requests
        url = "https://music.163.com/api/search/get/web"
        params = {
            "csrf_token": "",
            "s": keyword,
            "type": 1000,
            "offset": 0,
            "total": "true",
            "limit": limit,
        }
        r = requests.get(url, params=params, headers=NETEASE_HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"[netease] 搜索 HTTP {r.status_code}", flush=True)
            return []
        data = r.json()
        result_node = data.get("result")
        if not isinstance(result_node, dict):
            return []
        items = result_node.get("playlists")
        if not isinstance(items, list):
            return []

        result = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = (it.get("name") or "").strip()
            pid = it.get("id")
            count = it.get("trackCount") or it.get("playCount") or 0
            cover = it.get("coverImgUrl") or it.get("picUrl") or ""
            if name and pid:
                try:
                    count = int(count)
                except Exception:
                    count = 0
                result.append(PlaylistItem(
                    name=name, playlist_id=str(pid), cover=cover,
                    platform="netease", song_count=count,
                ))
        print(f"[netease] 搜歌单 '{keyword}' → {len(result)} 个", flush=True)
        return result
    except Exception as e:
        print(f"[netease] 搜索异常: {str(e)[:100]}", flush=True)
        return []


def netease_playlist_songs(playlist_id: str, limit: int = 0) -> List[PlaylistSong]:
    """获取网易云歌单所有歌曲。limit=0 表示不限制。"""
    try:
        import requests

        url = "https://music.163.com/api/v6/playlist/detail"
        params = {"id": playlist_id, "n": 100000, "s": 0}
        r = requests.get(url, params=params, headers=NETEASE_HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"[netease] 歌单详情 HTTP {r.status_code}", flush=True)
            return []
        data = r.json()
        pl = data.get("playlist")
        if not isinstance(pl, dict):
            print(f"[netease] 歌单详情结构异常", flush=True)
            return []

        track_ids_raw = pl.get("trackIds") or []
        if not isinstance(track_ids_raw, list):
            track_ids_raw = []

        if not track_ids_raw:
            tracks = pl.get("tracks") or []
            if isinstance(tracks, list):
                songs = []
                for t in tracks:
                    if not isinstance(t, dict):
                        continue
                    name = (t.get("name") or "").strip()
                    ar = t.get("ar") or t.get("artists") or []
                    artists = []
                    if isinstance(ar, list):
                        for a in ar:
                            if isinstance(a, dict) and a.get("name"):
                                artists.append(a["name"])
                    if name:
                        songs.append(PlaylistSong(
                            title=name,
                            artist="、".join(artists),
                        ))
                print(f"[netease] 歌单 {playlist_id}（无 trackIds）→ {len(songs)} 首",
                      flush=True)
                return songs[:limit] if limit else songs
            return []

        ids = []
        for item in track_ids_raw:
            if isinstance(item, dict) and item.get("id"):
                ids.append(int(item["id"]))
            elif isinstance(item, int):
                ids.append(item)

        if not ids:
            return []

        print(f"[netease] 歌单 {playlist_id} trackIds 共 {len(ids)} 首，拉取详情...",
              flush=True)

        songs = []
        BATCH = 500
        total = len(ids)
        for start in range(0, total, BATCH):
            batch = ids[start:start + BATCH]
            c_param = json.dumps([{"id": i} for i in batch])
            api = "https://music.163.com/api/v3/song/detail"

            batch_success = False
            for attempt in range(1, 4):
                try:
                    r2 = requests.post(
                        api,
                        data={"c": c_param},
                        headers={**NETEASE_HEADERS,
                                 "Content-Type": "application/x-www-form-urlencoded"},
                        timeout=20,
                    )
                    if r2.status_code != 200:
                        print(f"[netease] 详情 HTTP {r2.status_code} "
                              f"(批次 {start}, 尝试 {attempt})", flush=True)
                        if attempt < 3:
                            time.sleep(0.5 * attempt)
                            continue
                        break

                    d2 = r2.json()
                    song_list = d2.get("songs") or []
                    if not isinstance(song_list, list):
                        if attempt < 3:
                            time.sleep(0.5 * attempt)
                            continue
                        break

                    for t in song_list:
                        if not isinstance(t, dict):
                            continue
                        name = (t.get("name") or "").strip()
                        ar = t.get("ar") or t.get("artists") or []
                        artists = []
                        if isinstance(ar, list):
                            for a in ar:
                                if isinstance(a, dict) and a.get("name"):
                                    artists.append(a["name"])
                        if name:
                            songs.append(PlaylistSong(
                                title=name,
                                artist="、".join(artists),
                            ))
                    batch_success = True
                    print(f"[netease] 已拉取 {min(start + BATCH, total)}/{total}",
                          flush=True)
                    break
                except Exception as e:
                    print(f"[netease] 批次异常 (尝试 {attempt}): "
                          f"{str(e)[:100]}", flush=True)
                    if attempt < 3:
                        time.sleep(0.5 * attempt)

            if not batch_success:
                print(f"[netease] 批次 {start}-{min(start+BATCH, total)} 失败",
                      flush=True)

        print(f"[netease] 歌单 {playlist_id} → {len(songs)} 首", flush=True)
        return songs[:limit] if limit else songs
    except Exception as e:
        print(f"[netease] 歌单异常: {str(e)[:100]}", flush=True)
        return []


# ============================================================
#  统一入口
# ============================================================
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
    if platform == "netease":
        return search_netease_playlists(keyword, limit)
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
    if platform == "netease":
        return netease_playlist_songs(playlist_id)
    return []


def get_playlist_by_url(url: str) -> List[PlaylistSong]:
    platform, playlist_id = parse_playlist_url(url)
    if not platform or not playlist_id:
        return []
    return get_playlist_songs(platform, playlist_id)
