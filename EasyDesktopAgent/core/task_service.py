import os
import json
import time
import pyautogui
import threading
import sys
import base64
import requests
import win32gui
import win32con

pyautogui.FAILSAFE = False

sys.path.append("..")
from utils.logger import logger as Logger

class TaskService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.current_task = None
        self.task_log = []
        pyautogui.FAILSAFE = False
    
    def get_task_history(self):
        """获取任务历史"""
        history_file = self.config_manager.get('tasks.history_file', 'task_history.json')
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), history_file)
        
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                Logger.error(f"加载任务历史失败: {e}")
                return []
        else:
            return []
    
    def save_task_history(self, task_history):
        """保存任务历史"""
        history_file = self.config_manager.get('tasks.history_file', 'task_history.json')
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), history_file)
        
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(task_history, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            Logger.error(f"保存任务历史失败: {e}")
            return False
    
    def execute_task(self, task_description, processed_video, progress_callback=None):
        """执行任务
        
        Args:
            task_description: 任务描述
            processed_video: 已处理的视频名称
            progress_callback: 进度回调函数
        """
        # 创建任务记录
        self.current_task = {
            'description': task_description,
            'video': processed_video,
            'timestamp': time.time(),
            'status': 'running',
            'log': ''
        }
        
        # 清空日志
        self.task_log = []
        
        try:
            # 记录日志
            self.log(f"开始执行任务: {task_description}", progress_callback)
            
            # 获取视频帧描述
            from core.knowledge_service import KnowledgeService
            knowledge_service = KnowledgeService(self.config_manager)
            frame_descriptions = knowledge_service.get_frame_descriptions(processed_video)
            
            if not frame_descriptions:
                raise ValueError(f"无法获取视频 {processed_video} 的帧描述")
            
            self.log(f"已加载视频 {processed_video} 的帧描述", progress_callback)
            
            # 调用DeepSeek推理生成计划
            plan_json = self.query_deepseek(frame_descriptions, task_description)
            self.log(f"已生成执行计划: {plan_json}", progress_callback)

            # 最小化应用窗口，避免干扰
            self.log("最小化应用窗口，开始执行操作", progress_callback)
            hwnd = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
            # 解析计划
            try:
                plan_data = json.loads(plan_json)
                if isinstance(plan_data, dict) and "loop_count" in plan_data:
                    loop_count = plan_data.get("loop_count", 1)
                    plan = plan_data.get("steps", [])
                elif isinstance(plan_data, list):
                    # 兼容旧格式
                    if len(plan_data) > 0 and isinstance(plan_data[-1], dict) and "loop_count" in plan_data[-1] and "step" not in plan_data[-1]:
                        loop_count = plan_data.pop().get("loop_count", 1)
                        plan = plan_data
                    else:
                        loop_count = 1
                        plan = plan_data
                else:
                    loop_count = 1
                    plan = []
            except Exception as e:
                self.log(f"解析计划失败: {e}", progress_callback)
                raise ValueError(f"解析计划失败: {e}")
            
            self.log(f"任务将循环执行 {loop_count} 次", progress_callback)
            
            # 执行计划
            for current_loop in range(loop_count):
                self.log(f"开始执行第 {current_loop + 1}/{loop_count} 次循环", progress_callback)
                
                # 执行当前循环的所有步骤
                for step in plan:
                    self.log(f"执行步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}): {step['instruction']}", progress_callback)
                    
                    # 执行步骤
                    self.execute_step(step, current_loop, loop_count, progress_callback)
                    
                    # 等待一段时间
                    time.sleep(1)
                
                self.log(f"完成第 {current_loop + 1}/{loop_count} 次循环", progress_callback)
                
                # 循环之间的延迟
                if current_loop < loop_count - 1:
                    self.log("等待5秒后开始下一次循环...", progress_callback)
                    time.sleep(5)
            
            # 更新任务状态
            self.current_task['status'] = 'completed'
            self.current_task['log'] = '\n'.join(self.task_log)
            
            # 保存到历史记录
            task_history = self.get_task_history()
            task_history.append(self.current_task)
            self.save_task_history(task_history)
            
            self.log("任务执行完成", progress_callback)
             # 恢复应用窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
            
        except Exception as e:
            # 更新任务状态
            self.current_task['status'] = 'failed'
            self.current_task['log'] = '\n'.join(self.task_log)
            self.current_task['error'] = str(e)
            
            # 保存到历史记录
            task_history = self.get_task_history()
            task_history.append(self.current_task)
            self.save_task_history(task_history)
            
            self.log(f"任务执行失败: {e}", progress_callback)
             # 恢复应用窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            raise
    
    def log(self, message, callback=None):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_message = f"[{timestamp}] {message}"
        self.task_log.append(log_message)
        
        if callback:
            callback(log_message)
        
        Logger.info(log_message)
    
    def query_deepseek(self, frames_descriptions, task_description):
        """调用DeepSeek模型生成计划"""
        import requests
        import base64
        import os
        
        api_key = self.config_manager.get('api_key', '')
        api_host = self.config_manager.get('api_host', 'https://ark.cn-beijing.volces.com/api/v3')
        planning_model_ep = self.config_manager.get('models.planning_model_ep', '')
        
        if not api_key or not planning_model_ep:
            raise ValueError("API密钥或模型EP未配置")
        
        system_prompt = f"""
        你是一个智能助手，根据以下用户界面描述和任务描述，生成操作计划。

        界面描述：
        {frames_descriptions}

        输出要求：
        1. 仅输出有效的JSON数据
        2. 不使用任何代码块标记（如```json```）
        3. 不添加任何解释文字
        4. 直接以{{开始，以}}结束

        JSON格式：
        {{"steps":[{{"instruction": "打开微信", "step": 0}}], "loop_count": 100}}

        字段说明：
        - steps：操作步骤数组，包含原子操作，不包含重复循环类指令
        - instruction：具体操作指令，要求详细明确
        - step：步骤序号，从0开始递增
        - loop_count：整个流程循环次数（如需要）

        输出示例：
        {{"steps":[{{"instruction": "打开微信", "step": 0}}, {{"instruction": "发送消息", "step": 1}}], "loop_count": 3}}

        任务描述：
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description}
        ]
        
        # 发送请求到API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            data = {
                'model': planning_model_ep,
                'messages': messages,
                'temperature': 0.8
            }
            response = requests.post(f'{api_host}/chat/completions', headers=headers, json=data)
            
            response_data = response.json()
            response_content = response_data['choices'][0]['message']['content']
            return response_content
        except Exception as e:
            self.log(f"调用DeepSeek API失败: {e}")
            raise ValueError(f"调用DeepSeek API失败: {e}")
    
    def execute_step(self, step, current_loop, loop_count, progress_callback=None):
        """执行单个步骤
        
        Args:
            step: 步骤信息
            current_loop: 当前循环次数
            loop_count: 总循环次数
            progress_callback: 进度回调函数
        """
        import pyautogui
        import time
        import base64
        import os
        import win32gui
        import win32con
        import io
        from PIL import Image
        
        # 获取配置信息
        api_key = self.config_manager.get('api_key', '')
        api_host = self.config_manager.get('api_host', 'https://ark.cn-beijing.volces.com/api/v3')
        uitars_model_ep = self.config_manager.get('models.uitars_model_ep', '')
        vlm_model_ep = self.config_manager.get('models.vlm_model_ep', '')
        
        if not api_key or not uitars_model_ep or not vlm_model_ep:
            raise ValueError("API密钥或模型EP未配置")
        
        # 为指令添加当前循环信息
        current_instruction = f"{step['instruction']} (循环 {current_loop + 1}/{loop_count})"
        self.log(f"当前指令: {current_instruction}", progress_callback)
        
        # 设置超时时间
        start_time = time.time()
        timeout =  self.config_manager.get('tasks.timeout', 180)  # 3分钟超时
        Logger.info(f"超时时间: {timeout}秒")
        finished = False
        last_response = None
        
        # 编码图像为base64
        def encode_image_base64(image_path, quality=80): # 增加quality参数，默认为80
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
        # 调用API
        def chat(messages, model):
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            try:
                data = {
                    'model': model,
                    'messages': messages,
                    'temperature': 0.8
                }
                response = requests.post(f'{api_host}/chat/completions', headers=headers, json=data)
                
                response_data = response.json()
                response_content = response_data['choices'][0]['message']['content']
                return response_content
            except Exception as e:
                self.log(f"调用API失败: {e}", progress_callback)
                raise ValueError(f"调用API失败: {e}")
        
        # 解析坐标框
        def parse_box_coordinates(action_text):
            bbox_start = action_text.find("<bbox>") + len("<bbox>")
            bbox_end = action_text.find("</bbox>")
            bbox_str = action_text[bbox_start:bbox_end]
            return [int(x) for x in bbox_str.split()]
        
        # 解析拖拽坐标
        def parse_drag_coordinates(action_text):
            import re
            matches = re.findall(r"<bbox>([\d\s]+)</bbox>", action_text)
            start_box = list(map(int, matches[0].split()))
            end_box = list(map(int, matches[1].split()))
            return (start_box, end_box)
        
        # 解析按键内容
        def parse_key_content(action_text):
            start = action_text.find("'") + 1
            end = action_text.rfind("'")
            return action_text[start:end]
        
        # 解析滚动数据
        def parse_scroll_data(action_text):
            import re
            direction_match = re.search(r"direction\s*=\s*'(.*?)'", action_text)
            direction = direction_match.group(1) if direction_match else "down"
            
            start_box_match = re.search(r"start_box\s*=\s*'<bbox>(.*?)</bbox>'", action_text)
            if start_box_match:
                start_box = list(map(int, start_box_match.group(1).split()))
            else:
                start_box = [0, 0, 0, 0]
            return (start_box, direction)
        
        # 解析完成内容
        def parse_finished_content(action_text):
            start = action_text.find("content='") + len("content='")
            end = action_text.rfind("'")
            return action_text[start:end].replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")
        
        # 查询UI-TARS
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
            
            response = chat(messages, model=uitars_model_ep)
        
            # 解析响应
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

                # 解析Action
                uitars_command = {}
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
                    self.log(f"未知的Action: {action_text}", progress_callback)
                return result, uitars_command
            except Exception as e:
                self.log(f"解析UI-TARS响应失败: {e}", progress_callback)
                return {"error": str(e)}, {}
        
        # 检查步骤是否完成
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
            
            response = chat(messages, model=vlm_model_ep)
            return response
        
        # 执行操作
        def execute_action(action_data, uitars_command):
            if "thought" in action_data:
                self.log(f"[思考] {action_data['thought']}", progress_callback)
            
            if "action" in action_data:
                self.log(f"[操作] {action_data['action']}", progress_callback)
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
                    self.log(f"[点击] x={x}, y={y}", progress_callback)
                    pyautogui.moveTo(x, y)
                    pyautogui.click()
                    
                elif action_data["action"] == "left_double":
                    box = convert_coords(uitars_command["left_double"]["start_box"])
                    x = round((box[0] + box[2]) / 2)
                    y = round((box[1] + box[3]) / 2)
                    self.log(f"[双击] x={x}, y={y}", progress_callback)
                    pyautogui.moveTo(x, y)
                    pyautogui.doubleClick()
                    
                elif action_data["action"] == "right_single":
                    box = convert_coords(uitars_command["right_single"]["start_box"])
                    x = round((box[0] + box[2]) / 2)
                    y = round((box[1] + box[3]) / 2)
                    self.log(f"[右键] x={x}, y={y}", progress_callback)
                    pyautogui.moveTo(x, y)
                    pyautogui.rightClick()
                    
                elif action_data["action"] == "drag":
                    start_box = convert_coords(uitars_command["drag"]["start_box"])
                    end_box = convert_coords(uitars_command["drag"]["end_box"])
                    start_x = round((start_box[0] + start_box[2]) / 2)
                    start_y = round((start_box[1] + start_box[3]) / 2)
                    end_x = round((end_box[0] + end_box[2]) / 2)
                    end_y = round((end_box[1] + end_box[3]) / 2)
                    self.log(f"[拖拽] 从 x={start_x}, y={start_y} 到 x={end_x}, y={end_y}", progress_callback)
                    pyautogui.moveTo(start_x, start_y)
                    pyautogui.dragTo(end_x, end_y)
                    
                elif action_data["action"] == "hotkey":
                    self.log(f"[快捷键] {uitars_command['hotkey']}", progress_callback)
                    pyautogui.hotkey(*uitars_command["hotkey"].split('+'))
                    
                elif action_data["action"] == "type":
                    self.log(f"[输入] {uitars_command['type']}", progress_callback)
                    # 检查文本是否包含换行符
                    text_to_type = uitars_command["type"]
                    if "\n" in text_to_type:
                        lines = text_to_type.split("\n")
                        for i, line in enumerate(lines):
                            if line:
                                pyperclip.copy(line)
                                pyautogui.hotkey('ctrl', 'v')
                            if i < len(lines) - 1:
                                pyautogui.press('enter')
                    else:
                        # 先将文本复制到剪贴板
                        import pyperclip
                        pyperclip.copy(text_to_type)
                        # 然后使用快捷键粘贴
                        pyautogui.hotkey('ctrl', 'v')
                    
                elif action_data["action"] == "scroll":
                    box = convert_coords(uitars_command["scroll"]["start_box"])
                    direction = uitars_command["scroll"]["direction"]
                    x = round((box[0] + box[2]) / 2)
                    y = round((box[1] + box[3]) / 2)
                    
                    if x == 0 or y == 0:
                        x = int(screen_width * 0.5)
                        y = int(screen_height * 0.5)
                    pyautogui.moveTo(x, y)
                    amount = -500 if direction == "down" else 500  # 滚动量
                    self.log(f"[滚动] x={x}, y={y}, 方向={direction}", progress_callback)
                    pyautogui.scroll(amount)
                    
                elif action_data["action"] == "wait":
                    wait_time = uitars_command["wait"]
                    self.log(f"[等待] {wait_time}秒", progress_callback)
                    time.sleep(wait_time)
                    
                elif action_data["action"] == "finished":
                    self.log(f"[完成] {uitars_command['finished']}", progress_callback)
        
        # 主循环
        while not finished and (time.time() - start_time) < timeout:
            # 连续截取5张图
            screenshot_paths = []
            screenshot_count = self.config_manager.get('tasks.screenshot_count', 5) # 默认5张
            screenshot_interval = self.config_manager.get('tasks.screenshot_interval', 0.5) # 默认0.5秒
            Logger.debug(f"截图数量: {screenshot_count}")
            Logger.debug(f"截图间隔: {screenshot_interval}")
            for i in range(screenshot_count):
                path = f"current_screen_{i}.jpg"
                pyautogui.screenshot(path)
                screenshot_paths.append(path)
                time.sleep(screenshot_interval)  # 间隔0.5秒
            
            # 查询UI-TARS获取下一步操作
            action, uitars_cmd = query_uitars(screenshot_paths, current_instruction, last_response)
            
            last_response = action  # 保存当前响应
            self.log(f"步骤: {step['step']}", progress_callback)
            execute_action(action, uitars_cmd)

            # 再次截图检查是否完成
            '''
            screenshot_paths = []
            for i in range(screenshot_count):
                path = f"current_screen_{i}.jpg"
                pyautogui.screenshot(path)
                screenshot_paths.append(path)
                time.sleep(screenshot_interval)  # 间隔0.5秒
            
            vlm_state = check_step_is_finished(screenshot_paths, current_instruction, last_response)
            self.log(f"状态检查结果: {vlm_state}", progress_callback)
            '''
            if action.get("action") == "finished":
                finished = True
                self.log(f"步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}) 完成", progress_callback)
            else:
                time.sleep(1)
        
        if not finished:
            self.log(f"步骤 {step['step']} (循环 {current_loop + 1}/{loop_count}) 执行超时", progress_callback)
        