# 智能桌面操作系统核心逻辑示例（Python）
# 涵盖：视频抽帧、豆包视觉API调用、DeepSeek任务推理、UI-TARS决策、PyAutoGUI自动操作

import os
import base64
import requests
import json
import time
import cv2
import pyautogui

pyautogui.FAILSAFE = False
# 配置
api_key = os.environ.get("ARK_API_KEY")
api_host = "https://ark.cn-beijing.volces.com/api/v3"

# 视觉理解模型EP
vlm_model_ep = 'ep-20250418110236-jmbdw'
# UI TARS理解模型EP
uitars_model_ep = 'ep-20250417185159-jzzlk'
# 深度理解模型EP
planning_model_ep = 'ep-20250417185051-xg7xf'

uitars_command={
    "click":{"start_box":[0,0,0,0]},
    "left_double":{"start_box":[0,0,0,0]},
    "right_single":{"start_box":[0,0,0,0]},
    "drag":{"start_box":[0,0,0,0],"end_box":[0,0,0,0]},
    "hotkey":"",
    "type":"",
    "scroll":{"start_box":[0,0,0,0],"direction":""},
    "wait": 5,
    "finished": ""
}

action_records = []

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

# ----------- 3. DeepSeek推理 -----------
def plan_from_deepseek(frames_descriptions,task_description,operation_summary=""):
    system_prompt = f"""
    你是一个智能助手，根据以下用户界面描述和任务描述，生成操作计划，使用JSON输出,直接输出结果，不需要任何标签、说明。
    界面描述：
    {frames_descriptions}
    界面操作描述：
    {operation_summary}

    输出格式如下:
   {{"steps":[{{"instruction": "打开微信", "step": 0}}], "loop_count": 100}}
    `steps`为步骤集合，里面只需要有原子步骤，不需要包含重复指令步骤，如`返回搜索结果页，重复步骤3-6处`的步骤不需要,`instruction` 为步骤具体指令，需要尽量的具体，`step` 为步骤序号，从0开始。
    
    如果任务需要循环执行整个流程多次，请在JSON中添加一个额外的字段 `loop_count`，表示整个流程需要循环执行的次数，比如刷三个视频/帖子，就是要循环三次。
    例如：{{"steps":[{{"instruction": "打开微信", "step": 0}}, {{"instruction": "发送消息", "step": 1}}], "loop_count": 100}}
    
    务必只输出json, 直接输出内容，不要输出其他任何格式标签，如markdown json标签。

    任务描述：

    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(task_description)}
    ]

    response = chat(messages,model=planning_model_ep)
    return response

# ----------- 4. UI-TARS 决策 -----------
def screenshot():
    image_path = "current_screen.jpg"
    pyautogui.screenshot(image_path)
    return image_path


# 辅助解析函数
def parse_box_coordinates(action_text):
    """从action文本中解析坐标框<bbox>986 15 986 15</bbox>"""
    # 处理bbox格式
    bbox_start = action_text.find("<bbox>") + len("<bbox>")
    bbox_end = action_text.find("</bbox>")
    bbox_str = action_text[bbox_start:bbox_end]
    bbox = [int(x) for x in bbox_str.split()]

    return bbox

def parse_drag_coordinates(action_text):
    """解析拖拽操作的起始和结束坐标"""
    import re
    # 同时提取两个坐标
    matches = re.findall(r"<bbox>([\d\s]+)</bbox>", action_text)
    start_box = list(map(int, matches[0].split()))
    end_box = list(map(int, matches[1].split()))

    return (start_box,end_box)

def parse_key_content(action_text):
    """解析hotkey或type的内容"""
    start = action_text.find("'") + 1
    end = action_text.rfind("'")
    return action_text[start:end]

def parse_scroll_data(action_text):
    """解析滚动操作的数据"""
    import re
    direction_match = re.search(r"direction\s*=\s*'(.*?)'", action_text)
    direction = direction_match.group(1) if direction_match else "down"
    
    # 提取 start_box 的坐标（格式：<bbox>x1 y1 x2 y2</bbox>）
    start_box_match = re.search(r"start_box\s*=\s*'<bbox>(.*?)</bbox>'", action_text)
    if start_box_match:
        start_box = list(map(int, start_box_match.group(1).split()))
    else:
        start_box = [0, 0, 0, 0]  # 或设为默认值，如 [0, 0, 0, 0]
    return (start_box, direction)

def parse_finished_content(action_text):
    """解析finished操作的内容"""
    start = action_text.find("content='") + len("content='")
    end = action_text.rfind("'")
    return action_text[start:end].replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")

def check_step_is_finished(image_paths, command_text, last_response=None):
    system_prompt = f"""
    你是一个智能的UI页面状态判断专家，需要判断当前输入指令下，页面是否完成相关操作.
    ## 上一个指令
    {last_response if last_response else "No previous action"}
    ## 输出要求，只要输出已经完成或者未完成就行，不需要输出其他内容
    ```
    finished（表示已经完成）/ no(未完成)
    ```
    ## 当前指令
    {command_text}

    ## 示例
    - 用户指令："给短视频点赞"，输入图像对比之前图像有颜色改变（一般是红色或者黄色），未点赞一般是灰色
    - 输出： finished
    """

    image_contents = []
    for path in image_paths:
        image_data = encode_image_base64(path)
        image_contents.append({"type": "image_url", "image_url": {"url": image_data}})
    
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": image_contents
        }
    ]
    
    messages = [
        {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            }
        ]
    response = chat(messages,model=vlm_model_ep)

    return response

def query_uitars(image_paths, command_text, last_response=None):
    system_prompt = f"""
    You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task.
    ## Previous Action
    {last_response if last_response else "No previous action"}
    ## Output Format
    ```
    Thought: ...
    Action: ...
    ```
    ## Action Space
    click(start_box='[x1, y1, x2, y2]')
    left_double(start_box='[x1, y1, x2, y2]')
    right_single(start_box='[x1, y1, x2, y2]')
    drag(start_box='[x1, y1, x2, y2]', end_box='[x3, y3, x4, y4]')
    hotkey(key='')
    type(content='') #If you want to submit your input, use "\n" at the end of `content`.
    scroll(start_box='[x1, y1, x2, y2]', direction='down or up or right or left')
    wait() #Sleep for 5s and take a screenshot to check for any changes.
    finished(content='xxx') # Use escape characters \\', \\", and \\n in content part to ensure we can parse the content in normal python string format.
    ## Note
    - Use Chinese in `Thought` part.
    - Write a small plan and finally summarize your next action (with its target element) in one sentence in `Thought` part.
    ## User Instruction
    {command_text}
    """

    image_contents = []
    for path in image_paths:
        image_data = encode_image_base64(path)
        image_contents.append({"type": "image_url", "image_url": {"url": image_data}})
    
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": image_contents
        }
    ]
    
    messages = [
        {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            }
        ]
    response = chat(messages,model=uitars_model_ep)
  
    # 解析响应为JSON格式
    try:
        # 提取Thought部分
        thought_start = response.find("Thought:") + len("Thought:")
        thought_end = response.find("Action:")
        result = {
            "thought": response[thought_start:thought_end].strip()
        }
        
        # 提取Action部分
        action_start = response.find("Action:") + len("Action:")
        action_text = response[action_start:].strip()

      
        global uitars_command
    
        print(f"Action {action_text}")
        # 解析Action并更新uitars_command
        if action_text.startswith("click"):
            result["action"] = "click"
            uitars_command["click"] = {"start_box": parse_box_coordinates(action_text)}
        elif action_text.startswith("left_double"):
            result["action"] = "left_double"
            uitars_command["left_double"] = {"start_box": parse_box_coordinates(action_text)}
        elif action_text.startswith("right_single"):
            result["action"] = "right_single"
            uitars_command["right_single"] = {"start_box": parse_box_coordinates(action_text)}
        elif action_text.startswith("drag"):
            result["action"] = "drag"
            start_end = parse_drag_coordinates(action_text)
            uitars_command["drag"] = {
                "start_box": start_end[0],
                "end_box": start_end[1]
            }
        elif action_text.startswith("hotkey"):
            result["action"] = "hotkey"
            uitars_command["hotkey"] = parse_key_content(action_text)
        elif action_text.startswith("type"):
            result["action"] = "type"
            uitars_command["type"] = parse_key_content(action_text)
        elif action_text.startswith("scroll"):
            result["action"] = "scroll"
            scroll_data = parse_scroll_data(action_text)
            uitars_command["scroll"] = {
                "start_box": scroll_data[0],
                "direction": scroll_data[1]
            }
        elif action_text.startswith("wait"):
            result["action"] = "wait"
            uitars_command["wait"] = 5
        elif action_text.startswith("finished"):
            result["action"] = "finished"
            uitars_command["finished"] = parse_finished_content(action_text)
        else:
            result["action"] = "unknown"
            print(f"未知的Action: {action_text}")
        return result
        
    except Exception as e:
        print(f"解析UI-TARS响应失败: {e}")
        return {"error": str(e)}

# ----------- 5. 操作执行 -----------
def execute_action(action_data):
    global uitars_command
    #print(uitars_command)
    if "thought" in action_data:
        print(f"[Thought] {action_data['thought']}")
    
    if "action" in action_data:
        print(f"[Action] { action_data['action'] }")
        # 检查是否为未知动作
        if action_data["action"] == "unknown":
            raise ValueError("遇到未知动作类型，终止执行")
        # 获取屏幕尺寸用于坐标转换
        screen_width, screen_height = pyautogui.size()
        
        def convert_coords(box):
            """将相对坐标(0-1000范围)转换为绝对屏幕坐标"""
            x1 = round(screen_width * box[0] / 1000)
            y1 = round(screen_height * box[1] / 1000)
            x2 = round(screen_width * box[2] / 1000)
            y2 = round(screen_height * box[3] / 1000)
            return [x1, y1, x2, y2]
            
        if action_data["action"] == "click":
            box = convert_coords(uitars_command["click"]["start_box"])
            x = round((box[0] + box[2]) / 2)  # 取框的中心x坐标
            y = round((box[1] + box[3]) / 2)  # 取框的中心y坐标
            print(f"[Click] x={x}, y={y}")
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "x": x,
                "y": y,
                "timestamp": time.time()
            })
            pyautogui.moveTo(x, y)
            pyautogui.click()
            
        elif action_data["action"] == "left_double":
            box = convert_coords(uitars_command["left_double"]["start_box"])
            x = round((box[0] + box[2]) / 2)
            y = round((box[1] + box[3]) / 2)
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "x": x,
                "y": y,
                "timestamp": time.time()
            })
            pyautogui.moveTo(x, y)
            pyautogui.doubleClick()
            
        elif action_data["action"] == "right_single":
            box = convert_coords(uitars_command["right_single"]["start_box"])
            x = round((box[0] + box[2]) / 2)
            y = round((box[1] + box[3]) / 2)
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "x": x,
                "y": y,
                "timestamp": time.time()
            })
            pyautogui.moveTo(x, y)
            pyautogui.rightClick()
            
        elif action_data["action"] == "drag":
            start_box = convert_coords(uitars_command["drag"]["start_box"])
            end_box = convert_coords(uitars_command["drag"]["end_box"])
            start_x = round((start_box[0] + start_box[2]) / 2)
            start_y = round((start_box[1] + start_box[3]) / 2)
            end_x = round((end_box[0] + end_box[2]) / 2)
            end_y = round((end_box[1] + end_box[3]) / 2)
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "timestamp": time.time()
            })
            print(f"[Drag start end] x={start_x}, y={start_y},endx={end_x},endy={end_y}")
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y)
            
        elif action_data["action"] == "hotkey":
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "content":uitars_command["hotkey"].split('+'),
                "timestamp": time.time()
            })
            pyautogui.hotkey(*uitars_command["hotkey"].split('+'))
            
        elif action_data["action"] == "type":
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "content":uitars_command["type"],
                "timestamp": time.time()
            })
            # pyautogui.write(uitars_command["type"])
            # 先将文本复制到剪贴板
            import pyperclip
            pyperclip.copy(uitars_command["type"])
            # 然后使用快捷键粘贴
            pyautogui.hotkey('ctrl', 'v')
            
        elif action_data["action"] == "scroll":
            print(uitars_command["scroll"]["start_box"])
            box = convert_coords(uitars_command["scroll"]["start_box"])
            direction = uitars_command["scroll"]["direction"]
            x = round((box[0] + box[2]) / 2)
            y = round((box[1] + box[3]) / 2)
            
            if x == 0 or y == 0:
                x = 1500
                y = 1000
            pyautogui.moveTo(x, y)
            amount = -500 if direction == "down" else 500  # 滚动量
             # 记录操作
            action_records.append({
                "type": action_data["action"],
                "x":x,
                "y":y,
                "direction":direction,
                "timestamp": time.time()
            })
            pyautogui.scroll(amount)
            print(f"[Scroll move] x={x}, y={y + amount,},direction={direction}")
            # pyautogui.dragTo(x, y + amount, duration=1)
            
        elif action_data["action"] == "wait":
            # 记录操作
            action_records.append({
                "type": action_data["action"],
                "time": uitars_command["wait"],
                "timestamp": time.time(),
            })
            
            time.sleep(uitars_command["wait"])
            
def replay_actions(records_file=None, speed=1.0):
    """回放记录的操作
    :param records_file: 记录文件路径，如果为None则使用内存中的记录
    :param speed: 回放速度，1.0为原始速度
    """
    if records_file:
        with open(records_file, 'r') as f:
            records = json.load(f)
    else:
        records = action_records
    
    for i, record in enumerate(records):
        print(f"回放操作 {i+1}/{len(records)}: {record['type']}")
        
        if record['type'] == 'click':
            pyautogui.moveTo(record['x'], record['y'])
            pyautogui.click()
        elif record['type'] == 'double_click':
            pyautogui.moveTo(record['x'], record['y'])
            pyautogui.doubleClick()
        elif record['type'] == 'right_click':
            pyautogui.moveTo(record['x'], record['y'])
            pyautogui.rightClick()
        elif record['type'] == 'drag':
            pyautogui.moveTo(record['start_x'], record['start_y'])
            pyautogui.dragTo(record['end_x'], record['end_y'])
        elif record['type'] == 'hotkey':
            pyautogui.hotkey(*record['content'])
        elif record['type'] == 'type':
            pyautogui.write(record['content'])
        elif record['type'] == 'scroll':
            pyautogui.moveTo(record['x'], record['y'])
            amount = -100 if record['direction'] == 'up' else 100  # 滚动量
            pyautogui.scroll(amount)
        elif record['type'] == 'wait':
            time.sleep(record['time'])
        
        # 计算等待时间
        if i < len(records) - 1:
            wait_time = (records[i+1]['timestamp'] - record['timestamp']) / speed
            if wait_time > 0:
                time.sleep(wait_time)
        time.sleep(2)  # 每个操作之间的延迟

def save_action_records(filename):
    """保存操作记录到文件"""
    with open(filename, 'w') as f:
        json.dump(action_records, f, indent=2)
# ----------- 主流程 -----------
def main():
    if not api_key:
        raise ValueError("请设置ARK_API_KEY环境变量")
    try:
        # 从文件读取frame_descriptions
        with open("frame_descriptions.txt", "r", encoding="utf-8") as f:
            frame_descriptions = f.read()
        
        with open("operation_summary.txt", "r", encoding="utf-8") as f:
            operation_summary = f.read()
        
        task_description = "找三个关于筑梦岛的帖子，打开点赞数超过200的帖子，给点赞，并且给热门的评论添加回复'我也喜欢'"
        #frame_descriptions = ""
        plan_json_text = plan_from_deepseek(frame_descriptions,task_description)
        print(f"Planned Step:{plan_json_text}")
        
        # 解析计划和循环次数
        try:
            # 尝试解析包含loop_count的JSON格式
            plan_data = json.loads(plan_json_text)
            if isinstance(plan_data, dict) and "loop_count" in plan_data:
                loop_count = plan_data.get("loop_count", 1)
                plan = plan_data.get("steps", [])
                print(f"任务将循环执行 {loop_count} 次")
                print(f"计划步骤: {plan}")
            elif isinstance(plan_data, list):
                # 兼容旧格式，检查是否有额外的loop_count字段
                if len(plan_data) > 0 and isinstance(plan_data[-1], dict) and "loop_count" in plan_data[-1] and "step" not in plan_data[-1]:
                    loop_count = plan_data.pop().get("loop_count", 1)
                    plan = plan_data
                else:
                    # 没有循环信息，默认执行一次
                    loop_count = 1
                    plan = plan_data
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试提取循环信息
            import re
            loop_match = re.search(r'"loop_count":\s*(\d+)', plan_json_text)
            loop_count = int(loop_match.group(1)) if loop_match else 1
            # 再次尝试解析计划部分
            plan = json.loads(plan_json_text)
        
        print(f"任务将循环执行 {loop_count} 次")
        
        # 执行循环
        for current_loop in range(loop_count):
            print(f"\n开始执行第 {current_loop + 1}/{loop_count} 次循环")
            last_response = None  # 每次循环重置上一次的响应
            
            # 执行当前循环的所有步骤
            for step in plan:
                print(f"执行步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}): {step['instruction']}")
                
                start_time = time.time()
                timeout = 180
                finished = False
                
                while not finished and (time.time() - start_time) < timeout:
                    # 连续截取5张图
                    screenshot_paths = []
                    for i in range(5):
                        path = f"current_screen_{i}.jpg"
                        pyautogui.screenshot(path)
                        screenshot_paths.append(path)
                        time.sleep(1)  # 间隔1秒
                    
                    # 为指令添加当前循环信息
                    current_instruction = f"{step['instruction']} (循环 {current_loop + 1}/{loop_count})"
                    
                    action = query_uitars(screenshot_paths, current_instruction, last_response)
                    
                    last_response = action  # 保存当前响应
                    print(f"Step: {step['step']}")
                    execute_action(action)

                    screenshot_paths = []
                    for i in range(5):
                        path = f"current_screen_{i}.jpg"
                        pyautogui.screenshot(path)
                        screenshot_paths.append(path)
                        time.sleep(0.5)  # 间隔1秒
                    vlm_state = check_step_is_finished(screenshot_paths, current_instruction, last_response)
                    print(f"VLM Check State is {vlm_state}")
                    
                    if action.get("action") == "finished" or "finished" in vlm_state:
                        finished = True
                        print(f"步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}) 完成: {uitars_command['finished']}")
                    else:
                        time.sleep(1)
                
                if not finished:
                    print(f"步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}) 执行超时")
                    # 可以选择是否继续执行当前循环的后续步骤
                    # 如果要中断当前循环，可以添加 break
            
            print(f"完成第 {current_loop + 1}/{loop_count} 次循环")
            
            # 可以在循环之间添加一些延迟
            if current_loop < loop_count - 1:
                print("等待5秒后开始下一次循环...")
                time.sleep(5)
        
        # 保存记录
        save_action_records("action_records.json")
        print(f"任务执行完成，共循环 {loop_count} 次，操作记录已保存")
        
    except Exception as e:
        print(f"执行过程中出错: {e}")
        import traceback
        traceback.print_exc()

# 示例用法
if __name__ == "__main__":
    main()
    # 回放记录
    #replay_actions("action_records.json")
