import os
import json
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from PySide6.QtCore import QPoint, QSize
from pydantic import BaseModel, ValidationError, Field, field_validator
import logging  # Import logging

SETTINGS_FILE: str = "drawers-settings.json"


# Pydantic Models for settings structure validation
class SizeModel(BaseModel):
    width: int
    height: int


class DrawerModel(BaseModel):
    name: str
    path: Path
    size: Optional[SizeModel] = None

    @field_validator("path")
    def path_must_exist(cls, v):
        if not v.exists():
            logging.warning(f"Path does not exist during validation: {v}")
        return v


class WindowPositionModel(BaseModel):
    x: int
    y: int


class SettingsModel(BaseModel):
    drawers: List[DrawerModel] = Field(default_factory=list)
    window_position: Optional[WindowPositionModel] = None
    # Store HSLA in CSS standard format: H(0-359 int), S(0-100 int), L(0-100 int), A(0.0-1.0 float)
    background_color_hsla: Tuple[int, int, int, float] = Field(
        default=(0, 0, 10, 0.8)
    )  # Default: dark grey, 80% alpha
    start_with_windows: bool = False
    # New settings for defaults
    default_icon_folder_path: str = "asset/icons/folder_icon.png"
    default_icon_file_theme: str = "text-x-generic"  # Theme name for generic file
    default_icon_unknown_theme: str = "unknown"  # Theme name for unknown
    thumbnail_size: SizeModel = Field(default=SizeModel(width=64, height=64))


DrawerDict = Dict[str, Any]


class SettingsManager:
    # Keep defaults here for fallback if file is totally corrupt or missing (CSS format)
    DEFAULT_BG_COLOR_HSLA: Tuple[int, int, int, float] = (
        0,
        0,
        10,
        0.8,
    )  # H(0-359), S(0-100), L(0-100), A(0.0-1.0)
    DEFAULT_START_WITH_WINDOWS: bool = False
    DEFAULT_ICON_FOLDER_PATH: str = "asset/icons/folder_icon.png"
    DEFAULT_ICON_FILE_THEME: str = "text-x-generic"
    DEFAULT_ICON_UNKNOWN_THEME: str = "unknown"
    DEFAULT_THUMBNAIL_SIZE: SizeModel = SizeModel(width=64, height=64)

    @staticmethod
    def load_settings() -> Tuple[
        List[DrawerDict],
        Optional[QPoint],
        Tuple[int, int, int, float],  # Return HSLA in CSS format
        bool,
        str,  # icon_folder_path
        str,  # icon_file_theme
        str,  # icon_unknown_theme
        QSize,  # thumbnail_qsize
    ]:
        """
        Loads settings using Pydantic models for validation.
        Returns a tuple containing drawers, window_pos, bg_color, start_flag,
        icon paths/themes, and thumbnail size.
        """
        settings: SettingsModel
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                settings = SettingsModel.model_validate(raw_data)
                logging.debug("Settings file loaded and validated.")
            else:
                logging.warning(
                    f"Settings file '{SETTINGS_FILE}' not found. Using defaults."
                )
                settings = SettingsModel()  # Use default values from model
        except (json.JSONDecodeError, ValidationError, OSError) as e:
            logging.error(
                f"Error loading or validating config '{SETTINGS_FILE}': {e}. Using defaults."
            )
            settings = SettingsModel()  # Use default values on error

        # --- Process loaded or default settings ---
        app_drawers: List[DrawerDict] = []
        if settings.drawers:  # Check if drawers list exists
            for drawer_model in settings.drawers:
                try:
                    # Validate path existence again during processing
                    if not drawer_model.path.exists():
                        logging.warning(
                            f"Skipping drawer '{drawer_model.name}' as path no longer exists: {drawer_model.path}"
                        )
                        continue

                    drawer_dict: DrawerDict = {
                        "name": drawer_model.name,
                        "path": str(drawer_model.path),  # Store path as string
                    }
                    if drawer_model.size:
                        drawer_dict["size"] = QSize(
                            drawer_model.size.width, drawer_model.size.height
                        )
                    app_drawers.append(drawer_dict)
                except Exception as drawer_err:
                    logging.error(
                        f"Error processing drawer '{drawer_model.name}': {drawer_err}"
                    )

        # This block should be outside the 'if settings.drawers:' block, at the same level
        app_window_position: Optional[QPoint] = None
        if settings.window_position:
            app_window_position = QPoint(
                settings.window_position.x, settings.window_position.y
            )

            # Use loaded or default values from the validated model
            app_bg_color_raw = settings.background_color_hsla
            app_start_with_windows = settings.start_with_windows
            app_icon_folder_path = settings.default_icon_folder_path
            app_icon_file_theme = settings.default_icon_file_theme
            app_icon_unknown_theme = settings.default_icon_unknown_theme
            app_thumbnail_size = QSize(
                settings.thumbnail_size.width, settings.thumbnail_size.height
            )

            # --- Convert loaded HSLA to CSS standard format ---
            # Check if loaded data is likely old format (all floats <= 1.0)
            is_old_format = all(
                isinstance(x, float) and 0.0 <= x <= 1.0 for x in app_bg_color_raw
            )

            if is_old_format and len(app_bg_color_raw) == 4:
                logging.info(
                    "Converting background color from old format (0-1 floats) to CSS format."
                )
                h_f, s_f, l_f, a_f = app_bg_color_raw
                app_bg_color_css = (
                    round(h_f * 359),  # H: 0-359 int
                    round(s_f * 100),  # S: 0-100 int
                    round(l_f * 100),  # L: 0-100 int
                    a_f,  # A: 0.0-1.0 float
                )
            elif (
                isinstance(app_bg_color_raw, tuple)
                and len(app_bg_color_raw) == 4
                and isinstance(app_bg_color_raw[0], int)
                and isinstance(app_bg_color_raw[1], int)
                and isinstance(app_bg_color_raw[2], int)
                and isinstance(app_bg_color_raw[3], float)
            ):
                # Assume it's already in the correct CSS format
                app_bg_color_css = app_bg_color_raw
            else:
                # Invalid format or length, use default
                logging.warning(
                    f"Invalid background color format loaded: {app_bg_color_raw}. Using default."
                )
                app_bg_color_css = SettingsManager.DEFAULT_BG_COLOR_HSLA

        # This return statement should be here, after processing all settings
        return (
            app_drawers,
            app_window_position,
            app_bg_color_css,  # Return converted value
            app_start_with_windows,
            app_icon_folder_path,
            app_icon_file_theme,
            app_icon_unknown_theme,
            app_thumbnail_size,
        )

    @staticmethod
    def save_settings(
        # User-modifiable settings
        drawers: List[DrawerDict],
        window_position: Optional[QPoint] = None,
        background_color_hsla: Optional[
            Tuple[int, int, int, float]
        ] = None,  # Expect CSS format (or None)
        start_with_windows: Optional[bool] = None,  # Allow None to use default
        # Non-user-modifiable (loaded) settings - pass them through
        default_icon_folder_path: str = DEFAULT_ICON_FOLDER_PATH,
        default_icon_file_theme: str = DEFAULT_ICON_FILE_THEME,
        default_icon_unknown_theme: str = DEFAULT_ICON_UNKNOWN_THEME,
        thumbnail_size: QSize = QSize(
            DEFAULT_THUMBNAIL_SIZE.width, DEFAULT_THUMBNAIL_SIZE.height
        ),
    ) -> None:
        """
        Saves settings using Pydantic models for serialization.
        Uses provided values or falls back to defaults defined in the model or class.
        """
        drawer_models: List[DrawerModel] = []
        if drawers:  # Check if drawers list is provided
            for drawer_dict in drawers:
                size_model: Optional[SizeModel] = None
                if "size" in drawer_dict and isinstance(drawer_dict["size"], QSize):
                    qsize = drawer_dict["size"]
                    size_model = SizeModel(width=qsize.width(), height=qsize.height())

                try:
                    # Ensure path is stored correctly
                    path_str = drawer_dict.get("path")
                    if not path_str:
                        logging.error(
                            f"Skipping drawer with missing path: {drawer_dict.get('name', 'N/A')}"
                        )
                        continue
                    path_obj = Path(path_str)
                    # Path existence check during save might be too strict if user intends to fix it later
                    # if not path_obj.exists():
                    #     logging.warning(f"Path does not exist during save: {path_obj}")

                    drawer_models.append(
                        DrawerModel(
                            name=drawer_dict["name"], path=path_obj, size=size_model
                        )
                    )
                except Exception as e:
                    logging.error(
                        f"Skipping invalid drawer during save: {drawer_dict.get('name', 'N/A')} - Error: {e}"
                    )

        window_pos_model: Optional[WindowPositionModel] = None
        if window_position:
            window_pos_model = WindowPositionModel(
                x=window_position.x(), y=window_position.y()
            )

        # Use provided values or let Pydantic use defaults
        settings_data = {
            "drawers": drawer_models,
            "window_position": window_pos_model,
            # Pass None if not provided, Pydantic will use model default
            "background_color_hsla": background_color_hsla,
            "start_with_windows": start_with_windows,
            # Pass through the non-user-modifiable settings
            "default_icon_folder_path": default_icon_folder_path,
            "default_icon_file_theme": default_icon_file_theme,
            "default_icon_unknown_theme": default_icon_unknown_theme,
            "thumbnail_size": SizeModel(
                width=thumbnail_size.width(), height=thumbnail_size.height()
            ),
        }
        # Remove None values before validation if Pydantic defaults should apply
        settings_data_cleaned = {
            k: v for k, v in settings_data.items() if v is not None
        }

        try:
            # Validate before saving
            config_to_save = SettingsModel.model_validate(settings_data_cleaned)
            data_to_save = config_to_save.model_dump(
                mode="json"
            )  # Use mode="json" for Path serialization
        except ValidationError as e:
            logging.error(
                f"Validation error before saving settings: {e}. Settings not saved."
            )
            return

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            logging.debug(f"Settings successfully saved to {SETTINGS_FILE}")
        except OSError as e:
            logging.error(f"Error saving config to {SETTINGS_FILE}: {e}")

        # Keep these helper methods as they might still be useful,
        # but note they now load ALL settings just to return one piece.
        # Consider if they are still needed or if callers should load all settings once.

    @staticmethod
    def get_background_color_hsla() -> Tuple[int, int, int, float]:  # Return CSS format
        """Loads settings and returns only the background color HSLA tuple (CSS format)."""
        settings = SettingsManager.load_settings()
        return settings[2]  # Index for bg_color

    @staticmethod
    def get_start_with_windows() -> bool:
        """Loads settings and returns only the start with windows flag."""
        settings = SettingsManager.load_settings()
        return settings[3]  # Index for start_flag
