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


DrawerDict = Dict[str, Any]


class SettingsManager:
    @staticmethod
    def load_settings() -> Tuple[List[DrawerDict], Optional[QPoint]]:
        """
        Loads settings using Pydantic models for validation.
        Returns a tuple containing a list of drawer dictionaries (compatible with application logic)
        and an optional window position (QPoint).
        """
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                settings = SettingsModel.model_validate(raw_data)

                app_drawers: List[DrawerDict] = []
                for drawer_model in settings.drawers:
                    if not drawer_model.path.exists():
                        logging.warning(
                            f"Skipping drawer '{drawer_model.name}' as path no longer exists: {drawer_model.path}"
                        )
                        continue

                    drawer_dict: DrawerDict = {
                        "name": drawer_model.name,
                        "path": str(drawer_model.path),
                    }
                    if drawer_model.size:
                        drawer_dict["size"] = QSize(
                            drawer_model.size.width, drawer_model.size.height
                        )
                    app_drawers.append(drawer_dict)

                app_window_position: Optional[QPoint] = None
                if settings.window_position:
                    app_window_position = QPoint(
                        settings.window_position.x, settings.window_position.y
                    )

                return app_drawers, app_window_position

            except (json.JSONDecodeError, ValidationError, OSError) as e:
                logging.error(f"Error loading or validating config: {e}")
        return [], None

    @staticmethod
    def save_settings(
        drawers: List[DrawerDict], window_position: Optional[QPoint] = None
    ) -> None:
        """
        Saves settings using Pydantic models for serialization.
        """
        drawer_models: List[DrawerModel] = []
        for drawer_dict in drawers:
            size_model: Optional[SizeModel] = None
            if "size" in drawer_dict and isinstance(drawer_dict["size"], QSize):
                qsize = drawer_dict["size"]
                size_model = SizeModel(width=qsize.width(), height=qsize.height())

            try:
                path_obj = Path(drawer_dict["path"])
                if not path_obj.exists():
                    logging.warning(f"Path does not exist during save: {path_obj}")
                    # continue

                drawer_models.append(
                    DrawerModel(
                        name=drawer_dict["name"], path=path_obj, size=size_model
                    )
                )
            except Exception as e:
                logging.error(
                    f"Skipping invalid drawer path during save: {drawer_dict.get('path', 'N/A')} - Error: {e}"
                )

        window_pos_model: Optional[WindowPositionModel] = None
        if window_position:
            window_pos_model = WindowPositionModel(
                x=window_position.x(), y=window_position.y()
            )

        config_to_save = SettingsModel(
            drawers=drawer_models, window_position=window_pos_model
        )

        data_to_save = config_to_save.model_dump(mode="json", exclude_none=True)

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logging.error(f"Error saving config: {e}")
