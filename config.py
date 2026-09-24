"""全局配置"""
import os
from pathlib import Path

APP_NAME = "GeQuPlayer"
APP_VERSION = "1.2.2"
#============ 用户可调参数（首次启动写入 config.json） ============
DEFAULT_CONCURRENT_TASKS = 4          # 同时下载数（1-10）
DEFAULT_LYRICS_MODE = "line"          # "line" 逐行 / "word" 逐字
# ============ 下载目录的子文件夹 ============
DOWNLOAD_MP3_SUBDIR = "MP3"
DOWNLOAD_LRC_SUBDIR = "LRC"
# ============ GitHub 更新镜像（依次尝试） ============
UPDATE_MIRRORS = [
    "https://ghproxy.com/",
    "https://ghproxy.net/",
    "https://gh.api.99988866.xyz/",
    "https://gh.llkk.cc/",
    "https://gitproxy.click/",
]
UPDATE_API = "https://api.github.com/repos/tiankong-mc/GeQuPlayer/releases/latest"
# 路径
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "music.db"
CONFIG_PATH = DATA_DIR / "config.json"

# 默认下载目录
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Music" / "GeQuPlayer")

# ============ 缓存目录安全配置 ============
# 用户选择的缓存根目录下，程序固定使用这个子目录
# 防止用户误选桌面/文档 导致清空时误删
CACHE_SUBDIR_NAME = "GeQuPlayerCache"
# 缓存目录标识文件（清理时用于验证）
CACHE_MARKER_FILE = ".gequplayer_cache"

# ============ gequbao 相关 ============
GEQUBAO_BASE = "https://www.gequbao.com"
GEQUBAO_SEARCH = GEQUBAO_BASE + "/s/{keyword}"
GEQUBAO_PLAY_URL = GEQUBAO_BASE + "/api/play_url"
GEQUBAO_DOWNLOAD_URL = GEQUBAO_BASE + "/api/download"
GEQUBAO_LYRICS_URL = GEQUBAO_BASE + "/api/lyric"

# ============ 请求 ============
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20


# ============ 下载 ============
DOWNLOAD_WAIT_SECONDS = 30
DOWNLOAD_CHUNK = 64 * 1024

# ============ UI ============
WINDOW_MIN_WIDTH = 1080
WINDOW_MIN_HEIGHT = 680
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 780
