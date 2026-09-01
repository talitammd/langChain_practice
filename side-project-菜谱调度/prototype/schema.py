# -*- coding: utf-8 -*-
"""
菜谱步骤的结构化数据模型。

设计核心思路：
一份菜谱由若干「步骤」组成，每个步骤最关键的调度属性有三个：
1. 人力占用类型（ATTENDED / UNATTENDED）—— 决定这段时间人能不能腾出手做别的事
2. 占用的物理资源（灶眼、烤箱、蒸锅...）—— 决定资源冲突
3. 依赖关系（必须在哪个步骤完成后才能开始）—— 决定顺序约束

这三者是调度算法能"见缝插针"排程的全部依据。
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceType(str, Enum):
    """步骤的人力占用类型"""

    ATTENDED = "attended"  # 需要人全程盯着操作，比如切菜、颠勺、翻炒
    UNATTENDED = "unattended"  # 可以放着不管，人可以去做别的事，比如炖煮、腌制、烤箱烘烤
    PASSIVE_WAIT = "passive_wait"  # 需要等待但不能走开太久，比如收汁前观察，一般归为 attended 的弱化版


class ResourceType(str, Enum):
    """步骤占用的物理资源类型，用于检测资源冲突"""

    STOVE = "stove"  # 灶眼（炒、煮、炖）
    OVEN = "oven"  # 烤箱
    STEAMER = "steamer"  # 蒸锅
    HANDS = "hands"  # 人手（切配、装盘等不依赖灶具的操作）
    CUTTING_BOARD = "cutting_board"  # 案板


class RecipeStep(BaseModel):
    """单个菜谱步骤的结构化表示"""

    step_id: str = Field(..., description="步骤唯一标识，格式如 'dish1_step2'")
    dish_name: str = Field(..., description="所属菜品名称")
    order_in_dish: int = Field(..., description="该步骤在本道菜中的顺序号，从 1 开始")
    description: str = Field(..., description="步骤的自然语言描述，如'炒糖色至枣红色'")

    duration_minutes: float = Field(..., description="预计耗时（分钟）")
    attendance: AttendanceType = Field(..., description="人力占用类型")

    resources: list[ResourceType] = Field(
        default_factory=list, description="该步骤占用的物理资源列表，可能同时占用多种"
    )

    depends_on: Optional[str] = Field(
        default=None, description="前置依赖步骤的 step_id，必须等该步骤完成后才能开始，同菜内部依赖"
    )

    # 执行跟随层用到的字段：记录实际发生的情况，用于动态重新调度
    actual_start_minute: Optional[float] = Field(default=None, description="实际开始时间（相对计划起点的分钟数），未开始为 None")
    actual_duration_minutes: Optional[float] = Field(default=None, description="实际耗时，未完成为 None")

    @property
    def is_done(self) -> bool:
        return self.actual_duration_minutes is not None


class Recipe(BaseModel):
    """一道菜的完整结构化表示"""

    dish_name: str
    steps: list[RecipeStep]

    def total_duration_if_serial(self) -> float:
        """如果这道菜单独、串行执行，总耗时是多少（用于对比排程收益）"""
        return sum(s.duration_minutes for s in self.steps)


class MealPlan(BaseModel):
    """多道菜组成的一餐，是调度算法的输入"""

    dishes: list[Recipe]

    def all_steps(self) -> list[RecipeStep]:
        result: list[RecipeStep] = []
        for dish in self.dishes:
            result.extend(dish.steps)
        return result

    def naive_serial_total_minutes(self) -> float:
        """完全不并行、按菜品顺序一道道做完的总耗时，作为调度算法效果的基线对比"""
        return sum(dish.total_duration_if_serial() for dish in self.dishes)
