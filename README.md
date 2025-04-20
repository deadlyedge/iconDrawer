# Icon Drawer Manager
![App Icon](https://github.com/deadlyedge/iconDrawer/blob/master/asset/drawer.icon.4.png)

## Introduction

I've been using Stardock Fences, but I realized that what I really need is a simple application to organize my desktop icons effectively. After some searching and research, I found that there wasn't a straightforward implementation for this simple function, which led to the creation of this project.

Built with PySide6, this application is a graphical desktop management tool. Users can manage and browse folders (drawers) stored on their computer, displaying the drawer list and drawer content in two separate windows. From an efficiency and functionality perspective, I believe C# and .NET would be better development platforms. However, I'm not familiar with C, so I attempted to implement the basic features using Python. I hope this project inspires developers (ideally, the PowerToys team) to recognize the utility of this feature and create even better products.

Anyway, one thing is very important: the goal of icon drawer is to manage the desktop, and not to mess it up.

## Main Features
- **Drawer List Management**
  - Loads drawer information from the configuration file (`drawers.json`).
  - Displays the list of drawers; users can move the window using the drag area.
  - Supports adding new drawers by selecting a folder through a directory selection dialog and saving it to the configuration file.

- **Drawer Content Display**
  - When hovering over or clicking a drawer list item, the drawer content window on the right automatically displays the contents (file and folder icons) of the selected folder.
  - The content window is borderless with a semi-transparent background and always stays to the right of the drawer list window, automatically adjusting its position as the list window moves or resizes.
  - The content window automatically hides when no drawer is selected or the mouse leaves the list window area.
  - Supports resizing the list window using a custom size grip handle.

- **Visual and Interaction Design**
  - Both the window and the two main components feature a borderless design with a semi-transparent background (opacity 0.8) for a modern visual effect.
  - The top of the drawer list window includes a drag area, allowing users to move the window for custom positioning.

## Technical Details
- **Development Framework**: Uses PySide6 for interface development.
- **Configuration File**: Manages drawer information (`name` and `path`) in `drawers.json` using the `modules/config_manager.py` module.
- **Window Management & Interaction**:
  - `DrawerListWindow`: Displays the drawer list, includes a drag area (`modules/drag_area.py`) for moving the window and a size grip (`modules/custom_size_grip.py`) for resizing.
  - `DrawerContentWindow`: Displays the content of the selected drawer (`modules/content.py`, `modules/content_utils.py`).
  - `modules/controller.py`: Coordinates the interaction logic between the list and content windows.
  - `modules/icon_utils.py`: Handles the display of file and folder icons.
- **Styling**: Uses Qt Style Sheets (`modules/style.qss`) for custom interface styling.

## How to Use
1. Run the program to display the drawer list window.
2. Move the drawer list window by dragging the area at the top.
3. Click the "Add Drawer" button to select a new directory and add a drawer.
4. Hover over or click a drawer item to display its contents in the right window; the right window hides when the mouse leaves the list area or no drawer is selected.

## Dependencies and Environment
- Python Version Requirement: Python 3.x (specific version can be found in `.python-version`)
- Dependency Management: Project dependencies are defined in the `pyproject.toml` file.
- Main Dependencies: PySide6, etc. (see `pyproject.toml` for details).

## Installation and Running
1.  **Install Dependencies**: It is recommended to use `uv` or `pip` to install dependencies. Run the following in the project root directory:
    ```bash
    # Using uv (recommended)
    uv pip install -r requirements.txt
    # or uv sync

    # Or using pip
    pip install -r requirements.txt
    # or pip install .
    ```
    *Note: If `requirements.txt` does not exist or is not up-to-date, please generate it based on `pyproject.toml` or use `pip install .` directly.*

2.  **Run the Program**:
    ```bash
    python main.py

    # or using uv
    uv run main.py
    ```

3.  **Build with Nuitka**:
    ```bash
    uv run nuitka --onefile --windows-console-mode=disable --include-data-dir=asset=asset --mingw64 --enable-plugin=pyside6 main.py
    ```

## Maintenance and Extension
- Users can directly modify drawer configuration information by editing `drawers-settings.json`.
- The window layout and interface style of this application are easy to extend. Contributions for new features and interface improvements are welcome.

## TODOs
- [ ] make a new module for folder read, with cache and force re-read.
- [ ] add preload back.
- [x] simplify icon collector.