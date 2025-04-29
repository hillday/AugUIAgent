# 智能桌面操作系统核心逻辑示例（Python）
# 涵盖：视频抽帧、豆包视觉API调用、DeepSeek任务推理、UI-TARS决策、PyAutoGUI自动操作

import os
import base64
import requests
import json
import time
import cv2
import pyautogui

# 配置
api_key = os.environ.get("ARK_API_KEY")
api_host = "https://ark.cn-beijing.volces.com/api/v3"
vlm_model_ep = 'ep-20250418110236-jmbdw'

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

def chat(messages,model, retries=1):
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

def analyze_frame_doubao(image_path):
    image_data = encode_image_base64(image_path)
    messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述该截图中的界面元素（主要是可能能被操作，比如点击，输入，拖拽的元素）和用户正在进行的操作，简洁明了，不超过500字。"},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            }
        ]
    response = chat(messages,model=vlm_model_ep)
    return response

# ----------- 主流程 -----------
def main():
    if not api_key:
        raise ValueError("请设置ARK_API_KEY环境变量")
    frame_dir = "frames"
    try:
        
        video_path = "demo5.mp4"
        extract_frames(video_path, frame_dir, fps=0.5)
    
        frame_descriptions = []

        for fname in sorted(os.listdir(frame_dir)):
            print(f"Frame:{fname}")
            path = os.path.join(frame_dir, fname)
            desc = analyze_frame_doubao(path)
            print(f"Desc:{desc}")
            frame_descriptions.append(f"{fname}: {desc}")

        # 新增代码：将描述拼接并写入文件
        output_content = "\n".join(frame_descriptions)
        with open("frame_descriptions.txt", "w", encoding="utf-8") as f:
            f.write(output_content)
        
    except ValueError as e:
        print(f"错误: {e}")
        return

# 示例用法
if __name__ == "__main__":
    main()
