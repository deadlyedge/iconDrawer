# Qt 组件关系图

以下 Mermaid 图展示了 iconDrawer 应用中 Qt 组件的层级关系和信号连接。每个组件都有明确的 objectName，用于在 style.qss 中定义样式。

```mermaid
classDiagram
    class MainWindow {
        objectName: "mainWindow"
        +QWidget leftPanel
        +DragArea dragArea
        +DrawerListWidget drawerList
        +QPushButton addButton
        +DrawerContentWidget drawerContent
        +AppController controller
        +QSystemTrayIcon trayIcon
        +QMenu trayMenu
        +show_settings_dialog()
        +populate_drawer_list()
        +add_drawer_item()
        +set_background_color()
    }

    class DragArea {
        objectName: "dragArea"
        +Signal settingsRequested
        +Signal dragFinished
        +QLabel dragLabel
        +QPushButton settingsButton
    }

    class DrawerListWidget {
        objectName: "drawerList"
        +Signal itemSelected
        +Signal selectionCleared
    }

    class DrawerContentWidget {
        objectName: "drawerContent"
        +Signal closeRequested
        +Signal sizeChanged
        +Signal resizeFinished
        +QWidget main_visual_container
        +QLabel folder_label
        +QLabel folder_icon_label
        +QPushButton refresh_button
        +QPushButton close_button
        +QScrollArea scroll_area
        +QWidget scroll_widget
        +QGridLayout grid_layout
        +CustomSizeGrip size_grip
        +update_content()
        +open_current_folder()
    }

    class FileIconWidget {
        +QWidget visual_container
        +QLabel icon_label
        +QLabel text_label
        +set_icon()
    }

    class CustomSizeGrip {
        objectName: "sizeGrip"
        +Signal resized
        +Signal resizeStarted
        +Signal resizeFinished
    }

    class SettingsDialog {
        objectName: "settingsDialog"
        +Signal backgroundPreviewRequested
        +Signal backgroundApplied
        +Signal startupToggled
        +Signal quitApplicationRequested
        +QSlider hue_slider
        +QSlider saturation_slider
        +QSlider lightness_slider
        +QSlider alpha_slider
        +QWidget color_preview
        +QCheckBox startup_checkbox
    }

    class AppController {
        +Signal showDrawerContent
        +Signal hideDrawerContent
        +Signal updateDrawerContent
        +add_new_drawer()
        +handle_item_selected()
        +handle_selection_cleared()
        +handle_settings_requested()
        +handle_content_close_requested()
        +handle_background_applied()
        +handle_startup_toggled()
    }

    MainWindow "1" --> "1" DragArea : contains
    MainWindow "1" --> "1" DrawerListWidget : contains
    MainWindow "1" --> "1" DrawerContentWidget : contains
    MainWindow "1" --> "1" AppController : owns
    MainWindow "1" --> "1" SettingsDialog : creates on demand

    DrawerContentWidget "1" --> "*" FileIconWidget : contains
    DrawerContentWidget "1" --> "1" CustomSizeGrip : contains

    DragArea "1" --|> QWidget
    DrawerListWidget "1" --|> QListWidget
    DrawerContentWidget "1" --|> QWidget
    FileIconWidget "1" --|> QWidget
    CustomSizeGrip "1" --|> QWidget
    SettingsDialog "1" --|> QDialog

    AppController ..> MainWindow : controls
    AppController ..> DrawerContentWidget : controls
    AppController ..> DrawerListWidget : controls
    AppController ..> DragArea : controls

    DragArea : settingsRequested --> AppController.handle_settings_requested
    DragArea : dragFinished --> AppController.handle_window_drag_finished

    DrawerListWidget : itemSelected --> AppController.handle_item_selected
    DrawerListWidget : selectionCleared --> AppController.handle_selection_cleared

    DrawerContentWidget : closeRequested --> AppController.handle_content_close_requested
    DrawerContentWidget : resizeFinished --> AppController.handle_content_resize_finished
    DrawerContentWidget : sizeChanged --> MainWindow._handle_content_size_changed

    CustomSizeGrip : resizeFinished --> DrawerContentWidget.resizeFinished

    SettingsDialog : backgroundPreviewRequested --> MainWindow.set_background_color
    SettingsDialog : backgroundApplied --> AppController.handle_background_applied
    SettingsDialog : startupToggled --> AppController.handle_startup_toggled
    SettingsDialog : quitApplicationRequested --> QApplication.quit()
```

## 组件 objectName 命名方案

| 组件类型 | 组件名称 | objectName |
|---------|---------|------------|
| QMainWindow | MainWindow | mainWindow |
| QWidget | 左侧面板 | leftPanel |
| DragArea | 拖拽区域 | dragArea |
| DrawerListWidget | 抽屉列表 | drawerList |
| QPushButton | 添加按钮 | addButton |
| DrawerContentWidget | 右侧内容区域 | drawerContent |
| QWidget | 内容区域容器 | drawerContentContainer |
| QLabel | 文件夹路径标签 | folderLabel |
| QLabel | 文件夹图标标签 | folderIconLabel |
| QPushButton | 刷新按钮 | refreshButton |
| QPushButton | 关闭按钮 | closeButton |
| QScrollArea | 滚动区域 | scrollArea |
| QWidget | 滚动内容区域 | scrollWidget |
| CustomSizeGrip | 大小调整手柄 | sizeGrip |
| SettingsDialog | 设置对话框 | settingsDialog |
| QMenu | 系统托盘菜单 | trayMenu |
| FileIconWidget | 文件图标部件 | fileItem |
| QWidget | 文件图标视觉容器 | visualContainer |
| QLabel | 文件图标标签 | iconLabel |
| QLabel | 文件名标签 | textLabel |

## 文件与组件对应关系

| 文件名 | 主要组件 |
|-------|---------|
| main_window.py | MainWindow |
| drag_area.py | DragArea |
| list.py | DrawerListWidget |
| content.py | DrawerContentWidget, ClickableWidget |
| file_item.py | FileIconWidget |
| custom_size_grip.py | CustomSizeGrip |
| settings_dialog.py | SettingsDialog |
| controller.py | AppController |
