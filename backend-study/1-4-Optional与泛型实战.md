# 1-4 Optional 与泛型实战

> 阶段：Java 核心基础 | 掌握程度：熟悉 | 预计学时：4h
> 泛型的源码级深挖（擦除原理）在 2-6《序列化与泛型》，本节目标：读懂 + 会用 + 答上高频题。

## 本节定位

你的外呼项目里有一条真实代码（WorkflowServiceImpl.java:382）：

```java
List<WorkflowNodeBO> nodesBO = Optional.ofNullable(nodes)
        .orElse(Collections.emptyList())
        .stream()
        .filter(Objects::nonNull)
        .map(DoToBoUtils::nodeDoToBO)
        .filter(Objects::nonNull)
        .collect(Collectors.toList());
```

一条链同时用到了 Optional、泛型、Stream、方法引用——本节学完，这条 AI 写的防御性代码你就完全读懂了。面试中 Optional 的 orElse vs orElseGet 和泛型的 PECS 是高频题。

## 核心知识讲解

### Part A：Optional

#### 1. Optional 解决什么问题

**结论先行**：Optional = 把"返回值可能为 null"从隐藏约定变成显式类型声明，逼调用方处理空值。

```
传统写法                          Optional 写法
WorkflowDO w = dao.get(id);       Optional<WorkflowDO> w = dao.findById(id);
if (w == null) throw ...;         w.map(WorkflowDO::getInfo)
                                    .orElse("默认");
// 忘了判 null → 运行时 NPE        // 类型系统提醒你：这个值可能不存在
```

#### 2. 创建与消费速查

| 操作 | 语义 | 坑 |
|---|---|---|
| `Optional.of(x)` | 包装非空值 | x 为 null 直接 NPE |
| `Optional.ofNullable(x)` | 可空值包装 | **业务代码默认用它** |
| `Optional.empty()` | 空实例 | — |
| `.map(f)` | 有值则转换 | 返回 Optional，可链 |
| `.flatMap(f)` | 有值则转换(f 已返回 Optional) | 防止 Optional 套 Optional |
| `.orElse(v)` | 空则取默认值 | **v 永远先执行（见下）** |
| `.orElseGet(s)` | 空才执行 s 取默认 | 惰性 |
| `.orElseThrow(s)` | 空则抛指定异常 | — |
| `.ifPresent(c)` | 有值才消费 | — |
| `.isPresent()` / `.get()` | 判断/取值 | **反模式组合** |

#### 3. orElse vs orElseGet（面试必考）

**区别只有一个：参数求值时机**。orElse 的参数是个值，**无论如何都会先计算**；orElseGet 的参数是个函数，**只有 Optional 为空才执行**。

```java
String getDefault() { System.out.println("执行了默认值逻辑"); return "default"; }

Optional<String> hasValue = Optional.of("hello");
hasValue.orElse(getDefault());     // 打印"执行了默认值逻辑"！浪费
hasValue.orElseGet(() -> getDefault()); // 什么都不打印 ✅

// 生产级后果：orElse(查数据库兜底()) → 每次调用都白查一次库
```

**记住口诀：默认值代价大用 orElseGet，字面量随意用 orElse。**

#### 4. 三大反模式（面试表达"工程素养"的送分题）

1. `if (opt.isPresent()) { opt.get()... }` —— 脱裤子放屁，等价于 `!= null`，白写
2. Optional 做方法参数 / 实体字段 —— 增加调用方负担，序列化不友好，官方定位只用于返回值
3. 不带兜底直接 `.get()` —— 比 null 判断更危险的 NPE

#### 5. 防御性链的标准姿势（对照你项目的代码）

```java
Optional.ofNullable(nodes)                 // nodes 可能是 null
    .orElse(Collections.emptyList())       // null → 空列表
    .stream()                              // 空列表 → 空 Stream（不会 NPE）
    .filter(Objects::nonNull)              // 元素级判空
    .map(DoToBoUtils::nodeDoToBO)          // 转换
    .filter(Objects::nonNull)              // 转换结果再判空
    .collect(Collectors.toList());         // 收集
```

这套写法 = "从数据到结果的每一跳都防空"，AI coding 生成防御性代码的固定套路，读懂后你也会写。

---

### Part B：泛型

#### 1. 为什么需要泛型

**结论先行**：泛型 = 编译期类型检查，运行时被擦除。没有它，List 里什么都能放，取出来强转炸 ClassCastException。

```java
List list = new ArrayList();          // 原始类型，没有泛型约束
list.add("abc");
list.add(123);                        // 编译器不拦你
String s = (String) list.get(1);      // 运行时 ClassCastException 💥

List<String> safe = new ArrayList<>();
safe.add(123);                        // 编译期就报错 ✅ 错误提前暴露
```

#### 2. 泛型三种用法速查（对照你项目里的真实签名）

| 用法 | 形式 | 你项目里的真实例子 |
|---|---|---|
| 泛型类 | `class Page<T>` | MyBatis 分页 `PageInfo<XxxDO>` |
| 泛型接口 | `interface Mapper<T>` | 所有 `XxxDOMapper extends Mapper<XxxDO>` |
| 泛型方法 | `<T> List<T> query(...)` | Dao 层通用查询方法 |

读法口诀：尖括号里的字母是"占位符"，调用时填什么类型，编译器就按什么类型检查。`T`=Type、`E`=Element、`K/V`=Key/Value、`R`=Return。

#### 3. 复杂泛型签名怎么读（AI 代码里全是这种）

```
CompletableFuture<List<CallRecordDTO>>
  → 一个异步计算任务，算完的结果是 List<CallRecordDTO>
  → 从里往外读：List<X> 是元素集合，CompletableFuture<X> 是"未来才有的 X"

Function<? super CallRecordDO, ? extends CallRecordBO>
  → 一个函数：吃 CallRecordDO（或其父类），吐 CallRecordBO（或其子类）
  → 就是"DO 转 BO 的转换器"

Map<String, List<Processor>>
  → key 是字符串（如 chainType），value 是处理器列表
  → 你项目的回调路由表结构
```

#### 4. 通配符与 PECS（面试高频）

| 通配符 | 读法 | 能读？ | 能写？ | 定位 |
|---|---|---|---|---|
| `? extends T` | T 或其子类 | ✅ 读出来当 T 用 | ❌ | **P**roducer，生产者，只取 |
| `? super T` | T 或其父类 | ❌ 读出来只能当 Object | ✅ 写 T 进去 | **C**onsumer，消费者，只放 |

**PECS = Producer Extends, Consumer Super**：你要从容器**取**数据（它生产给你）用 extends；你要往容器**放**数据（它消费你的）用 super。

```java
// 项目里的真实场景：排序
records.sort(Comparator.comparing(CallRecord::getNextCallTime));
// Comparator.comparing 的签名：
//   <T, U extends Comparable<? super U>> Comparator<T> comparing(Function<? super T, ? extends U>)
// U extends Comparable：时间字段必须"可比较"；? super T：函数能接受 T 的父类参数也行
```

#### 5. 两个高频追问（简版，深挖在 2-6）

1. **`List<String>` 能赋给 `List<Object>` 吗？** 不能。如果能，`listObj.add(123)` 就合法了，读回 String 时直接炸。泛型没有协变，`? extends` 才是受控的协变。
2. **泛型擦除是什么？** 编译后 T 被替换为上界（无上界则是 Object），运行时拿不到 `T.class`。所以 `new T()`、`T instanceof String` 都不合法。深挖（桥方法、如何绕过）留到 2-6。

## 代码示例

```java
// 例1：Optional 防御性查询（外呼 Bot 配置取工作流的真实场景）
public Map<String, String> getBotConfig(Long workflowId) {
    return Optional.ofNullable(workflowDao.getById(workflowId))   // 查不到 → Optional.empty
            .map(w -> w.getInfo())                                 // 有工作流 → 取 info
            .map(info -> info + "\n" + buildNodesPrompt(workflowId)) // 拼节点 prompt
            .map(p -> Collections.singletonMap("prompt", p))       // 包成 Map
            .orElse(Collections.emptyMap());                       // 任意一环空 → 空Map
}   // 全程零 NPE 风险，零 if-null

// 例2：orElseGet 的生产级用法（默认值很贵时）
String model = Optional.ofNullable(workflow.getModalName())
        .orElseGet(() -> lionConfig.getDefaultModel()); // 只有没配置才走 Lion 拉默认值

// 例3：泛型方法（Dao 层通用模式）
public <T> T getByUniqueKey(String key, Class<T> clazz) {  // 调用方声明要什么类型
    Object value = dao.get(key);
    return clazz.cast(value);   // 类型安全的转换
}

// 例4：PECS 实操
List<? extends Number> producers = List.of(1, 2.0, 3L);
Number n = producers.get(0);        // ✅ 能读，当 Number 用
// producers.add(1);                // ❌ 编译错，不知道确切类型，不许写

List<? super Integer> consumers = new ArrayList<Number>();
consumers.add(42);                  // ✅ 能写 Integer（Integer 一定是其中子类）
// Number x = consumers.get(0);     // ❌ 编译错，读出来只能当 Object
```

## 面试高频问题

1. **orElse 和 orElseGet 的区别？** 参数求值时机：orElse 无条件先算，orElseGet 空才执行；默认值有开销（查库/调接口）必须用 orElseGet。
2. **Optional 能不能做方法参数？** 不推荐，官方定位是返回值类型；参数用重载或 @Nullable 表达。
3. **Optional.of 传 null 会怎样？** 立即 NPE，所以业务代码统一 ofNullable。
4. **PECS 是什么？** Producer Extends Consumer Super；取用 extends、放用 super，典型例子 Comparator/Function 的签名。
5. **List\<String> 是 List\<Object> 的子类吗？** 不是，泛型不变（invariant），原因见"两个高频追问 1"。
6. **什么是泛型擦除？** 编译后 T → 上界/Object，运行时无类型信息，一句话版必会。

## 练习题

### 概念自测题

1. `Optional.of(null)` 和 `Optional.ofNullable(null)` 分别发生什么？
2. `opt.orElse(queryDB())`：opt 有值时 queryDB 执行吗？
3. `Optional<WorkflowDO> opt`，`opt.get()` 一定安全吗？
4. `List<? extends Number>` 里能 add(new Integer(1)) 吗？
5. `Function<? super T, ? extends R>` 中两个通配符的方向各是什么？

### 动手编码题

1. 把下面的 null 判断地狱改写成 Optional 链：
```java
WorkflowDO wf = workflowDao.getById(id);
String prompt;
if (wf != null) {
    if (wf.getInfo() != null && !wf.getInfo().isEmpty()) {
        prompt = wf.getInfo();
    } else {
        prompt = defaultPrompt();
    }
} else {
    throw new IllegalArgumentException("工作流不存在");
}
```
2. 写一个泛型方法 `<T> List<T> filterByType(List<?> list, Class<T> clazz)`：从混合类型的列表里筛出指定类型的元素。
3. 读代码答类型：`Map<String, Function<CallRecordDO, CallRecordBO>>` 描述的是什么数据结构？（用一句中文说出它的用途）

### 面试模拟题（含追问链）

1. 「你项目里怎么处理查询返回 null 的？」→ 讲 Optional 防御链 → 追问：「orElse 和 orElseGet 你怎么选的？」→ 追问：「如果 orElse 里放了远程调用会发生什么？」
2. 「解释一下 `List<? extends Number>` 和 `List<? super Number>` 的区别？」→ 追问：「把 Integer 加到 `List<? super Number>` 里合法吗？」（合法，Integer 是 Number 的子类，能被父类容器消费）
3. 「泛型擦除了运行时还能拿到泛型信息吗？」→ 基础版：拿不到 T.class → 加分版：通过继承（class Sub extends Base\<String>）和 getGenericSuperclass 能拿到（2-6 展开讲）

## 答案要点

<details>
<summary>点击展开答案</summary>

**概念自测**：
1. `of(null)` 立即抛 NPE；`ofNullable(null)` 返回 `Optional.empty()`。
2. **执行**。orElse 参数无条件先求值，这就是生产事故点。
3. 不一定。opt 为 empty 时 get() 抛 NoSuchElementException，必须先判断或用 orElse 链。
4. 不能。`? extends` 是生产者只读，编译器不知道确切元素类型，禁止写入（唯一例外 add(null)）。
5. `? super T`：参数方向，函数可接受 T 的父类；`? extends R`：返回值方向，函数返回 R 的子类。

**动手编码 1**：
```java
String prompt = Optional.ofNullable(workflowDao.getById(id))
        .map(WorkflowDO::getInfo)
        .filter(StringUtils::isNotBlank)
        .orElseGet(() -> Optional.ofNullable(workflowDao.getById(id))
                .map(w -> defaultPrompt()).orElseThrow(() -> new IllegalArgumentException("工作流不存在")));
```
（更清晰的写法：先 orElseThrow 保证工作流存在，再取 info 兜底——两种都算对，能说清取舍即可）

**动手编码 2**：
```java
public static <T> List<T> filterByType(List<?> list, Class<T> clazz) {
    return list.stream()
            .filter(clazz::isInstance)     // 元素是该类型（或子类）的实例
            .map(clazz::cast)              // 类型安全转换
            .collect(Collectors.toList());
}
```

**动手编码 3**：一个"转换器注册表"——按字符串 key（如链路类型）注册"DO 转 BO"的函数，回调路由时取出来调用。

**面试 1 要点**：防御链 + 默认值轻用 orElse、重用 orElseGet；orElse 放远程调用 = 每次都白调一次，QPS 高时放大成性能故障。
**面试 2 要点**：extends 只读 super 只写；Integer 加进 `List<? super Number>` 合法——super 方向保证容器至少能装 Number，Integer 是其子类必然兼容。
**面试 3 要点**：直说"擦除后拿不到，但通过带泛型的匿名子类/getGenericSuperclass 能恢复"即可，展示知道边界。

</details>

## 小结 & 下节预告

Optional 三句话：返回值专用、ofNullable 起手、默认值贵用 orElseGet。泛型三句话：编译期检查运行时擦除、T 是占位符、PECS 管 extends/super 的读写方向。下一节 1-5 回到 JDK 主线：IO 与 NIO——外呼项目里 OkHttp 调 LLM 接口时 response.body().string() 背后就是这套 IO 体系。
