import os
import json
import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QTextEdit,
                             QMessageBox, QGroupBox, QSplitter, QComboBox,
                             QPlainTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize

from core.task_service import TaskService

class TaskExecutionThread(QThread):
    progress_updated = pyqtSignal(str)
    execution_complete = pyqtSignal(bool, str)
    
    def __init__(self, task_service, task_description, processed_video):
        super().__init__()
        self.task_service = task_service
        self.task_description = task_description
        self.processed_video = processed_video
    
    def run(self):
        try:
            self.task_service.execute_task(
                self.task_description,
                self.processed_video,
                progress_callback=self.progress_updated.emit
            )
            self.execution_complete.emit(True, "任务执行完成")
        except Exception as e:
            self.execution_complete.emit(False, f"执行失败: {str(e)}")

class TaskPanel(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.task_service = TaskService(config_manager)
        
        self.init_ui()
        self.refresh()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 任务创建组
        task_create_group = QGroupBox("创建任务")
        task_create_layout = QVBoxLayout()
        
        # 选择已处理视频
        video_layout = QHBoxLayout()
        video_layout.addWidget(QLabel("选择已处理视频:"))
        self.video_combo = QComboBox()
        video_layout.addWidget(self.video_combo)
        
        # 任务描述
        task_create_layout.addLayout(video_layout)
        task_create_layout.addWidget(QLabel("任务描述:"))
        self.task_description = QPlainTextEdit()
        self.task_description.setPlaceholderText("输入任务描述，例如：找三个关于筑梦岛的帖子，打开点赞数超过200的帖子，给点赞，并且给热门的评论添加回复'我也喜欢'")
        task_create_layout.addWidget(self.task_description)
        
        # 执行按钮
        buttons_layout = QHBoxLayout()
        self.execute_button = QPushButton("执行任务")
        self.execute_button.clicked.connect(self.execute_task)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.execute_button)
        task_create_layout.addLayout(buttons_layout)
        
        task_create_group.setLayout(task_create_layout)
        
        # 任务历史组
        task_history_group = QGroupBox("任务历史")
        task_history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.show_task_details)
        
        task_history_layout.addWidget(self.history_list)
        
        task_history_group.setLayout(task_history_layout)
        
        # 任务详情组
        task_details_group = QGroupBox("任务详情")
        task_details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        
        task_details_layout.addWidget(self.details_text)
        
        task_details_group.setLayout(task_details_layout)
        
        # 添加到分割器
        splitter.addWidget(task_create_group)
        splitter.addWidget(task_history_group)
        splitter.addWidget(task_details_group)
        
        # 设置初始大小
        splitter.setSizes([200, 200, 200])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def refresh(self):
        """刷新面板数据"""
        self.history_list.clear()
        self.details_text.clear()
        self.video_combo.clear()
        
        # 加载已处理视频列表
        from core.knowledge_service import KnowledgeService
        knowledge_service = KnowledgeService(self.config_manager)
        processed_videos = knowledge_service.get_processed_videos()
        
        for video_name in processed_videos:
            self.video_combo.addItem(video_name)
        
        # 加载任务历史
        task_history = self.task_service.get_task_history()
        
        for task in reversed(task_history):  # 最新的任务显示在前面
            timestamp = datetime.datetime.fromtimestamp(task['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            item = QListWidgetItem(f"{timestamp} - {task['description'][:30]}...")
            item.setData(Qt.UserRole, task)  # 存储完整任务数据
            self.history_list.addItem(item)
    
    def execute_task(self):
        """执行任务"""
        task_description = self.task_description.toPlainText().strip()
        if not task_description:
            QMessageBox.warning(self, "输入错误", "请输入任务描述")
            return
        
        if self.video_combo.count() == 0:
            QMessageBox.warning(self, "错误", "没有可用的已处理视频，请先处理视频")
            return
        
        processed_video = self.video_combo.currentText()
        
        # 确认执行
        reply = QMessageBox.question(
            self, "确认执行", 
            f"确定要执行以下任务吗？\n\n{task_description}\n\n执行过程中应用将最小化。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 创建并启动执行线程
            self.execution_thread = TaskExecutionThread(
                self.task_service, task_description, processed_video
            )
            self.execution_thread.progress_updated.connect(self.update_progress)
            self.execution_thread.execution_complete.connect(self.execution_finished)
            
            # 禁用执行按钮
            self.execute_button.setEnabled(False)
            
            # 最小化应用窗口
            self.window().showMinimized()
            
            # 启动线程
            self.execution_thread.start()
    
    def update_progress(self, message):
        """更新进度信息"""
        self.details_text.append(message)
    
    def execution_finished(self, success, message):
        """执行完成回调"""
        # 恢复窗口
        self.window().showNormal()
        self.window().activateWindow()
        
        # 恢复按钮状态
        self.execute_button.setEnabled(True)
        
        # 更新状态
        self.details_text.append(f"\n{message}")
        
        if success:
            # 刷新任务历史
            self.refresh()
            QMessageBox.information(self, "执行完成", message)
        else:
            QMessageBox.warning(self, "执行失败", message)
    
    def show_task_details(self, item):
        """显示任务详情"""
        task = item.data(Qt.UserRole)
        if not task:
            return
        
        # 格式化任务详情
        timestamp = datetime.datetime.fromtimestamp(task['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        details = f"<h3>任务详情</h3>"
        details += f"<p><b>时间:</b> {timestamp}</p>"
        details += f"<p><b>视频:</b> {task.get('video', '未知')}</p>"
        details += f"<p><b>描述:</b> {task['description']}</p>"
        details += f"<p><b>状态:</b> {task.get('status', '未知')}</p>"
        
        if 'log' in task and task['log']:
            details += f"<h4>执行日志:</h4>"
            details += f"<pre>{task['log']}</pre>"
        
        self.details_text.setHtml(details)