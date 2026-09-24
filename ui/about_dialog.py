"""关于对话框"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
)

from config import APP_NAME, APP_VERSION
from utils.icon_helper import get_icon


# ============================================================
#  ★★★ 这里改成你自己的内容 ★★★
# ============================================================

ABOUT_TITLE = f"{APP_NAME} {APP_VERSION}"

ABOUT_HTML = """
<h3>GeQuPlayer</h3>
<p>一个基于 gequbao.com 的轻量级 Windows 音乐播放器。</p>

<p><b>主要功能</b></p>
<ul>
  <li>在线搜索 / 试听 / 批量下载</li>
  <li>桌面逐字歌词（卡拉 OK 效果）</li>
  <li>本地音乐库 / .m3u 歌单管理</li>
  <li>四种播放模式</li>
</ul>

<p><b>开源协议</b>：MIT License</p>
<p><b>项目主页</b>：
<a href="https://github.com/tiankong-mc/GeQuPlayer">
github.com/tiankong-mc/GeQuPlayer</a></p>

<p style="color:#888; font-size:11px;">
免责声明：本项目仅供个人学习和技术研究使用。所有音乐来自 gequbao.com 的公开搜索结果，
请勿用于商业用途，下载的音乐版权归原平台所有，请在 24 小时内删除。
</p>
"""

# ============================================================


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"关于 {APP_NAME}")
        self.setMinimumSize(520, 420)
        self.setWindowIcon(get_icon("play", 32))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(14)

        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("play", 48).pixmap(48, 48))
        header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_lbl = QLabel(ABOUT_TITLE)
        title_lbl.setStyleSheet("font-size:18px; font-weight:bold; color:#ffffff;")
        sub_lbl = QLabel("基于 gequbao.com 的轻量级音乐播放器")
        sub_lbl.setStyleSheet("color:#9a9a9a; font-size:12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(ABOUT_HTML)
        browser.setStyleSheet(
            "QTextBrowser { background:#1b1c20; border:1px solid #26272c; "
            "border-radius:8px; padding:10px; color:#e6e6e6; }"
        )
        layout.addWidget(browser, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("关闭")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
