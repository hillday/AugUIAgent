import os
import cv2
import base64
import requests
import json
import time
from collections import deque
import sys
from PIL import Image # 导入Pillow库
import io # 导入io模块
sys.path.append("..")
from utils.logger import logger as Logger

class VideoProcessor:
    def __init__(self, config_manager):
        self.config_manager = config_manager # 新增
        self.frame_window = deque(maxlen=self.config_manager.get("knowledge_base.window_size", 3)) # 新增，假设window_size在配置中
        # 您可能需要在 settings.json 的 knowledge_base 部分添加 "window_size": 3
    
    def _encode_image_base64(self, image_path, quality=80): # 增加quality参数，默认为80
        """将图片文件编码为Base64字符串，并在编码前进行压缩"""
        try:
            # 打开图片
            img = Image.open(image_path)
            
            # 将图片保存到内存中的字节流，并进行JPEG压缩
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr = img_byte_arr.getvalue()
            
            # 编码为Base64字符串
            return f"data:image/jpeg;base64,{base64.b64encode(img_byte_arr).decode()}"
        except Exception as e:
            Logger.error(f"图像编码或压缩失败: {e}")
            return None

    def _chat(self, messages, model_ep, retries=1):
        
        """调用聊天API"""
        api_key = self.config_manager.get_api_key()
        api_host = self.config_manager.get("api_host")
        
        if not api_key:
            # self.logger.error("API Key not configured.") # 假设有logger
            Logger.error("API Key 未配置.")
            return "错误: API Key 未配置."

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        for attempt in range(retries):
            try:
                data = {
                    'model': model_ep,
                    'messages': messages,
                    'temperature': 0.8
                }
                #Logger.debug(f"Sending request to Chat API: {data}")
                response = requests.post(f'{api_host}/chat/completions', headers=headers, json=data)
                response.raise_for_status() # 检查HTTP错误
                response_data = response.json()
                if 'choices' not in response_data or not response_data['choices']:
                    # self.logger.error(f"API响应格式错误: {response_data}")
                    Logger.error(f"API响应格式错误: {response_data}")
                    return "错误: API响应格式无效"
                response_content = response_data['choices'][0]['message']['content']
                return response_content
            except requests.exceptions.RequestException as e:
                # self.logger.error(f"Chat API request error: {e}, attempt {attempt + 1} of {retries}")
                Logger.error(f"Chat API 请求错误: {e}, 尝试次数 {attempt + 1} / {retries}")
                time.sleep(2)
            except Exception as e:
                # self.logger.error(f"Chat error: {e}, attempt {attempt + 1} of {retries}")
                Logger.error(f"Chat 错误: {e}, 尝试次数 {attempt + 1} / {retries}")
                time.sleep(2)
        return "错误: 无法获取响应"

    def _analyze_frame_doubao(self, image_path, previous_descriptions=None):
        """
        分析当前帧，并结合之前帧的描述信息
        
        Args:
            image_path: 当前帧图像路径
            previous_descriptions: 之前帧的描述信息列表，格式为[(frame_name, description), ...]
        
        Returns:
            当前帧的描述
        """
        image_data = self._encode_image_base64(image_path)
        vlm_model_ep = self.config_manager.get_model_ep("vlm_model_ep")

        if not vlm_model_ep:
            # self.logger.error("VLM model endpoint not configured.")
            Logger.error("错误: VLM 模型端点未配置.")
            return "错误: VLM 模型端点未配置."
        
        prompt = "请描述该截图中的界面元素（主要是可能能被操作，比如点击，输入，拖拽的元素）和用户正在进行的操作，简洁明了，不超过500字。"
        
        if previous_descriptions and len(previous_descriptions) > 0:
            history_context = "\n\n前几帧的操作描述：\n"
            for idx, (frame_name, desc) in enumerate(previous_descriptions):
                history_context += f"帧{frame_name}: {desc}\n"
            
            prompt = f"{prompt}\n\n{history_context}\n请结合前几帧的操作上下文，更准确地描述当前帧中用户正在进行的操作，特别关注操作的连续性和变化。"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            }
        ]
        
        response = self._chat(messages, model_ep=vlm_model_ep)
        return response

    def extract_frames(self, video_path, output_dir, fps=1, progress_callback=None):
        """从视频中提取帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            fps: 每秒提取的帧数
            progress_callback: 进度回调函数
        """
        os.makedirs(output_dir, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        
        # 获取视频信息
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = int(video_fps / fps)
        
        count, saved = 0, 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % interval == 0:
                filename = os.path.join(output_dir, f"frame_{saved:04d}.jpg")
                cv2.imwrite(filename, frame)
                saved += 1
            
            count += 1
        
        cap.release()

        
        # 创建帧描述文件
        self.create_frame_descriptions(output_dir, os.path.join(output_dir, "frame_descriptions.txt"), progress_callback)
        
        return saved
    
    def create_frame_descriptions(self, frames_dir, output_file, progress_callback=None):
        """创建帧描述文件"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        frames = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
        
        all_frame_descriptions = []
        self.frame_window.clear() # 清空历史记录以处理新视频
        count = 0
        total_frames = len(frames)

        for frame_name in frames:
            frame_path = os.path.join(frames_dir, frame_name)
            Logger.info(f"处理帧: {frame_name}") # 可以替换为logger
            
            # 将前几帧的描述作为上下文传递给分析函数
            description = self._analyze_frame_doubao(frame_path, list(self.frame_window))
            Logger.info(f"描述: {description}") # 可以替换为logger
            
            # 保存当前帧信息
            self.frame_window.append((frame_name, description))
            all_frame_descriptions.append(f"{frame_name}: {description}")

            if progress_callback and total_frames > 0:
                    progress = min(100, int(count * 100 / total_frames))
                    progress_callback(progress)

            count += 1
            
            # (可选) 每处理N帧保存一次临时结果，避免意外中断丢失数据
            # if len(all_frame_descriptions) % 5 == 0:
            #     temp_output_path = os.path.join(os.path.dirname(output_file), "frame_descriptions_temp.txt")
            #     with open(temp_output_path, "w", encoding="utf-8") as f_temp:
            #         f_temp.write("\n\n".join(all_frame_descriptions))

        # 确保进度达到100%
        if progress_callback:
            progress_callback(100)
        # 保存最终描述
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_frame_descriptions))
        
        Logger.info(f"帧描述已保存到: {output_file}") # 可以替换为logger
        return output_file

    def generate_operation_summary(self, frame_descriptions_file, output_summary_file):
        """基于帧描述文件生成操作摘要"""
        if not os.path.exists(frame_descriptions_file):
            Logger.error(f"错误: 帧描述文件不存在 {frame_descriptions_file}")
            return

        with open(frame_descriptions_file, "r", encoding="utf-8") as f:
            descriptions_content = f.read()
        
        # 简单地按双换行符分割，因为我们之前是这样保存的
        # 如果帧描述本身可能包含双换行，需要更鲁棒的解析
        individual_descriptions = descriptions_content.split("\n\n")
        if not individual_descriptions or (len(individual_descriptions) == 1 and not individual_descriptions[0].strip()):
            Logger.error("错误: 帧描述内容为空或格式不正确")
            return

        planning_model_ep = self.config_manager.get_model_ep("planning_model_ep") # 使用规划模型进行总结
        if not planning_model_ep:
            Logger.error("错误: Planning model endpoint 未配置.")
            return "错误: Planning model endpoint 未配置."

        prompt = "以下是一段视频中各帧的界面和操作描述，请总结用户在整个视频中执行的完整操作流程，按时间顺序列出关键步骤：\n"
        prompt += descriptions_content # 直接使用文件内容作为上下文
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        summary = self._chat(messages, model_ep=planning_model_ep)
        
        # 保存操作摘要
        os.makedirs(os.path.dirname(output_summary_file), exist_ok=True)
        with open(output_summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        Logger.info(f"操作摘要已生成: {output_summary_file}")
        return output_summary_file