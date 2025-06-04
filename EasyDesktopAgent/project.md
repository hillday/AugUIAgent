EasyDesktopAgent/
├── main.py                 # 程序入口
├── config/
│   ├── __init__.py
│   ├── config_manager.py   # 配置管理
│   └── settings.json       # 配置文件
├── gui/
│   ├── __init__.py
│   ├── main_window.py      # 主窗口
│   ├── config_dialog.py    # 配置对话框
│   ├── knowledge_panel.py  # 知识库管理面板
│   ├── task_panel.py       # 任务管理面板
│   └── resources/          # 图标和资源文件
├── core/
│   ├── __init__.py
│   ├── video_processor.py  # 视频处理
│   ├── task_service.py     # 任务服务
│   └── knowledge_service.py # 知识库服务
└── utils/
    ├── __init__.py
    └── logger.py           # 日志工具