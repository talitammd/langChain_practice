import json,asyncio
from openai import OpenAI
import os

# 示例 2：并行工具调用 + 并发执行
# 使用 Qwen API（兼容 OpenAI 格式）
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
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
}]

async def run_tool(call):
    args = json.loads(call.function.arguments)
    city = args['city']
    # 模拟异步IO调用（如调用外部天气API）
    await asyncio.sleep(1)

    return {
        "role":"tool",
        "tool_call_id":call.id,
        "content":f"当前 {city} 的天气是 晴天 25C"
    }

async def main(msgs, tools):
    resp = client.chat.completions.create(
        model="qwen-turbo",
        messages=msgs,
        tools=tools
    )
    msg = resp.choices[0].message
    print(msg.tool_calls)
    #  tool_calls=[ChatCompletionMessageFunctionToolCall(id='call_09d6b728bf4c4a91998ceb', function=Function(arguments='{"city": "北京"}', name='get_current_weather'), type='function', index=0), ChatCompletionMessageFunctnToolCall(id='call_658c89783257474aa17955', function=Function(arguments='{"city": "上海"}', name='get_current_ather'), type='function', index=1), ChatCompletionMessageFunctionToolCall(id='call_b00dacc939674c07b0066a', function=Function(arguments='{"city": "广州"}', name='get_current_weather'), type='function', index=2)]
    if not msg.tool_calls:
        return msg.content
    msgs.append(msg)
    results = await asyncio.gather(*[run_tool(call) for call in msg.tool_calls])
    msgs.extend(results)
    final = client.chat.completions.create(
        model="qwen-turbo",
        messages=msgs
    )
    return final.choices[0].message.content

if __name__ == "__main__":
    # 查询多个城市，触发并行工具调用
    asyncio.run(main([{"role": "user", "content": "查询北京、上海、广州的天气"}], tools))