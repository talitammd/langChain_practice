from openai import OpenAI
import os

# 示例一：流式调用 OpenAI + 逐 token 打印（最小版）
# 使用 Qwen API（兼容 OpenAI 格式）
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

stream = client.chat.completions.create(
    model="qwen-turbo",
    messages=[{"role": "user", "content": "解释下大A的补缺口是什么意思，缺口怎么定义的"}],
    stream=True, # 开启流式
)
# 逐 chunk 接收并输出
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
print() # 换行