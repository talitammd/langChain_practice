# 跳跃游戏 II

> 来源：LeetCode 45
> 日期：2026-08-05
> 难度：中等

## 题目描述

给定一个非负整数数组 nums，最初位于第一个下标，每个元素代表该位置可跳跃的最大长度。返回到达最后一个下标的最小跳跃次数。保证可以到达。

## 解题思路

### 核心知识点

- 贪心 + 层次推进：按"每跳一次能到的范围"推进，走到范围尽头才跳一次
- 与 LC55 的关系：LC55 判断能不能到（维护 maxReach），LC45 算最少跳几次（维护 maxReach + curEnd + jumps）
- 循环只到 nums.length - 2，走到最后一个位置不需要再跳

### 步骤拆解

1. jumps = 0，curEnd = 0，maxReach = 0
2. 遍历到倒数第二个位置：更新 maxReach = max(maxReach, i + nums[i])
3. 当 i == curEnd（走到当前范围尽头）：jumps++，curEnd = maxReach
4. 返回 jumps

## 最终代码

```java
class Solution {
    public int jump(int[] nums) {
        int jumps = 0;
        int curEnd = 0;
        int maxReach = 0;

        for (int i = 0; i < nums.length - 1; i++) {
            maxReach = Math.max(maxReach, i + nums[i]);
            if (i == curEnd) {
                jumps++;
                curEnd = maxReach;
            }
        }
        return jumps;
    }
}
```

## 踩过的坑

- 无，一次写对

## Java API 笔记

- `Math.max(a, b)`：巩固使用，取两个值最大值

## 一句话总结

跳跃游戏 II 的核心是层次推进：维护当前范围边界 curEnd 和下一跳最远 maxReach，走到 curEnd 才跳一次，循环不到最后一个位置。
