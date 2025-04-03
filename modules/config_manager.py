import os
import json
from typing import List, Dict, Tuple, Optional, Any # Added Tuple, Optional, Any
from PySide6.QtCore import QPoint # Added QPoint

CONFIG_FILE: str = "drawers.json"


class ConfigManager:
    @staticmethod
    def load_config() -> Tuple[List[Dict[str, str]], Optional[QPoint]]:
        """
        加载配置文件，验证抽屉数据，并加载窗口位置。
        返回一个包含抽屉列表和可选窗口位置 (QPoint) 的元组。
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data: Dict[str, Any] = json.load(f) # Type hint for data

                # 加载抽屉
                drawers_data = data.get("drawers", [])
                valid_drawers: List[Dict[str, str]] = []
                if isinstance(drawers_data, list):
                    for drawer in drawers_data:
                        if (
                            isinstance(drawer, dict)
                            and isinstance(drawer.get("name"), str)
                            and isinstance(drawer.get("path"), str)
                        ):
                            # 保留原始结构，不在此处添加 position
                            valid_drawers.append({"name": drawer["name"], "path": drawer["path"]})

                # 加载窗口位置
                window_pos_data = data.get("window_position")
                window_position: Optional[QPoint] = None
                if isinstance(window_pos_data, dict) and \
                   isinstance(window_pos_data.get("x"), int) and \
                   isinstance(window_pos_data.get("y"), int):
                    window_position = QPoint(window_pos_data["x"], window_pos_data["y"])

                return valid_drawers, window_position

            except (json.JSONDecodeError, OSError) as e:
                print(f"加载配置错误: {e}")
        return [], None # Return empty list and None if file doesn't exist or error occurs

    @staticmethod
    def save_config(drawers: List[Dict[str, str]], window_position: Optional[QPoint] = None) -> None:
        """
        保存抽屉配置和窗口位置。
        """
        data: Dict[str, Any] = {"drawers": drawers} # Type hint for data
        if window_position:
            data["window_position"] = {"x": window_position.x(), "y": window_position.y()}

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"保存配置错误: {e}")
