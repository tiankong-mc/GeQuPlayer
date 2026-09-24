"""更新提示对话框"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
)


class UpdateDialog(QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发现新版本")
        self.setMinimumSize(560, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        title = QLabel(f"发现新版本 v{info.get('latest_version', '')}")
        title.setStyleSheet("font-size:17px; font-weight:bold; color:#ffffff;")
        layout.addWidget(title)

        notes = info.get("release_notes", "") or "（本次更新无详细说明）"
        # 简单处理 markdown 里的标题
        notes_html = self._md_to_html(notes)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(f"""
            <div style="color:#e6e6e6; font-size:13px; line-height:1.6;">
            {notes_html}
            </div>
        """)
        browser.setStyleSheet(
            "QTextBrowser { background:#1b1c20; border:1px solid #26272c; "
            "border-radius:8px; padding:10px; }"
        )
        layout.addWidget(browser, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_later = QPushButton("稍后再说")
        btn_later.setFixedWidth(100)
        btn_later.clicked.connect(self.reject)
        btn_row.addWidget(btn_later)

        btn_download = QPushButton("立即更新")
        btn_download.setObjectName("PrimaryButton")
        btn_download.setFixedWidth(110)
        btn_download.clicked.connect(self.accept)
        btn_row.addWidget(btn_download)

        layout.addLayout(btn_row)

    @staticmethod
    def _md_to_html(text: str) -> str:
        lines = []
        for line in text.split("\n"):
            s = line.rstrip()
            if s.startswith("### "):
                lines.append(f"<h4>{s[4:]}</h4>")
            elif s.startswith("## "):
                lines.append(f"<h3>{s[3:]}</h3>")
            elif s.startswith("# "):
                lines.append(f"<h2>{s[2:]}</h2>")
            elif s.startswith("- ") or s.startswith("* "):
                lines.append(f"<div>• {s[2:]}</div>")
            elif s.strip() == "":
                lines.append("<br>")
            else:
                lines.append(f"<div>{s}</div>")
        return "\n".join(lines)
