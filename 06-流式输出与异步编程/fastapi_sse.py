from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
import asyncio
import os

app = FastAPI()
aclient = AsyncOpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

async def stream_llm(prompt:str):
    """异步生成器：逐 chunk 产出 SSE 格式数据"""
    stream = await aclient.chat.completions.create(
        model="qwen-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True, # 开启流式
    )
    # 逐 chunk 接收并输出
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield f"data: {chunk.choices[0].delta.content}\n\n" #SSE格式
    yield "data: [DONE]\n\n"

@app.get("/chat")
async def chat(prompt:str):
    return StreamingResponse(stream_llm(prompt), media_type="text/event-stream")

# 前端用 EventSource("/chat?q=...") 即可逐字接收

