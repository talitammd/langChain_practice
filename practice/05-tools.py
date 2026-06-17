import json
import os
from openai import OpenAI

# 使用 Qwen API（兼容 OpenAI 格式）
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

tools = [{
  "type":"function",
  "function":{
    "name":"get_weather",
  }
}]