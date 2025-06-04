import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QFileDialog,
                             QMessageBox, QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from core.video_processor import VideoProcessor
from core.knowledge_service import KnowledgeService

class VideoProcessingThread(QThread):
    progress_updated = pyqtSignal(int)
    processing_complete = pyqtSignal(bool, str)
    
    def __init__(self, video_path, output_dir, fps,config_manager):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.fps = fps
        self.config_manager = config_manager
        self.processor = VideoProcessor(config_manager)
    
    def run(self):
        try:
            self.processor.extract_frames(self.video_path, self.output_dir, self.fps, 
                                          progress_callback=self.progress_updated.emit)
            self.processing_complete.emit(True, "视频处理完成")
        except Exception as e:
            self.processing_complete.emit(False, f"处理失败: {str(e)}")

class KnowledgePanel(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.knowledge_service = KnowledgeService(config_manager)
        
        self.init_ui()
        self.refresh()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        
        # 视频列表组
        video_group = QGroupBox("视频列表")
        video_layout = QVBoxLayout()
        
        # 视频列表和按钮
        self.video_list = QListWidget()
        self.video_list.itemDoubleClicked.connect(self.process_video)
        
        video_buttons_layout = QHBoxLayout()
        self.add_video_button = QPushButton("添加视频")
        self.add_video_button.clicked.connect(self.add_video)
        self.process_video_button = QPushButton("处理视频")
        self.process_video_button.clicked.connect(self.process_selected_video)
        self.remove_video_button = QPushButton("删除视频")
        self.remove_video_button.clicked.connect(self.remove_video)
        
        video_buttons_layout.addWidget(self.add_video_button)
        video_buttons_layout.addWidget(self.process_video_button)
        video_buttons_layout.addWidget(self.remove_video_button)
        
        video_layout.addWidget(self.video_list)
        video_layout.addLayout(video_buttons_layout)
        
        video_group.setLayout(video_layout)
        
        # 处理进度组
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label = QLabel("就绪")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        
        # 已处理视频组
        processed_group = QGroupBox("已处理视频")
        processed_layout = QVBoxLayout()
        
        self.processed_list = QListWidget()
        
        processed_layout.addWidget(self.processed_list)
        
        processed_group.setLayout(processed_layout)
        
        # 添加到主布局
        main_layout.addWidget(video_group, 3)  # 权重3
        main_layout.addWidget(progress_group, 1)  # 权重1
        main_layout.addWidget(processed_group, 2)  # 权重2
        
        self.setLayout(main_layout)
    
    def refresh(self):
        """刷新面板数据"""
        self.video_list.clear()
        self.processed_list.clear()
        
        # 获取视频目录
        video_dir = self.config_manager.get('knowledge_base.video_dir', '')
        if not video_dir or not os.path.exists(video_dir):
            return
        
        # 获取帧目录
        frame_dir = self.config_manager.get('knowledge_base.frame_dir', '')
        if not frame_dir:
            return
        
        # 加载视频列表
        video_files = [f for f in os.listdir(video_dir) 
                      if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
        
        for video_file in video_files:
            item = QListWidgetItem(video_file)
            self.video_list.addItem(item)
        
        # 加载已处理视频列表
        processed_videos = self.knowledge_service.get_processed_videos()
        for video_name in processed_videos:
            item = QListWidgetItem(video_name)
            self.processed_list.addItem(item)
    
    def add_video(self):
        """添加视频文件"""
        video_dir = self.config_manager.get('knowledge_base.video_dir', '')
        if not video_dir:
            QMessageBox.warning(self, "配置错误", "请先在配置中设置视频目录")
            return
        
        # 确保目录存在
        os.makedirs(video_dir, exist_ok=True)
        
        # 选择视频文件
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if not file_paths:
            return
        
        # 复制视频文件到视频目录
        import shutil
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(video_dir, file_name)
            
            try:
                shutil.copy2(file_path, dest_path)
                item = QListWidgetItem(file_name)
                self.video_list.addItem(item)
            except Exception as e:
                QMessageBox.warning(self, "添加失败", f"添加视频 {file_name} 失败: {str(e)}")
    
    def process_selected_video(self):
        """处理选中的视频"""
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要处理的视频")
            return
        
        self.process_video(selected_items[0])
    
    def process_video(self, item):
        """处理视频"""
        video_name = item.text()
        video_dir = self.config_manager.get('knowledge_base.video_dir', '')
        frame_dir = self.config_manager.get('knowledge_base.frame_dir', '')
        fps = float(self.config_manager.get('knowledge_base.fps', 0.5))
        
        if not video_dir or not frame_dir:
            QMessageBox.warning(self, "配置错误", "请先在配置中设置视频目录和帧目录")
            return
        
        # 确保目录存在
        os.makedirs(frame_dir, exist_ok=True)
        
        video_path = os.path.join(video_dir, video_name)
        output_dir = os.path.join(frame_dir, os.path.splitext(video_name)[0])
        
        # 创建并启动处理线程
        self.processing_thread = VideoProcessingThread(video_path, output_dir, fps,self.config_manager)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_complete.connect(self.processing_finished)
        
        # 禁用按钮，防止重复操作
        self.add_video_button.setEnabled(False)
        self.process_video_button.setEnabled(False)
        self.remove_video_button.setEnabled(False)
        
        # 更新状态
        self.status_label.setText(f"正在处理: {video_name}")
        self.progress_bar.setValue(0)
        
        # 启动线程
        self.processing_thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def processing_finished(self, success, message):
        """处理完成回调"""
        # 恢复按钮状态
        self.add_video_button.setEnabled(True)
        self.process_video_button.setEnabled(True)
        self.remove_video_button.setEnabled(True)
        
        # 更新状态
        self.status_label.setText(message)
        
        if success:
            # 刷新已处理视频列表
            self.refresh()
            QMessageBox.information(self, "处理完成", message)
        else:
            QMessageBox.warning(self, "处理失败", message)
    
    def remove_video(self):
        """删除选中的视频"""
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的视频")
            return
        
        video_name = selected_items[0].text()
        video_dir = self.config_manager.get('knowledge_base.video_dir', '')
        
        if not video_dir:
            return
        
        video_path = os.path.join(video_dir, video_name)
        
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", f"确定要删除视频 {video_name} 吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(video_path)
                # 从列表中移除
                self.video_list.takeItem(self.video_list.row(selected_items[0]))
                QMessageBox.information(self, "删除成功", f"视频 {video_name} 已删除")
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"删除视频 {video_name} 失败: {str(e)}")