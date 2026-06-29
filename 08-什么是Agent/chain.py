from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def chain_example(topic):
    """Chain：A→B→C，代码写死路径，路径永远是 A→B→C，模型不做路径决策"""
    # Step A：生成大纲
    outline = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{"role": "user", "content": topic}]
    ).choices[0].message.content

    # Step B：根据大纲写摘要（路径写死：A 的输出一定流向 B）
    summary = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{"role": "user", "content": f"根据大纲写摘要：{outline}"}]
    ).choices[0].message.content

    # Step C：翻译成英文（路径写死：B 的输出一定流向 C）
    english = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{"role": "user", "content": f"将以下内容翻译成英文：{summary}"}]
    ).choices[0].message.content

    return english