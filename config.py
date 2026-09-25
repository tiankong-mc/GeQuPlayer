"""全局配置"""
import os
import tempfile
from pathlib import Path


# ============================================================
#  应用信息
# ============================================================
APP_NAME = "GeQuPlayer"
APP_VERSION = "1.2.3"
APP_AUTHOR = "tiankong"
APP_GITHUB = "https://github.com/tiankong-mc/GeQuPlayer"


# ============================================================
#  路径
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "music.db"
CONFIG_PATH = DATA_DIR / "config.json"


# ============================================================
#  下载目录
# ============================================================
# 默认下载目录（用户在设置里可改）
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Music" / "GeQuPlayer")

# 下载目录的子文件夹
DOWNLOAD_MP3_SUBDIR = "MP3"
DOWNLOAD_LRC_SUBDIR = "LRC"


# ============================================================
#  缓存目录安全配置
# ============================================================
# 用户选择的缓存根目录下，程序固定使用这个子目录
# 防止用户误选桌面/文档导致清空时误删
CACHE_SUBDIR_NAME = "GeQuPlayerCache"

# 缓存目录标识文件（清理时用于验证）
CACHE_MARKER_FILE = ".gequplayer_cache"


# ============================================================
#  用户可调参数（首次启动写入 config.json）
# ============================================================
DEFAULT_CONCURRENT_TASKS = 4        # 同时下载数（1-10）
DEFAULT_LYRICS_MODE = "line"        # "line" 逐行 / "word" 逐字


# ============================================================
#  gequbao 相关
# ============================================================
GEQUBAO_BASE = "https://www.gequbao.com"
GEQUBAO_API_BASE = "https://www.gequbao.net"
GEQUBAO_SEARCH = GEQUBAO_BASE + "/s/{keyword}"
GEQUBAO_DETAIL = GEQUBAO_BASE + "/music/{song_id}"
GEQUBAO_PLAY_API = GEQUBAO_API_BASE + "/api/play-url"

# 兼容旧命名
GEQUBAO_PLAY_URL = GEQUBAO_BASE + "/api/play_url"
GEQUBAO_DOWNLOAD_URL = GEQUBAO_BASE + "/api/download"
GEQUBAO_LYRICS_URL = GEQUBAO_BASE + "/api/lyric"


# ============================================================
#  网络请求
# ============================================================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20


# ============================================================
#  下载参数
# ============================================================
DOWNLOAD_WAIT_SECONDS = 30          # 免费下载等待时间（gequbao 页面提示）
DOWNLOAD_CHUNK = 64 * 1024          # 分块大小


# ============================================================
#  UI 尺寸
# ============================================================
WINDOW_MIN_WIDTH = 1080
WINDOW_MIN_HEIGHT = 680
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 780


# ============================================================
#  GitHub 更新镜像（依次尝试）
# ============================================================
UPDATE_MIRRORS = [
    "https://ghproxy.com/",
    "https://ghproxy.net/",
    "https://gh.api.99988866.xyz/",
    "https://gh.llkk.cc/",
    "https://gitproxy.click/",
]

UPDATE_API = (
    f"https://api.github.com/repos/tiankong-mc/GeQuPlayer/releases/latest"
)


# ============================================================
#  兼容旧引用（早期代码用的变量名）
# ============================================================
DEFAULT_CACHE_DIR = str(Path(tempfile.gettempdir()) / CACHE_SUBDIR_NAME)
