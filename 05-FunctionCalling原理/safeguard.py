from pydantic import BaseModel, field_validator

DANGEROUS = {"delete_file", "transfer_money","send_email"}

class ToolCallArgs(BaseModel):
    # 对模型输出的参数做强校验，当成不可信输入
    path:str
    @field_validator('path')
    @classmethod
    def must_be_safe(cls, v):
        if ".." in v or v.startswith("/"): # 防止目录穿越/绝对路径
            raise ValueError(f"参数 {v} 存在安全风险")
        return v

def execute_tool(name, raw_args, registry, confirm=lambda n, _:False):
    # 校验：模型参数先过pydanticÏ
    if name == "delete_file":
        args=ToolCallArgs(**raw_args)
        # model_dump 用来把 Pydantic 模型对象转换成 Python 字典
        raw_args=args.model_dump()
    # 危险操作：强制人工确认
    if name in DANGEROUS and not confirm(name, raw_args):
        raise ValueError(f"操作 {name} 被用户拒绝，已取消")
    # 权限/存在性检查后再执行
    if name not in registry:
        raise PermissionError(f"未注册或无权限的工具: {name}")
    return  registry[name](**raw_args)

# confirm 在生产里弹窗给用户点确认，这里mock直接拒绝
print(execute_tool("delete_file", {"path": "parallel.py"},
                   registry={"delete_file": lambda path: f"删除文件 {path}"},
                   confirm=lambda n, a: False))

