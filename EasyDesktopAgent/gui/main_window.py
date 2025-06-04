import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QAction, QMessageBox,
                             QToolBar, QStatusBar, QFileDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from .config_dialog import ConfigDialog
from .knowledge_panel import KnowledgePanel
from .task_panel import TaskPanel

class MainWindow(QMainWindow):
    def __init__(self, config_manager):
        super().__init__()
        
        self.config_manager = config_manager
        self.setWindowTitle("Easy Desktop Agent")
        self.resize(1000, 700)
        
        # 创建中心部件
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建面板
        self.knowledge_panel = KnowledgePanel(self.config_manager)
        self.task_panel = TaskPanel(self.config_manager)
        
        # 添加标签页
        self.tabs.addTab(self.knowledge_panel, "本地知识库")
        self.tabs.addTab(self.task_panel, "任务管理")
        
        # 创建菜单和工具栏
        self.create_menu()
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 检查API密钥
        self.check_api_key()
    
    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        # 配置选项
        config_action = QAction("配置", self)
        config_action.triggered.connect(self.show_config_dialog)
        file_menu.addAction(config_action)
        
        # 退出选项
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        # 关于选项
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)
        
        # 配置按钮
        config_action = QAction("配置", self)
        config_action.triggered.connect(self.show_config_dialog)
        toolbar.addAction(config_action)
        
        # 刷新按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_panels)
        toolbar.addAction(refresh_action)
    
    def show_config_dialog(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.config_manager, self)
        if dialog.exec_():
            # 配置已更新，刷新面板
            self.refresh_panels()
            self.statusBar.showMessage("配置已更新", 3000)
    
    def refresh_panels(self):
        """刷新所有面板"""
        self.knowledge_panel.refresh()
        self.task_panel.refresh()
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 Easy Desktop Agent",
                          "<h3>Easy Desktop Agent</h3>"
                          "<p>版本: 1.0.0</p>"
                          "<p>基于AI的桌面自动化工具</p>")
    
    def check_api_key(self):
        """检查API密钥是否已配置"""
        api_key = self.config_manager.get_api_key()
        if not api_key:
            QMessageBox.warning(self, "配置提示",
                               "请先配置API密钥和模型参数。")
            self.show_config_dialog()