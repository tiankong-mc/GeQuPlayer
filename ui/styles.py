"""深色主题 QSS（Qt 兼容版，避免语法错误）"""
from PyQt6.QtWidgets import QApplication


QSS = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow, QWidget#RootWidget {
    background-color: #17181c;
    color: #e6e6e6;
}

QWidget {
    background-color: #17181c;
    color: #e6e6e6;
}

QLabel {
    background: transparent;
    color: #cfcfcf;
}

QLabel#TitleLabel {
    font-size: 15px;
    font-weight: bold;
    color: #ffffff;
}

/* ============ 输入框 ============ */
QLineEdit {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #1db954;
}

QLineEdit:focus {
    border: 1px solid #1db954;
}

/* ============ 按钮（基础） ============ */
QPushButton {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 7px 16px;
    color: #e6e6e6;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #2c2d33;
    border-color: #3a3b42;
}

QPushButton:pressed {
    background-color: #1f2024;
}

QPushButton:disabled {
    color: #666;
    background-color: #1f2024;
    border-color: #2a2b30;
}

/* ============ 主按钮（绿色） ============ */
QPushButton#PrimaryButton {
    background-color: #1db954;
    border: 1px solid #1db954;
    color: #0e0f12;
    font-weight: bold;
}

QPushButton#PrimaryButton:hover {
    background-color: #24d162;
    border: 1px solid #24d162;
    color: #0e0f12;
}

QPushButton#PrimaryButton:pressed {
    background-color: #17a349;
    border: 1px solid #17a349;
    color: #0e0f12;
}

QPushButton#PrimaryButton:disabled {
    background-color: #2e4d3a;
    border: 1px solid #2e4d3a;
    color: #7c8a80;
}

QPushButton#IconButton {
    padding: 4px 8px;
    min-width: 30px;
}

/* ============ Tab ============ */
QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar {
    background: transparent;
    qproperty-drawBase: 0;
}

QTabBar::tab {
    background: transparent;
    color: #9a9a9a;
    padding: 10px 22px;
    margin-right: 4px;
    border-bottom: 2px solid transparent;
    font-size: 14px;
}

QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #1db954;
}

QTabBar::tab:hover:!selected {
    color: #d0d0d0;
}

/* ============ 列表 ============ */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #1b1c20;
    border: 1px solid #26272c;
    border-radius: 10px;
    color: #e6e6e6;
    outline: none;
    padding: 4px;
}

QListWidget::item {
    padding: 7px 10px;
    border-radius: 6px;
}

QListWidget::item:hover {
    background-color: #232428;
}

QListWidget::item:selected {
    background-color: #1db954;
    color: #0e0f12;
}

/* ============ 滚动条 ============ */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #3a3b42;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #4a4b54;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #3a3b42;
    border-radius: 5px;
    min-width: 24px;
}

/* ============ 滑块 ============ */
QSlider::groove:horizontal {
    height: 4px;
    background: #33343b;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #1db954;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    width: 12px;
    height: 12px;
    border-radius: 6px;
    margin: -5px 0;
}

/* ============ 下拉框 ============ */
QComboBox {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 6px 10px;
    color: #e6e6e6;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #3a3b42;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #232428;
    border: 1px solid #2e2f35;
    selection-background-color: #1db954;
    selection-color: #0e0f12;
    color: #e6e6e6;
    outline: none;
}

/* ============ 进度条 ============ */
QProgressBar {
    border: none;
    background-color: #232428;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #1db954;
    border-radius: 4px;
}

/* ============ 菜单 ============ */
QMenu {
    background-color: #1f2024;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 6px;
    color: #e6e6e6;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #1db954;
    color: #0e0f12;
}

QStatusBar {
    background: #1b1c20;
    color: #9a9a9a;
}

/* ============ 单选框（避免 gradient 语法，用 border 实现） ============ */
QRadioButton {
    color: #e6e6e6;
    background: transparent;
    padding: 4px 2px;
    spacing: 8px;
    min-height: 22px;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 8px;
    border: 2px solid #5a5b62;
    background-color: #232428;
}

QRadioButton::indicator:hover {
    border-color: #1db954;
}

QRadioButton::indicator:checked {
    /* 加粗外圈 + 白心：视觉上等于绿圈白点 */
    border: 5px solid #1db954;
    background-color: #ffffff;
    width: 8px;
    height: 8px;
    border-radius: 9px;
}

QRadioButton:disabled {
    color: #666;
}

/* ============ 复选框 ============ */
QCheckBox {
    color: #e6e6e6;
    background: transparent;
    padding: 4px 2px;
    spacing: 8px;
    min-height: 22px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #5a5b62;
    background-color: #232428;
}

QCheckBox::indicator:hover {
    border-color: #1db954;
}

QCheckBox::indicator:checked {
    border: 2px solid #1db954;
    background-color: #1db954;
}

/* ============ 数字输入框 ============ */
QSpinBox {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 6px;
    padding: 4px 6px;
    color: #ffffff;
    min-height: 22px;
    min-width: 60px;
}

QSpinBox:focus {
    border: 1px solid #1db954;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #2e2f35;
    border: none;
    width: 18px;
    border-radius: 3px;
    margin: 1px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3a3b42;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #e6e6e6;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #e6e6e6;
    width: 0;
    height: 0;
}

/* ============ 分组框 ============ */
QGroupBox {
    color: #e6e6e6;
    border: 1px solid #26272c;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 14px 14px 14px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #ffffff;
}

/* ============ 文本浏览框 ============ */
QTextBrowser, QPlainTextEdit {
    background-color: #1b1c20;
    border: 1px solid #26272c;
    border-radius: 8px;
    color: #e6e6e6;
    padding: 8px;
}

/* ============ 对话框 ============ */
QDialog {
    background-color: #17181c;
    color: #e6e6e6;
}

QMessageBox {
    background-color: #1b1c20;
}

QMessageBox QLabel {
    color: #e6e6e6;
}
"""


def apply_style(app: QApplication):
    app.setStyleSheet(QSS)
