"""The desktop landing page and its persisted recent-project list."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .branding import APPLICATION_DESCRIPTION, bind_application_icon, logo_pixmap

# The palette echoes the editor's dark chrome with the product's warm accent.
_BACKGROUND_TOP = QColor("#1b222c")
_BACKGROUND_BOTTOM = QColor("#0e131a")
_PANEL = "#1a212b"
_PANEL_HOVER = "#212b37"
_PANEL_BORDER = "#2a3441"
_TEXT = "#e8ecf1"
_MUTED = "#8b98a8"
_ACCENT = "#edc398"
_ACCENT_HOVER = "#f7d6b3"
_ACCENT_TEXT = "#20242a"


class RecentProjects:
    """Remember successful opens and saves without dropping missing files."""

    KEY = "welcome/recentProjects"
    LIMIT = 10

    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = (settings if settings is not None
                         else QSettings("Stavellum", "Stavellum"))

    @staticmethod
    def _absolute(path: str) -> str:
        return os.path.abspath(os.path.expanduser(path))

    def paths(self) -> list[str]:
        raw = self.settings.value(self.KEY, [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, (list, tuple)):
            return []
        result: list[str] = []
        seen: set[str] = set()
        for value in raw:
            if not isinstance(value, str) or Path(value).suffix.lower() != ".stproj":
                continue
            path = self._absolute(value)
            key = os.path.normcase(path)
            if key not in seen:
                result.append(path)
                seen.add(key)
            if len(result) == self.LIMIT:
                break
        return result

    def record(self, path: str) -> None:
        if Path(path).suffix.lower() != ".stproj":
            return
        absolute = self._absolute(path)
        key = os.path.normcase(absolute)
        paths = [absolute, *(p for p in self.paths() if os.path.normcase(p) != key)]
        self.settings.setValue(self.KEY, paths[:self.LIMIT])
        self.settings.sync()


class _BrandHeader(QWidget):
    """Logo mark, wordmark and tagline; owns the chosen logo pixmap for tests."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logo = logo_pixmap()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.logo_label = QLabel()
        self.logo_label.setPixmap(self._logo.scaled(
            64, 64, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.logo_label)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.title_label = QLabel("Stavellum")
        title_font = self.title_label.font()
        title_font.setPointSize(23)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)
        self.title_label.setFont(title_font)
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)
        chip_row.addWidget(self.title_label)
        self.version_chip = QLabel(f"v{__version__}")
        self.version_chip.setObjectName("VersionChip")
        chip_row.addWidget(self.version_chip)
        chip_row.addStretch(1)
        titles.addLayout(chip_row)
        self.tagline_label = QLabel(APPLICATION_DESCRIPTION)
        self.tagline_label.setObjectName("Tagline")
        titles.addWidget(self.tagline_label)
        layout.addLayout(titles)
        layout.addStretch(1)
        # The header band doubles as the drag area; text must not eat clicks.
        for child in (self, self.logo_label, self.title_label,
                      self.tagline_label, self.version_chip):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class _StaffArt:
    """Static painter helpers for the right-side decorative score art."""

    @staticmethod
    def paint(painter: QPainter, width: int, height: int) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        glow = QRadialGradient(QPointF(width * 0.82, height * 0.36), width * 0.45)
        glow.setColorAt(0.0, QColor(88, 140, 255, 34))
        glow.setColorAt(0.55, QColor(88, 140, 255, 12))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(QRectF(0, 0, width, height), glow)
        # Five staff lines flowing down the right side of the page.
        stroke = QLinearGradient(width * 0.52, 0, width, 0)
        stroke.setColorAt(0.0, QColor(232, 236, 241, 0))
        stroke.setColorAt(0.45, QColor(232, 236, 241, 34))
        stroke.setColorAt(1.0, QColor(232, 236, 241, 10))
        painter.setPen(QPen(stroke, 1.4))
        for index in range(5):
            offset = index * 15
            line = QPainterPath()
            start_y = height * (0.16 + 0.012 * index)
            line.moveTo(width * 0.50, start_y + offset * 0.4)
            line.cubicTo(width * 0.68, start_y - 60 + offset,
                         width * 0.80, height * 0.62 + offset,
                         width + 24, height * (0.52 + 0.05 * index) + offset)
            painter.drawPath(line)
        # A few luminous noteheads riding those lines.
        notes = ((0.62, 0.24, 5.2), (0.70, 0.33, 4.2), (0.78, 0.47, 5.8),
                 (0.86, 0.30, 3.6), (0.92, 0.58, 4.6))
        for progress_x, progress_y, radius in notes:
            x, y = width * progress_x, height * progress_y
            halo = QRadialGradient(QPointF(x, y), radius * 3.2)
            halo.setColorAt(0.0, QColor(237, 195, 152, 90))
            halo.setColorAt(1.0, QColor(237, 195, 152, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(QPointF(x, y), radius * 3.2, radius * 3.2)
            painter.setBrush(QColor(240, 208, 170, 215))
            painter.drawEllipse(QPointF(x, y), radius, radius)
        painter.restore()


class WelcomePage(QWidget):
    """Frameless landing window; MainWindow owns document and application lifetime."""

    new_requested = Signal()
    open_requested = Signal()
    resume_requested = Signal()
    project_requested = Signal(str)
    demo_requested = Signal()
    close_requested = Signal()
    cancel_task_requested = Signal()

    _GUIDE_SECTIONS = (
        ("从来源到谱面", "创建新工程，选择 FLP 或 MIDI；可选原曲音频，再选择自动处理方案。"),
        ("检查来源与时间", "导入默认使用第一个 Arrangement。进入编辑器后可调整编曲、速度、拍号和音频同步；FLP 未确认固定时钟时，需人工核对速度与拍号。"),
        ("整理分谱", "检查建议的乐器分组，在分谱设置中调整音符简化、八度移位和演奏法识别。"),
        ("预览与导出", "生成谱面预览，保存 .stproj 工程，或导出分谱和滚动谱视频。"),
    )
    _ABOUT_SECTIONS = (
        (f"Stavellum  {__version__}", APPLICATION_DESCRIPTION),
        ("一个工程，完整保留", "工程保存来源信息、分谱、原曲音频路径和渲染设置，便于继续编辑和再次导出。"),
        ("开源许可", "Stavellum 使用 GNU GPL v3 或更新版本。第三方库与字体保留各自的许可证；完整文本及来源随发行包提供。"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("欢迎 · Stavellum")
        bind_application_icon(self)
        self.resize(1060, 720)
        self.setMinimumSize(900, 620)
        self._allow_close = False
        self._busy = False
        self._has_document = False
        self.setObjectName("WelcomePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget#WelcomePage QWidget {{ color: {_TEXT}; font-size: 13px; }}
            QLabel#Tagline {{ color: {_MUTED}; }}
            QLabel#VersionChip {{
                color: {_ACCENT}; border: 1px solid rgba(237, 195, 152, 90);
                border-radius: 9px; padding: 1px 9px; font-size: 11px;
            }}
            QLabel#SectionHeading {{
                color: {_MUTED}; font-size: 12px;
                letter-spacing: 2px;
            }}
            QWidget#WelcomePage QPushButton {{
                color: {_TEXT}; background: {_PANEL}; border: 1px solid {_PANEL_BORDER};
                border-radius: 8px; padding: 9px 16px;
            }}
            QWidget#WelcomePage QPushButton:hover {{ background: {_PANEL_HOVER}; }}
            QWidget#WelcomePage QPushButton:disabled {{ color: #66717e; }}
            QWidget#WelcomePage QPushButton:disabled:hover {{ background: {_PANEL}; }}
            QPushButton#CreateProject {{
                color: {_ACCENT_TEXT}; background: {_ACCENT}; border-color: {_ACCENT};
                font-size: 14px; font-weight: 600; padding: 11px 26px;
            }}
            QPushButton#CreateProject:hover {{ background: {_ACCENT_HOVER}; }}
            QPushButton#CreateProject:disabled {{
                color: #6d6355; background: #4a4237; border-color: #4a4237;
            }}
            QPushButton#OpenProject {{ font-size: 14px; padding: 11px 22px; }}
            QPushButton#LinkButton {{
                background: transparent; border: 0; color: {_MUTED}; padding: 4px 2px;
            }}
            QPushButton#LinkButton:hover {{ color: {_TEXT}; }}
            QPushButton#AccentLink {{
                background: transparent; border: 0; color: {_ACCENT}; padding: 4px 2px;
            }}
            QPushButton#AccentLink:hover {{ color: {_ACCENT_HOVER}; }}
            QToolButton#WindowButton {{
                background: transparent; border: 0; border-radius: 7px;
                color: {_MUTED}; font-size: 13px; padding: 3px 9px;
            }}
            QToolButton#WindowButton:hover {{ background: {_PANEL_HOVER}; color: {_TEXT}; }}
            QListWidget#RecentList {{
                background: transparent; border: 0; outline: 0;
            }}
            QListWidget#RecentList::item {{
                background: {_PANEL}; border: 1px solid {_PANEL_BORDER};
                border-radius: 10px; padding: 10px 14px; margin: 3px 0;
            }}
            QListWidget#RecentList::item:hover {{ background: {_PANEL_HOVER}; }}
            QListWidget#RecentList::item:selected {{
                background: #232e3b; border: 1px solid rgba(237, 195, 152, 130);
            }}
            QProgressBar {{
                background: {_PANEL}; border: 1px solid {_PANEL_BORDER};
                border-radius: 4px; max-height: 6px;
            }}
            QProgressBar::chunk {{ background: {_ACCENT}; border-radius: 4px; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.pages.addWidget(self._build_main_page())
        self.pages.addWidget(self._text_page(self._GUIDE_SECTIONS, "使用指南"))
        self.pages.addWidget(self._text_page(self._ABOUT_SECTIONS, "关于"))
        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(18, 18)
        self._grip.setStyleSheet("background: transparent;")

    # --- painting and window chrome -------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0.0, _BACKGROUND_TOP)
        background.setColorAt(1.0, _BACKGROUND_BOTTOM)
        painter.fillRect(self.rect(), background)
        _StaffArt.paint(painter, self.width(), self.height())

    def mousePressEvent(self, event) -> None:
        position = event.position()
        # Drag from the header band or the decorative right zone; interactive
        # widgets swallow their own clicks before this handler runs.
        decorative = position.x() > self.width() - 320
        if (event.button() == Qt.MouseButton.LeftButton
                and (position.y() < 104 or decorative)
                and self.windowHandle() is not None):
            self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def _window_button(self, glyph: str, tip: str, handler) -> QToolButton:
        button = QToolButton()
        button.setObjectName("WindowButton")
        button.setText(glyph)
        button.setToolTip(tip)
        button.clicked.connect(handler)
        return button

    def _close(self) -> None:
        self.close()

    # --- page construction -----------------------------------------------

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        page.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 26, 26, 14)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.header = _BrandHeader()
        header.addWidget(self.header, 1)
        self.minimize_button = self._window_button("—", "最小化", self.showMinimized)
        self.close_button = self._window_button("✕", "关闭", self._close)
        header.addWidget(self.minimize_button)
        header.addWidget(self.close_button)
        layout.addLayout(header)
        layout.addSpacing(26)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.new_button = QPushButton("新建工程")
        self.new_button.setObjectName("CreateProject")
        self.new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_button.clicked.connect(lambda: self._emit(self.new_requested))
        self.open_button = QPushButton("打开工程…")
        self.open_button.setObjectName("OpenProject")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.clicked.connect(lambda: self._emit(self.open_requested))
        actions.addWidget(self.new_button)
        actions.addWidget(self.open_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addSpacing(10)

        links = QHBoxLayout()
        links.setSpacing(18)
        self.demo_button = QPushButton("生成示例工程")
        self.demo_button.setObjectName("AccentLink")
        self.demo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.demo_button.clicked.connect(lambda: self._emit(self.demo_requested))
        self.resume_button = QPushButton("返回编辑器")
        self.resume_button.setObjectName("LinkButton")
        self.resume_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resume_button.clicked.connect(lambda: self._emit(self.resume_requested))
        self.resume_button.hide()
        links.addWidget(self.demo_button)
        links.addWidget(self.resume_button)
        links.addStretch(1)
        layout.addLayout(links)
        layout.addSpacing(24)

        heading_row = QHBoxLayout()
        self.list_heading = QLabel("最近打开")
        self.list_heading.setObjectName("SectionHeading")
        heading_row.addWidget(self.list_heading)
        heading_row.addStretch(1)
        layout.addLayout(heading_row)
        layout.addSpacing(2)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName("RecentList")
        self.recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_list.setAccessibleName("最近工程")
        self.recent_list.setSpacing(2)
        self.recent_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recent_list.itemActivated.connect(self._activate_recent)
        self.recent_list.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self.recent_list, 1)

        self.empty_label = QLabel("还没有最近工程。\n新建工程，或打开已有的 .stproj 开始。")
        self.empty_label.setObjectName("Tagline")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label, 1)

        footer = QHBoxLayout()
        self.path_label = QLabel("成功打开或保存的工程会出现在这里。")
        self.path_label.setObjectName("Tagline")
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        footer.addWidget(self.path_label, 1)
        self.selected_button = QPushButton("打开所选工程")
        self.selected_button.clicked.connect(self._activate_selection)
        self.selected_button.setEnabled(False)
        footer.addWidget(self.selected_button)
        layout.addSpacing(8)
        layout.addLayout(footer)
        layout.addSpacing(10)

        task_row = QHBoxLayout()
        task_row.setSpacing(12)
        self.task_status = QWidget()
        task_inner = QHBoxLayout(self.task_status)
        task_inner.setContentsMargins(0, 0, 0, 0)
        task_inner.setSpacing(12)
        self.job_label = QLabel("就绪")
        self.job_label.setObjectName("Tagline")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.cancel_task_button = QPushButton("取消任务")
        self.cancel_task_button.clicked.connect(self.cancel_task_requested.emit)
        task_inner.addWidget(self.job_label, 0)
        task_inner.addWidget(self.progress, 1)
        task_inner.addWidget(self.cancel_task_button, 0)
        task_row.addWidget(self.task_status, 1)
        layout.addLayout(task_row)
        self.task_status.hide()

        bottom = QHBoxLayout()
        bottom.setSpacing(18)
        guide_button = QPushButton("使用指南")
        guide_button.setObjectName("LinkButton")
        guide_button.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        about_button = QPushButton("关于")
        about_button.setObjectName("LinkButton")
        about_button.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        bottom.addWidget(guide_button)
        bottom.addWidget(about_button)
        bottom.addStretch(1)
        version = QLabel(f"Stavellum v{__version__}")
        version.setObjectName("Tagline")
        bottom.addWidget(version)
        layout.addLayout(bottom)
        return page

    def _text_page(self, sections: tuple[tuple[str, str], ...], title: str) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QWidget()
        content.setObjectName("TextPage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 26, 30, 20)
        layout.setSpacing(14)
        back = QPushButton("← 返回")
        back.setObjectName("AccentLink")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        layout.addWidget(back)
        heading = QLabel(title)
        heading_font = heading.font()
        heading_font.setPointSize(18)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addSpacing(6)
        layout.addWidget(heading)
        layout.addSpacing(6)
        for section_title, text in sections:
            section = QLabel(section_title)
            font = section.font()
            font.setBold(True)
            section.setFont(font)
            section.setWordWrap(True)
            body = QLabel(text)
            body.setObjectName("Tagline")
            body.setWordWrap(True)
            layout.addWidget(section)
            layout.addWidget(body)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # --- behavior ---------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
            self.close_requested.emit()
            # The shared exit handler may approve this very close request.
            event.setAccepted(self._allow_close)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._grip.move(self.width() - 18, self.height() - 18)

    def set_recent_projects(self, paths: list[str]) -> None:
        self.recent_list.clear()
        for path in paths:
            source = Path(path)
            name = source.name
            if not source.is_file():
                name += "  （文件已移动或删除）"
            item = QListWidgetItem()
            item.setText(f"{name}\n{path}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.recent_list.addItem(item)
        self.empty_label.setVisible(not paths)
        self.recent_list.setVisible(bool(paths))
        if paths:
            self.recent_list.setCurrentRow(0)
        self._selection_changed()

    def set_has_document(self, has_document: bool) -> None:
        self._has_document = has_document
        self.resume_button.setVisible(has_document)
        self.resume_button.setEnabled(has_document and not self._busy)

    def set_busy(self, busy: bool) -> None:
        # The task bar (cancel button included) lives inside the main page,
        # so only the individual action controls are disabled — never the
        # page stack that hosts the running task's progress.
        self._busy = busy
        for control in (self.new_button, self.open_button, self.demo_button,
                        self.selected_button, self.recent_list):
            control.setEnabled(not busy)
        self.resume_button.setEnabled(self._has_document and not busy)
        self._selection_changed()

    def _emit(self, signal) -> None:
        if not self._busy:
            signal.emit()

    def _selection_changed(self, *_args) -> None:
        # Signals may arrive while the page itself is still being built.
        if not hasattr(self, "selected_button"):
            return
        item = self.recent_list.currentItem()
        self.selected_button.setEnabled(item is not None and not self._busy)
        if item is not None:
            self.path_label.setText(item.data(Qt.ItemDataRole.UserRole))
        else:
            self.path_label.setText("成功打开或保存的工程会出现在这里。")

    def _activate_recent(self, item: QListWidgetItem) -> None:
        if not self._busy:
            self.project_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _activate_selection(self) -> None:
        if (item := self.recent_list.currentItem()) is not None:
            self._activate_recent(item)
