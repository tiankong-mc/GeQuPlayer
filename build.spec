# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 - MusicPlayer"""
import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# ---------- 图标 ----------
if os.path.exists("myicon_1.ico"):
    datas += [("myicon_1.ico", ".")]

# ---------- 三方库 ----------
for pkg in ("curl_cffi", "playwright", "just_playback"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
        print(f"[build] collected {pkg}")
    except Exception as e:
        print(f"[build] collect {pkg} warning: {e}")

# ---------- Playwright 浏览器内核打包 ----------
# 找到 Playwright 的浏览器缓存目录，把它一起打包
pw_cache = os.path.expanduser("~/AppData/Local/ms-playwright")
if os.path.isdir(pw_cache):
    for item in os.listdir(pw_cache):
        full = os.path.join(pw_cache, item)
        if not os.path.isdir(full):
            continue
        # 只打包 chromium 和 ffmpeg 相关的
        low = item.lower()
        if "chromium" in low or "ffmpeg" in low:
            datas += [(full, f"ms-playwright/{item}")]
            print(f"[build] bundled playwright browser: {item}")
else:
    print("[build] 警告：找不到 Playwright 浏览器目录，用户首次运行需自行下载")

# ---------- 项目模块 ----------
hiddenimports += [
    "core.audio_engine",
    "core.gequbao_api",
    "core.lyrics_parser",
    "core.local_library",
    "core.playlist_parser",
    "core.downloader",
    "ui.main_window",
    "ui.search_panel",
    "ui.playlist_panel",
    "ui.local_panel",
    "ui.download_panel",
    "ui.settings_panel",
    "ui.player_bar",
    "ui.lyrics_window",
    "ui.styles",
    "utils.helpers",
    "utils.http_client",
    "data.database",
]

# 初始 data 目录
if os.path.isdir("data"):
    datas += [("data", "data")]


# ---------- 分析 ----------
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
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
    icon="myicon_1.ico" if os.path.exists("myicon_1.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MusicPlayer",
)