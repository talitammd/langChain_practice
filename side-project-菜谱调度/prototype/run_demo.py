# -*- coding: utf-8 -*-
"""
端到端演示脚本：把三道菜（红烧肉、清蒸鱼、炒青菜）喂给调度算法，
输出并行排程时间线，并和"串行做完一道再做下一道"的耗时做对比。
"""
from sample_recipes import sample_meal_plan
from scheduler import ScheduleResult, schedule_meal_plan


def format_minute(m: float) -> str:
    """把分钟数格式化成 mm:ss 形式，方便阅读"""
    total_seconds = round(m * 60)
    mm, ss = divmod(total_seconds, 60)
    return f"{mm:02d}:{ss:02d}"


def print_timeline(result: ScheduleResult) -> None:
    print("=" * 60)
    print("并行排程时间线（按开始时间排序）")
    print("=" * 60)
    for item in result.timeline_sorted():
        step = item.step
        tag = "【需盯着】" if step.attendance.value == "attended" else "【可放手】"
        print(
            f"[{format_minute(item.start_minute)} - {format_minute(item.end_minute)}] "
            f"{tag} {step.dish_name} · {step.description}"
        )
    print("-" * 60)
    print(f"并行排程总耗时：{format_minute(result.total_minutes)}（{result.total_minutes:.1f} 分钟）")


def print_comparison(result: ScheduleResult) -> None:
    serial_total = sample_meal_plan.naive_serial_total_minutes()
    parallel_total = result.total_minutes
    saved = serial_total - parallel_total
    saved_pct = saved / serial_total * 100 if serial_total > 0 else 0

    print("=" * 60)
    print("效果对比：并行排程 vs 依次做完每道菜")
    print("=" * 60)
    print(f"依次串行做完三道菜预计耗时：{format_minute(serial_total)}（{serial_total:.1f} 分钟）")
    print(f"AI 并行排程后总耗时      ：{format_minute(parallel_total)}（{parallel_total:.1f} 分钟）")
    print(f"节省时间                 ：{format_minute(saved)}（约 {saved_pct:.0f}%）")


def print_gantt_ascii(result: ScheduleResult) -> None:
    """用字符画一个简易甘特图，直观看到多道菜步骤如何交叉并行"""
    print("=" * 60)
    print("简易甘特图（每格代表 1 分钟）")
    print("=" * 60)

    dishes = sorted({item.step.dish_name for item in result.scheduled})
    total = int(result.total_minutes) + 1

    # 为每道菜画一行时间轴
    for dish in dishes:
        row = ["·"] * total
        for item in result.scheduled:
            if item.step.dish_name != dish:
                continue
            symbol = "█" if item.step.attendance.value == "attended" else "▒"
            start = int(item.start_minute)
            end = int(item.end_minute)
            for t in range(start, max(end, start + 1)):
                if t < total:
                    row[t] = symbol
        print(f"{dish:<6}|" + "".join(row))

    print("图例：█ = 需要人盯着(ATTENDED)   ▒ = 可以放手(UNATTENDED)   · = 未开始/空闲")
    # 打印时间刻度（每 5 分钟标一个数字）
    ruler = ["".join(str(t % 10) if t % 5 == 0 else " " for t in range(total))]
    print("       " + ruler[0])


def sanity_check(result: ScheduleResult) -> list[str]:
    """基本合理性校验：检查有没有资源冲突或依赖顺序错误，返回问题列表（空列表表示通过）"""
    problems: list[str] = []
    items = result.timeline_sorted()

    # 1. 校验依赖顺序：每个 depends_on 的完成时间必须 <= 本步骤开始时间
    finish_time = {item.step.step_id: item.end_minute for item in items}
    for item in items:
        dep = item.step.depends_on
        if dep is not None:
            if finish_time[dep] > item.start_minute + 1e-6:
                problems.append(
                    f"依赖顺序错误：{item.step.step_id} 在依赖 {dep} 完成前就开始了"
                )

    # 2. 校验资源冲突：同一资源同一时刻不能被两个步骤占用
    from collections import defaultdict

    resource_intervals: dict = defaultdict(list)
    for item in items:
        for r in item.step.resources:
            resource_intervals[r].append((item.start_minute, item.end_minute, item.step.step_id))

    for r, intervals in resource_intervals.items():
        intervals.sort()
        for i in range(len(intervals) - 1):
            _, end1, id1 = intervals[i]
            start2, _, id2 = intervals[i + 1]
            if start2 < end1 - 1e-6:
                problems.append(f"资源冲突：{r} 被 {id1} 和 {id2} 同时占用")

    # 3. 校验人力唯一性：同一时刻 ATTENDED 步骤不能超过一个
    attended_items = [it for it in items if it.step.attendance.value == "attended"]
    attended_items.sort(key=lambda it: it.start_minute)
    for i in range(len(attended_items) - 1):
        if attended_items[i].end_minute > attended_items[i + 1].start_minute + 1e-6:
            problems.append(
                f"人力冲突：{attended_items[i].step.step_id} 和 "
                f"{attended_items[i + 1].step.step_id} 同时需要人盯着"
            )

    return problems


def main() -> None:
    result = schedule_meal_plan(sample_meal_plan)

    print_timeline(result)
    print()
    print_gantt_ascii(result)
    print()
    print_comparison(result)

    print()
    print("=" * 60)
    print("合理性校验")
    print("=" * 60)
    problems = sanity_check(result)
    if problems:
        print("发现问题：")
        for p in problems:
            print(f"  - {p}")
    else:
        print("通过：没有发现资源冲突、人力冲突或依赖顺序错误。")


if __name__ == "__main__":
    main()
