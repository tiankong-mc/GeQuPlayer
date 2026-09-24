"""SVG 图标加载工具"""
import os
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer


_ICON_CACHE = {}
_ICON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "icons"
)

DEFAULT_COLOR = "#e6e6e6"   # 深色主题下的浅灰色


def get_icon(name: str, size: int = 22, color: str = None) -> QIcon:
    """
    加载 SVG 图标。
    name: 不带 .svg 后缀，例如 "play" / "pause"
    size: 图标尺寸（像素）
    color: 覆盖 SVG 里的 currentColor，默认浅灰色
    """
    if color is None:
        color = DEFAULT_COLOR

    cache_key = (name, size, color)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    svg_path = os.path.join(_ICON_DIR, f"{name}.svg")
    if not os.path.exists(svg_path):
        print(f"[icon] 未找到图标: {svg_path}", flush=True)
        return QIcon()

    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_data = f.read()

        # 替换颜色
        svg_data = svg_data.replace("currentColor", color)

        renderer = QSvgRenderer(svg_data.encode("utf-8"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        icon = QIcon(pixmap)
        _ICON_CACHE[cache_key] = icon
        return icon
    except Exception as e:
        print(f"[icon] 加载 {name} 失败: {e}", flush=True)
        return QIcon()
