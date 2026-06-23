"""
极简 Agent —— 不依赖框架，~90 行实现完整工具循环
依赖：pip install openai pydantic jinja2
"""
import json
from typing import Any,Callable
from pydantic import BaseModel
from jinja2 import Template
from openai import OpenAI
import os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Prompt 模板（Jinja2 拆三块）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM_TEMPLATE = Template("""
你是一个{{ role }}。
约束：
- 回答语言：{{ lang }}
- 如果不确定答案，诚实说"我不知道"
- 尽量简洁
""".strip())

def build_system_prompt(role="通用助手",lang="中文"):
    return SYSTEM_TEMPLATE.render(role=role,lang=lang)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 工具注册表
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ToolRegistry:
    """工具白名单：注册函数 + schema，Agent 只能调注册过的"""
    def __init__(self):
        self._tools = {}
        self._schemas = []
    def register(self,name,description,parameters,func):
        self._tools[name]=func
        self._schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })

    @property
    def schemas(self):
        return self._schemas

    def execute(self,name,arguments):
        # 1. 检查工具是否存在
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        try:
            # 2. 调用工具函数，**arguments 是解包字典为关键字参数
            # 比如 arguments={"city": "北京"} 变成 get_weather(city="北京")
            result=self._tools[name](**arguments)
            # 3. 统一返回字符串格式
            # 如果 result 不是字符串，用 json.dumps 转成 JSON 字符串
            # ensure_ascii=False 保证中文不乱码
            return json.dumps(result,ensure_ascii=False) if not isinstance(result,str) else result
        except Exception as e:
            raise ValueError(f"Error executing tool {name}: {e}")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Agent Loop（核心）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MiniAgent:
    def __init__(self,registry,model,max_turns=10):
        self.client = OpenAI(
            api_key=os.getenv("QWEN_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.registry = registry
        self.model = model
        self.max_turns = max_turns
        self.messages = [{
            "role":"system",
            "content": build_system_prompt()
        }]

    def chat(self,user_input):
        self.messages.append({
            "role":"user",
            "content": user_input
        })
        for turn in range(self.max_turns):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.registry.schemas
            )
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))
            # —— 没有 tool_calls → 模型觉得够了，返回文本 ——
            if not msg.tool_calls:
                return msg.content or ""
            # —— 有 tool_calls → 执行工具，结果回填 ——
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments)
                result = self.registry.execute(call.function.name,args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result
                })
        return "[Agent] 达到最大轮次限制 强制退出"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 注册工具 & 运行
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_weather(city,unit="c"):
    fake_data={"北京":25,"上海":26,"广州":27,"深圳":28}
    temp=fake_data.get(city,99)
    return f"{city} 晴天 {temp}°{'C' if unit=='c' else 'F'}"

def calculate(expression):
    allowed = set("0123456789+-*/()")
    if not all(char in allowed for char in expression):
        raise ValueError("Expression contains disallowed characters")
    try:
        return str(eval(expression))
    except Exception as e:
        raise ValueError(f"Error calculating expression: {e}")

if __name__ == "__main__":
    reg = ToolRegistry()
    reg.register(
        "get_weather", "获取天气", {
            "type": "object",
            "properties": {
                "city": {"type": "string","description": "城市名称"},
                "unit": {"type": "string","description": "温度单位","enum": ["c","f"]}
            },
            "required": ["city"]
        }, get_weather)
    reg.register(
        "calculate", "计算表达式", {
            "type": "object",
            "properties": {
                "expression": {"type": "string","description": "数学表达式"}
            },
            "required": ["expression"]
        }, calculate)
    agent = MiniAgent(reg, "qwen-turbo")
    print(agent.chat("北京和贵州的天气"))
    print(agent.chat("那两个城市的温度差是多少"))