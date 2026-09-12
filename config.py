"""全局配置"""
import os
from pathlib import Path

APP_NAME = "MusicPlayer"
APP_VERSION = "0.1.0"

# 路径
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "music.db"
CONFIG_PATH = DATA_DIR / "config.json"

# 默认下载目录
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Music" / "MusicPlayer")

# gequbao 相关
GEQUBAO_BASE = "https://www.gequbao.net"
GEQUBAO_SEARCH = GEQUBAO_BASE + "/s/{keyword}"
GEQUBAO_PLAY_URL = GEQUBAO_BASE + "/api/play-url"  # 更新为新的 POST 地址
GEQUBAO_DOWNLOAD_URL = GEQUBAO_BASE + "/api/download" # 这个地址也可能已变更，暂时保留
GEQUBAO_LYRICS_URL = GEQUBAO_BASE + "/api/lyric"      # 这个地址也可能已变更，暂时保留


# 请求
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20

# 下载
DOWNLOAD_WAIT_SECONDS = 30   # 免费下载等待时间（gequbao 页面提示一般 30s）
DOWNLOAD_CHUNK = 64 * 1024

# UI
WINDOW_MIN_WIDTH = 1080
WINDOW_MIN_HEIGHT = 680
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 780
