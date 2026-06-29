import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
# 分支
def handle_weather(query):
    return "25°C"
def handle_flight(query):
    return "12:00"
def handle_hotel(query):
    return "100元"
def handle_chat(query):
    return "你好"

def workflow_example(query):
    """Workflow：代码定义分支逻辑"""
    # 先让模型分类（模型干活，但分支逻辑是代码定的）
    category = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{"role": "user", "content": f"请根据以下内容判断其类别属于[天气/航班/酒店/聊天]：{query}"}]
    ).choices[0].message.content
    # 代码定义的分支：根据分类走不同路径
    # 分支存在，但"走哪条"是代码 if/elif 决定的

    if "天气" in category:
        return handle_weather(query)
    elif "航班" in category:
        return handle_flight(query)
    elif "酒店" in category:
        return handle_hotel(query)
    elif "聊天" in category:
        return handle_chat(query)