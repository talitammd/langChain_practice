# tools 可供agent调用的工具，由于工具有很多，所以是一个列表
def calc(expr):
    try:
        return str(eval(expr))
    except Exception as e:
        return f"计算出错{e}"


def weather(text):
    return f"{text}是晴天"


TOOLS = {"calculator": calc, "weather": weather}


# reason 推理模型根据当前上下文决定下一步行动
def llm(history):
    last = history[-1]
    if "需要计算" in last and "结果" not in "".join(history):
        # 这里不调用真的llm了，模拟llm提取出了23*17+8这个表达式
        return {"action": "calculator", "input": "23*17+8"}
    elif "天气" in last and "结果" not in "".join(history):
        return {"action": "weather", "input": "天气"}
    elif "结果" in "".join(history):
        return {"action": "finish", "input": "结果已给出"}
    else:
        return {"action": "err", "input": "未找到工具"}


# agent 主循环
def run_agent(task, max_steps=5):
    history = ["任务{}：是什么".format(task)]
    for step in range(max_steps):
        decision = llm(history)  # 推理模型决定下一步要做什么
        # 拿到推理模型下一步要做的行动和要传给该行动的输入
        action, action_input = decision["action"], decision["input"]
        # 如果推理模型决定提前结束，就退出循环
        print(f"第{step+1}步")
        if action == "finish":
            print("最终答案是{}".format(action_input))
            return action_input
        # 否则就调用工具tools来执行下一步行动
        try:
            observation = TOOLS[action](action_input)
            result = f"调用{action}({action_input})，得到结果{observation}"
            history.append(result)
            print(f"{action}({action_input}) = {observation} → {result}")
        except Exception as e:
            print("未找到相应工具")
    print("达到最大步数，未完成任务")


if __name__ == "__main__":
    run_agent("帮我算一下23 乘 17 再加 8")
