import os
import json

class KnowledgeService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def get_processed_videos(self):
        """获取已处理的视频列表"""
        frame_dir = self.config_manager.get('knowledge_base.frame_dir', '')
        if not frame_dir or not os.path.exists(frame_dir):
            return []
        
        # 查找包含frame_descriptions.txt文件的子目录
        processed_videos = []
        for item in os.listdir(frame_dir):
            item_path = os.path.join(frame_dir, item)
            if os.path.isdir(item_path):
                desc_file = os.path.join(item_path, "frame_descriptions.txt")
                if os.path.exists(desc_file):
                    processed_videos.append(item)
        
        return processed_videos
    
    def get_frame_descriptions(self, video_name):
        """获取指定视频的帧描述"""
        frame_dir = self.config_manager.get('knowledge_base.frame_dir', '')
        if not frame_dir:
            return ""
        
        desc_file = os.path.join(frame_dir, video_name, "frame_descriptions.txt")
        if not os.path.exists(desc_file):
            return ""
        
        with open(desc_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def get_frames(self, video_name):
        """获取指定视频的所有帧文件路径"""
        frame_dir = self.config_manager.get('knowledge_base.frame_dir', '')
        if not frame_dir:
            return []
        
        video_frame_dir = os.path.join(frame_dir, video_name)
        if not os.path.exists(video_frame_dir):
            return []
        
        frames = [os.path.join(video_frame_dir, f) 
                 for f in os.listdir(video_frame_dir) 
                 if f.lower().endswith('.jpg')]
        
        return sorted(frames)