# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - GeQuPlayer v1.2.2
使用：
    python -m PyInstaller build.spec --noconfirm
产物：
    dist/MusicPlayer/MusicPlayer.exe
"""
import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []


# ============================================================
#  1. 图标 + 资源目录
# ============================================================
if os.path.exists("myicon.ico"):
    datas += [("myicon.ico", ".")]
    print("[build] bundled icon: myicon.ico")
else:
    print("[build] 警告：找不到 myicon.ico，任务栏图标将使用默认")

if os.path.isdir("assets"):
    datas += [("assets", "assets")]
    print("[build] bundled assets directory")
else:
    print("[build] 警告：找不到 assets 目录（SVG 图标将缺失）")


# ============================================================
#  2. 第三方库
# ============================================================
for pkg in ("curl_cffi", "playwright", "just_playback", "ddddocr"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
        print(f"[build] collected {pkg}")
    except Exception as e:
        print(f"[build] collect {pkg} warning: {e}")


# ============================================================
#  3. Playwright 浏览器内核
# ============================================================
pw_cache = os.path.expanduser("~/AppData/Local/ms-playwright")
if os.path.isdir(pw_cache):
    for item in os.listdir(pw_cache):
        full = os.path.join(pw_cache, item)
        if not os.path.isdir(full):
            continue
        low = item.lower()
        if "chromium" in low or "ffmpeg" in low:
            datas += [(full, f"ms-playwright/{item}")]
            print(f"[build] bundled playwright browser: {item}")
else:
    print("[build] 警告：找不到 Playwright 浏览器目录，用户首次运行需自行下载")


# ============================================================
#  4. 项目模块（保险起见显式声明）
# ============================================================
hiddenimports += [
    # core
    "core.audio_engine",
    "core.gequbao_api",
    "core.lyrics_parser",
    "core.local_library",
    "core.playlist_parser",
    "core.downloader",
    "core.playback_queue",
    # ui
    "ui.main_window",
    "ui.search_panel",
    "ui.playlist_panel",
    "ui.local_panel",
    "ui.download_panel",
    "ui.settings_panel",
    "ui.player_bar",
    "ui.lyrics_window",
    "ui.about_dialog",
    "ui.update_dialog",
    "ui.styles",
    # utils
    "utils.helpers",
    "utils.http_client",
    "utils.log_capture",
    "utils.icon_helper",
    "utils.updater",
    # data
    "data.database",
]


# ============================================================
#  5. 初始 data 目录
# ============================================================
if os.path.isdir("data"):
    datas += [("data", "data")]
    print("[build] bundled data directory")


# ============================================================
#  6. Analysis
# ============================================================
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "numpy.testing",
        "PIL.ImageQt",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)


# ============================================================
#  7. EXE
# ============================================================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MusicPlayer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="myicon.ico" if os.path.exists("myicon.ico") else None,
)


# ============================================================
#  8. COLLECT
# ============================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MusicPlayer",
)