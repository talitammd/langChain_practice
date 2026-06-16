# 示例 1：Pydantic 定义 + OpenAI Structured Outputs
import json
# pydantic 数据验证和序列化库。定义数据模型（类），自动做类型检查、转换、验证，还能生成 JSON Schema。
from pydantic import BaseModel, Field
from openai import OpenAI


# 使用 Qwen API（兼容 OpenAI 格式）
client = OpenAI(
    api_key="sk-bf3e4253e80048d898629a645d78b378",  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# Pydantic v2 要求所有字段必须有类型注解
class Invoice(BaseModel):
    """发票信息抽取结果"""
    vendor: str = Field(description="开票方名称")
    amount: float = Field(description="金额")
    date: str = Field(description="开票日期，YYYY-MM-DD")
    items: list[str] = Field(default_factory=list, description="商品明细")


# 让模型输出 JSON，再解析成 Pydantic 对象
#  model_json_schema() 生成模型的 JSON Schema（描述模型结构的元数据）
resp = client.chat.completions.create(
    model="qwen-max",  # 或其他 Qwen 模型如 qwen-turbo、qwen-plus
    messages=[
        {
            "role": "system",
            "content": f"从文本中抽取发票信息，按 JSON 格式返回，结构如下：{Invoice.model_json_schema()}",
        },
        {
            "role": "user",
            "content": "美团科技 2026-06-15 开票，金额 1280 元，含云服务、技术支持",
        },
    ],
    response_format={"type": "json_object"},
)

content = resp.choices[0].message.content
# model_validate_json() 把 JSON 字符串解析并验证成 Pydantic 对象
invoice = Invoice.model_validate_json(content)
print(invoice.vendor, invoice.amount, invoice.date, invoice.items)

# 示例 2：手写带错误重试的兜底（不依赖框架）
import json
from os import name
from pydantic import BaseModel, ValidationError
from openai import OpenAI


class Person(BaseModel):
    name: str
    age: int


def parse_with_retry(call_llm, prompt, model_cls, max_retries=3):
    """通用兜底：校验失败把错误塞回模型让它改"""
    last_err = None
    # Qwen 要求消息里必须包含 "json" 字样才能用 response_format={"type": "json_object"}
    msgs = [
        {"role": "system", "content": "请返回 JSON 格式数据"},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(max_retries):
        raw = call_llm(msgs)
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
            # 把报错喂回去，让模型"看着错误改一遍"
            msgs.append({"role": "assistant", "content": raw})
            msgs.append(
                {
                    "role": "user",
                    "content": f"上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n{e}",
                }
            )
            print(msgs)
    raise RuntimeError(f"重试{max_retries}次扔失败：{last_err}")


# 演示用 mock：第一次返回坏数据，第二次返回正确
class MockLLM:
    def __init__(self):
        self.n = 0
        # 使用 Qwen API（兼容 OpenAI 格式）
        self.client = OpenAI(
            api_key="sk-bf3e4253e80048d898629a645d78b378",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def __call__(self, messages):
        self.n += 1
        resp = self.client.chat.completions.create(
            model="qwen-max",
            messages=messages,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content


person = parse_with_retry(MockLLM(), "抽取姓名和年龄：name=张三，age=26", Person)
print(person.age)  # 25，第二次重试成功

# [{'role': 'user', 'content': '抽取姓名和年龄'}, {'role': 'assistant', 'content': '为了帮助你抽取姓名和年龄，我需要一段具体的文本作为例子。请提供包含姓名和年龄信息的一段文字，这样我可以更准确地示范如何从中提取这些信息。'}, {'role': 'user', 'content': "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='为了帮助你抽取姓...提取这些信息。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid"}]
# [
#     {"role": "user", "content": "抽取姓名和年龄"},
#     {
#         "role": "assistant",
#         "content": "为了帮助你抽取姓名和年龄，我需要一段具体的文本作为例子。请提供包含姓名和年龄信息的一段文字，这样我可以更准确地示范如何从中提取这些信息。",
#     },
#     {
#         "role": "user",
#         "content": "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='为了帮助你抽取姓...提取这些信息。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid",
#     },
#     {
#         "role": "assistant",
#         "content": '我理解了您的需求，您希望从给定的文本中抽取姓名和年龄，并以JSON格式返回结果。请提供一段包含姓名和年龄的具体文本示例，以便我能准确地完成这项任务。如果没有特定的文本，我将构造一个例子来展示如何进行。\n\n假设没有具体的输入文本，这里是一个例子：\n\n**示例文本**: "张三今年28岁了。"\n\n基于这个例子，输出应该是这样的：\n\n```json\n{\n  "姓名": "张三",\n  "年龄": 28\n}\n```\n\n如果您有具体的文本，请提供，这样我可以直接根据您的数据生成对应的JSON。',
#     },
#     {
#         "role": "user",
#         "content": "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='我理解了您的需求...生成对应的JSON。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid",
#     },
# ]
# [
#     {"role": "user", "content": "抽取姓名和年龄"},
#     {
#         "role": "assistant",
#         "content": "为了帮助你抽取姓名和年龄，我需要一段具体的文本作为例子。请提供包含姓名和年龄信息的一段文字，这样我可以更准确地示范如何从中提取这些信息。",
#     },
#     {
#         "role": "user",
#         "content": "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='为了帮助你抽取姓...提取这些信息。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid",
#     },
#     {
#         "role": "assistant",
#         "content": '我理解了您的需求，您希望从给定的文本中抽取姓名和年龄，并以JSON格式返回结果。请提供一段包含姓名和年龄的具体文本示例，以便我能准确地完成这项任务。如果没有特定的文本，我将构造一个例子来展示如何进行。\n\n假设没有具体的输入文本，这里是一个例子：\n\n**示例文本**: "张三今年28岁了。"\n\n基于这个例子，输出应该是这样的：\n\n```json\n{\n  "姓名": "张三",\n  "年龄": 28\n}\n```\n\n如果您有具体的文本，请提供，这样我可以直接根据您的数据生成对应的JSON。',
#     },
#     {
#         "role": "user",
#         "content": "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='我理解了您的需求...生成对应的JSON。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid",
#     },
#     {
#         "role": "assistant",
#         "content": '明白了，您需要一个具体的JSON格式输出。请提供包含姓名和年龄的文本示例，以便我能够从中抽取信息并生成正确的JSON。\n\n假设没有具体的输入文本，这里是一个例子：\n\n**示例文本**: "张三今年28岁了。"\n\n基于这个例子，输出应该是这样的：\n\n```json\n{\n  "姓名": "张三",\n  "年龄": 28\n}\n```\n\n如果您有具体的文本，请提供，这样我可以直接根据您的数据生成对应的JSON。如果没有，我将使用上述示例文本生成JSON。\n\n请提供具体的文本或确认使用上述示例。',
#     },
#     {
#         "role": "user",
#         "content": "上面的输出不符合要求，校验错误如下，请仅输出修正后的合法 JSON：\n1 validation error for Person\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='明白了，您需要一...使用上述示例。', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/json_invalid",
#     },
# ]

# 示例 3：Pydantic 字段校验器，约束业务规则
from pydantic import BaseModel, field_validator


class Order(BaseModel):
    order_id: str
    status: str
    amount: float

    # field_validator 当 status 字段被赋值时，自动调用下面的校验方法，校验失败会抛出 ValueError
    # classmethod 表示这是一个类方法，不需要创建实例就能调用
    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v):
        allowed = {"pay", "me", "back", "baby"}
        if v not in allowed:
            raise ValueError(f"status必须是{allowed}之一，收到{v!r}")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v < 0:
            raise ValueError("amount必须大于0")
        return v


# 合法
# print(Order(order_id="A1",status="me",amount=39.0))

# 非法status
try:
    print(Order(order_id="A2", status="sassa", amount=19.0))

except Exception as e:
    print("校验拦截", e)
