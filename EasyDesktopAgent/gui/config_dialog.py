from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QTabWidget, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt

class ConfigDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        self.setWindowTitle("配置")
        self.resize(500, 400)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 创建API配置页
        self.api_tab = self.create_api_tab()
        self.tabs.addTab(self.api_tab, "API配置")
        
        # 创建模型配置页
        self.models_tab = self.create_models_tab()
        self.tabs.addTab(self.models_tab, "模型配置")
        
        # 创建知识库配置页
        self.knowledge_tab = self.create_knowledge_tab()
        self.tabs.addTab(self.knowledge_tab, "知识库配置")
        
        # 创建任务配置页
        self.tasks_tab = self.create_tasks_tab()
        self.tabs.addTab(self.tasks_tab, "任务配置")
        
        # 创建按钮
        self.buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_config)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.cancel_button)
        
        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addLayout(self.buttons_layout)
        
        self.setLayout(self.main_layout)
        
        # 加载当前配置
        self.load_config()
    
    def create_api_tab(self):
        """创建API配置标签页"""
        tab = QGroupBox("API设置")
        layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)  # 密码模式显示
        self.api_host_edit = QLineEdit()
        
        layout.addRow("API密钥:", self.api_key_edit)
        layout.addRow("API主机:", self.api_host_edit)
        
        tab.setLayout(layout)
        return tab
    
    def create_models_tab(self):
        """创建模型配置标签页"""
        tab = QGroupBox("模型设置")
        layout = QFormLayout()
        
        self.vlm_model_edit = QLineEdit()
        self.uitars_model_edit = QLineEdit()
        self.planning_model_edit = QLineEdit()
        
        layout.addRow("视觉理解模型EP:", self.vlm_model_edit)
        layout.addRow("UI TARS模型EP:", self.uitars_model_edit)
        layout.addRow("深度理解模型EP:", self.planning_model_edit)
        
        tab.setLayout(layout)
        return tab
    
    def create_knowledge_tab(self):
        """创建知识库配置标签页"""
        tab = QGroupBox("知识库设置")
        layout = QFormLayout()
        
        self.video_dir_edit = QLineEdit()
        self.frame_dir_edit = QLineEdit()
        self.fps_edit = QLineEdit()
        
        # 添加浏览按钮
        video_dir_layout = QHBoxLayout()
        video_dir_layout.addWidget(self.video_dir_edit)
        video_dir_browse = QPushButton("浏览...")
        video_dir_browse.clicked.connect(lambda: self.browse_directory(self.video_dir_edit))
        video_dir_layout.addWidget(video_dir_browse)
        
        frame_dir_layout = QHBoxLayout()
        frame_dir_layout.addWidget(self.frame_dir_edit)
        frame_dir_browse = QPushButton("浏览...")
        frame_dir_browse.clicked.connect(lambda: self.browse_directory(self.frame_dir_edit))
        frame_dir_layout.addWidget(frame_dir_browse)
        
        layout.addRow("视频目录:", video_dir_layout)
        layout.addRow("帧目录:", frame_dir_layout)
        layout.addRow("抽帧FPS:", self.fps_edit)
        
        tab.setLayout(layout)
        return tab
    
    def create_tasks_tab(self):
        """创建任务配置标签页"""
        tab = QGroupBox("任务设置")
        layout = QFormLayout()
        
        self.history_file_edit = QLineEdit()
        self.log_dir_edit = QLineEdit()
        
        # 添加浏览按钮
        log_dir_layout = QHBoxLayout()
        log_dir_layout.addWidget(self.log_dir_edit)
        log_dir_browse = QPushButton("浏览...")
        log_dir_browse.clicked.connect(lambda: self.browse_directory(self.log_dir_edit))
        log_dir_layout.addWidget(log_dir_browse)
        
        layout.addRow("历史记录文件:", self.history_file_edit)
        layout.addRow("日志目录:", log_dir_layout)
        
        tab.setLayout(layout)
        return tab
    
    def browse_directory(self, line_edit):
        """浏览并选择目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录")
        if directory:
            line_edit.setText(directory)
    
    def load_config(self):
        """加载当前配置到界面"""
        # API配置
        self.api_key_edit.setText(self.config_manager.get('api_key', ''))
        self.api_host_edit.setText(self.config_manager.get('api_host', ''))
        
        # 模型配置
        self.vlm_model_edit.setText(self.config_manager.get('models.vlm_model_ep', ''))
        self.uitars_model_edit.setText(self.config_manager.get('models.uitars_model_ep', ''))
        self.planning_model_edit.setText(self.config_manager.get('models.planning_model_ep', ''))
        
        # 知识库配置
        self.video_dir_edit.setText(self.config_manager.get('knowledge_base.video_dir', ''))
        self.frame_dir_edit.setText(self.config_manager.get('knowledge_base.frame_dir', ''))
        self.fps_edit.setText(str(self.config_manager.get('knowledge_base.fps', 0.5)))
        
        # 任务配置
        self.history_file_edit.setText(self.config_manager.get('tasks.history_file', ''))
        self.log_dir_edit.setText(self.config_manager.get('tasks.log_dir', ''))
    
    def save_config(self):
        """保存配置"""
        try:
            # API配置
            self.config_manager.set('api_key', self.api_key_edit.text())
            self.config_manager.set('api_host', self.api_host_edit.text())
            
            # 模型配置
            self.config_manager.set('models.vlm_model_ep', self.vlm_model_edit.text())
            self.config_manager.set('models.uitars_model_ep', self.uitars_model_edit.text())
            self.config_manager.set('models.planning_model_ep', self.planning_model_edit.text())
            
            # 知识库配置
            self.config_manager.set('knowledge_base.video_dir', self.video_dir_edit.text())
            self.config_manager.set('knowledge_base.frame_dir', self.frame_dir_edit.text())
            try:
                fps = float(self.fps_edit.text())
                self.config_manager.set('knowledge_base.fps', fps)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "FPS必须是一个有效的数字")
                return
            
            # 任务配置
            self.config_manager.set('tasks.history_file', self.history_file_edit.text())
            self.config_manager.set('tasks.log_dir', self.log_dir_edit.text())
            
            # 保存成功后关闭对话框
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错: {str(e)}")