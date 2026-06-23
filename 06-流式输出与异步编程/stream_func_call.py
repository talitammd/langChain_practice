import json
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 1. 定义工具函数
def get_current_weather(city):
    return f"{city}当前天气：晴天 25度"

# 工具名映射到函数
TOOLS_MAP = {
    "get_current_weather": get_current_weather
}

# 工具定义
tools = [{
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "获取当前天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        }
    }
}]

# ========== 第1轮：获取工具调用 ==========
stream = client.chat.completions.create(
    model="qwen-turbo",
    messages=[{"role": "user", "content": "北京和贵州的天气"}],
    tools=tools,
    stream=True,
)

# 攒分片
tool_calls_acc = {}
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.tool_calls:
        for tc in delta.tool_calls:
            idx = tc.index
            if idx not in tool_calls_acc:
                tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
            if tc.id:
                tool_calls_acc[idx]["id"] = tc.id
            if tc.function.name:
                tool_calls_acc[idx]["name"] += tc.function.name
            if tc.function.arguments:
                tool_calls_acc[idx]["arguments"] += tc.function.arguments

print("需要调用的工具：", tool_calls_acc)

# ========== 第2轮：执行工具 ==========
# 构造 messages，包含原始用户消息 + assistant 的 tool_calls
messages = [
    {"role": "user", "content": "北京和贵州的天气"},
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"]
                }
            } for tc in tool_calls_acc.values()
        ]
    }
]

# 执行工具，添加 tool 结果到 messages
for tc in tool_calls_acc.values():
    func_name = tc["name"]
    func_args = json.loads(tc["arguments"])  # arguments 是 JSON 字符串，需要解析

    # 调用函数
    result = TOOLS_MAP[func_name](**func_args)
    print(f"执行 {func_name}({func_args}) => {result}")

    # 添加 tool 结果到 messages
    messages.append({
        "role": "tool",
        "tool_call_id": tc["id"],
        "content": result
    })

# ========== 第3轮：把工具结果传回大模型，生成最终回复 ==========
stream2 = client.chat.completions.create(
    model="qwen-turbo",
    messages=messages,
    tools=tools,
    stream=True,
)

print("\n最终回复：")
for chunk in stream2:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
print()
