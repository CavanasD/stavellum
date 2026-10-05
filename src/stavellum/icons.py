"""Best-effort instrument aliases for cached, bundled SVG pictograms."""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer

from .qt import ensure_app

ICON_RESOURCES = {
    "bell": "bell-thin-100.svg",
    "drum": "drum-thin-100.svg",
    "piano": "piano-thin-100.svg",
    "keyboard": "piano-keyboard-thin-100.svg",
    "violin": "violin-thin-100.svg",
}
ICON_ALIASES = {
    "bell": "bell", "bells": "bell", "celesta": "bell",
    "glockenspiel": "bell", "music box": "bell", "tubular bells": "bell",
    "铃": "bell", "钟": "bell",
    "drum": "drum", "drums": "drum", "percussion": "drum",
    "timpani": "drum", "snare": "drum", "kick": "drum", "鼓": "drum", "打击乐": "drum",
    "piano": "piano", "grand piano": "piano", "钢琴": "piano",
    "keyboard": "keyboard", "piano keyboard": "keyboard", "electric piano": "keyboard",
    "harpsichord": "keyboard", "organ": "keyboard", "synth": "keyboard",
    "synthesizer": "keyboard", "键盘": "keyboard", "风琴": "keyboard",
    "violin": "violin", "viola": "violin", "cello": "violin",
    "double bass": "violin", "strings": "violin", "string": "violin",
    "小提琴": "violin", "中提琴": "violin", "大提琴": "violin",
    "低音提琴": "violin", "弦乐": "violin",
}


def _resource_name(kind: str) -> str | None:
    normalized = re.sub(r"[\s_-]+", " ", kind.strip().casefold().removesuffix(".svg"))
    for filename in ICON_RESOURCES.values():
        if normalized == re.sub(r"[\s_-]+", " ", filename.removesuffix(".svg")):
            return filename
    for alias in sorted(ICON_ALIASES, key=len, reverse=True):
        # English tokens avoid matching bassoon to bass. Chinese aliases may
        # appear within a section name such as 第一小提琴 or 打击乐组.
        if f" {alias} " in f" {normalized} " or (not alias.isascii() and alias in normalized):
            return ICON_RESOURCES[ICON_ALIASES[alias]]
    return None


@lru_cache(maxsize=len(ICON_RESOURCES))
def _load_icon(filename: str) -> QSvgRenderer | None:
    try:
        data = files("stavellum").joinpath("icons", filename).read_bytes()
        renderer = QSvgRenderer(data)
        if not renderer.isValid():
            return None
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        return renderer
    except (OSError, ValueError, RuntimeError):
        return None


def icon_renderer(kind: str) -> QSvgRenderer | None:
    """Return a reusable vector renderer, or None for the caller's fallback."""
    filename = _resource_name(kind)
    if filename is None:
        return None
    ensure_app()
    return _load_icon(filename)
