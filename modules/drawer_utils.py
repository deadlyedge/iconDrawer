import logging  # Import logging
from PySide6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QWidget,
    QPushButton,
)  # Added QPushButton
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt, QSize
from typing import Protocol, Any


def truncate_text(text: str, label: QLabel, available_width: int) -> str:
    """
    根据可用宽度截断文本以适应显示 (最多 2 行)。
    """
    fm = QFontMetrics(label.font())
    if available_width <= 0:
        available_width = 50  # Default small width if calculation fails

    # Try eliding in one line first
    elided_line1 = fm.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
    # Check if the elided text fits and is the full text (no elision happened)
    # or if the original text already fits
    if (
        fm.boundingRect(elided_line1).width() <= available_width
        and "\n" not in elided_line1
    ):
        if elided_line1 == text:
            return text  # Original text fits in one line

    # If one line doesn't fit or elision happened, try two lines
    # Estimate characters per line
    avg_char_width = fm.averageCharWidth()
    if avg_char_width <= 0:
        avg_char_width = 6  # Estimate if calculation fails
    chars_per_line = max(1, available_width // avg_char_width)

    # Allow roughly two lines worth of characters before forced truncation with "..."
    max_chars_two_lines = chars_per_line * 2
    if len(text) > max_chars_two_lines:
        # Truncate and add ellipsis
        # The -3 accounts for the length of "..."
        truncated_text = text[: max_chars_two_lines - 3] + "..."
    else:
        # Text is short enough for two lines potentially, let QLabel handle wrapping/eliding
        # Or it might fit exactly within the estimated two lines
        truncated_text = text

    # Note: This approach prioritizes showing *some* text over perfect two-line elision.
    # For true two-line elision, more complex logic involving QStaticText or manual
    # line breaking and measurement would be needed. QLabel's wordWrap should handle
    # the display part if the text isn't excessively long.
    return truncated_text


def calculate_available_label_width(
    container_widget: QWidget,
    header_layout: QHBoxLayout,
    icon_label: QLabel,
    refresh_button: QPushButton,
    close_button: QPushButton,
) -> int:
    """
    计算 header 中 folder_label 的可用宽度。
    需要传入主容器、头部布局以及头部内的图标、刷新按钮和关闭按钮部件。
    """
    # Restore original calculation:
    if (
        not container_widget
        or not header_layout
        or not icon_label
        or not refresh_button
        or not close_button
    ):  # Added refresh_button check
        logging.warning(
            "calculate_available_label_width: Missing required widgets/layout."
        )
        return 100  # Default if widgets are missing

    # Get total width available for the header layout
    header_total_width = container_widget.width()
    header_margins = header_layout.contentsMargins()
    header_available_width = (
        header_total_width - header_margins.left() - header_margins.right()
    )

    # Get widths of fixed elements and spacing within the header layout
    refresh_button_width = (
        refresh_button.sizeHint().width()
        if refresh_button.width() <= 0
        else refresh_button.width()
    )
    close_button_width = (
        close_button.sizeHint().width()
        if close_button.width() <= 0
        else close_button.width()
    )
    # header_spacing applies between folder_container and refresh_button, and between refresh_button and close_button
    header_spacing = header_layout.spacing()

    # Get widths/spacing within the folder_container (which holds the icon and label)
    folder_container = icon_label.parentWidget()
    if not folder_container:
        logging.warning(
            "calculate_available_label_width: Icon label has no parent widget."
        )
        return 100  # Safety check
    folder_layout = folder_container.layout()
    if not folder_layout:
        logging.warning(
            "calculate_available_label_width: Folder container has no layout."
        )
        return 100  # Safety check

    folder_margins = folder_layout.contentsMargins()
    folder_spacing = folder_layout.spacing()  # Space between icon and label
    icon_width = (
        icon_label.sizeHint().width() if icon_label.width() <= 0 else icon_label.width()
    )

    # Calculate available width for the label directly
    # Total header available width
    # - Width of refresh button
    # - Width of close button
    # - Space between folder_container and refresh_button
    # - Space between refresh_button and close_button
    # - Left margin inside folder_container
    # - Width of icon inside folder_container
    # - Space between icon and label inside folder_container
    # - Right margin inside folder_container
    available_width = (
        header_available_width
        - refresh_button_width  # Use refresh button width
        - close_button_width  # Use close button width
        - header_spacing * 2  # Two spaces: container-refresh, refresh-close
        - folder_margins.left()
        - icon_width
        - folder_spacing
        - folder_margins.right()
    )

    # Add a small buffer for safety/aesthetics
    available_width -= 5

    return max(20, available_width)  # Ensure a minimum width


# === 内容组件接口协议 ===
class IDrawerContent(Protocol):
    # 内容刷新
    def update_content(self, path: str) -> None: ...
    # QWidget 基础方法
    def resize(self, size: QSize) -> None: ...
    def move(self, x: int, y: int) -> None: ...
    def setVisible(self, visible: bool) -> None: ...
    def isVisible(self) -> bool: ...
    def setObjectName(self, name: str) -> None: ...
    def setMinimumSize(self, w: int, h: int) -> None: ...
    def raise_(self) -> None: ...
    def size(self) -> QSize: ...

    # Qt 信号（属性）
    closeRequested: Any
    resizeFinished: Any
    sizeChanged: Any
