"""gequbao.com 接口封装：搜索 + 播放 + 歌词

播放策略：
  1. Playwright 打开 song_id 对应的详情页（保证是当前歌曲）
  2. 等页面加载完成，清空捕获列表
  3. 点击"播放"按钮，只捕获点击后的音频请求
  4. 用 page.request.get 复用 cookie 下载（绕过 CDN 校验）
  5. 失败则重试 2 次；再失败回退 gequbao API + curl_cffi
"""
import base64
import hashlib
import html as html_lib
import os
import re
import tempfile
import time
import warnings
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from curl_cffi import requests as curl_requests

warnings.filterwarnings("ignore", category=SyntaxWarning)


# ---------- 常量 ----------
GEQUBAO_BASE = "https://www.gequbao.com"
GEQUBAO_API_BASE = "https://www.gequbao.net"
GEQUBAO_SEARCH_URL = GEQUBAO_BASE + "/s/{keyword}"
GEQUBAO_DETAIL_URL = GEQUBAO_BASE + "/music/{song_id}"
GEQUBAO_PLAY_API_NEW = GEQUBAO_API_BASE + "/api/play-url"

MIN_VALID_SIZE = 400 * 1024
IMPERSONATE = "chrome120"
PW_CACHE_VER = "pw_v3"

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "musicplayer_cache"

# 点击播放按钮时尝试的 CSS 选择器
PLAY_BUTTON_SELECTORS = [
    "a:has-text('播放')",
    "button:has-text('播放')",
    "text=播放",
    ".btn:has-text('播放')",
    "[data-action='play']",
    "a.play-btn",
    ".player-play",
    "i.fa-play",
]


# ---------- 缓存目录 ----------
def get_cache_dir() -> Path:
    try:
        from utils.helpers import load_config
        cfg = load_config()
        custom = cfg.get("cache_dir")
        p = Path(custom) if custom else _DEFAULT_CACHE_DIR
    except Exception:
        p = _DEFAULT_CACHE_DIR
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def get_default_cache_dir() -> Path:
    return _DEFAULT_CACHE_DIR


_CACHE_DIR = _DEFAULT_CACHE_DIR


# ---------- Song ----------
class Song:
    __slots__ = ("title", "artist", "song_id", "detail_url")

    def __init__(self, title, artist, song_id, detail_url=""):
        self.title = title.strip()
        self.artist = artist.strip()
        self.song_id = song_id
        self.detail_url = detail_url or GEQUBAO_DETAIL_URL.format(song_id=song_id)

    @property
    def display(self):
        return f"{self.title} - {self.artist}" if self.artist else self.title

    def __repr__(self):
        return f"<Song {self.display}>"


# ---------- 搜索 ----------
_SONG_LINK_RE = re.compile(
    r'<a\s+href="/music/(\d+)"[^>]*class="hover-zoom[^"]*"[^>]*title="([^"]*)"',
    re.I,
)
_SONG_LINK_RE2 = re.compile(
    r'<a\s+href="/music/(\d+)"[^>]*title="([^"]*)"[^>]*class="hover-zoom[^"]*"',
    re.I,
)
_TITLE_SPLIT = re.compile(r"\s*-\s*", re.I)


def _parse_title_artist(raw):
    raw = html_lib.unescape(raw).strip()
    if not raw:
        return "", ""
    parts = _TITLE_SPLIT.split(raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw, ""


def search(keyword: str, limit: int = 40) -> List[Song]:
    r = curl_requests.get(
        GEQUBAO_SEARCH_URL.format(keyword=keyword),
        headers={"Referer": GEQUBAO_BASE + "/"},
        impersonate=IMPERSONATE,
        timeout=20,
    )
    r.encoding = "utf-8"
    html = r.text
    songs, seen = [], set()
    for pattern in (_SONG_LINK_RE, _SONG_LINK_RE2):
        if songs:
            break
        for m in pattern.finditer(html):
            sid, title_attr = m.group(1), m.group(2)
            if sid in seen:
                continue
            seen.add(sid)
            title, artist = _parse_title_artist(title_attr)
            if title:
                songs.append(Song(title=title, artist=artist, song_id=sid))
                if len(songs) >= limit:
                    break
    return songs


# ---------- 缓存路径 ----------
def _cache_path_for(url: str) -> Path:
    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    return get_cache_dir() / f"{h}.mp3"


def _pw_cache_path(song_id: str) -> Path:
    return get_cache_dir() / f"{PW_CACHE_VER}_{song_id}.mp3"


def _clean_song_cache(song_id: str):
    """清掉这首歌的缓存，用于重试前重置"""
    for p in [
        _pw_cache_path(song_id),
        _pw_cache_path(song_id).with_suffix(".part"),
    ]:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def _save_body(cache: Path, body: bytes, source: str) -> Optional[str]:
    if len(body) < MIN_VALID_SIZE:
        print(f"[gequbao] {source} 文件过小 {len(body)}", flush=True)
        return None
    tmp = cache.with_suffix(".part")
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, cache)
    print(f"[gequbao] ✓ {source} 保存成功 size={len(body)}", flush=True)
    return str(cache)


# ---------- curl_cffi 下载 ----------
def _download_mp3(song_id: str, url: str) -> Optional[str]:
    cache = _cache_path_for(url)
    if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE:
        print(f"[gequbao] 使用缓存 ({cache.stat().st_size} 字节)", flush=True)
        return str(cache)

    headers = {
        "Referer": GEQUBAO_DETAIL_URL.format(song_id=song_id),
        "Origin": GEQUBAO_BASE,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        r = curl_requests.get(
            url, headers=headers, impersonate=IMPERSONATE,
            timeout=30, stream=True,
        )
        if r.status_code >= 400:
            print(f"[gequbao] curl_cffi status={r.status_code}", flush=True)
            return None
        body = b""
        for chunk in r.iter_content(64 * 1024):
            if chunk:
                body += chunk
        return _save_body(cache, body, "curl_cffi")
    except Exception as e:
        print(f"[gequbao] curl_cffi 下载异常: {e}", flush=True)
    return None


# ---------- Playwright 抓取（一次尝试） ----------
def _try_playwright_once(song_id: str, cache: Path, attempt: int) -> Optional[str]:
    """执行一次 Playwright 抓取，成功返回路径，失败返回 None"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[playwright] 未安装", flush=True)
        return None

    captured = []
    state = {"clicked": False}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=DESKTOP_UA,
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()

            def on_response(resp):
                if not state["clicked"]:
                    return
                u = resp.url
                if (".mp3" in u or "/resource/n" in u
                        or "car-bj" in u or "kw-er" in u):
                    captured.append(u)

            page.on("response", on_response)

            detail_url = GEQUBAO_DETAIL_URL.format(song_id=song_id)
            print(f"[playwright] 尝试 {attempt} 打开 {detail_url}", flush=True)
            page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)

            # 等页面完全稳定：推荐、广告先跑完
            page.wait_for_timeout(2500 + attempt * 800)

            # 进入点击阶段
            captured.clear()
            state["clicked"] = True

            clicked = False
            for sel in PLAY_BUTTON_SELECTORS:
                try:
                    page.click(sel, timeout=2000)
                    print(f"[playwright] 已点击 {sel}", flush=True)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                print(f"[playwright] 未找到播放按钮", flush=True)

            # 等待音频请求
            page.wait_for_timeout(6000 + attempt * 1500)

            # 从最新的开始尝试（越新越可能是当前歌曲）
            for url in reversed(captured):
                try:
                    print(f"[playwright] 下载 {url[:100]}", flush=True)
                    resp = page.request.get(url)
                    body = resp.body()
                    if len(body) >= MIN_VALID_SIZE:
                        tmp = cache.with_suffix(".part")
                        with open(tmp, "wb") as f:
                            f.write(body)
                        os.replace(tmp, cache)
                        print(f"[playwright] ✓ 成功 size={len(body)}", flush=True)
                        browser.close()
                        return str(cache)
                except Exception as e:
                    print(f"[playwright] 下载异常: {e}", flush=True)

            browser.close()
    except Exception as e:
        print(f"[playwright] 尝试 {attempt} 异常: {e}", flush=True)
    return None


def _download_via_playwright(song_id: str, max_retry: int = 2) -> Optional[str]:
    """多次尝试 Playwright 抓取"""
    cache = _pw_cache_path(song_id)
    if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE:
        print(f"[playwright] 使用缓存 ({cache.stat().st_size} 字节)", flush=True)
        return str(cache)

    for attempt in range(1, max_retry + 1):
        # 每次尝试前清缓存
        _clean_song_cache(song_id)
        result = _try_playwright_once(song_id, cache, attempt)
        if result:
            return result
        if attempt < max_retry:
            print(f"[playwright] 第 {attempt} 次失败，1.5 秒后重试...", flush=True)
            time.sleep(1.5)

    return None


# ---------- gequbao 新版 POST API ----------
def _fetch_play_url_new_api(song_id: str) -> Optional[str]:
    encoded_id = base64.b64encode(str(song_id).encode("utf-8")).decode("utf-8")
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": GEQUBAO_DETAIL_URL.format(song_id=song_id),
        "Origin": GEQUBAO_API_BASE,
    }
    try:
        curl_requests.get(GEQUBAO_API_BASE + "/", impersonate=IMPERSONATE, timeout=10)
        r = curl_requests.post(
            GEQUBAO_PLAY_API_NEW,
            data={"id": encoded_id},
            headers=headers,
            impersonate=IMPERSONATE,
            timeout=15,
        )
        print(f"[gequbao] POST /api/play-url -> {r.status_code}", flush=True)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, dict) and data.get("code") == 1:
            inner = data.get("data")
            if isinstance(inner, dict):
                url = inner.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url.replace("\\/", "/")
    except Exception as e:
        print(f"[gequbao] 新版接口异常: {e}", flush=True)
    return None


# ---------- 歌词 ----------
def _get_lyrics_from_detail(song_id: str) -> Optional[str]:
    detail_url = GEQUBAO_DETAIL_URL.format(song_id=song_id)
    try:
        r = curl_requests.get(
            detail_url,
            headers={"Referer": GEQUBAO_BASE + "/"},
            impersonate=IMPERSONATE, timeout=20,
        )
        if r.status_code == 200:
            text = r.text
            m = re.search(r'<div[^>]*id="content-lrc"[^>]*>(.*?)</div>', text, re.S | re.I)
            if m:
                content = m.group(1)
                content = content.replace("\\n", "\n").replace("\\r", "").replace("\\/", "/")
                content = html_lib.unescape(re.sub(r"<br\s*/?>", "\n", content))
                content = re.sub(r"<[^>]+>", "", content)
                if "[" in content and "]" in content:
                    return content.strip()
    except Exception as e:
        print(f"[gequbao] 歌词提取异常: {e}", flush=True)
    return None


# ---------- 统一入口 ----------
def resolve_song(song_id: str, title: str = "", artist: str = "",
                 max_retry: int = 2) -> Dict:
    """
    解析歌曲：
      1. 检查 Playwright 缓存
      2. Playwright 抓取（多次重试）
      3. 兜底 gequbao API + curl_cffi
    """
    pw_cache = _pw_cache_path(song_id)
    if pw_cache.exists() and pw_cache.stat().st_size >= MIN_VALID_SIZE:
        print(f"[gequbao] 使用 Playwright 缓存 ({pw_cache.stat().st_size} 字节)", flush=True)
        lyrics = _get_lyrics_from_detail(song_id)
        return {"url": None, "file": str(pw_cache), "lyrics": lyrics}

    # Playwright
    print("[gequbao] 启用 Playwright 详情页抓取...", flush=True)
    file_path = _download_via_playwright(song_id, max_retry=max_retry)
    if file_path:
        lyrics = _get_lyrics_from_detail(song_id)
        return {"url": None, "file": file_path, "lyrics": lyrics}

    # 兜底
    print("[gequbao] Playwright 全部失败，回退 gequbao API...", flush=True)
    url = _fetch_play_url_new_api(song_id)
    if url:
        file_path = _download_mp3(song_id, url)

    lyrics = _get_lyrics_from_detail(song_id)
    return {"url": url, "file": file_path, "lyrics": lyrics}


def get_play_url(song_id: str, title: str = "", artist: str = "") -> Optional[str]:
    return resolve_song(song_id, title, artist).get("url")


def get_lyrics(song_id: str) -> Optional[str]:
    return _get_lyrics_from_detail(song_id)


def get_download_url(song_id: str) -> Optional[str]:
    return get_play_url(song_id)
