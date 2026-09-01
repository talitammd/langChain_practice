# -*- coding: utf-8 -*-
"""
三道菜的结构化样例数据。

这一步在生产系统里应该由「LLM 解析层」自动从自然语言菜谱生成
（把菜谱文字喂给 LLM，用 Recipe 这个 Pydantic Schema 做 structured output 约束）。
原型阶段为了让我们聚焦验证调度算法本身是否合理，先手工构造这三道菜的结构化数据，
相当于"假设解析层已经完美工作"，输出恰好符合 schema.py 里定义的结构。

选的三道菜刻意覆盖不同的调度特征：
- 红烧肉：大量 UNATTENDED 炖煮时间，且占用灶眼 —— 调度算法应该把这段空闲插给别的菜
- 清蒸鱼：ATTENDED 处理 + UNATTENDED 蒸制，占用蒸锅（与灶眼资源不冲突）
- 炒青菜：全程 ATTENDED，耗时短，适合插在别的菜的等待间隙里，且必须最后做（避免出锅后放凉）
"""
from schema import AttendanceType, MealPlan, Recipe, RecipeStep, ResourceType

# ---------- 红烧肉 ----------
hongshaorou_steps = [
    RecipeStep(
        step_id="hsr_1",
        dish_name="红烧肉",
        order_in_dish=1,
        description="五花肉切块，冷水下锅焯水",
        duration_minutes=8,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE, ResourceType.HANDS],
        depends_on=None,
    ),
    RecipeStep(
        step_id="hsr_2",
        dish_name="红烧肉",
        order_in_dish=2,
        description="热锅冷油，下冰糖炒糖色至枣红色",
        duration_minutes=5,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE],
        depends_on="hsr_1",
    ),
    RecipeStep(
        step_id="hsr_3",
        dish_name="红烧肉",
        order_in_dish=3,
        description="下肉块翻炒上色，加葱姜八角料酒生抽老抽，加热水没过肉",
        duration_minutes=5,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE],
        depends_on="hsr_2",
    ),
    RecipeStep(
        step_id="hsr_4",
        dish_name="红烧肉",
        order_in_dish=4,
        description="转小火炖煮，中途基本不用管，偶尔看一眼別烧干",
        duration_minutes=40,
        attendance=AttendanceType.UNATTENDED,
        resources=[ResourceType.STOVE],
        depends_on="hsr_3",
    ),
    RecipeStep(
        step_id="hsr_5",
        dish_name="红烧肉",
        order_in_dish=5,
        description="大火收汁，需要人守着防止糊锅",
        duration_minutes=5,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE],
        depends_on="hsr_4",
    ),
]

# ---------- 清蒸鱼 ----------
qingzhengyu_steps = [
    RecipeStep(
        step_id="qzy_1",
        dish_name="清蒸鱼",
        order_in_dish=1,
        description="鱼处理干净，打花刀，姜片垫底铺葱",
        duration_minutes=10,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.HANDS, ResourceType.CUTTING_BOARD],
        depends_on=None,
    ),
    RecipeStep(
        step_id="qzy_2",
        dish_name="清蒸鱼",
        order_in_dish=2,
        description="上锅蒸制，全程可以离开去做别的事",
        duration_minutes=10,
        attendance=AttendanceType.UNATTENDED,
        resources=[ResourceType.STEAMER],
        depends_on="qzy_1",
    ),
    RecipeStep(
        step_id="qzy_3",
        dish_name="清蒸鱼",
        order_in_dish=3,
        description="出锅倒掉蒸鱼水，铺新葱丝姜丝，浇热油淋蒸鱼豉油",
        duration_minutes=4,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE, ResourceType.HANDS],
        depends_on="qzy_2",
    ),
]

# ---------- 炒青菜 ----------
chaoqingcai_steps = [
    RecipeStep(
        step_id="cqc_1",
        dish_name="炒青菜",
        order_in_dish=1,
        description="青菜择洗干净，蒜切片",
        duration_minutes=6,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.HANDS, ResourceType.CUTTING_BOARD],
        depends_on=None,
    ),
    RecipeStep(
        step_id="cqc_2",
        dish_name="炒青菜",
        order_in_dish=2,
        description="大火快炒，全程需要人不停颠勺，出锅即装盘",
        duration_minutes=3,
        attendance=AttendanceType.ATTENDED,
        resources=[ResourceType.STOVE],
        depends_on="cqc_1",
    ),
]

hongshaorou = Recipe(dish_name="红烧肉", steps=hongshaorou_steps)
qingzhengyu = Recipe(dish_name="清蒸鱼", steps=qingzhengyu_steps)
chaoqingcai = Recipe(dish_name="炒青菜", steps=chaoqingcai_steps)

sample_meal_plan = MealPlan(dishes=[hongshaorou, qingzhengyu, chaoqingcai])

# 关键调度提示：炒青菜应该最后炒（出锅即食，放久会蔫），
# 这类"软约束"后面调度算法里通过"晚开始优先级"体现，而不是写死顺序。
