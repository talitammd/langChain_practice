from agent import agent_example

def classify(q): return "research"
def simple_llm_call(q): return "直接回答"
def format_output(r): return f"最终结果: {r}"

def hybrid_system(task):
    """生产常见模式：外层 Workflow + 内层 Agent"""
    # ━━ 外层 Workflow：代码定义大流程 ━━
    # Step 1: 验证输入（确定性逻辑，不用模型）
    if not task.get("query"):
        return "请输入查询词"
    # Step 2: 路由（代码规则 or 简单分类）
    task_type=classify(task["query"]) #确定性路由
    # Step 3: 复杂节点用 Agent 处理
    if task_type == "research":
        # ★ 这个节点套一个 Agent，因为研究路径不可穷举
        return agent_example(task["query"])
    elif task_type == "simple":
        # 简单路径的节点可以复用 LLM 调用
        return simple_llm_call(task["query"])
    else:
        return "未知任务类型"

    # Step 4: 后处理（确定性逻辑）
    return format_output(result)

