# 1-1 JDK 核心类源码精读（上）

> 阶段：一 · Java 核心基础 | 掌握程度：掌握 | 预计学时：6h

## 本节定位

```
后端面试暖场题分布（本节覆盖）

  ┌─ 面试官开场 ──────────────────────────────┐
  │                                            │
  │  "说说 equals 和 hashCode 的关系"   ★★★★★  │ ← Object
  │  "String 为什么不可变"             ★★★★★  │ ← String
  │  "三个 String 有什么区别"          ★★★★☆  │ ← StringBuilder
  │  "为什么枚举是最佳单例"            ★★★★☆  │ ← Enum
  └────────────────────────────────────────────┘
```

目标：面对 JDK 核心类的追问，你能讲到源码级别。

---

## 核心知识讲解

### 一、Object 类：Java 类的共同祖先

**一句话结论：所有类隐式继承 `java.lang.Object`，面试常考其中 5 个方法。**

| 方法 | 签名 | 作用 | 面试频率 |
|------|------|------|----------|
| `equals` | `boolean equals(Object obj)` | 判断两个对象是否"逻辑相等" | ★★★★★ |
| `hashCode` | `int hashCode()` | 返回对象的哈希码 | ★★★★★ |
| `clone` | `protected Object clone()` | 创建并返回对象副本 | ★★★★☆ |
| `getClass` | `Class<?> getClass()` | 返回运行时类型（final 不可重写） | ★★★☆☆ |
| `toString` | `String toString()` | 返回对象的字符串表示 | ★★☆☆☆ |
| `wait/notify/notifyAll` | — | 线程协作（final 不可重写） | ★★★★☆ |
| `finalize` | `protected void finalize()` | GC 回收前调用（JDK 9+ 已废弃） | ★★☆☆☆ |

#### 1.1 equals 方法

**一句话结论：默认的 equals 就是 `==`，比较内存地址；重写后才能实现"逻辑相等"。**

```java
// Object.java 源码
public boolean equals(Object obj) {
    return (this == obj);   // 默认 = 比较地址
}
```

**重写 equals 的五条契约（Java 规范）：**

1. **自反性**：`x.equals(x)` 必须返回 `true`
2. **对称性**：`x.equals(y)` 为 `true`，则 `y.equals(x)` 也必须为 `true`
3. **传递性**：`x.equals(y)` 为 `true` 且 `y.equals(z)` 为 `true`，则 `x.equals(z)` 必须为 `true`
4. **一致性**：多次调用 `x.equals(y)` 结果不变（前提是对象未被修改）
5. **非空性**：`x.equals(null)` 必须返回 `false`

#### 1.2 hashCode 方法

**一句话结论：默认 hashCode 基于内存地址（native 方法）；equals 和 hashCode 有严格契约，违反则哈希表崩坏。**

```java
// Object.java 源码
@HotSpotIntrinsicCandidate
public native int hashCode();
```

**equals 和 hashCode 的契约（面试最高频题之一）：**

| 前提 | 结论 | 说明 |
|------|------|------|
| `a.equals(b) == true` | `a.hashCode() == b.hashCode()` **必须**成立 | 硬性要求 |
| `a.equals(b) == false` | hashCode 可等可不等 | 相等即"哈希冲突"，正常现象 |
| `a.hashCode() != b.hashCode()` | `equals` **一定**为 `false` | 上面的逆否命题 |

**为什么重写 equals 必须重写 hashCode？看内存图就懂了。**

```
Person p1 = new Person(1, "张三");   // 只重写了 equals（按 id 比）
Person p2 = new Person(1, "张三");

栈                     堆
┌──────────┐          ┌─────────────────────┐
│ p1 = 0x100│──────→  │ Person 对象 @0x100  │ id=1  hashCode=1234567（地址算的）
└──────────┘          ├─────────────────────┤
│ p2 = 0x200│──────→  │ Person 对象 @0x200  │ id=1  hashCode=7654321（地址算的）
└──────────┘          └─────────────────────┘

p1.equals(p2)  → true   （id 相同，逻辑相等）
p1.hashCode()  → 1234567
p2.hashCode()  → 7654321   （不同！没重写，走地址默认实现）
```

再放进 HashSet，看桶的分配：

```
HashSet 内部（数组 = 桶）

         桶下标 = hash & (n-1)
              ↓
  ┌────┬────┬────┬────┬────┬────┐
  │ 0  │ 1  │ 2  │ 3  │ 4  │ 5  │
  └─┬──┴────┴─┬──┴────┴─┬──┴────┘
    │         │         │
    ▼         ▼         ▼
  p1对象    (空)       p2对象
  hash=1234567          hash=7654321
  落桶3                 落桶5

  set.add(p1); set.add(p2);
  → hash 不同 → 落不同桶 → 根本不会调 equals 比较
  → set.size() == 2     （本应去重为 1，去重失效！）
```

**本质：哈希表用 hashCode 做预分桶，用 equals 做桶内精确匹配。equals 相等但 hashCode 不等，"去重"和"快速查找"彻底失效。**

#### 1.3 clone 方法

**一句话结论：`Object.clone()` 是浅拷贝；需要实现标记接口 `Cloneable`，否则抛 `CloneNotSupportedException`。实际开发不推荐用。**

```
浅拷贝 vs 深拷贝（克隆 Person{age, name→String对象}）

原对象                浅拷贝                     深拷贝
┌──────────┐        ┌──────────┐              ┌──────────┐
│ age = 25 │        │ age = 25 │  值复制       │ age = 25 │
│ name ─────┼──┐    │ name ────┼──┐           │ name ──→ 新String
└──────────┘  │    └──────────┘  │           └──────────┘
              ↓                   ↓
         ┌─────────┐  ←── 两个引用指向【同一个】String 对象
         │ "张三"  │
         └─────────┘
```

| 对比项 | 浅拷贝 | 深拷贝 |
|--------|--------|--------|
| 基本类型字段 | 复制值 | 复制值 |
| 引用类型字段 | 复制引用（指向同一对象） | 递归复制引用指向的对象 |
| 修改副本的引用字段 | 影响原对象 | 不影响原对象 |
| 实现方式 | `super.clone()` | 手动递归 clone 或序列化 |

实际开发推荐**拷贝构造方法**或**工厂方法**，深拷贝用序列化/反序列化。Josh Bloch 在《Effective Java》中明确建议不要使用 clone。

---

### 二、String：不可变字符串的源码级剖析

#### 2.1 JDK 9 前后的存储变化

**一句话结论：JDK 9 把 `char[]` 改成 `byte[]` + coder 标记，纯 Latin-1 字符串省一半内存。**

```java
// JDK 8 及之前
public final class String implements Serializable, Comparable<String>, CharSequence {
    private final char[] value;  // 每个 char 占 2 字节
}

// JDK 9 及之后（Compact Strings，JEP 254）
public final class String implements Serializable, Comparable<String>, CharSequence {
    private final byte[] value;  // 按 coder 决定每个字符占 1 还是 2 字节
    private final byte coder;    // 0 = LATIN1, 1 = UTF16
    private int hash;            // 缓存 hashCode
}
```

```
为什么改？—— char 固定 2 字节，浪费严重

JDK 8:  "abc"   → char[3] = 6 字节   ┐
JDK 9:  "abc"   → byte[3] = 3 字节   ┘ 省 50%

现实：绝大多数字符串（JSON key、HTTP header、日志）只含 Latin-1 字符
String 是堆中占用最大的类型 → 官方数据：平均省 25%~30% 堆内存 + 降低 GC 压力
```

**编码选择机制**（运行时自动判断，对开发者透明）：

| 场景 | coder 值 | 每字符占用 | 示例 |
|------|----------|-----------|------|
| 纯 Latin-1 字符 | 0 (LATIN1) | 1 字节 | `"hello"`, `"123"` |
| 含非 Latin-1 字符 | 1 (UTF16) | 2 字节 | `"你好"`, `"café"` |
| 混合内容 | 1 (UTF16) | 2 字节（整体升格） | `"hello世界"` |

注意"按需升格"：只要有一个非 Latin-1 字符，整条字符串统一升格为 UTF-16，不是逐字符混编。

#### 2.2 String 的不可变性

**一句话结论：不可变不靠 `final` 一个关键字，而是四重防线共同保证。**

```
内存布局：final 只锁"引用"，锁不住"内容"

  String 对象
  ┌──────────────────┐
  │ value = 0x1000   │──final──→  堆中 byte[] @0x1000: [h][e][l][l][o]
  └──────────────────┘                  ↑
       final 保证：value 永远指向 0x1000 │ 但 value[0]='x' 理论上可改内容（若有访问权限）
                                          │
       真正的防线：private + 没有任何 setter/修改方法 → 外部根本摸不到这个数组
```

**四重防线：**

| # | 防线 | 挡住什么 |
|---|------|---------|
| 1 | 类被 `final` 修饰 | 子类继承后破坏不可变 |
| 2 | `value` 数组 `private final` | 外部直接访问/换引用 |
| 3 | 无任何修改 `value` 内容的公共方法 | `value[0] = 'x'` 这类操作 |
| 4 | 所有"修改"方法（`concat`/`replace`/`substring`/`toUpperCase`）都返回新对象 | 误以为修改了原对象 |

**String 不可变的好处：**

| 好处 | 说明 |
|------|------|
| 线程安全 | 不可变对象天然线程安全，无需同步 |
| 字符串常量池 | 不可变才能安全复用同一个 String 实例 |
| hashCode 缓存 | hashCode 只需计算一次，后续直接返回缓存值 |
| 安全性 | 防止敏感信息（如数据库 URL）被意外修改 |
| 作为 HashMap 的 key | 不可变保证了 hashCode 不变，不会出现"放进去找不到了"的问题 |

#### 2.3 字符串常量池

**一句话结论：字面量进常量池复用，`new String` 一定在堆上再造一个对象——`==` 结果由此决定。**

```java
String s1 = "hello";           // 字面量，从常量池取或创建
String s2 = "hello";           // 常量池已有，复用同一个对象
String s3 = new String("hello"); // 在堆上创建新对象，但 value 指向常量池的 "hello"
String s4 = s3.intern();       // 将 s3 放入常量池（如果不存在），返回常量池引用

s1 == s2       // true，同一引用
s1 == s3       // false，s3 是堆上新对象
s1 == s4       // true，intern 返回常量池引用
s1.equals(s3)  // true，内容相同
```

**内存图（必背）：**

```
              StringTable（堆中的哈希表，JDK 7+）
              ┌───────────────────────────────┐
              │  "hello" → 0x1000 (堆对象A)   │
              └───────────────────────────────┘

栈                         堆
┌─────────────┐           ┌──────────────────────┐
│ s1 = 0x1000 │──────┐    │ 对象A @0x1000        │ ← 常量池登记的那个
├─────────────┤      ├──→ │  value ──→ "hello"   │
│ s2 = 0x1000 │──────┘    ├──────────────────────┤
├─────────────┤           │ 对象B @0x2000 (new)  │
│ s3 = 0x2000 │────────→  │  value ──→ "hello"   │ ← 内容相同，但是新对象！
├─────────────┤           └──────────────────────┘
│ s4 = 0x1000 │──────→ intern() 把 s3 换成常量池里的对象A
└─────────────┘

s1 == s2  → true   （都指 0x1000）
s1 == s3  → false  （0x1000 vs 0x2000）
s1 == s4  → true   （intern 拿回 0x1000）
```

常量池位置变迁：

| JDK 版本 | 常量池位置 |
|---------|-----------|
| JDK 6 及之前 | 永久代（PermGen） |
| JDK 7+ | 堆中 |
| JDK 8+ | 堆中（永久代被元空间 Metaspace 取代，常量池不动） |

---

### 三、StringBuilder vs StringBuffer

**一句话结论：两者都继承 `AbstractStringBuilder`，唯一区别是 StringBuffer 的方法全加了 `synchronized`——实际开发几乎全用 StringBuilder。**

| 对比项 | String | StringBuilder | StringBuffer |
|--------|--------|---------------|--------------|
| 可变性 | 不可变 | 可变 | 可变 |
| 线程安全 | 安全（不可变） | 不安全 | 安全（synchronized） |
| 性能 | 最低（频繁创建新对象） | 最高 | 较低（锁开销） |
| JDK 引入 | 1.0 | 1.5 | 1.0 |
| 适用场景 | 少量操作、固定文本 | 单线程大量拼接 | 多线程拼接（基本淘汰） |

**StringBuffer 的线程安全实现**——每个公共方法都加了 `synchronized`：

```java
// StringBuffer.java 源码
@Override
public synchronized StringBuffer append(String str) {
    toStringCache = null;
    super.append(str);
    return this;
}

@Override
public synchronized StringBuffer delete(int start, int end) {
    toStringCache = null;
    super.delete(start, end);
    return this;
}
```

**StringBuilder 没有任何同步**：

```java
// StringBuilder.java 源码
@Override
public StringBuilder append(String str) {
    super.append(str);
    return this;
}
```

**实际开发选型：**

```
需要多线程拼字符串？
  │
  ├─ 否 → StringBuilder（99% 的场景）
  │
  └─ 是 → 不要用 StringBuffer
          → 每个线程各用一个 StringBuilder，最后合并结果
```

**AbstractStringBuilder 的扩容逻辑**（面试追问点）：

```java
// AbstractStringBuilder.java 源码（简化）
private int newCapacity(int minCapacity) {
    int oldCapacity = value.length >> 1;  // 当前容量的 2 倍
    int newCapacity = value.length + oldCapacity + 2;  // 扩容为原来的 ~2 倍
    if (newCapacity - minCapacity < 0) {
        newCapacity = minCapacity;  // 不够就用需求值
    }
    return newCapacity <= 0 || MAX_ARRAY_SIZE - newCapacity < 0
        ? hugeCapacity(minCapacity)
        : newCapacity;
}
```

**扩容可视化：默认容量 16，不断 append 之后——**

```
new StringBuilder()            append "hello" (5字符)
┌──────────────┐               ┌──────────────┐
│capacity = 16 │               │capacity = 16 │ 无需扩容
└──────────────┘               └──────────────┘

append 到第 17 个字符时触发扩容：16 * 2 + 2 = 34

  扩容前                          扩容后
┌───────────────┐               ┌────────────────────────────┐
│ byte[16]      │  Arrays.copyOf│ byte[34]                   │
│ [a][b][c]...  │ ────复制────→ │ [a][b][c]... + 18 个空位    │
└───────────────┘   (新数组+拷贝)└────────────────────────────┘

再次装满：34 * 2 + 2 = 70 → 142 → 286 → ...
每次扩容 = 分配新数组 + 全量复制旧数据 → 开销不小
```

所以能预估容量就创建时指定：`new StringBuilder(1024)`。

---

### 四、Enum：语法糖与枚举单例

#### 4.1 枚举的本质——编译器生成的 final 类

**一句话结论：`enum` 是语法糖，编译后变成"继承 Enum 的 final 类 + 一组 public static final 实例"。**

```java
// 你写的代码
public enum Season {
    SPRING, SUMMER, AUTUMN, WINTER;
}

// 编译后的等价代码（javap 反编译）
public final class Season extends Enum<Season> {
    public static final Season SPRING = new Season("SPRING", 0);
    public static final Season SUMMER = new Season("SUMMER", 1);
    public static final Season AUTUMN = new Season("AUTUMN", 2);
    public static final Season WINTER = new Season("WINTER", 3);

    private Season(String name, int ordinal) {
        super(name, ordinal);
    }

    public static Season[] values() { return new Season[]{SPRING, SUMMER, AUTUMN, WINTER}; }
    public static Season valueOf(String name) { return Enum.valueOf(Season.class, name); }
}
```

**编译后的类结构图：**

```
        java.lang.Enum<Season>
               ▲
               │ extends
     ┌─────────┴──────────────┐
     │  final class Season    │  ← final：不能被继承
     │────────────────────────│
     │ + SPRING : Season      │  ← public static final 实例
     │ + SUMMER : Season      │     类加载时在 static 块中创建
     │ + AUTUMN : Season      │     （JVM 保证线程安全）
     │ + WINTER : Season      │
     │────────────────────────│
     │ - Season(name, ord)    │  ← 构造器私有：外部不能 new
     │ + values()             │  ← 编译器生成
     │ + valueOf(String)      │
     └────────────────────────┘

方法区/元空间中的 static 域：
  Season.SPRING ──→ 堆中唯一的 Season 实例（name="SPRING", ordinal=0）
```

关键特征：final 修饰（不能被继承）、构造器私有（不能 new）、每个常量是 public static final 实例、类加载时在 static 块中初始化（JVM 保证线程安全）。

#### 4.2 Enum 类的核心方法

| 方法 | 说明 |
|------|------|
| `name()` | 返回枚举常量名称（如 `"SPRING"`） |
| `ordinal()` | 返回声明顺序（从 0 开始）——实际开发不推荐依赖 |
| `compareTo(E o)` | 按 ordinal 比较，实现自 Comparable 接口 |
| `values()` | 返回所有枚举常量的数组（编译器生成，不是 Enum 类的方法） |
| `valueOf(String name)` | 按名称获取枚举常量，不存在则抛 IllegalArgumentException |

#### 4.3 枚举单例——最佳的单例实现方式

**一句话结论：JVM 类加载保证唯一 + 线程安全，且天然免疫反射和序列化两种单例攻击。**

```java
public enum Singleton {
    INSTANCE;

    public void doSomething() {
        System.out.println("业务逻辑");
    }
}
```

**为什么防得住？看攻击路径图：**

```
攻击方式             普通单例(DCL)              枚举单例
─────────────────────────────────────────────────────────
反射攻击         Constructor.newInstance     Constructor.newInstance
                 可调私有构造器 ✗ 被攻破      内部检查 Modifier.ENUM
                                            直接抛异常 ✓ 防住

序列化攻击       反序列化创建新对象            readObject 特殊处理
                 （需手写 readResolve 防御）   直接返回已有常量 ✓ 防住
                 ✗ 可防但需手写
─────────────────────────────────────────────────────────
                 结论：枚举是唯一同时防御两种攻击的写法（Effective Java 推荐）
```

JVM 在类加载阶段保证了枚举实例的全局唯一性和线程安全性，无需手写双重检查锁或静态内部类。

---

## 代码示例

### 示例 1：正确重写 equals 和 hashCode

```java
import java.util.Objects;

public class Person {
    private int id;
    private String name;
    private int age;

    public Person(int id, String name, int age) {
        this.id = id;
        this.name = name;
        this.age = age;
    }

    // 正确的 equals 写法
    @Override
    public boolean equals(Object o) {
        // 1. 先判断是否是同一引用（短路优化）
        if (this == o) return true;
        // 2. null 返回 false
        if (o == null) return false;
        // 3. 判断类型（getClass 比 instanceof 更严格，子类不算相等）
        if (getClass() != o.getClass()) return false;
        // 4. 类型转换后逐字段比较
        Person person = (Person) o;
        return id == person.id
            && age == person.age
            && Objects.equals(name, person.name);  // name 可能为 null，用 Objects.equals
    }

    // 正确的 hashCode 写法（使用 Objects.hash）
    @Override
    public int hashCode() {
        return Objects.hash(id, name, age);  // 参与 equals 的字段必须全部参与 hash
    }

    // 标准的 toString
    @Override
    public String toString() {
        return "Person{id=" + id + ", name='" + name + "', age=" + age + "}";
    }
}
```

### 示例 2：验证 hashCode 契约

```java
import java.util.HashSet;
import java.util.Set;

public class HashCodeContractDemo {
    public static void main(String[] args) {
        // 场景：只重写 equals 不重写 hashCode 的 Person
        Person p1 = new Person(1, "张三", 25);
        Person p2 = new Person(1, "张三", 25);
        // 内存状态：p1 → 0x100, p2 → 0x200（两个不同堆对象）

        System.out.println("equals: " + p1.equals(p2));       // true
        System.out.println("hashCode p1: " + p1.hashCode());  // 如 1234567
        System.out.println("hashCode p2: " + p2.hashCode());  // 如 2345678（不同！）
        // hash 不同 → 落进 HashSet 不同桶 → 去重失效

        Set<Person> set = new HashSet<>();
        set.add(p1);  // p1 落桶 A
        set.add(p2);  // p2 的 hash 不同 → 落桶 B → 不会触发 equals 比较
        System.out.println("Set size: " + set.size());  // 如果没重写 hashCode，输出 2（应该去重为 1）
        // 结论：破坏了 Set 的去重语义
    }
}
```

### 示例 3：StringBuilder 性能对比

```java
public class StringConcatDemo {
    public static void main(String[] args) {
        int n = 100000;

        // 方式 1：String + 循环拼接（灾难性能）
        // 每次循环创建一个新 StringBuilder + 新 String
        long start = System.currentTimeMillis();
        String result1 = "";
        for (int i = 0; i < n; i++) {
            result1 += i;  // 编译器等价于 result1 = new StringBuilder().append(result1).append(i).toString()
            // 每次循环：新建 StringBuilder → append 旧内容 → append i → toString 新 String
            // 时间复杂度 O(n²)，因为每次都要复制越来越长的字符串
        }
        System.out.println("String += : " + (System.currentTimeMillis() - start) + "ms");

        // 方式 2：StringBuilder（推荐）
        start = System.currentTimeMillis();
        StringBuilder sb = new StringBuilder(n * 4);  // 预估容量，避免扩容
        for (int i = 0; i < n; i++) {
            sb.append(i);  // 始终操作同一个内部数组，偶尔扩容
        }
        String result2 = sb.toString();
        System.out.println("StringBuilder: " + (System.currentTimeMillis() - start) + "ms");
        // 时间复杂度 O(n)，性能提升几十到几百倍
    }
}
```

```
两种方式的内存行为对比（n 次循环）：

String +=（O(n²)）：
  循环1: new SB → 复制 0   字符 → new String → 丢弃
  循环2: new SB → 复制 1   字符 → new String → 丢弃
  循环3: new SB → 复制 2   字符 → new String → 丢弃
  ...                    ↑ 复制量线性增长 → 总复制量 O(n²)

StringBuilder（O(n)）：
  全程只有一个 byte[]，装满才扩容（摊还 O(1)/次 append）
```

### 示例 4：枚举带字段和策略模式

```java
public enum PayStatus {
    PENDING(0, "待支付") {
        @Override
        public boolean canTransitionTo(PayStatus next) {
            return next == PAID || next == CANCELLED;
        }
    },
    PAID(1, "已支付") {
        @Override
        public boolean canTransitionTo(PayStatus next) {
            return next == REFUNDED;
        }
    },
    CANCELLED(2, "已取消") {
        @Override
        public boolean canTransitionTo(PayStatus next) {
            return false;  // 终态，不可流转
        }
    },
    REFUNDED(3, "已退款") {
        @Override
        public boolean canTransitionTo(PayStatus next) {
            return false;  // 终态
        }
    };

    private final int code;
    private final String desc;

    PayStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public int getCode() { return code; }
    public String getDesc() { return desc; }

    // 抽象方法：每个枚举常量自行实现状态流转逻辑（策略模式）
    public abstract boolean canTransitionTo(PayStatus next);

    // 根据 code 获取枚举（实际开发常用）
    public static PayStatus fromCode(int code) {
        for (PayStatus status : values()) {
            if (status.code == code) return status;
        }
        throw new IllegalArgumentException("Unknown pay status code: " + code);
    }
}
```

```
编译后结构：带抽象方法的枚举 → 每个常量是一个匿名子类实例

             abstract PayStatus
             ▲      ▲      ▲      ▲
             │      │      │      │  （编译器生成的匿名子类）
        PENDING   PAID  CANCELLED REFUNDED
          实例     实例    实例     实例   ← 各自持有自己的 canTransitionTo 实现
```

---

## 面试高频问题

**Q1：equals 和 == 的区别？**

`==` 对基本类型比较值，对引用类型比较内存地址。`equals` 是 Object 定义的方法，默认行为和 `==` 一样（比较地址），但通常被重写为比较对象内容。String、Integer 等都重写了 equals 来实现值比较。

**Q2：为什么重写 equals 必须重写 hashCode？**

哈希表（HashMap/HashSet）依赖 hashCode 做预分桶，依赖 equals 做精确匹配。如果 equals 返回 true 但 hashCode 不同，两个"相等"的对象会被放在不同的桶里，HashSet 就无法去重，HashMap 就会存重复 key。契约要求：equals 相等的对象 hashCode 必须相等。

**Q3：String 为什么是不可变的？（追问：final 修饰数组就够了吗？）**

不够。final 只保证引用不变，不能保证数组内容不变。String 不可变靠四重设计：类被 final 修饰（不能继承）、数组被 private final 修饰（外部不可访问）、不提供修改数组的方法、所有"修改"操作返回新对象。

**Q4：JDK 9 为什么把 String 的 char[] 改成 byte[]？**

节省内存。绝大多数字符串只含 Latin-1 字符，1 字节就够，但 char 固定占 2 字节，浪费 50%。改为 byte[] 后，配合 coder 标记，纯 Latin-1 字符串每个字符用 1 字节存储，平均节省 25%~30% 堆内存，同时减少 GC 压力。

**Q5：String s = new String("hello") 创建了几个对象？**

如果常量池中没有 "hello"，创建了 2 个对象：一个在常量池中（字面量 "hello"），一个在堆中（new 出来的 String 对象，其 value 指向常量池中的 "hello" 的 value）。如果常量池中已有 "hello"，则只创建 1 个堆对象。

**Q6：String、StringBuilder、StringBuffer 的区别？**

String 不可变，每次修改创建新对象；StringBuilder 可变、线程不安全、性能最高；StringBuffer 可变、线程安全（方法加了 synchronized）、性能较低。单线程用 StringBuilder，多线程几乎不会用 StringBuffer（更好的方案是各线程各自用 StringBuilder 再合并）。

**Q7：StringBuilder 和 StringBuffer 的扩容机制？**

默认扩容为原容量的 2 倍加 2（`oldCapacity * 2 + 2`），如果不够就用所需容量。底层是 `Arrays.copyOf` 创建新数组。建议创建时预估容量，避免频繁扩容。

**Q8：枚举为什么是单例的最佳实现？**

JVM 在类加载时初始化枚举实例，保证了线程安全和全局唯一。而且枚举天然防御反射攻击（Constructor.newInstance 对枚举抛异常）和序列化破坏（反序列化直接返回已有常量）。普通单例无法防御反射，枚举是唯一能同时防御两种攻击的写法。

**Q9：枚举的 ordinal() 方法有什么问题？**

ordinal 返回声明顺序（从 0 开始），但它依赖枚举常量的声明位置。如果后续重新排列枚举常量，ordinal 值会变化，导致依赖 ordinal 的逻辑出错。实际开发中应该自定义 code 字段，而不是依赖 ordinal。

**Q10：clone() 是浅拷贝还是深拷贝？如何实现深拷贝？**

Object.clone() 默认是浅拷贝——基本类型复制值，引用类型复制引用（指向同一对象）。深拷贝需要：方式一，手动递归 clone 所有引用类型字段；方式二，通过序列化/反序列化（如先.writeObject 再 readObject）；方式三，使用拷贝构造方法。推荐用拷贝构造方法，不要用 clone（Effective Java 建议）。

---

## 练习题

### 概念自测题

**1.** 以下代码输出什么？

```java
String s1 = "hello";
String s2 = "hello";
String s3 = new String("hello");
System.out.println(s1 == s2);
System.out.println(s1 == s3);
System.out.println(s1.equals(s3);
```

A. true, true, true
B. true, false, true
C. false, false, true
D. true, false, false

**2.** 以下哪个说法是正确的？

A. hashCode 相等的两个对象，equals 一定返回 true
B. equals 返回 true 的两个对象，hashCode 必须相等
C. hashCode 不同的两个对象，equals 可能返回 true
D. 不重写 hashCode 也能正常使用 HashSet

**3.** 以下代码创建了几个 String 对象（假设常量池为空）？

```java
String s1 = new String("ab");
String s2 = "ab";
String s3 = new String("ab");
```

A. 2 个
B. 3 个
C. 4 个
D. 5 个

**4.** 关于 Java 枚举，以下说法错误的是？

A. 枚举类不能被继承
B. 枚举可以实现接口
C. 枚举的构造方法可以是 public
D. 枚举天然的线程安全

### 动手编码题

**1.** 实现一个 `Money` 类，包含 `amount`（long）和 `currency`（String）字段。正确重写 `equals`、`hashCode` 和 `toString`。并写一个测试类，验证放入 `HashSet` 后能正确去重。

**2.** 编写代码验证 JDK 9+ 的 String Compact Strings 特性：创建一个纯 ASCII 字符串和一个含中文字符的字符串，通过反射获取它们的 `coder` 字段值，验证编码策略。

提示：`String.class.getDeclaredField("coder")` 可以获取 coder 字段。

**3.** 实现一个枚举 `OrderStatus`，包含待付款、已付款、已发货、已完成、已取消五个状态。每个状态带 code 和描述。添加一个 `canTransitionTo(OrderStatus next)` 方法，定义合法的状态流转规则（如已发货可以流转到已完成但不能流转到待付款）。

### 面试模拟题

**1.** 面试官：「说说你对 equals 和 hashCode 的理解。」

追问链：
- 那如果不重写 hashCode 会怎样？
- 我在 HashMap 里放了一个对象，然后修改了这个对象的字段，会怎样？
- HashMap 是怎么用 hashCode 的？能说说put的流程吗？

**2.** 面试官：「String 为什么设计成不可变的？」

追问链：
- 不可变有什么好处？
- 如果我想频繁修改字符串，应该用什么？
- StringBuilder 内部是怎么扩容的？
- 为什么不直接用StringBuffer？

**3.** 面试官：「写一个线程安全的单例模式。」

追问链：
- 枚举单例为什么能防反射？
- 双重检查锁为什么要用 volatile？
- 静态内部类方式的原理是什么？

---

## 答案要点

<details>
<summary>点击展开答案</summary>

### 概念自测题答案

**1. B**
s1 和 s2 都指向常量池中的同一个 "hello"（== 为 true）。s3 是 new 出来的堆对象，地址不同（== 为 false）。equals 比较内容，返回 true。

**2. B**
equals 相等 → hashCode 必须相等。但 hashCode 相等 → equals 不一定相等（哈希冲突）。hashCode 不同 → equals 一定为 false（逆否命题）。不重写 hashCode 会导致 HashSet 不去重。

**3. B（3 个）**
`new String("ab")` 第一次：常量池创建 "ab"（1 个），堆创建 String 对象（1 个）→ 2 个。`s2 = "ab"`：常量池已有，复用 → 0 个。`new String("ab")` 第二次：常量池已有，堆创建 String 对象（1 个）→ 1 个。总计 3 个。

**4. C**
枚举的构造方法只能是 private（不写修饰符默认也是 private），不能是 public。

### 动手编码题参考

**1. Money 类：**

```java
import java.util.Objects;

public class Money {
    private final long amount;
    private final String currency;

    public Money(long amount, String currency) {
        this.amount = amount;
        this.currency = currency;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Money money = (Money) o;
        return amount == money.amount
            && Objects.equals(currency, money.currency);
    }

    @Override
    public int hashCode() {
        return Objects.hash(amount, currency);
    }

    @Override
    public String toString() {
        return amount + " " + currency;
    }
}

// 测试
class MoneyTest {
    public static void main(String[] args) {
        Set<Money> set = new HashSet<>();
        set.add(new Money(100, "CNY"));
        set.add(new Money(100, "CNY"));  // 相同对象，正确去重
        set.add(new Money(200, "CNY"));
        System.out.println(set.size());  // 输出 2
    }
}
```

**2. Compact Strings 验证：**

```java
import java.lang.reflect.Field;

public class CompactStringsDemo {
    public static void main(String[] args) throws Exception {
        Field coderField = String.class.getDeclaredField("coder");
        coderField.setAccessible(true);

        String ascii = "hello123";
        String chinese = "你好世界";
        String mixed = "hello世界";

        System.out.println("ascii coder: " + coderField.getInt(ascii));   // 0 (LATIN1)
        System.out.println("chinese coder: " + coderField.getInt(chinese)); // 1 (UTF16)
        System.out.println("mixed coder: " + coderField.getInt(mixed));    // 1 (UTF16，混合升格)
    }
}
```

**3. OrderStatus 枚举：**

```java
public enum OrderStatus {
    PENDING(0, "待付款") {
        @Override public boolean canTransitionTo(OrderStatus next) {
            return next == PAID || next == CANCELLED;
        }
    },
    PAID(1, "已付款") {
        @Override public boolean canTransitionTo(OrderStatus next) {
            return next == SHIPPED || next == CANCELLED;
        }
    },
    SHIPPED(2, "已发货") {
        @Override public boolean canTransitionTo(OrderStatus next) {
            return next == COMPLETED;
        }
    },
    COMPLETED(3, "已完成") {
        @Override public boolean canTransitionTo(OrderStatus next) {
            return false;
        }
    },
    CANCELLED(4, "已取消") {
        @Override public boolean canTransitionTo(OrderStatus next) {
            return false;
        }
    };

    private final int code;
    private final String desc;

    OrderStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public int getCode() { return code; }
    public String getDesc() { return desc; }
    public abstract boolean canTransitionTo(OrderStatus next);
}
```

### 面试模拟题要点

**Q1 追问链要点：**
- 不重写 hashCode：equals 相等的对象被分到不同桶，HashSet 不去重，HashMap 出现重复 key
- 修改对象字段后：hashCode 可能变化，原来在桶 A，现在算出来是桶 B，get 时去桶 B 找不到 → 内存泄漏。所以 HashMap 的 key 应该是不可变的
- HashMap put 流程：算 hashCode → 定位桶 → 桶为空直接放 → 桶非空用 equals 遍历链表/红黑树 → key 相同则覆盖 value → key 不同则追加（链表长度 ≥8 转红黑树）

**Q2 追问链要点：**
- 不可变好处：线程安全、常量池复用、hashCode 缓存、HashMap key 安全
- StringBuilder 扩容：原容量 * 2 + 2，不够用所需值，Arrays.copyOf 创建新数组
- 不用 StringBuffer 因为：synchronized 开销大、现代开发中多线程拼字符串场景极少、即使有也用各线程独立 StringBuilder 再合并

**Q3 追问链要点：**
- 枚举防反射：Constructor.newInstance 内部检查 Modifier.ENUM，是枚举就抛 IllegalArgumentException
- volatile 防指令重排：new 对象分三步（分配内存、初始化、赋引用），不加 volatile 可能重排为 1→3→2，其他线程拿到未初始化的对象
- 静态内部类原理：利用类加载机制保证线程安全，外部类加载时不会加载静态内部类，只有调用 getInstance 时才触发类加载和初始化（懒加载）

</details>

---

## 小结 & 下节预告

**四个结论，一张图记住本节：**

```
┌──────────────────────────────────────────────────────┐
│ ① equals 相等 ⇒ hashCode 必须相等，否则哈希表崩坏     │
│    （hashCode 分桶 + equals 精确匹配，缺一不可）      │
│ ② String：byte[] + coder（省内存）                    │
│    不可变 = final类 + private final字段 + 无setter     │
│    + 修改方法一律返回新对象（四重防线）                │
│ ③ 三者唯一分水岭：synchronized                        │
│    StringBuilder(无锁) > StringBuffer(有锁)           │
│    循环里 String += 是 O(n²) 灾难                     │
│ ④ 枚举 = final类 + 私有构造 + static final实例        │
│    唯一同时防反射 + 防序列化的单例                     │
└──────────────────────────────────────────────────────┘
```

下一节 **1-2 JDK 核心类源码精读（下）** 进入 Throwable/Exception 异常体系、Class 反射基础、ClassLoader 双亲委派模型和 SPI 机制。双亲委派和类加载是面试重灾区，也是理解 Spring、Tomcat 等框架工作原理的前置知识。下节课见。
