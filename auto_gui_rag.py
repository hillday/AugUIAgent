# 智能桌面操作系统核心逻辑示例（Python）
# 涵盖：视频抽帧、豆包视觉API调用、DeepSeek任务推理、UI-TARS决策、PyAutoGUI自动操作

import os
import base64
import requests
import json
import time
import cv2
import pyautogui
from collections import deque

# 配置
api_key = os.environ.get("ARK_API_KEY")
api_host = "https://ark.cn-beijing.volces.com/api/v3"
# 视觉理解模型EP
vlm_model_ep = 'ep-20250418110236-jmbdw'
# 滑动窗口大小（保留前N帧的信息）
WINDOW_SIZE = 3

# ----------- 1. 视频抽帧 -----------
def extract_frames(video_path, output_dir, fps=1):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    interval = int(video_fps / fps)
    count, saved = 0, 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            filename = os.path.join(output_dir, f"frame_{saved:04}.jpg")
            cv2.imwrite(filename, frame)
            saved += 1
        count += 1
    cap.release()

# ----------- 2. 豆包视觉API调用 -----------
def encode_image_base64(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"

def chat(messages, model, retries=1):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    for attempt in range(retries):
        try:
            data = {
                'model': model,
                'messages': messages,
                'temperature': 0.8
            }
            response = requests.post(f'{api_host}/chat/completions', headers=headers, json=data)
            
            response_data = response.json()
            #print(response_data)
            response_content = response_data['choices'][0]['message']['content']
            return response_content
        except Exception as e:
            print(f"Chat error: {e}, attempt {attempt + 1} of {retries}")
            time.sleep(2)
    return "错误: 无法获取响应"

def analyze_frame_doubao(image_path, previous_descriptions=None):
    """
    分析当前帧，并结合之前帧的描述信息
    
    Args:
        image_path: 当前帧图像路径
        previous_descriptions: 之前帧的描述信息列表，格式为[(frame_name, description), ...]
    
    Returns:
        当前帧的描述
    """
    image_data = encode_image_base64(image_path)
    
    # 构建提示，包含历史帧信息
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
    
    response = chat(messages, model=vlm_model_ep)
    return response

# ----------- 主流程 -----------
def main():
    if not api_key:
        raise ValueError("请设置ARK_API_KEY环境变量")
    frame_dir = "frames"
    try:
        video_path = "xiaohs.mp4"
        extract_frames(video_path, frame_dir, fps=0.5)
    
        # 使用滑动窗口保存前N帧的描述
        frame_window = deque(maxlen=WINDOW_SIZE)
        all_frame_descriptions = []

        # 获取并排序所有帧
        all_frames = sorted(os.listdir(frame_dir))
        
        for fname in all_frames:
            print(f"处理帧: {fname}")
            path = os.path.join(frame_dir, fname)
            
            # 将前几帧的描述作为上下文传递给分析函数
            desc = analyze_frame_doubao(path, list(frame_window))
            print(f"描述: {desc}")
            
            # 保存当前帧信息
            frame_window.append((fname, desc))
            all_frame_descriptions.append(f"{fname}: {desc}")
            
            # 每处理5帧保存一次结果，避免意外中断丢失数据
            if len(all_frame_descriptions) % 5 == 0:
                temp_output = "\n\n".join(all_frame_descriptions)
                with open("frame_descriptions_temp.txt", "w", encoding="utf-8") as f:
                    f.write(temp_output)

        # 最终结果保存
        # 为了更好地展示操作序列，使用双空行分隔每个帧的描述
        output_content = "\n\n".join(all_frame_descriptions)
        with open("frame_descriptions.txt", "w", encoding="utf-8") as f:
            f.write(output_content)
        
        # 生成操作摘要
        generate_operation_summary(all_frame_descriptions)
        
    except ValueError as e:
        print(f"错误: {e}")
        return

def generate_operation_summary(frame_descriptions):
    """
    基于所有帧的描述，生成整个视频的操作摘要
    """
    if not frame_descriptions:
        return
    
    # 构建提示，请求模型总结整个操作流程
    prompt = "以下是一段视频中各帧的界面和操作描述，请总结用户在整个视频中执行的完整操作流程，按时间顺序列出关键步骤："
    for desc in frame_descriptions:
        prompt += f"\n{desc}"
    
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    summary = chat(messages, model=vlm_model_ep)
    
    # 保存操作摘要
    with open("operation_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    
    print("已生成操作摘要: operation_summary.txt")

# 示例用法
if __name__ == "__main__":
    main()