"""Shared, packaged visual identity for the desktop application."""

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap

LOGO_PATH = Path(__file__).with_name("assets") / "logo.png"
APPLICATION_DESCRIPTION = "基于受支持格式的自动乐谱化与演示实用程序"


def application_icon() -> QIcon:
    return QIcon(str(LOGO_PATH))


def logo_pixmap() -> QPixmap:
    return QPixmap(str(LOGO_PATH))
