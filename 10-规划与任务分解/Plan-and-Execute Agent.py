import json
import openai
from typing import List,Optional
import os

client = openai.OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 替换成你的 Qwen API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 1.数据结构
class SubTask:
    def __init__(self, id: int, description: str, status:str="pending"):
        self.id = id
        self.description = description
        self.status = status
        self.result: Optional[str] = None
    # 当你打印这个对象时，会自动调用这个方法
    def __repr__(self):
        return f"SubTask(id={self.id}, description='{self.description}', status='{self.status}', result='{self.result}')"

# 2.Planner：把总目标（Goal）扔给大模型，并用 System Prompt 强力约束它：“必须输出 JSON 数组”。
def plan(goal: str) -> List[SubTask]:
    """让 LLM 把用户目标分解为子任务列表"""
    resp = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{
            "role": "system",
            "content": """你是一个任务规划器。用户会给你一个总目标，
你需要将它分解为 3-7 个有序的子任务。
输出 JSON 数组，每个元素有 id (int) 和 description (string)。
只输出 JSON，不要其他文字。"""
        },{
            "role": "user",
            "content": f"用户目标：{goal}"
        }],
        temperature=0,
        response_format={"type": "json_object"}
    )
    task_data = json.loads(resp.choices[0].message.content)
    task_list = task_data if isinstance(task_data, List) else [task_data]
    return [SubTask(**task) for task in task_list]
# 3.Executor: 基于已有的上下文，把当前这一个子任务扩写/回答出来，并返回结果字符串。
# 它的工作非常纯粹。它不知道总目标是什么，它只接收两个东西：之前已经做完的所有成果（context）以及当前要做的这一个子任务（task.description）。
def executor(context: str, task: SubTask) -> str:
    resp = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{
            "role": "system",
            "content": "你是一个任务执行器。根据已有上下文完成指定子任务，输出执行结果。"
        },{
            "role": "user",
            "content": f"已完成的上下文:\n{context}\n\n当前子任务: {task.description}"
        }],
        temperature=0,
        max_tokens=512
    )
    return resp.choices[0].message.content

# 4.Re-Planner:每做完一个子任务，都要叫醒大模型重新审计一次,让它判断任务是否需要变更
'''
代码会把已经做完的成果和还未做的计划打包发给大模型。

让模型当裁判：

如果发现后面的计划不用做了，大目标已经达到了，就返回 {"done": true}。

如果发现之前查到的林志玲已经结婚了，接下来的“去给林志玲写情书”计划就不适用了，模型就会动态修改并返回一套新的剩余任务列表。
'''
def replan(
        goal: str,
        completed: list[SubTask],
        remaining: list[SubTask]
)-> tuple[bool, list[SubTask]]:
    """
        根据已完成结果判断是否需要调整计划
        返回: (is_done, updated_remaining_tasks)
    """
    completed_summary = "\n".join([f"✅ {t.id}. {t.description} → 结果: {t.result[:200]}" for t in completed])
    remaining_summary = "\n".join([f"❌ {t.id}. {t.description}" for t in remaining])
    resp = client.chat.completions.create(
        model="qwen-turbo",
        messages=[{
            "role": "system",
            "content": '''
                你是一个计划审查器。根据总目标、已完成的子任务结果、剩余计划，判断:
1. 总目标是否已经完成？如果是，输出 {"done": true, "tasks": []}
2. 剩余计划是否需要调整？如果需要，输出修改后的剩余任务列表。
3. 如果不需要调整，原样返回剩余任务。
输出 JSON: {"done": bool, "tasks": [{"id": int, "description": str}]}
            '''
        },{
            "role": "user",
            "content": f"用户目标：{goal}\n\n已完成的计划:\n{completed_summary}\n\n剩余计划:\n{remaining_summary}"
        }],
        temperature=0,
        response_format={"type": "json_object"}
    )

    result = json.loads(resp.choices[0].message.content)
    if result["done"]:
        return True, []
    new_remaining = [SubTask(**task) for task in result["tasks"]]
    return False, new_remaining

# 5.循环
"""
1. 调用 plan(goal) 生成初始的任务列表
2. 进入循环，最多十步
3. current = tasks.pop(0)，把任务队列里的第一个任务拿出来，送给 executor 去执行
4. 拿到执行结果后，打上 completed 标签，存入已完成列表，并塞进 context 笔记本中
5. 调用 replan。如果裁判说 is_done 是 True，直接提鞋下班；如果返回了新的剩余任务，就用 tasks = new_remaining 覆盖掉老计划。
"""
def plan_and_execute(goal: str,max_steps:int=10) -> None:
    """Plan-and-Execute Agent 主循环"""
    print(f"🎯 目标: {goal}\n")

    # Step1:初始规划
    tasks = plan(goal)
    print("📋 初始计划:")
    for t in tasks:
        print(f"  {t}")
    print()
    completed: List[SubTask] = []
    context: str = ""

    # Step2:逐步执行 + Replan
    for step in range(max_steps):
        if not tasks:
            break

        current = tasks.pop(0)
        print(f"▶️  执行: {current.description}")

        # 执行子任务
        result = executor(context, current)
        current.status = "completed"
        current.result = result
        completed.append(current)
        context += f"▶️  执行: {current.description}\n{result}\n\n"

        # Replan: 检查是否需要调整
        is_done, new_remaining = replan(goal, completed, tasks)
        if is_done:
            print("🎉 目标达成！")
            break

        tasks = new_remaining

    # 汇总最终结果
    final_result = "\n".join([f"✅ {t.id}. {t.description} → 结果: {t.result[:200]}" for t in completed])
    print(f"📊 最终结果:\n{final_result}")
    return final_result

# 6.运行示例
if __name__ == "__main__":
    result = plan_and_execute("帮我看下股票传艺科技")
    print(f"\n📄 最终结果:\n{result}")
