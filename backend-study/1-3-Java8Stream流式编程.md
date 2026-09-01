# 1-3 Java 8 Stream 流式编程

> 阶段：Java 核心基础 | 掌握程度：熟悉 | 预计学时：5h
> 示例全部取材于外呼项目 shangou-merchant-ai-marketing，读的时候直接对照你自己的代码。

## 本节定位

你读不懂的那行 `callTask.setPoiIds(String.join(",", createDTO.getPoiIds().stream().map(String::valueOf).collect(Collectors.toList())))` 就是本节的入口。业务代码里 80% 的数据转换逻辑是 Stream 链，**读懂它是看懂 AI coding 代码的第一关**；面试中 Stream 是 Java 8 语法必考项，核心考点两个：惰性求值、collect 家族。

## 核心知识讲解

### 1. 三段式结构（一张图记住 Stream）

```
list.stream()        .filter(...)   .map(...)      .collect(...)
     ↑                  ↑              ↑                ↑
  创建流            中间操作①      中间操作②         终端操作
 (数据源开闸)      (记账，不执行)  (记账，不执行)    (结账，真正执行)
```

**结论先行**：中间操作只是"记账"，终端操作才"结账"。没有终端操作，中间操作一行都不会执行——这叫**惰性求值**，面试必考。

### 2. Lambda 语法速读（看懂一切链式代码的前置）

**Lambda 就是一段"现写的迷你函数"**：`->` 左边是参数列表，右边是函数体（表达式的值就是返回值）。

| Lambda | 读法 | 用在哪 |
|---|---|---|
| `x -> x > 5` | 接收 x，返回 x>5 | filter 的条件 |
| `x -> x.getStatus()` | 接收 x，返回状态 | map 的转换 |
| `(oldV, newV) -> oldV` | 接收两个值，返回前者 | toMap 冲突时保留旧值 |
| `() -> getDefault()` | 无参，返回默认值 | orElseGet 的兜底 |

**本节最重要的心智模型——"函数三问"**。`filter`、`toMap` 这些 API 的参数不是数据，是**函数**。你把函数交给 API，API 在内部调用它。任何 lambda 看不懂时，问：

1. **谁调用它？** → API 内部（不是你的代码）
2. **参数从哪来？** → API 把遍历到的数据塞给你
3. **返回值去哪了？** → 被 API 接收，决定 API 的行为

语法只有"左边参数、右边返回"一件事，难的从来是这三问。

### 3. 中间操作 vs 终端操作

| 类别 | 操作 | 作用 | 惰性？ |
|---|---|---|---|
| 中间 | filter | 过滤 | ✅ |
| 中间 | map | 一对一转换 | ✅ |
| 中间 | flatMap | 一对多打平 | ✅ |
| 中间 | sorted / distinct | 排序 / 去重 | ✅ |
| 中间 | limit / skip | 截取 / 跳过 | ✅ |
| 中间 | peek | 偷看（调试用） | ✅ |
| 终端 | collect | 收集为集合/Map | 触发执行 |
| 终端 | forEach | 逐个消费 | 触发执行 |
| 终端 | count / min / max | 计数 / 最值 | 触发执行 |
| 终端 | anyMatch / allMatch / noneMatch | 短路判断 | 触发执行 |
| 终端 | findFirst / findAny | 找第一个/任意一个 | 触发执行 |
| 终端 | reduce | 归约累加 | 触发执行 |

### 4. map vs flatMap（面试高频对比）

```
map:      ["a","b"]        →  ["A","B"]          一对一
flatMap:  ["a b","c d"]    →  ["a","b","c","d"]   一对多后打平
```

一句话：map 是"每个元素变身"，flatMap 是"每个元素变身后拆开摊平"。flatMap 的入参必须返回一个 Stream。

### 5. collect 家族（业务代码出现率最高）

| 收集器 | 作用 | 项目场景 |
|---|---|---|
| `toList()` / `toSet()` | 收集为 List/Set | 通用 |
| `joining(",")` | 拼字符串 | poiIds 拼接 |
| `toMap(k, v)` | 转 Map | **重复 key 抛异常，见下方大坑** |
| `groupingBy(classifier)` | 按键分组 | 外呼记录按状态分组 |
| `counting()` / `summingInt()` | 计数 / 求和 | 报表统计 |
| `partitioningBy(pred)` | 按布尔分两组 | 接通/未接通 |

**toMap 两大坑（面试 + 生产双高频）**：
1. 重复 key → `IllegalStateException: Duplicate key`，解决：加第三个参数——merge 函数（执行轨迹见下）
2. value 为 null → NPE，解决：value 先兜底 `Objects.toString(v, "")`

**merge 函数执行全过程（拿真实数据逐行走一遍）**：

```java
// 场景：两个任务圈选了同一家店，列表里有两个 id=1
List<Poi> poiList = Arrays.asList(
        new Poi(1L, "永辉超市"),
        new Poi(2L, "物美超市"),
        new Poi(1L, "永辉二店"));   // ⚠️ 和第 1 个撞 key

Map<Long, String> m = poiList.stream().collect(
        Collectors.toMap(Poi::getId, Poi::getName, (oldV, newV) -> oldV));
```

```
toMap 内部执行轨迹（逐个放入）：
(1,"永辉超市")  → key=1 不存在 → 直接放入        {1:"永辉超市"}
(2,"物美超市")  → key=2 不存在 → 直接放入        {1:"永辉超市", 2:"物美超市"}
(1,"永辉二店")  → key=1 已存在！
                 此刻 toMap 调用你写的函数（函数三问在此刻发生）：
                 oldV = "永辉超市"  ← map 里已有的旧值（toMap 塞给你）
                 newV = "永辉二店"  ← 正要放入的新值（toMap 塞给你）
                 (oldV, newV) -> oldV 返回 "永辉超市"
                 返回值被 toMap 拿走 → 作为 key=1 最终保留的值
                 结果 {1:"永辉超市", 2:"物美超市"}   ← 旧值获胜
```

**merge 函数 = 冲突仲裁员**：只有撞 key 的瞬间才被调用，问你"旧值新值留哪个"，返回值就是裁决。前两个商家没有冲突，仲裁员根本不出场。换成 `(oldV, newV) -> newV` = 新值覆盖；不传 = toMap 无从裁决，直接抛 `IllegalStateException: Duplicate key`。

### 6. 方法引用四种形态（读懂 AI 代码的钥匙）

| 写法 | 等价 lambda | 出现场景 |
|---|---|---|
| `String::valueOf` | `x -> String.valueOf(x)` | 静态方法 |
| `CallRecord::getStatus` | `x -> x.getStatus()` | 类的实例方法 |
| `list::add` | `x -> list.add(x)` | 对象的方法 |
| `CallRecordDO::new` | `() -> new CallRecordDO()` | 构造器 |

看到 `类名::方法` 不知道是静态还是实例？看方法签名：静态方法 `valueOf(Long)` 只有一个参数；实例方法 `getStatus()` 零参数，参数其实是元素自己。

### 7. 并行流 parallelStream（面试高频）

**结论先行**：默认用 `stream()`，并行流必须单独评估。

| 可以用并行流 | 别用并行流 |
|---|---|
| CPU 密集 + 数据量大（10万+） | IO 密集（RPC/DB 调用，占死公共 ForkJoinPool） |
| 数据源易拆分（ArrayList） | 有共享可变变量（线程不安全） |
| 元素处理互相独立 | 要求顺序、有状态依赖 |

追问"为什么 IO 密集不行"：并行流共用全局 ForkJoinPool.commonPool()，IO 阻塞会占满线程池，拖垮整个 JVM 里所有并行流。

### 8. 三个必踩的坑

1. **流只能消费一次**：复用同一个 Stream 对象再操作 → `IllegalStateException: stream has already been operated upon`
2. **forEach 里改外部集合**：要么 ConcurrentModificationException，要么逻辑错乱
3. **只写中间操作没写终端**：整条链一次都不执行（惰性求值的另一面）

## 代码示例

```java
// 例1：你问的那行，逐步注释执行状态
List<Long> poiIds = Arrays.asList(123L, 456L, 789L);
String result = String.join(",",
        poiIds.stream()                     // Stream<Long>: 123,456,789
              .map(String::valueOf)         // Stream<String>: "123","456","789"
              .collect(Collectors.toList()));// List<String>
// String.join 拼接 → "123,456,789"

// 例2：外呼记录按状态分组（报表统计真实写法，SjCallCrane 里的逻辑）
// 状态: 1=INIT 2=CREATE_CALL 3=CALL_BACK 4=REGISTER
Map<Integer, List<CallRecord>> byStatus = records.stream()
        .collect(Collectors.groupingBy(CallRecord::getStatus));
// 结果: {1=[...待外呼], 2=[...已创建], 3=[...已回调]}

// 例3：分组+计数一步到位（运营平台任务进度条就这么算的）
Map<Integer, Long> countByStatus = records.stream()
        .collect(Collectors.groupingBy(CallRecord::getStatus, Collectors.counting()));

// 例4：toMap 的坑与正确写法
Map<Long, String> poiIdToName = poiList.stream()
        .collect(Collectors.toMap(Poi::getId, Poi::getName));
        // ⚠️ 两个任务圈选了同一个 poi → IllegalStateException
Map<Long, String> fixed = poiList.stream()
        .collect(Collectors.toMap(Poi::getId, Poi::getName, (oldV, newV) -> oldV)); // ✅

// 例5：filter + findFirst 短路求值（找第一个待外呼的记录）
Optional<CallRecord> first = records.stream()
        .filter(r -> r.getStatus() == 1)
        .findFirst();   // 命中即停，后面的元素不再遍历
```

## 面试高频问题

1. **什么是惰性求值？** 中间操作只构建操作链不执行，终端操作触发一次性遍历整条管道。
2. **map vs flatMap？** 一对一转换 vs 一对多打平，flatMap 参数必须返回 Stream。
3. **toMap 重复 key 会怎样？** 抛 IllegalStateException，用三参重载给合并函数。
4. **orElse vs orElseGet？**（Optional 课展开，先记住：参数求值时机不同）
5. **findFirst vs findAny？** 串行流里基本等价（都返回第一个），并行流里 findAny 谁先完成返回谁、性能更好。
6. **Stream 和 for 循环谁快？** 小数据量 for 快（Stream 有管道构建开销）；大数据量+CPU 密集并行流有优势；业务代码以可读性为先，性能敏感路径单独压测。
7. **并行流的坑？** 共用 commonPool，IO 密集场景占满线程池；有共享可变状态会出错。

## 练习题

### 概念自测题（判断对错）

1. `.stream().filter(x -> x > 5)` 执行后，过滤已经发生了。
2. 同一个 Stream 对象可以先 count() 再 collect()。
3. `map(x -> x.split(","))` 想把 `"a,b"` 变成 `["a","b"]`，结果流的元素类型是 String[]。
4. `collect(Collectors.toMap(Poi::getId, Poi::getName))` 中 value 出现 null 会抛 NPE。
5. parallelStream 一定能加速。

### 动手编码题

1. 把下面 AI coding 的 for 循环改写成 Stream 链（保留语义）：
```java
List<String> phones = new ArrayList<>();
for (KaCallContactDTO c : contacts) {
    if (c.getPhone() != null && c.getPhone().startsWith("1")) {
        phones.add(c.getPhone());
    }
}
```
2. 给 `List<CallRecord>`（字段：status, poiId），输出 `Map<Integer, Long>`——每个状态多少条记录。
3. 排错：这段代码想把任务名拼成逗号分隔字符串，但有 bug（两个），找出来：
```java
Stream<CallTask> s = tasks.stream().map(t -> t.getTaskName());
String names = String.join(",", s.collect(Collectors.toList()));
String again = String.join(",", s.collect(Collectors.toList()));
```

4. 上机题：构造含重复 id 的 `List<Poi>`，分别用 `(oldV, newV) -> oldV`、`(oldV, newV) -> newV`、不传 merge 函数三种方式 toMap，记下三种结果。

### 面试模拟题（含追问链）

1. 「你们项目里哪里用了 Stream？」→ 讲 poiIds 拼接或状态分组统计 → 追问：「为什么用 Collectors.groupingBy 而不是 for 循环往 Map 里塞？」
2. 「map 和 flatMap 的区别？」→ 追问：「你项目里哪个场景必须用 flatMap？」（提示：List<List<X>> 打平，如多个任务的记录合并）
3. 「parallelStream 你敢在生产用吗？」→ 追问：「你们外呼 10 万商家为什么不并行处理？」（答案方向：调外部平台 IO 密集 + 平台侧限流，不是本地 CPU 瓶颈）
4. 「Stream 惰性求值底层怎么实现的？」（简单版：每个操作包装成一层 Stage/Sink，终端操作从最后一层往回拉数据，元素逐个流过管道，类似流水线）

## 答案要点

<details>
<summary>点击展开答案</summary>

**概念自测**：1.✗（惰性，无终端操作不执行）2.✗（流只能消费一次，第二次抛 IllegalStateException）3.✓（split 返回 String[]，想打平要用 flatMap）4.✓（toMap value 为 null 抛 NPE）5.✗（数据量小反而更慢，共享状态会出错）

**动手编码 1**：
```java
List<String> phones = contacts.stream()
        .map(KaCallContactDTO::getPhone)
        .filter(p -> p != null && p.startsWith("1"))
        .collect(Collectors.toList());
```

**动手编码 2**：
```java
Map<Integer, Long> result = records.stream()
        .collect(Collectors.groupingBy(CallRecord::getStatus, Collectors.counting()));
```

**动手编码 3**：① `s` 消费两次，第二行抛 IllegalStateException；② `map(t -> t.getTaskName())` 之后流里是 String 不是 CallTask，但变量声明 `Stream<CallTask>` 编译不过——声明应改为 `Stream<String>`。

**动手编码 4**：三种结果分别是——保留旧值（"永辉超市"）、新值覆盖（"永辉二店"）、抛 `IllegalStateException: Duplicate key`。

**面试 1 要点**：groupingBy 一行表达"按 key 分组"的意图，for 循环要先 get 再 put 还要判空；语义化程度高，但性能上差别不大，不形成性能理由。
**面试 2 要点**：`taskList.stream().map(t -> t.getRecords().stream()).flatMap(...)` 或直接 `flatMap(t -> t.getRecords().stream())` 把多任务记录合并成一个流。
**面试 3 要点**：外呼瓶颈在数字人平台的拨打并发，本地逻辑是轻量的 DB 读写（IO 密集），并行流会占满 commonPool 影响其他任务，且批次节奏本身由 Crane 控制。
**面试 4 要点**：能说出"操作链/管道 + 终端触发 + 逐元素流过"即可，深挖到 Sink 链是加分项（1-11 之后回来补）。

</details>

## 小结 & 下节预告

记住三句话：三段式（源→中间→终端）、中间记账终端结账、collect 是业务代码的主角。下一节上 Optional 和泛型——就是那条链里 `Optional.ofNullable(nodes).orElse(Collections.emptyList())` 的同款语法，学完你就能完全读懂 WorkflowServiceImpl 里的工作流组装代码了。
