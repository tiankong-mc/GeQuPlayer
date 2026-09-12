"""深色主题 QSS"""
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

QPushButton {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 7px 16px;
    color: #e6e6e6;
}

QPushButton:hover {
    background-color: #2c2d33;
    border-color: #3a3b42;
}

QPushButton:pressed {
    background-color: #1f2024;
}

QPushButton#PrimaryButton {
    background-color: #1db954;
    border: none;
    color: #0e0f12;
    font-weight: bold;
}

QPushButton#PrimaryButton:hover {
    background-color: #24d162;
}

QPushButton#PrimaryButton:disabled {
    background-color: #2e4d3a;
    color: #7c8a80;
}

QPushButton#IconButton {
    padding: 5px 10px;
    min-width: 34px;
}

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

QComboBox {
    background-color: #232428;
    border: 1px solid #2e2f35;
    border-radius: 8px;
    padding: 6px 10px;
    color: #e6e6e6;
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
"""


def apply_style(app: QApplication):
    app.setStyleSheet(QSS)
