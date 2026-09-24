# GeQuPlayer

> 🎵 一个基于 [gequbao.com](https://www.gequbao.com) 的轻量级 Windows 音乐播放器
>
> 在线搜索 · 批量下载 · 桌面逐字歌词 · 本地歌单管理

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

---

## ✨ 特性

### 🎧 在线音乐
- **搜索**：直接在软件内搜索 gequbao.com 的歌曲
- **试听**：双击即播，自动播放队列中的下一首
- **批量下载**：单曲下载或整个歌单"一键下载全部"，自动附带 `.lrc` 歌词
- **歌单导入**：
  - 酷狗码（如 `17960538`）
  - 酷狗分享名片链接
  - 酷狗网页分享链接
  - QQ音乐歌单链接
  - **歌单搜索**：关键词搜酷狗/QQ音乐的歌单
- **热门榜单**：一键加载酷狗/QQ音乐的热门歌单

### ⬇️ 下载管理
- **两轮调度**：第一轮直连，失败任务冷却后自动重试
- **多线程分块下载**：8 线程并发，速度提升 5-10 倍
- **自动识别验证码**（ddddocr）
- **实时进度日志**：下载页可开启，右侧显示后台运行详情
- **歌单勾选下载**：全选 / 全不选 / 下载勾选
- **智能跳过**：gequbao 搜不到的歌曲自动跳过，不浪费重试时间
- **下载完成后自动删缓存**（正在播放的除外）
- SQLite 记录下载历史

### 🎼 桌面歌词
- **透明无边框**悬浮窗，置顶显示
- **逐字染色**卡拉OK效果（有逐字 LRC 时自动启用）
- 鼠标**直接拖动**换位置，滚轮调字号
- **一键锁定**：锁定后鼠标穿透，不挡其他窗口操作
- 启动状态记忆，下次打开保持上次的显示/隐藏

### 📚 本地音乐库
- 扫描指定目录下的 `.mp3` 和 `.lrc` 文件
- **下载的歌单自动生成 `.m3u` 播放列表**，在"本地音乐"面板可直接一键顺序播放
- **本地搜索**：实时过滤歌名/歌手，双击以搜索结果作为播放队列
- 支持多歌单并存、右键删除/打开位置

### 🔀 播放队列
- 四种播放模式：**列表循环** / **单曲循环** / **顺序播放** / **随机播放**
- 上一首 / 下一首按钮
- 播放模式状态跨会话保存

### ⚙️ 其它
- 深色主题，现代界面
- 可自定义**下载目录**和**缓存目录**
- 缓存管理：查看大小、清空、切换位置（带安全校验，防误删）
- 安装包支持自定义**安装位置 / 缓存目录 / 下载目录**

---

## 🚀 快速开始

### 方式一：使用安装包（推荐普通用户）

从 [Releases](https://github.com/tiankong-mc/GeQuPlayer/releases) 页面下载最新的 `GeQuPlayer_Setup_v1.2.0.exe`，双击安装即可。

安装程序会引导你设置：
- 软件安装位置
- 缓存目录
- 下载目录

**系统要求**：Windows 10 / 11

### 方式二：从源码运行（开发者）

**环境要求**：Python 3.10+，Windows 10/11

```bash
# 1. 克隆仓库
git clone https://github.com/tiankong-mc/GeQuPlayer.git
cd GeQuPlayer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器内核（首次运行需要）
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
python -m playwright install chromium

# 4. 启动
python main.py
```

---

## 📦 打包发布

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 打包（会自动带上 Chromium 内核，最终体积约 300-500MB）
python -m PyInstaller build.spec --noconfirm

# 3. 产物在 dist/MusicPlayer/ 目录
```

制作安装包使用 [Inno Setup](https://jrsoftware.org/isdl.php)，脚本参见 `GeQuPlayer.iss`。

---

## 🗂️ 项目结构

```
GeQuPlayer/
├── main.py                    # 入口
├── config.py                  # 全局配置
├── requirements.txt
├── build.spec                 # PyInstaller 打包配置
├── GeQuPlayer.iss             # Inno Setup 安装脚本
│
├── core/                      # 核心业务层
│   ├── audio_engine.py        # 音频播放引擎
│   ├── gequbao_api.py         # gequbao 接口封装
│   ├── playlist_parser.py     # 歌单解析
│   ├── downloader.py          # 批量下载
│   ├── local_library.py       # 本地音乐扫描 + .m3u
│   ├── lyrics_parser.py       # LRC 解析（含逐字）
│   └── playback_queue.py      # 播放队列 + 播放模式
│
├── ui/                        # 界面层
│   ├── main_window.py
│   ├── search_panel.py
│   ├── playlist_panel.py
│   ├── local_panel.py
│   ├── download_panel.py
│   ├── settings_panel.py
│   ├── player_bar.py
│   ├── lyrics_window.py
│   └── styles.py
│
├── utils/                     # 工具层
│   ├── http_client.py
│   ├── helpers.py
│   └── log_capture.py         # 日志捕获
│
└── data/                      # 数据层
    └── database.py
```

---

## 🛠️ 技术栈

| 层面 | 技术 |
|---|---|
| GUI | PyQt6 |
| 音频播放 | just-playback (基于 miniaudio) |
| 网络请求 | curl-cffi + requests |
| 浏览器自动化 | Playwright (Chromium) |
| 验证码识别 | ddddocr |
| 数据存储 | SQLite |
| 打包 | PyInstaller + Inno Setup |

---

## ⚠️ 免责声明

- 本项目仅供**个人学习和技术研究**使用。
- 请勿用于商业用途。
- 下载的音乐版权归原平台和版权方所有，请在下载后 **24 小时内删除**，或购买正版支持创作者。
- 使用本项目产生的任何法律后果由使用者自行承担。

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

特别欢迎以下类型的贡献：
- 支持更多的音乐平台音源
- 改进歌词渲染效果
- 界面美化 / 主题
- 打包 / 安装脚本优化
- Bug 修复

提交 PR 前请：
1. Fork 仓库
2. 创建分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [gequbao.com](https://www.gequbao.com) — 提供音乐搜索和播放接口
- [PyQt6](https://pypi.org/project/PyQt6/) — GUI 框架
- [just-playback](https://github.com/cheofusi/just_playback) — 音频播放
- [Playwright](https://playwright.dev/) — 浏览器自动化
- [curl-cffi](https://github.com/lexiforest/curl_cffi) — HTTP 客户端
- [ddddocr](https://github.com/sml2h3/ddddocr) — 验证码识别

---

## ⭐ Star History

如果这个项目对你有帮助，欢迎点一个 Star ⭐！

[![Star History Chart](https://api.star-history.com/svg?repos=tiankong-mc/GeQuPlayer&type=Date)](https://star-history.com/#tiankong-mc/GeQuPlayer&Date)
