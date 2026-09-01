# -*- coding: utf-8 -*-
"""
多菜谱并行调度算法。

问题本质：这是一个"带资源约束的任务调度问题"（Resource-Constrained Project
Scheduling Problem, RCPSP 的简化版）。

约束条件：
1. 依赖约束：每个步骤必须在它的 depends_on 步骤完成后才能开始（同菜内的顺序不能乱）
2. 资源约束：同一时刻，同一种资源（灶眼/蒸锅/人手...）只能被一个步骤占用
3. 人力唯一约束：ATTENDED 类型的步骤必须有人全程盯着，而人只有一个，
   所以任意时刻最多只有一个 ATTENDED 步骤在执行
   （UNATTENDED 步骤不占用人力，可以和任意其他步骤同时进行，只要不抢物理资源）

算法思路：事件驱动的贪心调度（greedy list scheduling）
- 维护一个"当前时间"指针，每次向前推进到下一个关键事件（某步骤完成的时刻）
- 每个事件点，找出所有"依赖已满足 + 所需资源空闲 + 人力空闲(若需要)"的候选步骤
- 按优先级规则从候选中选步骤开始执行：
    优先级 1：ATTENDED 步骤优先于新开始 UNATTENDED 步骤
             （尽快让人手动起来，不要让人闲着，UNATTENDED 步骤反正不占人，可以晚点开始）
    优先级 2：同类型步骤中，剩余总耗时（含后续依赖链）更长的优先
             （类似关键路径法 CPM，越可能拖累总工期的步骤要尽早启动）
- 重复直到所有步骤都被安排完
"""
from __future__ import annotations

from dataclasses import dataclass, field

from schema import AttendanceType, MealPlan, RecipeStep, ResourceType


@dataclass
class ScheduledStep:
    """一个步骤被排入时间线后的记录"""

    step: RecipeStep
    start_minute: float
    end_minute: float

    @property
    def duration(self) -> float:
        return self.end_minute - self.start_minute


@dataclass
class ScheduleResult:
    scheduled: list[ScheduledStep] = field(default_factory=list)

    @property
    def total_minutes(self) -> float:
        if not self.scheduled:
            return 0.0
        return max(s.end_minute for s in self.scheduled)

    def timeline_sorted(self) -> list[ScheduledStep]:
        return sorted(self.scheduled, key=lambda s: (s.start_minute, s.step.dish_name))


def _remaining_chain_duration(step: RecipeStep, all_steps: dict[str, RecipeStep]) -> float:
    """计算某步骤之后，同一道菜里还剩多少耗时（含自己），用作关键路径优先级依据。"""
    total = step.duration_minutes
    # 找到同一道菜里 order_in_dish 更大的步骤，简化处理：按顺序号线性链式相加
    dish_steps = [s for s in all_steps.values() if s.dish_name == step.dish_name]
    for s in dish_steps:
        if s.order_in_dish > step.order_in_dish:
            total += s.duration_minutes
    return total


def schedule_meal_plan(meal_plan: MealPlan) -> ScheduleResult:
    all_steps: dict[str, RecipeStep] = {s.step_id: s for s in meal_plan.all_steps()}

    # 每个 step_id 的状态： pending -> scheduled（已排入日程，但可能还没到结束时间）-> done（真正执行完毕）
    # 关键点：一个步骤在被调度的那一刻只是"开始"，不能立刻视为"完成"，
    # 必须等 current_time 推进到它的 end_minute，才能让依赖它的步骤开始。
    status: dict[str, str] = {sid: "pending" for sid in all_steps}
    finish_time: dict[str, float] = {}

    # 资源占用表：resource -> 释放时间（0 表示当前空闲）
    resource_free_at: dict[ResourceType, float] = {r: 0.0 for r in ResourceType}
    hands_free_at = 0.0  # 人力是全局唯一稀缺资源，单独建模

    result = ScheduleResult()
    current_time = 0.0
    remaining = set(all_steps.keys())

    def dependency_satisfied(step: RecipeStep, at_time: float) -> bool:
        if step.depends_on is None:
            return True
        dep_finish = finish_time.get(step.depends_on)
        # 依赖步骤必须已经真正结束（结束时间 <= 当前时间），而不是仅仅"已排入日程"
        return dep_finish is not None and dep_finish <= at_time + 1e-9

    def resources_available(step: RecipeStep, at_time: float) -> bool:
        for r in step.resources:
            if resource_free_at[r] > at_time + 1e-9:
                return False
        return True

    def hands_available(step: RecipeStep, at_time: float) -> bool:
        if step.attendance == AttendanceType.ATTENDED:
            return hands_free_at <= at_time + 1e-9
        return True  # UNATTENDED 不需要人手

    safety_counter = 0
    while remaining:
        safety_counter += 1
        if safety_counter > 10000:
            raise RuntimeError("调度循环超过安全上限，可能存在无法满足的依赖环")

        # 找出此刻可以开始的候选步骤
        candidates: list[RecipeStep] = []
        for sid in remaining:
            step = all_steps[sid]
            if (
                dependency_satisfied(step, current_time)
                and resources_available(step, current_time)
                and hands_available(step, current_time)
            ):
                candidates.append(step)

        if candidates:
            # 优先级排序：ATTENDED 优先于 UNATTENDED；同类型内关键路径长的优先
            candidates.sort(
                key=lambda s: (
                    0 if s.attendance == AttendanceType.ATTENDED else 1,
                    -_remaining_chain_duration(s, all_steps),
                )
            )

            step = candidates[0]
            start = current_time
            end = start + step.duration_minutes

            for r in step.resources:
                resource_free_at[r] = end
            if step.attendance == AttendanceType.ATTENDED:
                hands_free_at = end

            status[step.step_id] = "done"
            finish_time[step.step_id] = end
            remaining.remove(step.step_id)
            result.scheduled.append(ScheduledStep(step=step, start_minute=start, end_minute=end))
            # 不推进 current_time，同一时刻可能还有别的资源空闲、可以并行安排别的步骤
            continue

        # 没有立即可开始的候选，说明要等某个资源/人力/依赖释放，把时间推进到下一个"事件点"
        future_times = []
        future_times.extend(t for t in resource_free_at.values() if t > current_time + 1e-9)
        future_times.append(hands_free_at) if hands_free_at > current_time + 1e-9 else None
        if not future_times:
            raise RuntimeError(
                f"调度无法推进：剩余步骤 {remaining}，可能存在无法满足的依赖或资源死锁"
            )
        current_time = min(future_times)

    return result
