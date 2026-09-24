"""桌面歌词悬浮窗：透明背景 + 默认可拖动 + 可锁定穿透"""
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QGuiApplication,
)
from PyQt6.QtWidgets import QWidget

from core.lyrics_parser import Lyrics


def _get_lyrics_mode() -> str:
    try:
        from utils.helpers import load_config
        cfg = load_config()
        return cfg.get("lyrics_mode", "line")
    except Exception:
        return "line"


class LyricsWindow(QWidget):
    position_changed = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._font_main = QFont("Microsoft YaHei", 26)
        self._font_main.setBold(True)
        self._font_sub = QFont("Microsoft YaHei", 14)

        self._lyrics: Optional[Lyrics] = None
        self._current_idx = -1
        self._current_time = 0.0
        self._enabled = True
        self._locked = False

        self._line_main = ""
        self._line_next = ""
        self._word_progress = 0.0

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = int(avail.width() * 0.72)
            w = max(600, min(w, 1400))
            self.resize(w, 130)
            self.move((avail.width() - w) // 2, 60)
        else:
            self.resize(800, 130)

        self._dragging = False
        self._drag_offset = QPoint()
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    # ---------- 对外接口 ----------
    def set_lyrics(self, lyrics: Lyrics):
        self._lyrics = lyrics
        self._current_idx = -1
        self._update_display()
        self.update()

    def clear(self):
        self._lyrics = None
        self._line_main = ""
        self._line_next = ""
        self.update()

    def set_time(self, t: float):
        self._current_time = t
        if not self._lyrics or self._lyrics.is_empty():
            return
        idx = self._lyrics.index_at(t)
        if idx != self._current_idx:
            self._current_idx = idx
            self._update_display()
        self._update_word_progress()
        self.update()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.setVisible(enabled)

    def is_locked(self) -> bool:
        return self._locked

    def set_locked(self, locked: bool):
        if self._locked == locked:
            return
        self._locked = locked
        pos = self.pos()
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, locked)
        self.move(pos)
        if visible and self._enabled:
            self.show()
        if locked:
            self.unsetCursor()
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    # ---------- 内部 ----------
    def _update_display(self):
        if not self._lyrics or self._lyrics.is_empty():
            self._line_main = ""
            self._line_next = ""
            return
        idx = self._current_idx
        if idx < 0:
            self._line_main = "♪ 前奏..."
            self._line_next = self._lyrics.lines[0].text if self._lyrics.lines else ""
        else:
            self._line_main = self._lyrics.lines[idx].text
            self._line_next = self._lyrics.lines[idx + 1].text \
                if idx + 1 < len(self._lyrics.lines) else ""

    def _update_word_progress(self):
        # ============ 根据配置决定逐字还是逐行 ============
        mode = _get_lyrics_mode()

        if not self._lyrics or self._current_idx < 0:
            self._word_progress = 0.0
            return

        if mode == "line":
            # 逐行模式：整行均速染色
            line = self._lyrics.lines[self._current_idx]
            t0 = line.time
            t1 = self._lyrics.lines[self._current_idx + 1].time \
                if self._current_idx + 1 < len(self._lyrics.lines) else t0 + 4.0
            self._word_progress = max(0.0, min(1.0,
                (self._current_time - t0) / (t1 - t0))) if t1 > t0 else 1.0
            return

        # 逐字模式：优先用逐字时间戳，没有则退化为行级
        line = self._lyrics.lines[self._current_idx]
        if not line.words:
            t0 = line.time
            t1 = self._lyrics.lines[self._current_idx + 1].time \
                if self._current_idx + 1 < len(self._lyrics.lines) else t0 + 4.0
            self._word_progress = max(0.0, min(1.0,
                (self._current_time - t0) / (t1 - t0))) if t1 > t0 else 1.0
            return

        words = line.words
        cur = self._current_time
        total_chars = sum(len(w[1]) for w in words)
        if total_chars == 0:
            self._word_progress = 1.0
            return
        done = 0.0
        for i, (wt, txt) in enumerate(words):
            nxt_t = words[i + 1][0] if i + 1 < len(words) else wt + 0.4
            if cur >= nxt_t:
                done += len(txt)
            elif cur >= wt:
                span = max(0.01, nxt_t - wt)
                ratio = (cur - wt) / span
                done += len(txt) * max(0.0, min(1.0, ratio))
                break
            else:
                break
        self._word_progress = max(0.0, min(1.0, done / total_chars))

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        if not self._enabled:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 110))
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 14, 14)

        fm_main = QFontMetrics(self._font_main)
        fm_sub = QFontMetrics(self._font_sub)

        total_h = fm_main.height() + fm_sub.height() + 20
        top = max(10, (self.height() - total_h) // 2)

        main_text = self._line_main or "♪"
        main_w = fm_main.horizontalAdvance(main_text)
        main_x = max(16, (self.width() - main_w) // 2)
        main_y = top + fm_main.ascent()

        painter.setFont(self._font_main)
        painter.setPen(QPen(QColor(210, 210, 210, 180)))
        painter.drawText(main_x, main_y, main_text)

        if self._word_progress > 0 and main_w > 0:
            painter.save()
            clip_w = int(main_w * self._word_progress)
            painter.setClipRect(QRect(main_x, top, clip_w, fm_main.height()))
            painter.setPen(QPen(QColor(29, 185, 84)))
            painter.drawText(main_x, main_y, main_text)
            painter.restore()

        if self._line_next:
            painter.setFont(self._font_sub)
            sub_w = fm_sub.horizontalAdvance(self._line_next)
            sub_x = max(16, (self.width() - sub_w) // 2)
            sub_y = main_y + fm_main.descent() + fm_sub.ascent() + 8
            painter.setPen(QPen(QColor(180, 180, 180, 160)))
            painter.drawText(sub_x, sub_y, self._line_next)

        painter.end()

    # ---------- 鼠标 ----------
    def mousePressEvent(self, event):
        if self._locked:
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._locked:
            event.ignore()
            return
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._locked:
            event.ignore()
            return
        if self._dragging:
            self._dragging = False
            self.position_changed.emit(self.x(), self.y())
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self._locked:
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta != 0:
            size = self._font_main.pointSize() + (1 if delta > 0 else -1)
            size = max(14, min(60, size))
            self._font_main.setPointSize(size)
            self._font_sub.setPointSize(max(10, size // 2))
            self.update()
        super().wheelEvent(event)
