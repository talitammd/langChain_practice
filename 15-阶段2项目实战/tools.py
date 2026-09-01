from dataclasses import dataclass
from typing import Any
import json
import time

@dataclass
class ToolResult:
    success:bool
    data:Any
    error:str=""

def mock_search_api(query:str) -> Any:
    time.sleep(1)
    return json.dumps([{"title":query,"content":query}])

def mock_extract_web_content(url:str) -> Any:
    time.sleep(1)
    return "网页内容"

# 搜索工具
def search_web(query:str) -> ToolResult:
    try:
        results = mock_search_api(query)
        if not results:
            return ToolResult(success=False,error="搜索结果为空")
        return ToolResult(success=True,data=json.loads(results))
    except TimeoutError:
        return ToolResult(success=False,error="搜索超时")
    except Exception as e:
        return ToolResult(success=False,error=f"搜索异常：{e}")

# 网页内容提取工具
def extract_web_content(url:str) -> ToolResult:
    try:
        response = mock_extract_web_content(url)
        if not response:
            return ToolResult(success=False,error="提取内容失败")
        return ToolResult(success=True,data=response)
    except Exception as e:
        return ToolResult(success=False,error=f"提取内容异常：{e}")

# 代码执行工具
def execute_code(code:str) -> ToolResult:
    try:
        exec(code)
        return ToolResult(success=True,data="代码执行成功")
    except Exception as e:
        return ToolResult(success=False,error=f"代码执行异常：{e}")

# TOOLS 注册表
TOOLS = {
    "search_web":search_web,
    "extract":extract_web_content,
    "code":execute_code
}
