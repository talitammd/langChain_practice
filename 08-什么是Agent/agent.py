import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
# 工具定义
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
# 工具函数
def get_current_weather(city, unit="c"):
    return f"当前 {city} 的天气是 晴天 25{unit.upper()}" # 这里可以调用外部 API

def search_flight(arrive_city, depart_city, flight_date, seat):
    return f"查询到航班信息：{arrive_city}-{depart_city}，日期：{flight_date}，舱位：{seat}"

# 工具注册表
registry = {
    "get_current_weather": get_current_weather,
    "search_flight": search_flight
}

# 模型自己做所有路径决策：调什么、几次、何时停
def agent_example(query,max_turns=10):
    """Agent：模型自己决定调什么、什么时候停"""
    msgs = [{"role":"system","content":"你是一个助手，可以使用工具解决问题"},{"role": "user", "content": query}]
    for _ in range(max_turns):
        resp = client.chat.completions.create(
            model="qwen-turbo",
            messages=msgs,
            tools=tools
        )
        msg = resp.choices[0].message
        msgs.append(msg.model_dump(exclude_none=True))

        # ★ 关键：模型自己决定"还要不要继续调工具"
        if not msg.tool_calls:
            return msg.content # 模型决定不再调用工具
        # 模型决定继续调用工具
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = registry[call.function.name](**args) # 这里可以调用外部 API
            msgs.append({
                "role":"tool",
                "tool_call_id":call.id,
                "content":result
            })
    return "[超出最大轮次]"