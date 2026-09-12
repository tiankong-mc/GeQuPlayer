# MeloBox

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

### 🎼 桌面歌词
- **透明无边框**悬浮窗，置顶显示
- **逐字染色**卡拉OK效果（有逐字 LRC 时自动启用）
- 鼠标**直接拖动**换位置，滚轮调字号
- **一键锁定**：锁定后鼠标穿透，不挡其他窗口操作
- 启动状态记忆，下次打开保持上次的显示/隐藏

### 📚 本地音乐库
- 扫描指定目录下的 `.mp3` 和 `.lrc` 文件
- **下载的歌单自动生成 `.m3u` 播放列表**，在"本地音乐"面板可直接一键顺序播放
- 支持多歌单并存、右键删除/打开位置

### 🔀 播放队列
- 四种播放模式：**列表循环** / **单曲循环** / **顺序播放** / **随机播放**
- 上一首 / 下一首按钮
- 播放模式状态跨会话保存

### ⚙️ 其它
- 深色主题，现代界面
- 可自定义**下载目录**和**缓存目录**
- 缓存管理：查看大小、清空、切换位置
- SQLite 记录下载历史

---



## 🚀 快速开始

### 方式一：使用安装包（推荐普通用户）

从 [Releases](https://github.com/yourname/MeloBox/releases) 页面下载最新的 `MeloBox_Setup.exe`，双击安装即可。

安装程序会引导你设置：
- 软件安装位置
- 缓存目录
- 下载目录

### 方式二：从源码运行（开发者）

**环境要求**：Python 3.10+，Windows 10/11

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/MeloBox.git
cd MeloBox

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器内核（首次运行需要）
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
python -m playwright install chromium

# 4. 启动
python main.py
