# Augmented UI Agent(UI TARS)
[Doubao-1.5-UI-TARS ](https://www.volcengine.com/docs/82379/1536429)是一款原生面向图形界面交互（GUI）的Agent模型。通过感知、推理和动作执行等类人的能力，与 GUI 进行连续、流程的交互。与传统模块化框架不同，模型将所有核心能力（感知、推理、基础理解能力），统一集成在视觉大模型（VLM）中，实现无需预定义工作流程或人工规则的端到端任务自动化。

本项目结合了视频抽帧、多模态模型调用、任务推理和决策、自动操作执行等关键技术，使得UI Agent能够学习视频操作，确保了方案的可行性和有效性。同时，通过VLM辅助UI TARS进行任务状态判断，可以进一步提高UI智能代理的性能和稳定性。

## 学习视频
学习如何在短视频应用中搜索、点赞、收藏等（demo5.mp4）。
[学习视频](https://www.bilibili.com/video/BV1NjGCzyE1W/?vd_source=35bc330215defaf7822ec0773babe95f)
## UI Agent执行过程
[操作演示-example-zly-720.mp4](https://www.bilibili.com/video/BV1NjGCzyEfz/?vd_source=35bc330215defaf7822ec0773babe95f)

# 使用步骤
## 环境准备
1. 在[火山方舟](https://www.volcengine.com/docs/82379/1099455)创建视觉推理模型、豆包深度推理模型、UI TARS模型的推理节点。
2. 输入提示词
```text
找赵丽颖的视频，找到点赞数量1000以上的视频给点赞和收藏
```
3. 云手机（火山或者其他厂商），可以通过浏览器浏览（理论上客户端也可以），安装快手并完成登录、实名等验证，打开短视频App。
4. 安装python 环境和相关依赖库及设置环境变量。
```shell
pip install requests
pip install opencv-python
pip install pyautogui

export ARK_API_KEY=your_api_key
```
## 理解软件操作视频
理解学习操作视频，形成知识库中，本项目知识库存在本地文件中，如果很多内容超过深度推理模型的上下文长度（豆包深度推理模型最大128K），可以使用向量库等。
```python
python auto_gui_rag.py
```

## 自动化完成任务
根据知识库和用户指令生成任务执行规划，并自动化完成任务，指令和工程执行逻辑可能需要根据业务需要进行自定义适配。
```python
python auto_gui.py
```

# 参考项目
- [UI-TARS](https://github.com/bytedance/UI-TARS)
- [UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop)