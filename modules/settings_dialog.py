from typing import Optional, TYPE_CHECKING, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QLabel,
    QWidget,
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal, Slot
# from PySide6.QtGui import QColor, QPalette
# from typing import Optional, TYPE_CHECKING # Import Tuple

# Forward declare MainWindow for type hints
if TYPE_CHECKING:
    from modules.main_window import MainWindow
    from modules.settings_manager import SettingsManager


class SettingsDialog(QDialog):
    # Signal to request main window background update (h, s, l, a as 0-1 floats)
    backgroundPreviewRequested = Signal(float, float, float, float)
    # Signal to apply final background color (h, s, l, a as 0-1 floats)
    backgroundApplied = Signal(float, float, float, float)
    # Signal to toggle startup setting
    startupToggled = Signal(bool)
    # Signal to request application quit
    quitApplicationRequested = Signal()

    def __init__(
        self,
        settings_manager: "SettingsManager",
        parent: Optional["MainWindow"] = None,
    ) -> None:
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.main_window_ref: Optional["MainWindow"] = (
            parent  # Keep a reference if needed
        )

        self.setWindowTitle("设置")
        self.setMinimumWidth(400)

        # Store initial values for restoration on cancel (now in CSS format)
        self.initial_background_hsla_css: Tuple[int, int, int, float] = (
            self.settings_manager.get_background_color_hsla()
        )
        self.initial_start_with_windows: bool = (
            self.settings_manager.get_start_with_windows()
        )

        self._setup_ui()
        self._connect_signals()
        self._load_initial_settings()

        # Apply initial preview without saving
        self._update_preview_and_main_window()

    def _setup_ui(self) -> None:
        """Sets up the UI elements for the dialog."""
        main_layout = QVBoxLayout(self)

        # --- Background Group ---
        background_group = QGroupBox("背景颜色 (HSLA)")
        background_layout = QVBoxLayout()
        background_layout.addSpacing(10)

        form_layout = QFormLayout()

        # Hue Slider
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(0, 359)
        self.hue_label = QLabel("0")
        hue_layout = QHBoxLayout()
        hue_layout.addWidget(self.hue_slider)
        hue_layout.addWidget(self.hue_label)
        form_layout.addRow("色相 (H):", hue_layout)

        # Saturation Slider
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 100)
        self.saturation_label = QLabel("0%")
        saturation_layout = QHBoxLayout()
        saturation_layout.addWidget(self.saturation_slider)
        saturation_layout.addWidget(self.saturation_label)
        form_layout.addRow("饱和度 (S):", saturation_layout)

        # Lightness Slider
        self.lightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.lightness_slider.setRange(0, 100)
        self.lightness_label = QLabel("0%")
        lightness_layout = QHBoxLayout()
        lightness_layout.addWidget(self.lightness_slider)
        lightness_layout.addWidget(self.lightness_label)
        form_layout.addRow("亮度 (L):", lightness_layout)

        # Alpha Slider
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_label = QLabel("100%")
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(self.alpha_slider)
        alpha_layout.addWidget(self.alpha_label)
        form_layout.addRow("透明度 (A):", alpha_layout)

        background_layout.addLayout(form_layout)

        # Preview and Value Display
        preview_layout = QHBoxLayout()
        self.color_preview = QWidget()
        self.color_preview.setMinimumSize(50, 30)
        self.color_preview.setAutoFillBackground(True)  # Important for setting palette
        self.hsla_value_label = QLabel("hsla(0, 0%, 0%, 1.0)")
        self.hsla_value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )  # Make text selectable
        preview_layout.addWidget(QLabel("预览:"))
        preview_layout.addWidget(self.color_preview)
        preview_layout.addWidget(self.hsla_value_label)
        preview_layout.addStretch()
        background_layout.addLayout(preview_layout)

        background_group.setLayout(background_layout)
        main_layout.addWidget(background_group)
        main_layout.addSpacing(10)  # Add space below background group

        # --- Startup Group ---
        startup_group = QGroupBox("启动选项")
        startup_layout = QVBoxLayout()
        startup_layout.addSpacing(10)

        self.startup_checkbox = QCheckBox("开机时自动启动")
        startup_layout.addWidget(self.startup_checkbox)
        startup_group.setLayout(startup_layout)
        main_layout.addWidget(startup_group)
        # Optionally add space below the last group if needed before buttons
        # main_layout.addSpacing(10)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox()
        # Add standard OK and Cancel buttons
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        # Add custom Quit button
        self.quit_button = self.button_box.addButton(
            "退出程序", QDialogButtonBox.ButtonRole.DestructiveRole
        )

        main_layout.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        """Connects signals for sliders, checkbox, and buttons."""
        # Sliders update labels and preview
        self.hue_slider.valueChanged.connect(self._update_labels_and_preview)
        self.saturation_slider.valueChanged.connect(self._update_labels_and_preview)
        self.lightness_slider.valueChanged.connect(self._update_labels_and_preview)
        self.alpha_slider.valueChanged.connect(self._update_labels_and_preview)

        # Buttons
        self.button_box.accepted.connect(self.accept)  # OK button
        self.button_box.rejected.connect(self.reject)  # Cancel button
        # Connect the custom Quit button
        if self.quit_button:  # Ensure button was created
            self.quit_button.clicked.connect(self.quitApplicationRequested.emit)

    def _load_initial_settings(self) -> None:
        """Loads settings from SettingsManager (CSS format) and sets initial widget states."""
        h_css, s_css, l_css, a_float = self.initial_background_hsla_css
        self.hue_slider.setValue(h_css)  # 0-359
        self.saturation_slider.setValue(s_css)  # 0-100
        self.lightness_slider.setValue(l_css)  # 0-100
        self.alpha_slider.setValue(round(a_float * 100))  # 0-100

        self.startup_checkbox.setChecked(self.initial_start_with_windows)

        # Update labels and preview to reflect loaded values
        self._update_labels_and_preview()

    @Slot()
    def _update_labels_and_preview(self) -> None:
        """Updates the HSLA labels and color preview widget."""
        h = self.hue_slider.value()
        s = self.saturation_slider.value()
        l = self.lightness_slider.value()
        a = self.alpha_slider.value()

        self.hue_label.setText(str(h))
        self.saturation_label.setText(f"{s}%")
        self.lightness_label.setText(f"{l}%")
        self.alpha_label.setText(f"{a}%")

        # Update preview color using setStyleSheet for higher precedence
        hsla_str_style = f"hsla({h}, {s}%, {l}%, {a / 100.0:.2f})"
        # Add a border to make it visible even if color is similar to background
        self.color_preview.setStyleSheet(
            f"background-color: {hsla_str_style}; border: 1px solid grey;"
        )

        # Update HSLA text display
        hsla_str = hsla_str_style  # Reuse the string
        self.hsla_value_label.setText(hsla_str)

        # Emit signal for main window preview
        self._update_preview_and_main_window()

    def _update_preview_and_main_window(self) -> None:
        """Gets current slider values, converts to 0-1 floats, and emits the preview signal."""
        h_float = self.hue_slider.value() / 359.0
        s_float = self.saturation_slider.value() / 100.0
        l_float = self.lightness_slider.value() / 100.0
        a_float = self.alpha_slider.value() / 100.0
        # Ensure floats are within valid range due to potential rounding
        h_float = max(0.0, min(1.0, h_float))
        s_float = max(0.0, min(1.0, s_float))
        l_float = max(0.0, min(1.0, l_float))
        a_float = max(0.0, min(1.0, a_float))
        self.backgroundPreviewRequested.emit(h_float, s_float, l_float, a_float)

    # --- Overridden Methods ---

    def accept(self) -> None:
        """Emits signals with 0-1 float values and closes the dialog."""
        # Convert current slider values to 0-1 floats before emitting
        h_float = self.hue_slider.value() / 359.0
        s_float = self.saturation_slider.value() / 100.0
        l_float = self.lightness_slider.value() / 100.0
        a_float = self.alpha_slider.value() / 100.0
        # Ensure floats are valid
        h_float = max(0.0, min(1.0, h_float))
        s_float = max(0.0, min(1.0, s_float))
        l_float = max(0.0, min(1.0, l_float))
        a_float = max(0.0, min(1.0, a_float))

        self.backgroundApplied.emit(h_float, s_float, l_float, a_float)
        self.startupToggled.emit(self.startup_checkbox.isChecked())
        super().accept()

    def reject(self) -> None:
        """Restores initial background color preview and closes the dialog."""
        # Convert initial CSS format values back to 0-1 floats for the preview signal
        h_css, s_css, l_css, a_float = self.initial_background_hsla_css
        h_float = h_css / 359.0
        s_float = s_css / 100.0
        l_float = l_css / 100.0
        # Ensure floats are valid
        h_float = max(0.0, min(1.0, h_float))
        s_float = max(0.0, min(1.0, s_float))
        l_float = max(0.0, min(1.0, l_float))
        a_float = max(0.0, min(1.0, a_float))

        self.backgroundPreviewRequested.emit(
            h_float, s_float, l_float, a_float
        )  # Use preview signal to revert
        super().reject()

    # Optional: Override closeEvent if clicking 'X' should also revert
    # def closeEvent(self, event):
    #     """Handles the close event (e.g., clicking the 'X' button)."""
    #     self.reject() # Treat closing as cancel
    #     event.accept()
