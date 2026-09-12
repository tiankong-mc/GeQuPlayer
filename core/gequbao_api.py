"""gequbao.com 接口封装：搜索 + 播放 + 歌词"""
import base64
import hashlib
import html as html_lib
import os
import random
import re
import tempfile
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Tuple

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
PW_CACHE_VER = "pw_v15"

CHUNK_THREADS = 8
MIN_SIZE_FOR_CHUNKS = 2 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_TIMEOUT_MS = 180000

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

DESKTOP_UA = UA_POOL[0]

_DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "musicplayer_cache"


# ---------- 缓存文件保护（正在播放的不删） ----------
_protected_lock = threading.Lock()
_protected_files = set()


def protect_file(path: str):
    if not path:
        return
    with _protected_lock:
        _protected_files.add(os.path.abspath(str(path)))


def unprotect_file(path: str):
    if not path:
        return
    with _protected_lock:
        _protected_files.discard(os.path.abspath(str(path)))


def is_protected(path: str) -> bool:
    if not path:
        return False
    with _protected_lock:
        return os.path.abspath(str(path)) in _protected_files


def delete_cache_file(path: str, verbose: bool = True) -> bool:
    """
    删除缓存文件。如果文件正在播放（受保护）则跳过。
    返回 True 表示已删除或无需删除，False 表示被保护跳过。
    """
    if not path:
        return True
    p = os.path.abspath(str(path))
    if is_protected(p):
        if verbose:
            print(f"[cache] 跳过删除（正在播放）：{os.path.basename(p)}", flush=True)
        return False
    try:
        if os.path.exists(p):
            os.remove(p)
            if verbose:
                print(f"[cache] 已删除缓存：{os.path.basename(p)}", flush=True)
        return True
    except Exception as e:
        print(f"[cache] 删除失败 {p}: {e}", flush=True)
        return False


# ---------- 选择器 ----------
DOWNLOAD_BUTTON_SELECTORS = [
    "a:has-text('下载歌曲')",
    "button:has-text('下载歌曲')",
    "text=下载歌曲",
    ".btn:has-text('下载歌曲')",
]

QUALITY_DIALOG_SELECTORS = [
    "text=请选择音质",
    "text=下载低品质MP3",
    "text=下载高品质MP3",
    "text=低品质MP3",
    "text=高品质MP3",
]

LOW_QUALITY_SELECTORS = [
    "text=下载低品质MP3",
    "text=低品质MP3",
    ":has-text('低品质MP3')",
]

HIGH_QUALITY_SELECTORS = [
    "text=下载高品质MP3",
    "text=高品质MP3",
    ":has-text('高品质MP3')",
]

CAPTCHA_INPUT_SELECTORS = [
    "input[placeholder*='验证码']",
    "input[name*='captcha']",
    "input[name*='verify']",
    "div[role='dialog'] input[type='text']",
    "div.modal input[type='text']",
    "input[type='text']",
]

CAPTCHA_IMG_SELECTORS = [
    "img[src*='captcha']",
    "img[src*='verify']",
    ".captcha-img",
    ".captcha img",
    "div[role='dialog'] img",
    "div.modal img",
]

CAPTCHA_SUBMIT_SELECTORS = [
    "button:has-text('提交验证')",
    "button:has-text('提交')",
    "button:has-text('确定')",
    "a:has-text('提交验证')",
]


# ---------- 全局节流 ----------
_throttle_lock = threading.Lock()
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 2.0


def _throttle():
    global _last_request_time
    with _throttle_lock:
        now = time.time()
        wait = _MIN_REQUEST_INTERVAL - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.time()


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


_MP3_MAGIC = [
    b"ID3",
    b"\xff\xfb", b"\xff\xfa",
    b"\xff\xf3", b"\xff\xf2",
    b"\xff\xe3", b"\xff\xe2",
]


def _is_valid_mp3(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(4)
    except Exception:
        return False
    return any(head.startswith(m) for m in _MP3_MAGIC)


def _is_valid_mp3_bytes(body: bytes) -> bool:
    if len(body) < 4:
        return False
    return any(body[:4].startswith(m) for m in _MP3_MAGIC)


def _is_stopped(stop_flag) -> bool:
    return stop_flag is not None and stop_flag.is_set()


_SONG_LINK_RE = re.compile(
    r'<a\s+href="/music/(\d+)"[^>]*class="hover-zoom[^"]*"[^>]*title="([^"]*)"', re.I)
_SONG_LINK_RE2 = re.compile(
    r'<a\s+href="/music/(\d+)"[^>]*title="([^"]*)"[^>]*class="hover-zoom[^"]*"', re.I)
_TITLE_SPLIT = re.compile(r"\s*-\s*", re.I)


def _parse_title_artist(raw):
    raw = html_lib.unescape(raw).strip()
    if not raw:
        return "", ""
    parts = _TITLE_SPLIT.split(raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw, ""


_session_lock = threading.Lock()
_session = None


def _get_session():
    global _session
    with _session_lock:
        if _session is None:
            _session = curl_requests.Session(impersonate=IMPERSONATE)
            _session.headers.update({"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    return _session


def search(keyword: str, limit: int = 40) -> List[Song]:
    s = _get_session()
    r = s.get(
        GEQUBAO_SEARCH_URL.format(keyword=keyword),
        headers={"Referer": GEQUBAO_BASE + "/"},
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


def _pw_cache_path(song_id: str) -> Path:
    return get_cache_dir() / f"{PW_CACHE_VER}_{song_id}.mp3"


def _clean_song_cache(song_id: str):
    for p in [_pw_cache_path(song_id), _pw_cache_path(song_id).with_suffix(".part")]:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


# ---------- OCR ----------
_ocr_lock = threading.Lock()
_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    with _ocr_lock:
        if _ocr_instance is None:
            try:
                import ddddocr
                _ocr_instance = ddddocr.DdddOcr(show_ad=False)
                print("[captcha] ddddocr 已加载", flush=True)
            except Exception as e:
                print(f"[captcha] ddddocr 失败: {e}", flush=True)
                _ocr_instance = False
    return _ocr_instance if _ocr_instance is not False else None


def _has_captcha(page) -> bool:
    try:
        for text in ["安全验证", "请完成人机验证", "请输入验证码"]:
            try:
                if page.locator(f"text={text}").count() > 0:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def _solve_captcha(page) -> bool:
    ocr = _get_ocr()
    if ocr is None:
        return False
    try:
        img_locator = None
        for sel in CAPTCHA_IMG_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    img_locator = loc
                    print(f"[captcha] 定位: {sel}", flush=True)
                    break
            except Exception:
                continue
        if img_locator is None:
            return False
        img_bytes = img_locator.screenshot()
        code = ocr.classification(img_bytes)
        code = re.sub(r"[^0-9a-zA-Z]", "", code)
        print(f"[captcha] 识别: {code!r}", flush=True)
        if not (3 <= len(code) <= 6):
            return False
        input_ok = False
        for sel in CAPTCHA_INPUT_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.fill(code)
                    input_ok = True
                    break
            except Exception:
                continue
        if not input_ok:
            return False
        page.wait_for_timeout(500)
        for sel in CAPTCHA_SUBMIT_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.click()
                    page.wait_for_timeout(2500)
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


# ---------- 下载 ----------
def _download_chunk(session, url, headers, start, end, chunk_path, retries=3, stop_flag=None):
    for attempt in range(1, retries + 1):
        if _is_stopped(stop_flag):
            return False
        try:
            h = dict(headers)
            h["Range"] = f"bytes={start}-{end}"
            r = session.get(url, headers=h, timeout=60, stream=True)
            if r.status_code not in (200, 206):
                if attempt < retries:
                    time.sleep(0.5 * attempt)
                    continue
                return False
            with open(chunk_path, "wb") as f:
                for data in r.iter_content(32 * 1024):
                    if _is_stopped(stop_flag):
                        return False
                    if data:
                        f.write(data)
            expected = end - start + 1
            actual = chunk_path.stat().st_size
            if actual < expected * 0.95:
                if attempt < retries:
                    time.sleep(0.5 * attempt)
                    continue
                return False
            return True
        except Exception:
            if attempt < retries:
                time.sleep(0.5 * attempt)
    return False


def _probe_size(session, url, headers) -> int:
    try:
        h = dict(headers)
        h["Range"] = "bytes=0-0"
        r = session.get(url, headers=h, timeout=15)
        if r.status_code == 206:
            cr = r.headers.get("Content-Range", "")
            m = re.search(r"/(\d+)\s*$", cr)
            if m:
                return int(m.group(1))
        if r.status_code == 200:
            return int(r.headers.get("Content-Length", 0) or 0)
    except Exception:
        pass
    return 0


def _download_multithread(session, url, headers, dest, total_size, stop_flag=None):
    tmp_dir = dest.parent / f".{dest.stem}_chunks"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        chunks = []
        pos = 0
        while pos < total_size:
            end = min(pos + CHUNK_SIZE - 1, total_size - 1)
            chunks.append((pos, end))
            pos = end + 1
        max_workers = min(CHUNK_THREADS, len(chunks))
        print(f"[download] 分块 {len(chunks)} / {max_workers} 线程", flush=True)
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for i, (start, end) in enumerate(chunks):
                chunk_path = tmp_dir / f"chunk_{i:04d}"
                fut = pool.submit(_download_chunk, session, url, headers,
                                  start, end, chunk_path, 3, stop_flag)
                futures[fut] = i
            for fut in as_completed(futures):
                i = futures[fut]
                try:
                    results[i] = fut.result()
                except Exception:
                    results[i] = False
        if _is_stopped(stop_flag):
            return False
        if not all(results.get(i) for i in range(len(chunks))):
            return False
        with open(dest, "wb") as out:
            for i in range(len(chunks)):
                chunk_path = tmp_dir / f"chunk_{i:04d}"
                with open(chunk_path, "rb") as f:
                    while True:
                        data = f.read(1024 * 1024)
                        if not data:
                            break
                        out.write(data)
        return True
    finally:
        try:
            for f in tmp_dir.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            tmp_dir.rmdir()
        except Exception:
            pass


def _download_single(session, url, headers, dest, stop_flag=None):
    for attempt in range(1, 4):
        if _is_stopped(stop_flag):
            return False
        try:
            r = session.get(url, headers=headers, timeout=60, stream=True)
            if r.status_code >= 400:
                if attempt < 3:
                    time.sleep(0.8 * attempt)
                    continue
                return False
            with open(dest, "wb") as f:
                for data in r.iter_content(64 * 1024):
                    if _is_stopped(stop_flag):
                        return False
                    if data:
                        f.write(data)
            return True
        except Exception:
            if attempt < 3:
                time.sleep(0.8 * attempt)
    return False


def _download_from_url(song_id, url, stop_flag=None) -> Optional[str]:
    cache = _pw_cache_path(song_id)
    if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE and _is_valid_mp3(cache):
        return str(cache)

    headers = {
        "User-Agent": DESKTOP_UA,
        "Referer": GEQUBAO_DETAIL_URL.format(song_id=song_id),
        "Accept": "*/*",
    }
    session = _get_session()

    tmp = cache.with_suffix(".part")
    if tmp.exists():
        try:
            tmp.unlink()
        except Exception:
            pass

    total_size = _probe_size(session, url, headers)
    print(f"[download] 探测 {total_size} 字节", flush=True)

    if total_size >= MIN_SIZE_FOR_CHUNKS:
        ok = _download_multithread(session, url, headers, tmp, total_size, stop_flag)
    else:
        ok = _download_single(session, url, headers, tmp, stop_flag)

    if not ok or _is_stopped(stop_flag):
        try:
            tmp.unlink()
        except Exception:
            pass
        return None

    size = tmp.stat().st_size
    if size < MIN_VALID_SIZE or not _is_valid_mp3(tmp):
        print(f"[download] 校验失败 {size}", flush=True)
        try:
            tmp.unlink()
        except Exception:
            pass
        return None

    os.replace(tmp, cache)
    print(f"[download] ✓ 成功 {size}", flush=True)
    return str(cache)


# ---------- Playwright 工具 ----------
def _click_any(page, selectors, timeout=2500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=timeout)
            print(f"[pw] 点击: {sel}", flush=True)
            return True
        except Exception:
            continue
    return False


def _has_any(page, selectors) -> bool:
    for sel in selectors:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


def _get_audio_element_urls(page) -> List[str]:
    try:
        urls = page.evaluate("""
            () => {
                const result = [];
                const seen = new Set();
                function add(u) {
                    if (u && u.startsWith('http') && !seen.has(u)) { seen.add(u); result.push(u); }
                }
                document.querySelectorAll('audio').forEach(a => {
                    add(a.src); add(a.currentSrc);
                    a.querySelectorAll('source').forEach(s => add(s.src));
                });
                document.querySelectorAll('video').forEach(v => { add(v.src); add(v.currentSrc); });
                return result;
            }
        """)
        return urls or []
    except Exception:
        return []


def _try_download_urls(page, urls, cache, stop_flag=None) -> Optional[str]:
    for url in urls:
        if _is_stopped(stop_flag):
            return None
        if not url or url.startswith("blob:"):
            continue
        try:
            print(f"[pw] 下载: {url[:120]}", flush=True)
            resp = page.request.get(url, timeout=DOWNLOAD_TIMEOUT_MS)
            body = resp.body()
            if len(body) >= MIN_VALID_SIZE and _is_valid_mp3_bytes(body):
                tmp = cache.with_suffix(".part")
                with open(tmp, "wb") as f:
                    f.write(body)
                os.replace(tmp, cache)
                print(f"[pw] ✓ 成功 {len(body)}", flush=True)
                return str(cache)
            else:
                print(f"[pw] 无效 {len(body)}", flush=True)
        except Exception as e:
            print(f"[pw] 失败: {str(e)[:100]}", flush=True)
    return None


def _collect_all_urls(page, captured):
    audio_urls = _get_audio_element_urls(page)
    network_urls = [u for (u, _, _) in captured]
    all_urls = []
    for u in audio_urls:
        if u not in all_urls:
            all_urls.append(u)
    for u in network_urls:
        if u not in all_urls:
            all_urls.append(u)
    return all_urls


def _pw_session_attempt(song_id: str, session_idx: int, stop_flag=None
                        ) -> Tuple[Optional[str], bool]:
    cache = _pw_cache_path(song_id)
    if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE and _is_valid_mp3(cache):
        return str(cache), False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[pw] Playwright 未安装", flush=True)
        return None, False

    captured = []
    ua = random.choice(UA_POOL)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=ua,
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            page = ctx.new_page()

            def on_response(resp):
                try:
                    u = resp.url
                    ct = (resp.headers.get("content-type", "") or "").lower()
                    cl_str = resp.headers.get("content-length", "") or ""
                    cl = int(cl_str) if cl_str.isdigit() else 0

                    if ".js" in u.lower() or ".css" in u.lower() or ".html" in u.lower():
                        return
                    if "gequbao.com/build" in u:
                        return

                    is_audio = False
                    if "audio/" in ct or "mpeg" in ct or "octet-stream" in ct:
                        is_audio = True
                    elif ".mp3" in u.lower() or ".m4a" in u.lower() or ".flac" in u.lower():
                        is_audio = True
                    elif cl > 1_000_000 and not any(x in ct for x in
                                                    ["html", "json", "javascript", "css", "image", "font"]):
                        is_audio = True

                    if is_audio:
                        if u not in [c[0] for c in captured]:
                            captured.append((u, ct, cl))
                            print(f"[pw] 捕获: {u[:100]} (cl={cl})", flush=True)
                except Exception:
                    pass

            page.on("response", on_response)

            detail_url = GEQUBAO_DETAIL_URL.format(song_id=song_id)
            print(f"[pw] 会话{session_idx} 打开 {detail_url} (UA尾号{ua[-30:]})", flush=True)

            try:
                page.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print(f"[pw] 页面加载失败: {str(e)[:100]}", flush=True)
                browser.close()
                return None, False

            if _is_stopped(stop_flag):
                browser.close()
                return None, False

            page.wait_for_timeout(2500)
            _throttle()

            if _is_stopped(stop_flag):
                browser.close()
                return None, False

            print(f"[pw] 会话{session_idx} 步骤1：点击下载", flush=True)
            if not _click_any(page, DOWNLOAD_BUTTON_SELECTORS, timeout=3000):
                print("[pw] 未找到下载按钮", flush=True)
                browser.close()
                return None, False

            print(f"[pw] 会话{session_idx} 步骤2：等待倒计时", flush=True)
            quality_found = False
            for i in range(45):
                if _is_stopped(stop_flag):
                    browser.close()
                    return None, False
                page.wait_for_timeout(2000)
                if _has_any(page, QUALITY_DIALOG_SELECTORS):
                    quality_found = True
                    print(f"[pw] 音质对话框（{(i + 1) * 2}s）", flush=True)
                    break
            if not quality_found:
                print("[pw] 音质对话框超时", flush=True)
                browser.close()
                return None, False

            page.wait_for_timeout(1000)

            print(f"[pw] 会话{session_idx} 步骤3：选低品质", flush=True)
            q_clicked = _click_any(page, LOW_QUALITY_SELECTORS, timeout=3000)
            if not q_clicked:
                q_clicked = _click_any(page, HIGH_QUALITY_SELECTORS, timeout=3000)
            if not q_clicked:
                print("[pw] 未找到音质按钮", flush=True)
                browser.close()
                return None, False

            page.wait_for_timeout(2000)
            if _has_captcha(page):
                print(f"[pw] 会话{session_idx} 步骤4：验证码", flush=True)
                solved = False
                for attempt in range(3):
                    if _is_stopped(stop_flag):
                        browser.close()
                        return None, False
                    if _solve_captcha(page):
                        page.wait_for_timeout(2500)
                        if not _has_captcha(page):
                            print("[pw] 验证码通过", flush=True)
                            solved = True
                            break
                    else:
                        page.wait_for_timeout(1500)
                if not solved and _has_captcha(page):
                    print("[pw] 验证码未通过", flush=True)
                    browser.close()
                    return None, False

            print(f"[pw] 会话{session_idx} 步骤5：等待下载触发", flush=True)
            page.wait_for_timeout(8000)

            all_urls = _collect_all_urls(page, captured)
            print(f"[pw] 会话{session_idx} 收集 {len(all_urls)} 个 URL", flush=True)

            if all_urls:
                result = _try_download_urls(page, list(reversed(all_urls)), cache, stop_flag)
                if result:
                    browser.close()
                    return result, False

            if not all_urls:
                print(f"[pw] 会话{session_idx} 0 候选，再等 8 秒", flush=True)
                page.wait_for_timeout(8000)
                all_urls = _collect_all_urls(page, captured)
                if all_urls:
                    print(f"[pw] 会话{session_idx} 补收 {len(all_urls)} 个 URL", flush=True)
                    result = _try_download_urls(page, list(reversed(all_urls)), cache, stop_flag)
                    if result:
                        browser.close()
                        return result, False

            if not all_urls:
                browser.close()
                return None, True

            browser.close()
    except Exception as e:
        print(f"[pw] 会话{session_idx} 异常: {str(e)[:150]}", flush=True)
    return None, False


def _pw_download_song(song_id: str, max_sessions: int = 2,
                      stop_flag=None) -> Optional[str]:
    cache = _pw_cache_path(song_id)
    if cache.exists() and cache.stat().st_size >= MIN_VALID_SIZE and _is_valid_mp3(cache):
        return str(cache)

    for idx in range(1, max_sessions + 1):
        if _is_stopped(stop_flag):
            return None

        result, need_new = _pw_session_attempt(song_id, idx, stop_flag)
        if result:
            return result

        if not need_new:
            return None

        if idx < max_sessions:
            print(f"[pw] 会话{idx}被限流（0候选），重建会话...", flush=True)
            end = time.time() + 1.5
            while time.time() < end:
                if _is_stopped(stop_flag):
                    return None
                time.sleep(0.2)
            _clean_song_cache(song_id)

    return None


# ---------- API 兜底 ----------
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
        s = _get_session()
        s.get(GEQUBAO_API_BASE + "/", timeout=10)
        r = s.post(GEQUBAO_PLAY_API_NEW, data={"id": encoded_id},
                   headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, dict) and data.get("code") == 1:
            inner = data.get("data")
            if isinstance(inner, dict):
                url = inner.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url.replace("\\/", "/")
    except Exception:
        pass
    return None


def _get_lyrics_from_detail(song_id: str) -> Optional[str]:
    detail_url = GEQUBAO_DETAIL_URL.format(song_id=song_id)
    try:
        r = _get_session().get(detail_url,
                               headers={"Referer": GEQUBAO_BASE + "/"}, timeout=20)
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
    except Exception:
        pass
    return None


def resolve_song(song_id: str, title: str = "", artist: str = "",
                 max_retry: int = 1, stop_flag=None) -> Dict:
    if _is_stopped(stop_flag):
        return {"url": None, "file": None, "lyrics": None}

    pw_cache = _pw_cache_path(song_id)
    if pw_cache.exists() and pw_cache.stat().st_size >= MIN_VALID_SIZE and _is_valid_mp3(pw_cache):
        print(f"[gequbao] 缓存命中 {pw_cache.stat().st_size}", flush=True)
        return {"url": None, "file": str(pw_cache),
                "lyrics": _get_lyrics_from_detail(song_id)}

    for attempt in range(1, max_retry + 1):
        if _is_stopped(stop_flag):
            return {"url": None, "file": None, "lyrics": None}
        _clean_song_cache(song_id)
        result = _pw_download_song(song_id, max_sessions=2, stop_flag=stop_flag)
        if result:
            return {"url": None, "file": result,
                    "lyrics": _get_lyrics_from_detail(song_id)}
        if attempt < max_retry:
            time.sleep(1.5)

    if _is_stopped(stop_flag):
        return {"url": None, "file": None, "lyrics": None}

    print("[gequbao] 回退 API...", flush=True)
    url = _fetch_play_url_new_api(song_id)
    if url:
        file_path = _download_from_url(song_id, url, stop_flag)
        if file_path:
            return {"url": url, "file": file_path,
                    "lyrics": _get_lyrics_from_detail(song_id)}

    return {"url": None, "file": None,
            "lyrics": _get_lyrics_from_detail(song_id)}


def get_play_url(song_id: str, title: str = "", artist: str = "") -> Optional[str]:
    return resolve_song(song_id, title, artist).get("url")


def get_lyrics(song_id: str) -> Optional[str]:
    return _get_lyrics_from_detail(song_id)


def get_download_url(song_id: str) -> Optional[str]:
    return get_play_url(song_id)
