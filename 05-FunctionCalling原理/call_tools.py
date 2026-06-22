import json
import os
from openai import OpenAI

# 示例一：完整的三轮对话闭环（OpenAI）
# 使用 Qwen API（兼容 OpenAI 格式）
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# —— 工具定义：用 JSON Schema 描述函数 ——
tools = [{
  "type":"function",
  "function": {
      "name": "get_current_weather",
      "description": "查询指定城市的实时天气",
      "parameters": {
          "type": "object",
          "properties": {
              "city": {
                  "type": "string",
                  "description": "城市名，如 北京"
              },
              "unit": {
                  "type": "string",
                  "description": "温度单位，默认是 celsius",
                  "enum": ["c", "f"]
              }
          },
          "required": ["city"]
      }
  }
},
    {
        "type": "function",
        "function": {
            "name": "search_flight",
            "description": "查询航班信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "arrive_city": {
                        "type": "string",
                        "description": "到达城市"
                    },
                    "depart_city": {
                        "type": "string",
                        "description": "出发城市"
                    },
                    "flight_date": {
                        "type": "string",
                        "description": "航班日期",
                    },
                    "seat":{
                        "type":"string",
                        "description":"舱位",
                        "enum":["经济舱","商务舱"]
                    }
                },
                "required": ["arrive_city","depart_city","seat"]
            }
        }
    }
]

# 真正执行函数的是你的代码，也就是说，模型无法调用你没有提供的tool
def get_current_weather(city, unit="c"):
    return f"当前 {city} 的天气是 晴天 25{unit.upper()}" # 这里可以调用外部 API

msgs = [{"role": "user", "content": "查询北京天气"}]
if __name__ == "__main__":
    # 第一轮：发问（带上工具）
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=msgs,
        tools=tools
    )
    msg = response.choices[0].message
    if not msg.tool_calls:
        print(msg.content)
        exit()

    # 第二轮：模型返回 tool_calls（它只是"想调"，没真调）
    if msg.tool_calls:
        print(msg.tool_calls)
        # [ChatCompletionMessageFunctionToolCall(id='call_7ccb150f7dd24920a72b17', function=Function(arguments='{"city": "北京"}', name='get_current_weather'), type='function', index=0)]
        msgs.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            print(get_current_weather(**args))
            result = get_current_weather(**args) # 这里可以调用外部 API
            msgs.append({
                "role":"tool",
                "tool_call_id":call.id,
                "content":result
            })
    # 第三轮：回填结果，模型给自然语言答复
    final = client.chat.completions.create(
        model="qwen-turbo",
        messages=msgs
    )
    print(final.choices[0].message.content)
