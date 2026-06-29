from openai import OpenAI
import json
import re
import os

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

'''
整体思路：
    1.大模型先分析问题，再决定调用那个工具，并提取出参数
    2.代码执行工具拿到结果，喂回给大模型
    3.大模型拿到结果，重复1、2步骤
    4.反复循环，直到大模型觉得“我拿到最终答案”了，退出循环
'''

# ============ 1. 工具定义 ============
# 定义工具函数怎么执行，以及工具注册表TOOLS，里面保存了函数本身和描述，大模型通过描述来决定什么时候该用什么工具
def get_current_weather(city, unit="c"):
    return f"当前 {city} 的天气是 晴天 32{unit.upper()}"

def calculate(expression):
    return eval(expression)

TOOLS = [
    {"type": "function","description": "查询指定城市的实时天气","function": get_current_weather,"parameters": {"city": {"type": "string","description": "城市名，如 北京"},"unit": {"type": "string","description": "温度单位，默认是 celsius","enum": ["c", "f"]}}},
    {"type": "function", "description": "计算表达式","function": calculate,"parameters": {"expression": {"type": "string","description": "表达式"}}}
]

# ============ 2. ReAct Prompt 构造 ============
# 把TOOLS拼到Prompt里，告诉模型只能用这两个工具，并强制规定输出格式，按照[Thought想干嘛、Action想调哪个工具、Action Input传什么参数]的格式输出
# scratchpad（暂存板）用来记录历史轨迹，第二轮对话时，scratchpad 里会带着第一轮的“工具执行结果”，这样大模型才能看到“哦，原来刚才查到的天气是 32°C”。
def build_react_prompt(query, scratchpad):

    tool_desc = "\n".join(
        f"- {name}: {info['description']}" for name, info in TOOLS.items()
    )
    tool_names = ", ".join(TOOLS.keys())
    if len(scratchpad)>2000:
        scratchpad = client.chat.completions.create(
            model="qwen-turbo",
            messages=[{"role": "user", "content": f"请将以下 Agent 推理历史压缩为200字以内的摘要，保留关键信息:\n\n{scratchpad}"}],
            max_tokens=300
        ).choices[0].message.content
    prompt = f"""Answer the following question as best you can. You have access to these tools:{tool_desc}
Use EXACTLY this format:

Thought: <your reasoning>
Action: <tool name, one of [{tool_names}]>
Action Input: <input to the tool>

When you have the final answer, use:
Thought: I now know the final answer
Final Answer: <your answer>

Question: {query}
{scratchpad}"""

    return prompt


# ============ 3. 解析模型输出 ============
'''
大模型返回的是一段纯文本，所以需要正则表达式来切分文本:
    Final Answer: -> 说明大模型算完了，直接提取最终答案
    包含 Action: 和 Action Input: -> 说明大模型想调工具，把工具名和参数提取出来（比如 action="search_weather", action_input="北京"）
'''

def parse_output(text):
    """解析模型输出，提取 Action/Action Input 或 Final Answer"""
    # 检查是否有 Final Answer
    final_match = re.search(r"Final Answer:\s*(.+)")
    if final_match:
        return {"type":"final","answer":final_match.group(1).strip()}
    # 检查是否有 Action/Action Input
    action_match = re.search(r"Action:\s*(.+)",text)
    input_match = re.search(r"Action Input:\s*(.+)",text)
    if action_match and input_match:
        return {"type":"action","action":action_match.group(1).strip(),"action_input":input_match.group(1).strip()}
    return {"type":"error","raw":text}

# ============ 4. ReAct 主循环 ============
'''
ReAct 循环：
    1. 构造 Prompt
    2. 调用模型
    3. 解析模型输出，判断是否拿到最终答案
    4. 重复 1-3 步骤，直到模型认为“我拿到最终答案”了，退出循环
'''
def react_agent(question,max_turns=6):
    """
    ReAct Agent 主循环
    - 每轮: 调LLM获取Thought+Action → 执行工具 → 拼接Observation
    - 直到模型产出 Final Answer 或达到 max_turns
    """
    scratchpad = "" # 暂存板，记录历史轨迹

    for turn in range(max_turns):
        prompt = build_react_prompt(question, scratchpad)
        resp = client.chat.completions.create(
            model="qwen-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0,
            max_tokens=512
        )
        output = resp.choices[0].message.content
        parsed = parse_output(output)
        if parsed["type"] == "final":
            print(f"[Turn {turn+1}] Final Answer: {parsed['answer']}")
            return parsed["answer"]
        elif parsed["type"] == "action":
            action_name = parsed["action"]
            action_input = parsed["action_input"]
        try:
            # 执行工具
            if action_name in TOOLS:
                observation = TOOLS[action_name]["func"](action_input)
            else:
                observation = f"工具 {action_name} 不存在"

            # 拼接到scratchpad，下一次调用大模型时，这个 scratchpad 会被塞进 prompt 里，模型就能看到之前所有的"思考-行动-观察"历史，从而决定是继续调用工具还是给出最终答案。
            scratchpad += f"\nThought:{output.split('Thought:')[1].split('Action:')[0]}".strip() if 'Thought:' in output else ""
            scratchpad += f"\nAction: {action_name}"
            scratchpad += f"\nAction Input: {action_input}"
            scratchpad += f"\nObservation: {observation}"
        except Exception as e:
            print(f"[Turn {turn+1}] 执行工具失败: {e}")
            observation = "工具执行失败"

        else:
            print(f"[Turn {turn+1}] 解析模型输出失败: {parsed['raw']}")
            scratchpad += f"\n{output}Format error, please follow the exact format.\n"
    return "达到最大轮次仍未拿到最终答案"


# ============ 5. 运行示例 ============
if __name__ == '__main__':
    answer = react_agent("北京今天多少度？如果气温乘以2是多少？")
    print(f"最终结果: {answer}")