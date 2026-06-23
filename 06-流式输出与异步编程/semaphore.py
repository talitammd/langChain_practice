import asyncio
from openai import AsyncOpenAI
import os

aclent = AsyncOpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
SEM = asyncio.Semaphore(5) # 最多并发5个请求

async def call_with_guard(index,prompt,timeout=30.0):
    """带限流、超时、错误隔离的安全调用"""
    async with SEM: # 请求前获取一个令牌，请求结束后释放一个令牌
        try:
            resp = await asyncio.wait_for( # 等待请求完成或超时
                aclent.chat.completions.create(
                    model="qwen-turbo",
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=timeout
            )
            print(f"第{index}个请求结果：{resp.choices[0].message.content}")
            return resp.choices[0].message.content
        except asyncio.TimeoutError:
            return f"请求超时，timeout={timeout}"
        except Exception as e: # 错误隔离
            return f"请求异常，{e}"

async def batch_eval(prompts):
    tasks = [call_with_guard(index,prompt) for index,prompt in enumerate(prompts)]
    res = await asyncio.gather(*tasks)
    print(res)
    return res

asyncio.run(batch_eval([
    "帮我看下股票传艺科技",
    "帮我看下股票美利云",
    "帮我看下股票盛洋科技",
    "帮我看下股票豪能股份",
    "帮我看下股票梦网科技",
    "帮我看下股票国检集团",
    "帮我看下股票永臻股份",
    "帮我看下股票湘财股份",
    "帮我看下股票瑞康医药"
]))