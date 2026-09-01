# 买卖股票的最佳时机 II

> 来源：LeetCode 122
> 日期：2026-08-05
> 难度：中等

## 题目描述

给定一个数组 prices，可以反复买卖股票，但同一时间最多持有一股。求最大利润。

## 解题思路

### 核心知识点

- 贪心算法：只要今天比昨天贵就"昨天买今天卖"，把所有正差价累加
- 与 LC121 的区别：LC121 只能买卖一次（维护最小值），LC122 可以反复买卖（累加正差价）
- 可简化写法：不需要维护 minPrice，直接比较相邻两天差价

### 步骤拆解

1. maxProfit = 0
2. 从第二天开始遍历，计算与前一天的差价
3. 差价为正就加到 maxProfit 里
4. 返回 maxProfit

## 最终代码

```java
class Solution {
    public int maxProfit(int[] prices) {
        int maxProfit = 0;
        for (int i = 1; i < prices.length; i++) {
            if (prices[i] - prices[i - 1] > 0) {
                maxProfit += prices[i] - prices[i - 1];
            }
        }
        return maxProfit;
    }
}
```

## 踩过的坑

- 无逻辑错误，但初版多维护了一个 minPrice 变量，可简化为直接比较相邻差价

## Java API 笔记

- 无新增 API，巩固了 for 循环从 1 开始遍历

## 一句话总结

可反复买卖的股票题用贪心——把所有正差价加起来就是最大利润，不需要维护买入价，只看相邻两天的涨幅。
