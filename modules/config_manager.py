import os
import json
from typing import List, Dict

CONFIG_FILE: str = "drawers.json"


class ConfigManager:
    @staticmethod
    def load_config() -> List[Dict[str, str]]:
        """
        加载配置文件，并验证每个抽屉数据必须为包含字符串字段 'name' 和 'path' 的字典。
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                drawers = data.get("drawers", [])
                if isinstance(drawers, list):
                    valid_drawers: List[Dict[str, str]] = []
                    for drawer in drawers:
                        if (
                            isinstance(drawer, dict)
                            and isinstance(drawer.get("name"), str)
                            and isinstance(drawer.get("path"), str)
                        ):
                            valid_drawers.append(drawer)
                    return valid_drawers
            except (json.JSONDecodeError, OSError) as e:
                print(f"加载配置错误: {e}")
        return []

    @staticmethod
    def save_config(drawers: List[Dict[str, str]]) -> None:
        """
        保存抽屉配置，要求 drawers 为包含 'name' 和 'path' 键的字典列表。
        """
        data = {"drawers": drawers}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"保存配置错误: {e}")
