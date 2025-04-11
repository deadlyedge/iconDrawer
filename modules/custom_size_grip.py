from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QMouseEvent, QPaintEvent, QPainter, QColor


class CustomSizeGrip(QWidget):
    """
    一个自定义的大小调整手柄部件，允许用户通过拖动来调整父部件的大小。
    """

    resized = Signal(QPoint)  # 发出包含大小增量的信号
    resizeStarted = Signal()
    resizeFinished = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedSize(16, 16)  # 设置手柄的固定大小
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        # self.setStyleSheet("border-bottom-right-radius: 5px")
        self._is_resizing = False
        self._start_mouse_pos: QPoint | None = None
        self._start_widget_geo: QRect | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        当鼠标按下时开始调整大小的操作。
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_resizing = True
            self.resizeStarted.emit()
            # 将起始鼠标位置映射到父部件的父部件坐标系（通常是窗口）
            self._start_mouse_pos = event.globalPosition().toPoint()
            # 获取父部件（DrawerContentWidget的main_visual_container）的几何形状
            parent = self.parentWidget()
            if parent:
                # 我们需要调整的是 DrawerContentWidget 的大小，它是 self.parentWidget() 的父部件
                top_level_widget = parent.parentWidget()
                if top_level_widget:
                    self._start_widget_geo = top_level_widget.geometry()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        当鼠标移动时处理调整大小的逻辑。
        """
        if self._is_resizing and self._start_mouse_pos and self._start_widget_geo:
            # 计算鼠标移动的增量
            delta = event.globalPosition().toPoint() - self._start_mouse_pos

            # 计算新的几何形状
            new_geo = QRect(self._start_widget_geo)
            new_width = self._start_widget_geo.width() + delta.x()
            new_height = self._start_widget_geo.height() + delta.y()

            # 应用最小尺寸约束 (如果需要，可以从父部件获取)
            parent = self.parentWidget()
            top_level_widget = parent.parentWidget() if parent else None
            if top_level_widget:
                min_width = top_level_widget.minimumWidth()
                min_height = top_level_widget.minimumHeight()
                new_width = max(new_width, min_width)
                new_height = max(new_height, min_height)

            new_geo.setWidth(new_width)
            new_geo.setHeight(new_height)

            # 调整父部件（DrawerContentWidget）的大小
            if top_level_widget:
                top_level_widget.setGeometry(new_geo)

            # 发出包含增量的信号（如果需要）
            # self.resized.emit(delta) # Signal currently unused, keep commented
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        当鼠标释放时结束调整大小的操作。
        """
        if event.button() == Qt.MouseButton.LeftButton and self._is_resizing:
            self._is_resizing = False
            self._start_mouse_pos = None
            self._start_widget_geo = None
            self.resizeFinished.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        绘制手柄的外观。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a white filled triangle pointing to the bottom right
        painter.setBrush(QColor(Qt.GlobalColor.white))
        painter.setPen(Qt.GlobalColor.white)

        # Define the points of the triangle
        points = [
            QPoint(0, self.height()),  # Bottom left
            QPoint(self.width(), self.height()),  # Bottom right
            QPoint(self.width(), 0),  # Top right
        ]
        painter.drawPolygon(points)

        painter.end()
