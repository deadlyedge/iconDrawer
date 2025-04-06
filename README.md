# 图标抽屉管理器
![App Icon](https://github.com/deadlyedge/iconDrawer/blob/master/asset/drawer.icon.4.png)

## 简介

我之前一直在使用stardock fences，不过我意识到事实上我需要的只是一个能够很好的整理桌面图标的简单应用。我做了一些搜索和研究，我发现这个简单的功能似乎并没有一个简单的实现，于是就有了这个项目。

本应用基于 PySide6 构建，是一个图形化的抽屉管理工具。用户可以管理和浏览存储在计算机上的文件夹（抽屉），并通过两个独立窗口展示抽屉列表和抽屉内容。从效率和功能出发，当然我认为C#、.NET会是更好的开发平台。不过我本人实在是不懂C，所以只能尝试使用python来实现基础功能。希望通过这个项目，能有开发者（其实我觉得最好是PowerToys的开发人员）意识到这个功能的实用性，做出更好的产品。

## 主要功能
- **抽屉列表管理**
  - 从配置文件 (`drawers.json`) 加载抽屉信息。
  - 显示抽屉列表，用户可以通过拖拽区域移动窗口。
  - 支持添加新的抽屉，通过目录选择对话框选择文件夹，并将其保存到配置文件中。
  
- **抽屉内容展示**
  - 当鼠标悬停或点击抽屉列表项时，右侧的抽屉内容显示窗口会自动显示所选文件夹内的内容（文件和文件夹图标）。
  - 内容窗口采用无边框和半透明背景，且始终保持位于抽屉列表窗口的右侧，随窗口移动和大小变化而自动调整位置。
  - 当未选中任何抽屉或鼠标离开列表窗口时，内容窗口会自动隐藏。
  - 支持通过自定义大小调整手柄（Size Grip）调整列表窗口的大小。

- **视觉和交互设计**
  - 窗口和两个主要组件均采用无边框设计，并通过设置半透明背景（透明度为 0.8）实现现代化视觉效果。
  - 抽屉列表窗口顶部设置了一个拖拽区域，允许用户拖动窗口，实现自定义位置调整。

## 技术细节
- **开发框架**: 使用 PySide6 进行界面开发。
- **配置文件**: 使用 `modules/config_manager.py` 模块管理 `drawers.json` 中的抽屉信息（`name` 和 `path`）。
- **窗口管理与交互**: 
  - `DrawerListWindow`: 展示抽屉列表，包含用于移动窗口的拖拽区域 (`modules/drag_area.py`) 和用于调整大小的手柄 (`modules/custom_size_grip.py`)。
  - `DrawerContentWindow`: 展示所选抽屉的内容 (`modules/content.py`, `modules/content_utils.py`)。
  - `modules/controller.py`: 协调列表窗口和内容窗口之间的交互逻辑。
  - `modules/icon_utils.py`: 处理文件和文件夹图标的显示。
- **样式**: 通过 Qt Style Sheets (`modules/style.qss`) 实现自定义界面样式。

## 使用方法
1. 运行程序后，会显示抽屉列表窗口。
2. 用户可以通过拖拽窗口顶部的拖拽区域移动抽屉列表窗口。
3. 点击“添加抽屉”按钮可以选择新目录来添加抽屉。
4. 当鼠标悬停或点击某一抽屉时，右侧窗口会自动显示该抽屉内的文件及文件夹图标；若鼠标离开列表区域或未选中抽屉，右侧窗口则隐藏。

## 依赖与环境
- Python 版本要求：Python 3.x (具体版本可在 `.python-version` 查看)
- 依赖管理：项目依赖项定义在 `pyproject.toml` 文件中。
- 主要依赖：PySide6 等 (详见 `pyproject.toml`)。

## 安装与运行
1.  **安装依赖**: 建议使用 `uv` 或 `pip` 安装依赖。在项目根目录下运行：
    ```bash
    # 使用 uv (推荐)
    uv pip install -r requirements.txt 
    # 或 uv sync

    # 或者使用 pip
    pip install -r requirements.txt
    # 或 pip install . 
    ```
    *注意：如果 `requirements.txt` 不存在或不是最新的，请根据 `pyproject.toml` 生成或直接使用 `pip install .`*

2.  **运行程序**:
    ```bash
    python main.py
    ```

## 维护与扩展
- 用户可通过修改 `drawers-settings.json` 来直接更改抽屉配置信息。
- 本应用的窗口布局和界面风格易于扩展，欢迎贡献新的功能和界面改进。


## TODOs
- drag in to copy or move files to drawers
- settings
  - color
  - transparancy
- ~~stay in system tray~~
- ~~a logo and icons for the app~~
  