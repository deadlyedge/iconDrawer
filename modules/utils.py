import logging
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt


def truncate_text(text: str, label: QLabel, available_width: int) -> str:
    """
    根据可用宽度截断文本以适应显示 (最多 2 行)。
    """
    fm = QFontMetrics(label.font())
    if available_width <= 0:
        available_width = 50  # 默认小宽度

    elided_line1 = fm.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
    if (
        fm.boundingRect(elided_line1).width() <= available_width
        and "\n" not in elided_line1
    ):
        if elided_line1 == text:
            return text  # 原文一行可显示

    avg_char_width = fm.averageCharWidth() or 6
    chars_per_line = max(1, available_width // avg_char_width)
    max_chars_two_lines = chars_per_line * 2

    if len(text) > max_chars_two_lines:
        truncated_text = text[: max_chars_two_lines - 3] + "..."
    else:
        truncated_text = text

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
    需要传入主容器、头部布局及图标、刷新按钮和关闭按钮部件。
    """
    if not all(
        [container_widget, header_layout, icon_label, refresh_button, close_button]
    ):
        logging.warning(
            "calculate_available_label_width: Missing required widgets/layout."
        )
        return 100

    header_total_width = container_widget.width()
    header_margins = header_layout.contentsMargins()
    header_available_width = (
        header_total_width - header_margins.left() - header_margins.right()
    )

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
    header_spacing = header_layout.spacing()

    folder_container = icon_label.parentWidget()
    if not folder_container:
        logging.warning(
            "calculate_available_label_width: Icon label has no parent widget."
        )
        return 100
    folder_layout = folder_container.layout()
    if not folder_layout:
        logging.warning(
            "calculate_available_label_width: Folder container has no layout."
        )
        return 100

    folder_margins = folder_layout.contentsMargins()
    folder_spacing = folder_layout.spacing()
    icon_width = (
        icon_label.sizeHint().width() if icon_label.width() <= 0 else icon_label.width()
    )

    available_width = (
        header_available_width
        - refresh_button_width
        - close_button_width
        - header_spacing * 2
        - folder_margins.left()
        - icon_width
        - folder_spacing
        - folder_margins.right()
        - 5  # buffer
    )

    return max(20, available_width)
