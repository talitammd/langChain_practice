from pydoc import describe
from pydantic import BaseModel, Field
from openai import OpenAI

class Invoice(BaseModel):
    """发票信息抽取结果"""
    vendor = Field(description="开票方名称")
    amount = Field(description="金额")
    date = Field(description="开票日期，YYYY-MM-DD")
    items = Field(default_factory=list,description="商品明细")
client = OpenAI()

# 用 parse 接口直接拿到强类型对象，无需手动 json.loads
resp = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "从文本中抽取发票信息"},
        {
            "role": "user",
            "content": "美团科技 2026-06-15 开票，金额 1280 元，含云服务、技术支持",
        },
    ],
    response_format=Invoice,  # 直接传 Pydantic 模型
)

invoice: Invoice = resp.choices[0].message.parsed
print(invoice.vendor, invoice.amount, invoice.items)