我已经按照 validator/dispatcher/worker 模式成功重构了 modules/icon_utils.py。

## 主要更改包括：

- 创建了 modules/icon_provider.py 来管理默认图标。
- 创建了 modules/icon_validators.py 来验证路径并提取信息。
- 创建了 modules/icon_workers/ 目录，并在其中添加了：
  - base_worker.py (抽象基类)
  - directory_worker.py (处理目录)
  - utils.py (包含 try_get_icon 辅助函数)
  - lnk_worker.py (处理 .lnk 文件，包含 Pydantic 模型)
  - file_worker.py (处理普通文件)
- 创建了 modules/icon_dispatcher.py 来根据路径信息选择合适的 worker。
- 更新了 modules/icon_utils.py 作为公共接口，现在它调用新的验证器和调度器来获取图标。

这次重构将图标获取逻辑分解为更小、更专注的模块，提高了代码的组织性、可读性和可维护性。