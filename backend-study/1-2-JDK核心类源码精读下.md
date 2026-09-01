# 1-2 JDK 核心类源码精读（下）

> 阶段：阶段一 Java 核心基础 | 掌握程度：掌握 | 预计学时：6h

## 本节定位

```
JDK 核心类源码精读（上）  →  本节（下）
  Object/String/Enum        异常体系 / 反射 / ClassLoader / SPI / 时间API
                             ↑ 面试高频，每场必问
```

五大模块，面试出镜率极高：异常体系、反射、双亲委派、SPI、时间 API。掌握到源码细节，追问才能对答如流。

---

## 核心知识讲解

### 一、Java 异常体系：Throwable / Exception / Error

#### 1. 异常体系整体架构

```
                    Throwable
                   /        \
                Error      Exception
               /    \       /      \
    OutOfMemoryError  ...  IOException  RuntimeException
    StackOverflowError      SQLException  NullPointerException
                           (Checked)      ArrayIndexOutOfBoundsException
                                          (Unchecked)
```

| 维度 | Error | Checked Exception | Unchecked (RuntimeException) |
|------|-------|--------------------|---------------------------------------|
| 性质 | JVM 严重错误 | 编译期检查的异常 | 运行时异常 |
| 是否必须捕获 | 否 | 是（try-catch 或 throws） | 否 |
| 典型例子 | OOM、StackOverflow | IOException、SQLException | NPE、ClassCastException |
| 处理策略 | 让它崩，别 catch | 必须处理，否则编译不过 | 编码时预防，不靠 catch |

#### 2. Throwable 源码关键字段

```
Throwable 对象内存结构：
┌─────────────────────────────────────┐
│ String detailMessage  = "用户查询失败" │  ← 异常描述
│ Throwable cause       ──→ SQLException │  ← 异常链：指向原始异常
│ StackTraceElement[] stackTrace       │  ← 调用栈帧数组
│   [0] UserService.getUser():42      │
│   [1] UserController.handle():18    │
│   ...                              │
└─────────────────────────────────────┘
```

```java
public class Throwable implements Serializable {
    private String detailMessage;   // 异常描述信息
    private Throwable cause;        // 异常链——记录原始异常
    private StackTraceElement[] stackTrace; // 调用栈

    // 填充调用栈——native 方法，JVM 实现
    public synchronized Throwable fillInStackTrace() {
        stackTrace = getOurStackTrace();
        return this;
    }
}
```

`cause` 字段实现**异常链**机制：业务层捕获底层异常后包装成业务异常抛出，同时保留原始异常。

```java
try {
    // 数据库操作
} catch (SQLException e) {
    // 内存状态：new BusinessException 的 cause → e（SQLException）
    throw new BusinessException("用户数据查询失败", e); // e 作为 cause
}
// 异常栈打印时会出现 "Caused by: java.sql.SQLException: ..."
```

#### 3. try-catch-finally 执行顺序与陷阱

```
执行流程图：

    ┌─── try { ... } ──────────────┐
    │                              │
    │  无异常？    ┌── 有异常？──┐  │
    │     │         │              │  │
    │     ▼         ▼              │  │
    │  try体执行  catch匹配        │  │
    │     │         │              │  │
    │     │    匹配成功？          │  │
    │     │    ├──是→ catch体     │  │
    │     │    └──否→ 向上抛 ▲    │  │
    │     │         │              │  │
    │     ▼         ▼              ▼  │
    └──────────────────────────────────┘
                  │
                  ▼
           finally（总是执行）
                  │
                  ▼
              方法返回
```

**陷阱 1：finally 中的 return 会覆盖 try 中的 return**

```
JVM 操作数栈状态：

  try块: return 1;
    ① 将 1 压入返回值栈   栈: [1]
    ② 执行 finally
  finally块: return 2;
    ③ 将 2 压入返回值栈   栈: [1] → [2]（覆盖）
    ④ 方法返回 2          ← try 中的 1 被丢弃
```

```java
public int test() {
    try {
        return 1; // JVM 先把 1 存入返回栈
    } finally {
        return 2; // 返回值栈被覆盖为 2，try 中的 1 被丢弃
    }
}
```

**陷阱 2：finally 中修改基本类型不影响返回值**

```
JVM 操作数栈状态：

  try块: return x;  (x=1)
    ① 读取 x 的值 → 1
    ② 将 1 的副本压入返回值栈   栈: [1]  ← 是值的副本，不是引用
  finally块: x = 2;
    ③ 修改局部变量 x = 2       栈: [1]  ← 返回值栈不受影响
  方法返回 1
```

```java
public int test() {
    int x = 1;
    try {
        return x; // JVM 先把 x 的值 1 存入返回栈（值副本）
    } finally {
        x = 2;    // 修改局部变量，但返回栈中已经是 1
    }
    // 最终返回 1
}
```

**陷阱 3：try-with-resources（Java 7+）自动关闭**

```
编写时：                     编译器生成：
┌──────────────────┐    ┌───────────────────────────────┐
│ try (Resource r) │ → │ try { ... }                    │
│ { ... }           │    │ finally {                     │
└──────────────────┘    │   if (r2 != null) r2.close(); │
                         │   if (r1 != null) r1.close(); │  ← 逆序关闭
                         │ }                              │
                         │ // close异常 → addSuppressed  │
                         └───────────────────────────────┘
```

```java
// Java 7+ 自动资源管理，实现了 AutoCloseable 的资源会自动关闭
try (FileInputStream fis = new FileInputStream("test.txt");
     BufferedReader br = new BufferedReader(new InputStreamReader(fis))) {
    // 使用资源
} // 编译器自动生成 finally { br.close(); fis.close(); }
```

面试追问点：`try-with-resources` 底层原理是编译器生成 `try-catch-finally` 代码块，在 finally 中调用每个资源的 `close()` 方法，如果 close 也抛异常，会用 `addSuppressed` 保存为抑制异常，不会丢失。

#### 4. 异常处理的最佳实践

| 做法 | 问题 | 正确方式 |
|------|------|----------|
| `catch(Exception e){}` | 吞异常，问题无法追踪 | 捕获具体类型，记录日志 |
| `throw new RuntimeException(e)` 无信息 | 失去上下文 | 带业务消息 + 异常链 |
| 继承 Exception（Checked） | 到处 throws | 继承 RuntimeException |

```java
// 反面教材
catch (Exception e) {
    // 什么都不做，异常被吞掉
}

// 正面实践
catch (IOException e) {
    log.error("读取配置文件失败: {}", configPath, e);
    throw new ConfigException("配置加载失败", e);
}
```

自定义业务异常继承 `RuntimeException`（非受检），避免业务代码到处声明 throws。

```java
public class BizException extends RuntimeException {
    private int code;     // 内存: BizException{code=40001, message="参数错误", cause=null}
    private String message;

    public BizException(int code, String message) {
        super(message);
        this.code = code;
    }

    public BizException(int code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }
}
```

---

### 二、Java 反射机制

#### 1. 反射的核心类与基本操作

**结论先行**：反射 = 运行时动态获取类信息、创建实例、调用方法、访问字段。

```
Class 对象 = "镜子"，反射出堆中对象的完整结构：

  ┌─── JVM 方法区 ───────────────────┐
  │  Class<User>                     │  ← 类的运行时镜像（元数据）
  │  ├─ fields: [name:String, age:int]
  │  ├─ methods: [sayHello(String), getName()]
  │  ├─ constructors: [User(String,int)]
  │  └─ annotations: [@Service, @Autowired]
  └──────────────────┬───────────────┘
                     │ 镜像映射
  ┌─── JVM 堆 ────────┴───────────────┐
  │  User实例                          │  ← 实际对象
  │  ├─ name = "张三"                  │
  │  └─ age  = 25                      │
  └───────────────────────────────────┘
```

| 反射类 | 作用 | 常用方法 |
|--------|------|----------|
| `Class<?>` | 类的运行时镜像 | `forName()`, `newInstance()`, `getMethods()`, `getFields()` |
| `Method` | 方法元信息 | `invoke()`, `getName()`, `getParameterTypes()` |
| `Field` | 字段元信息 | `get()`, `set()`, `setAccessible()` |
| `Constructor<?>` | 构造器元信息 | `newInstance()`, `getParameterTypes()` |

#### 2. 获取 Class 对象的三种方式

```
方式1: String.class          方式2: str.getClass()        方式3: Class.forName("java.lang.String")
  ┌──────────┐               ┌──────────┐                 ┌──────────┐
  │ 编译期已知 │               │ 运行时已有  │                 │ 运行时动态  │
  │ 最安全     │               │ 实例       │                 │ 最灵活     │
  │ 无异常     │               │ 可能NPE   │                 │ 抛CNFE    │
  └─────┬────┘               └─────┬────┘                 └─────┬────┘
        │                          │                            │
        └──────── 三者返回同一个 Class 对象（同一类加载器下）─────────┘
                              ↓
                   System.out.println(clazz1 == clazz2 == clazz3) // true
```

```java
// 方式1：类名.class（编译期已知，最安全）
Class<String> clazz1 = String.class;

// 方式2：对象.getClass()（运行时获取）
String str = "hello";
Class<?> clazz2 = str.getClass();

// 方式3：Class.forName()（运行时动态加载，最灵活）
Class<?> clazz3 = Class.forName("java.lang.String");

// 三者返回的是同一个 Class 对象（同一类加载器下）
System.out.println(clazz1 == clazz2); // true
System.out.println(clazz2 == clazz3); // true
```

#### 3. 反射创建实例与调用方法

```
反射操作流程：Class.forName → 构造器 → 实例 → 方法 → invoke

  Class.forName("com.example.User")
       ↓
  getDeclaredConstructor(String.class, int.class)
       ↓                    ↓
  newInstance("张三", 25) ──→ User实例 {name="张三", age=25}
                                   ↓
  getDeclaredMethod("sayHello", String.class)
       ↓
  setAccessible(true)  ← 突破 private
       ↓
  invoke(user, "World") ──→ 执行 user.sayHello("World") → 返回结果
```

```java
// 创建实例
Class<?> clazz = Class.forName("com.example.User");
Constructor<?> constructor = clazz.getDeclaredConstructor(String.class, int.class);
// 运行时内存: constructor 指向 User(String, int) 的构造器元数据
Object user = constructor.newInstance("张三", 25);
// 运行时内存: 堆中新建 User{name="张三", age=25}

// 调用方法
Method method = clazz.getDeclaredMethod("sayHello", String.class);
method.setAccessible(true); // 突破 private 访问限制
Object result = method.invoke(user, "World");
// 运行时内存: 等价于 user.sayHello("World")，result 接收返回值

// 访问字段
Field field = clazz.getDeclaredField("name");
field.setAccessible(true);
String name = (String) field.get(user);
// 运行时内存: 直接读取 user 对象的 name 字段值 "张三"
```

#### 4. 反射在框架中的应用

```
Spring IoC 创建 Bean 的反射链路：

  XML/注解配置 "com.example.UserService"
       ↓ Class.forName()
  Class<UserService> clazz
       ↓ getDeclaredConstructor().newInstance()
  UserService实例 (字段都为null)
       ↓ 遍历 getDeclaredFields()
  发现 @Autowired 字段
       ↓ field.setAccessible(true) + field.set(instance, dependency)
  依赖注入完成
       ↓
  完整的 Bean 放入容器
```

```java
// Spring 通过反射创建 Bean 实例
public Object createBean(String className) throws Exception {
    Class<?> clazz = Class.forName(className);
    // 通过无参构造创建实例
    Object instance = clazz.getDeclaredConstructor().newInstance();
    // 运行时内存: instance 字段全为 null

    // 通过反射注入依赖
    for (Field field : clazz.getDeclaredFields()) {
        if (field.isAnnotationPresent(Autowired.class)) {
            field.setAccessible(true);
            Object dependency = getBean(field.getType());
            field.set(instance, dependency);  // 内存: instance.field ← dependency
        }
    }
    return instance;
}
```

#### 5. 反射的性能问题与优化

**结论**：反射比直接调用慢 1-2 个数量级。

| 原因 | 说明 | 优化手段 |
|------|------|----------|
| 方法查找 | 遍历方法表匹配名称和参数 | 缓存 Method 对象 |
| 安全检查 | `invoke()` 每次检查访问权限 | `setAccessible(true)` 跳过检查 |
| JIT 难优化 | 反射调用难以内联 | JDK 9+ 用 MethodHandle |

```java
// 1. 缓存 Method 对象，避免反复查找
private static final Method METHOD;
static {
    try {
        METHOD = User.class.getDeclaredMethod("sayHello", String.class);
        METHOD.setAccessible(true); // 关闭访问检查，提升约 20-30% 性能
    } catch (NoSuchMethodException e) {
        throw new RuntimeException(e);
    }
}

// 2. setAccessible(true) 跳过安全检查，提升约 20-30% 性能
// 3. JDK 9+ 使用 MethodHandle（方法句柄）比反射更快
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;

MethodHandles.Lookup lookup = MethodHandles.lookup();
MethodHandle mh = lookup.findVirtual(User.class, "sayHello",
    MethodType.methodType(String.class, String.class));
String result = (String) mh.invoke(user, "World");
```

---

### 三、ClassLoader 与双亲委派模型

#### 1. 类加载过程（五阶段）

```
.class 文件 ──→ 可用的 Class 对象

  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │ 加载    │───→│ 验证    │───→│ 准备    │───→│ 解析    │───→│ 初始化  │
  │ Loading │    │ Verify  │    │ Prepare │    │ Resolve │    │ Init    │
  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
  读取字节流       检查格式       静态变量=0      符号→直接      执行<clinit>
  生成Class       合法?          (非初值!)       引用           线程安全
```

| 阶段 | 做什么 | 关键点 |
|------|--------|--------|
| 加载 (Loading) | 通过 ClassLoader 读取 .class 字节流，生成 Class 对象 | 可自定义 ClassLoader |
| 验证 (Verification) | 检查字节码格式、元数据、符号引用 | 确保类符合 JVM 规范 |
| 准备 (Preparation) | 为静态变量分配内存并赋零值（非赋初值）| `static int x = 10` 此时 x=0 |
| 解析 (Resolution) | 常量池中符号引用 → 直接引用 | 可发生在初始化前或后（懒解析） |
| 初始化 (Initialization) | 执行 `<clinit>()` 方法（静态变量赋值+静态代码块） | 线程安全，JVM 保证只执行一次 |

**面试易错点**：准备阶段赋零值，初始化阶段才赋真实值。

```java
public class Demo {
    static int x = 10;        // 准备阶段: x = 0; 初始化阶段: x = 10
    static final int Y = 20;   // 常量在准备阶段就会被赋值: Y = 20 (ConstantValue 属性)
}

// 内存状态变化：
// 准备阶段:  Demo.class 中 x = 0,  Y = 20 (final常量直接赋值)
// 初始化阶段: x = 10 (执行 <clinit> 中的赋值)
```

#### 2. 类加载器层次结构

```
┌──────────────────────────────────────────────────────┐
│  Bootstrap ClassLoader (C++ 实现)                     │
│  加载: rt.jar / java.base 模块 (String, Object...)   │
│  特点: Java 中 getClassLoader() 返回 null            │
└───────────────────────────┬──────────────────────────┘
                            │ parent
┌───────────────────────────┴──────────────────────────┐
│  Platform ClassLoader (JDK 9+，替代 Extension)        │
│  加载: ext 目录 / 平台模块 (javax.sql.DataSource...)  │
└───────────────────────────┬──────────────────────────┘
                            │ parent
┌───────────────────────────┴──────────────────────────┐
│  Application ClassLoader (加载 classpath)              │
│  加载: 用户代码、第三方依赖 (com.example.* ...)       │
└───────────────────────────┬──────────────────────────┘
                            │ parent
┌───────────────────────────┴──────────────────────────┐
│  Custom ClassLoader (自定义)                           │
│  场景: Tomcat / OSGi / 热部署                          │
└──────────────────────────────────────────────────────┘
```

```java
// 验证类加载器层次
System.out.println(String.class.getClassLoader());        // null → Bootstrap
System.out.println(javax.sql.DataSource.class.getClassLoader()); // PlatformClassLoader (JDK 9+)
System.out.println(MyApp.class.getClassLoader());         // AppClassLoader

// JDK 9+ 的获取方式
ClassLoader.getPlatformClassLoader(); // 获取 Platform ClassLoader
ClassLoader.getSystemClassLoader();   // 获取 Application ClassLoader
```

#### 3. 双亲委派模型核心逻辑

**核心思想**：收到类加载请求时，先委派给父加载器去加载，父加载器加载不了才自己去加载。

```
双亲委派流程（请求向上，加载向下）：

  AppClassLoader 收到请求: "加载 java.lang.String"
       │
       │ ① 先委派给父加载器
       ▼
  PlatformClassLoader 收到请求
       │
       │ ② 继续委派给父加载器
       ▼
  Bootstrap ClassLoader 收到请求
       │
       │ ③ Bootstrap 能加载吗？→ YES!
       ▼
  加载成功，返回 Class 对象
       │
       │ ④ 结果向下传递
       ▼
  PlatformClassLoader: "父加载器已处理，我不需要加载"
       │
       ▼
  AppClassLoader: "父加载器已处理，返回结果"
```

```
反例：用户自定义了 java.lang.String（恶意替换核心类）

  AppClassLoader: "加载 java.lang.String"
       │ ① 委派给父加载器
       ▼
  Bootstrap: "我已经加载了真正的 String！" ← 核心类由 Bootstrap 优先加载
       │
       ▼
  返回真正的 java.lang.String → 用户伪造的 String 永远不会被加载
```

`ClassLoader.loadClass()` 源码：

```java
protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
    synchronized (getClassLoadingLock(name)) {
        // 1. 检查是否已加载
        Class<?> c = findLoadedClass(name);
        if (c == null) {
            try {
                // 2. 委派给父加载器
                if (parent != null) {
                    c = parent.loadClass(name, false);
                } else {
                    // 3. 父为空则委派给 Bootstrap
                    c = findBootstrapClassOrNull(name);
                }
            } catch (ClassNotFoundException e) {
                // 父加载器加载失败，不做处理
            }

            if (c == null) {
                // 4. 父加载器都加载不了，自己加载
                c = findClass(name);
            }
        }
        return c;
    }
}
```

| 好处 | 说明 |
|------|------|
| 安全性 | 防止用户自定义 `java.lang.String` 替代核心类（Bootstrap 先加载到真的 String） |
| 唯一性 | 同一类由同一加载器加载，保证全程序中 Class 对象唯一 |
| 层次清晰 | 核心类由 Bootstrap 加载，扩展类由 Platform 加载，应用类由 App 加载 |

#### 4. 破坏双亲委派模型

**方式一：重写 loadClass()（不推荐）**

直接覆写 `loadClass` 方法会破坏委派逻辑。JDK 历史上确实有过这种做法，但现在推荐重写 `findClass()` 而非 `loadClass()`。

**方式二：线程上下文类加载器（SPI 场景）**

这是最经典的"合理破坏"场景。

```
SPI/TCCL "反向委派" 机制：

  问题：DriverManager 由 Bootstrap 加载，但需要加载 classpath 上的 MySQL Driver

  ┌─────────────────────────────────────────────────────┐
  │  Bootstrap ClassLoader                               │
  │  加载了: java.sql.DriverManager, java.sql.Driver    │
  │  问题: Bootstrap 只能加载核心类，看不到 classpath!   │
  │                                                      │
  │  解决方案: 通过 TCCL "反向"使用子加载器              │
  │                                                      │
  │    Thread.currentThread()                            │
  │        .getContextClassLoader()  ────────────┐       │
  │                                              │       │
  └──────────────────────────────────────────────┼───────┘
                                                 │
  ┌──────────────────────────────────────────────┼───────┐
  │  AppClassLoader  ←──────────────────────────┘       │
  │  能加载 classpath 上的所有类！                        │
  │  包括: com.mysql.cj.jdbc.Driver                     │
  │                                                      │
  │  TCCL 打破了"父加载器无法委派子加载器"的限制          │
  └────────────────────────────────────────────────────┘
```

```java
// DriverManager 在 Bootstrap 中，但需要加载 classpath 上的 Driver 实现
// 通过 TCCL 获取应用类加载器来加载实现类
public class DriverManager {
    static {
        loadInitialDrivers();
    }

    private static void loadInitialDrivers() {
        // 使用 ServiceLoader 机制（SPI）
        // ServiceLoader 内部通过 TCCL 加载实现类
        ServiceLoader<Driver> loadedDrivers = ServiceLoader.load(Driver.class);
        Iterator<Driver> driversIterator = loadedDrivers.iterator();
        while (driversIterator.hasNext()) {
            driversIterator.next(); // 触发加载
        }
    }
}

// ServiceLoader.load 内部逻辑
public static <S> ServiceLoader<S> load(Class<S> service) {
    // 获取当前线程的上下文类加载器（通常是 AppClassLoader）
    ClassLoader cl = Thread.currentThread().getContextClassLoader();
    return new ServiceLoader<>(service, cl);
}
```

MySQL 驱动 jar 包中的 `META-INF/services/java.sql.Driver` 文件内容：
```
com.mysql.cj.jdbc.Driver
```

**方式三：Tomcat 等容器打破双亲委派**

```
标准双亲委派：                    Tomcat 类加载：
                                                        ┌──────────────┐
                                                        │ WebApp2 CL    │ ← App2独立Spring
                                                        │ (优先自己加载) │
  ┌──────────┐                                          └──────────────┘
  │App CL     │ ← 所有应用共用             ┌──────────┐ ┌──────────────┐
  │(先问父)   │                           │ WebApp1 CL│ │ Common CL    │ ← 共享库
  └────┬─────┘                           │(优先自己) │ │ (Tomcat/lib) │
       │                                 └────┬─────┘ └──────┬───────┘
  ┌────┴─────┐                                │              │
  │Platform  │                           ┌────┴─────┐ ┌──────┴───────┐
  │          │                           │App CL     │ │ Catalina CL   │
  └────┬─────┘                           │(Java核心) │ │ (Tomcat自身)  │
       │                                 └────┬─────┘ └───────────────┘
  ┌────┴─────┐                                │
  │Bootstrap  │                           ┌────┴─────┐
  │(核心类)   │                           │Platform  │
  └──────────┘                           └────┬─────┘
                                              │
                                         ┌────┴─────┐
                                         │Bootstrap  │
                                         └──────────┘

  关键区别: Tomcat 的 WebAppClassLoader 优先自己加载（非 java.* 的类）
           → 不同 Web 应用可以用不同版本的第三方库，互不冲突
```

Tomcat 为每个 Web 应用创建独立的 `WebAppClassLoader`，优先加载自己的 classpath，而不是先委派给父加载器。这样不同应用可以使用不同版本的第三方库，互不冲突。

#### 5. 自定义 ClassLoader

```java
public class CustomClassLoader extends ClassLoader {
    private String classPath;

    public CustomClassLoader(String classPath) {
        this.classPath = classPath;
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        try {
            byte[] classData = loadClassData(name);
            if (classData == null) {
                throw new ClassNotFoundException(name);
            }
            // defineClass 将字节数组转为 Class 对象
            // 运行时内存: 字节流 → JVM 方法区中的 Class 结构
            return defineClass(name, classData, 0, classData.length);
        } catch (IOException e) {
            throw new ClassNotFoundException(name, e);
        }
    }

    private byte[] loadClassData(String name) throws IOException {
        String path = classPath + "/" + name.replace('.', '/') + ".class";
        try (InputStream is = new FileInputStream(path);
             ByteArrayOutputStream bos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[1024];
            int len;
            while ((len = is.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
            return bos.toByteArray();
        }
    }

    // 测试
    public static void main(String[] args) throws Exception {
        CustomClassLoader loader = new CustomClassLoader("/path/to/classes");
        Class<?> clazz = loader.loadClass("com.example.HelloWorld");
        // 运行时内存: clazz.getClassLoader() == loader (自定义)
        Object instance = clazz.getDeclaredConstructor().newInstance();
        Method method = clazz.getDeclaredMethod("say");
        method.invoke(instance);
    }
}
```

---

### 四、SPI 机制详解

#### 1. SPI 是什么

**结论**：接口定义在核心库中，实现在外部 jar 包中，运行时动态发现并加载。

| 维度 | API (Application Programming Interface) | SPI (Service Provider Interface) |
|------|----------------------------------------|----------------------------------|
| 方向 | 调用方使用接口 | 实现方实现接口 |
| 关系 | 接口是 API，我来调用 | 接口是 SPI，我来实现 |
| 典型场景 | Spring Framework 提供 API | 各数据库厂商实现 JDBC Driver |

#### 2. SPI 使用流程

```
SPI 发现序列图：

  调用方              ServiceLoader           META-INF/services        实现类
    │                      │                       │                     │
    │── load(Driver.class)│                       │                     │
    │                      │── 读取文件 ──────────→│                     │
    │                      │←── "com.mysql...Driver"│                    │
    │                      │                       │                     │
    │                      │── Class.forName(实现类名, TCCL) ──────────→│
    │                      │                       │                     │
    │                      │←─────────── Class 对象 │                    │
    │                      │                       │                     │
    │                      │── newInstance() ────────────────────────→│
    │                      │←─────────── Driver 实例 │                    │
    │                      │                       │                     │
    │←── ServiceLoader ────│                       │                     │
    │ (持有所有实现的迭代器) │                       │                     │
```

```
1. 核心库定义接口：java.sql.Driver
2. 实现者编写实现类：com.mysql.cj.jdbc.Driver
3. 实现者在 jar 包中创建配置文件：
   META-INF/services/java.sql.Driver
   内容：com.mysql.cj.jdbc.Driver
4. 调用方使用 ServiceLoader 加载：
   ServiceLoader<Driver> loaders = ServiceLoader.load(Driver.class);
```

#### 3. SPI 在 JDK 中的应用

| 框架 | SPI 接口 | 实现方 | 配置文件 |
|------|---------|--------|---------|
| JDBC | `java.sql.Driver` | MySQL/Oracle 等 | `META-INF/services/java.sql.Driver` |
| SLF4J | `org.slf4j.spi.LocationAwareLogger` | Logback/Log4j2 | `META-INF/services/...` |
| Spring Boot | 自动配置接口 | 各 starter | `META-INF/spring.factories`（变体）|
| Dubbo | 自定义 SPI | 各扩展点 | `META-INF/dubbo/...`（支持 IOC+AOP）|

#### 4. JDK SPI 的缺点

| 缺点 | 说明 | 谁解决了 |
|------|------|----------|
| 一次性全加载 | 无法按需加载 | Dubbo ExtensionLoader |
| 不支持依赖注入 | 无法给实现注入依赖 | Dubbo |
| 无法起别名 | 不能按 key 取实现 | Dubbo |

---

### 五、System 类与时间 API

#### 1. System 类核心方法

```java
public final class System {
    // 三个标准流
    public static final InputStream in;      // 标准输入
    public static final PrintStream out;     // 标准输出
    public static final PrintStream err;     // 标准错误

    // 时间相关
    public static native long currentTimeMillis();  // 毫秒级时间戳
    public static native long nanoTime();           // 纳秒级计时器（只能算差值）

    // 数组拷贝
    public static native void arraycopy(Object src, int srcPos,
                                         Object dest, int destPos, int length);

    // 属性管理
    public static Properties getProperties();
    public static String getProperty(String key);

    // 环境变量
    public static Map<String, String> getenv();

    // GC（只是建议）
    public static void gc();

    // 退出
    public static void exit(int status);
}
```

| 维度 | currentTimeMillis() | nanoTime() |
|------|--------------------|------------| 
| 精度 | 毫秒 | 纳秒 |
| 用途 | 获取当前时间戳 | 计算时间差（性能测试） |
| 基准 | UTC 1970-01-01 | 不保证与任何时间关联 |
| 单调性 | 不保证单调（系统时间可被修改） | 保证单调递增 |

**面试陷阱**：`System.gc()` 只是建议 JVM 做 GC，不保证立即执行。JVM 可通过 `-XX:+DisableExplicitGC` 参数直接忽略。

#### 2. Java 时间 API 演进

```
时间线：

  JDK 1.0          JDK 1.1              JDK 8+
  ─────────────────────────────────────────────────→
  │                 │                     │
  ▼                 ▼                     ▼
┌──────────┐   ┌──────────────┐   ┌──────────────┐
│ Date      │   │ Calendar     │   │ java.time.*  │
│           │   │ SimpleDateFmt│   │ (JSR-310)    │
│ 已废弃    │   │ 线程不安全   │   │ 推荐！线程安全│
│ 设计糟糕  │   │ 月份从0开始  │   │ 不可变对象    │
└──────────┘   └──────────────┘   └──────────────┘
   1996            1997               2014
```

| 版本 | API | 状态 |
|------|-----|------|
| JDK 1.0 | `java.util.Date` | 已废弃，设计糟糕 |
| JDK 1.1 | `Calendar` / `SimpleDateFormat` | 可用但线程不安全 |
| JDK 8+ | `java.time.*`（JSR-310） | **推荐使用** |

#### 3. Java 8 时间 API（java.time）核心类

```
Instant / LocalDateTime / ZonedDateTime 关系图：

  ┌─────────────────────────────────────────────────────────┐
  │                                                          │
  │     Instant (UTC 时间线上的瞬时点)                         │
  │     例: 2026-08-12T07:30:45.123Z                         │
  │              │                                           │
  │     ┌────────┴────────┐                                 │
  │     │ + ZoneId         │ + ZoneId                        │
  │     ▼                  ▼                                 │
  │  ZonedDateTime     LocalDateTime                         │
  │  (带时区)          (不带时区)                              │
  │  例: 2026-08-12    例: 2026-08-12                         │
  │  T15:30:45.123    T15:30:45.123                          │
  │  +08:00[Asia/                                             │
  │   Shanghai]                                               │
  │                                                           │
  │  LocalDate = 日期部分   LocalTime = 时间部分               │
  │  例: 2026-08-12          例: 15:30:45.123                │
  └─────────────────────────────────────────────────────────┘

  Duration: 时分秒级别间隔    Period: 年月日级别间隔
```

```java
// 日期
LocalDate date = LocalDate.now();           // 2026-08-12
LocalDate date2 = LocalDate.of(2026, 8, 12);

// 时间
LocalTime time = LocalTime.now();           // 15:30:45.123
LocalTime time2 = LocalTime.of(15, 30, 0);

// 日期时间
LocalDateTime dateTime = LocalDateTime.now();

// 时间戳（UTC）
Instant instant = Instant.now();            // 2026-08-12T07:30:45.123Z

// 带时区
ZonedDateTime zdt = ZonedDateTime.now();    // 2026-08-12T15:30:45.123+08:00[Asia/Shanghai]

// 时间间隔
Duration duration = Duration.between(time1, time2);  // 时分秒级别
Period period = Period.between(date1, date2);         // 年月日级别

// 格式化
DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
String formatted = dateTime.format(formatter);
LocalDateTime parsed = LocalDateTime.parse("2026-08-12 15:30:00", formatter);
```

**线程安全对比**：

```
SimpleDateFormat (线程不安全):          DateTimeFormatter (线程安全):
┌──────────────────────────┐           ┌──────────────────────────┐
│ 内部 Calendar calendar    │ ← 可变!   │ 内部无共享可变状态         │ ← 不可变!
│ Thread1: calendar.set(...) │ ← 竞争!  │ Thread1: format()        │ ← 安全
│ Thread2: calendar.set(...) │ ← 竞争!  │ Thread2: format()        │ ← 安全
│ → 数据竞争，解析错误!       │           │ → 完全安全，可做 static  │
└──────────────────────────┘           └──────────────────────────┘
```

```java
// SimpleDateFormat 线程不安全（内部 Calendar 有状态）
// 多线程下会出现日期解析错误
SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
// 多个线程同时使用 sdf.parse() 会出错！

// DateTimeFormatter 线程安全（不可变对象）
DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyy-MM-dd");
// 多个线程同时使用 dtf 完全安全，可作为 static final 共享
```

**面试追问**：为什么 SimpleDateFormat 线程不安全？因为它的 `parse()` 方法内部会修改私有的 `Calendar calendar` 字段，这是共享可变状态，多线程并发访问会导致数据竞争。

---

## 代码示例

### 示例 1：自定义异常体系实战

```java
/**
 * 业务异常基类，含错误码
 */
public class BizException extends RuntimeException {
    private final int code;

    public BizException(int code, String message) {
        super(message);
        this.code = code;
    }

    public BizException(int code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}

/**
 * 用户不存在异常
 */
public class UserNotFoundException extends BizException {
    public UserNotFoundException(String userId) {
        super(40401, "用户不存在: " + userId);
    }
}

/**
 * 参数校验异常
 */
public class ParamInvalidException extends BizException {
    public ParamInvalidException(String detail) {
        super(40001, "参数校验失败: " + detail);
    }
}

// 使用示例
public class UserService {
    public User getUser(String userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new UserNotFoundException(userId);
        }
        return user;
    }

    public void updateUser(UserUpdateDTO dto) {
        if (dto.getUserId() == null || dto.getUserId().isEmpty()) {
            throw new ParamInvalidException("userId不能为空");
        }
        // try-catch 包装底层异常
        try {
            userMapper.update(dto);
        } catch (Exception e) {
            throw new BizException(50001, "用户更新失败", e); // 异常链
        }
    }
}
```

### 示例 2：反射动态调用（模拟简单RPC框架）

```java
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

/**
 * 简易服务注册与调用框架，模拟 RPC 核心
 */
public class SimpleRpcServer {
    // 服务注册表：接口名 → 实现实例
    private final Map<String, Object> serviceMap = new HashMap<>();

    // 注册服务
    public void register(Class<?> interfaceClass, Object implInstance) {
        serviceMap.put(interfaceClass.getName(), implInstance);
    }

    // 动态调用：接口名 + 方法名 + 参数类型 + 参数值
    public Object invoke(String interfaceName, String methodName,
                         Class<?>[] paramTypes, Object[] args) throws Exception {
        // 1. 查找服务实例
        Object serviceInstance = serviceMap.get(interfaceName);
        if (serviceInstance == null) {
            throw new RuntimeException("服务未注册: " + interfaceName);
        }

        // 2. 反射获取方法（缓存优化此处省略）
        Class<?> implClass = serviceInstance.getClass();
        Method method = implClass.getMethod(methodName, paramTypes);

        // 3. 反射调用
        return method.invoke(serviceInstance, args);
    }

    // 测试
    public interface HelloService {
        String sayHello(String name, int age);
    }

    public static class HelloServiceImpl implements HelloService {
        @Override
        public String sayHello(String name, int age) {
            return "Hello, " + name + "! You are " + age + " years old.";
        }
    }

    public static void main(String[] args) throws Exception {
        SimpleRpcServer server = new SimpleRpcServer();
        server.register(HelloService.class, new HelloServiceImpl());

        String result = (String) server.invoke(
            HelloService.class.getName(),
            "sayHello",
            new Class[]{String.class, int.class},
            new Object[]{"张三", 25}
        );
        System.out.println(result); // Hello, 张三! You are 25 years old.
    }
}
```

### 示例 3：自定义 ClassLoader 热加载

```java
import java.io.*;

/**
 * 自定义类加载器实现类热加载
 * 每次创建新实例即可加载最新class文件
 */
public class HotReloadClassLoader extends ClassLoader {

    private final String classDir;

    public HotReloadClassLoader(String classDir, ClassLoader parent) {
        super(parent);
        this.classDir = classDir;
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        String fileName = classDir + File.separator
                + name.replace('.', File.separatorChar) + ".class";
        try (InputStream is = new FileInputStream(fileName);
             ByteArrayOutputStream bos = new ByteArrayOutputStream()) {

            byte[] buffer = new byte[4096];
            int len;
            while ((len = is.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
            byte[] bytes = bos.toByteArray();

            return defineClass(name, bytes, 0, bytes.length);
        } catch (IOException e) {
            throw new ClassNotFoundException("加载类失败: " + name, e);
        }
    }

    /**
     * 热加载：每次用新 ClassLoader 实例加载
     * 旧 ClassLoader 加载的旧类会被 GC 回收
     */
    public static void main(String[] args) throws Exception {
        String classDir = "/path/to/classes";

        // 第一次加载
        HotReloadClassLoader loader1 = new HotReloadClassLoader(classDir,
                HotReloadClassLoader.class.getClassLoader());
        Class<?> clazz1 = loader1.findClass("com.example.HelloService");
        Object instance1 = clazz1.getDeclaredConstructor().newInstance();
        Method method1 = clazz1.getDeclaredMethod("say");
        System.out.println("第一次: " + method1.invoke(instance1));

        // 修改 class 文件后...第二次加载（热更新）
        Thread.sleep(2000);
        HotReloadClassLoader loader2 = new HotReloadClassLoader(classDir,
                HotReloadClassLoader.class.getClassLoader());
        Class<?> clazz2 = loader2.findClass("com.example.HelloService");
        Object instance2 = clazz2.getDeclaredConstructor().newInstance();
        Method method2 = clazz2.getDeclaredMethod("say");
        System.out.println("第二次: " + method2.invoke(instance2));

        // clazz1 != clazz2（不同 ClassLoader 加载的同一类是不同的 Class 对象）
        System.out.println("同一个类吗? " + (clazz1 == clazz2)); // false
    }
}
```

### 示例 4：Java 8 时间 API 实战

```java
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.*;

public class TimeApiDemo {
    // DateTimeFormatter 线程安全，可以全局共享
    private static final DateTimeFormatter FORMATTER =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public static void main(String[] args) {
        // 1. 基本日期时间操作
        LocalDate today = LocalDate.now();
        LocalDateTime now = LocalDateTime.now();

        System.out.println("今天: " + today);                    // 2026-08-12
        System.out.println("现在: " + now.format(FORMATTER));     // 2026-08-12 15:30:45

        // 2. 日期计算
        LocalDate nextWeek = today.plus(1, ChronoUnit.WEEKS);
        LocalDate nextMonth = today.plusMonths(1);
        LocalDate lastDayOfYear = LocalDate.of(today.getYear(), 12, 31);
        long daysLeft = ChronoUnit.DAYS.between(today, lastDayOfYear);

        System.out.println("下周: " + nextWeek);
        System.out.println("今年还剩: " + daysLeft + " 天");

        // 3. 时间戳与 Instant
        Instant instant = Instant.now();
        long timestamp = instant.getEpochSecond();  // 秒级时间戳
        long timestampMillis = instant.toEpochMilli(); // 毫秒级时间戳
        System.out.println("时间戳: " + timestampMillis);

        // Instant → LocalDateTime（需要指定时区）
        LocalDateTime ldt = LocalDateTime.ofInstant(instant, ZoneId.systemDefault());

        // LocalDateTime → Instant（需要指定时区）
        Instant back = now.atZone(ZoneId.systemDefault()).toInstant();

        // 4. Duration 和 Period
        LocalTime t1 = LocalTime.of(9, 0);
        LocalTime t2 = LocalTime.of(18, 30);
        Duration workHours = Duration.between(t1, t2);
        System.out.println("工作时长: " + workHours.toHours() + "小时" +
                (workHours.toMinutes() % 60) + "分钟"); // 9小时30分钟

        // 5. 计时性能（替代 System.nanoTime 手动计算）
        long start = System.nanoTime();
        // ... 执行代码 ...
        long elapsed = System.nanoTime() - start;
        System.out.println("耗时: " + elapsed + " ns (" +
                TimeUnit.NANOSECONDS.toMillis(elapsed) + " ms)");

        // 6. 多线程安全验证：DateTimeFormatter 并发安全
        ExecutorService pool = Executors.newFixedThreadPool(10);
        for (int i = 0; i < 100; i++) {
            pool.submit(() -> {
                String result = LocalDateTime.now().format(FORMATTER);
                // 100个线程同时用 FORMATTER，完全安全
            });
        }
        pool.shutdown();
    }
}
```

---

## 面试高频问题

### Q1：Java 异常体系是怎样的？Error 和 Exception 的区别？

**回答要点**：顶层是 Throwable，分两个子类。Error 是 JVM 级别严重错误（OOM、StackOverflow），程序无法也无需恢复，不应该 catch。Exception 分受检异常（编译期检查，必须 try-catch 或 throws，如 IOException）和非受检异常（RuntimeException 及其子类，如 NPE，编译器不强制处理）。

**追问：受检异常和非受检异常的使用场景？**

受检异常用于可恢复的业务异常（文件不存在、网络超时），强制调用方处理。非受检异常用于编程错误（空指针、数组越界），通常不应该 catch 而是修复代码。框架实践中，业务异常通常继承 RuntimeException。

### Q2：try-with-resources 的原理是什么？

**回答要点**：Java 7 引入的语法糖，编译器在编译时自动生成 try-catch-finally 代码块。要求资源实现 `AutoCloseable` 接口。编译器在 finally 中调用每个资源的 `close()` 方法，并且如果 try 块和 close 都抛异常，close 抛出的异常会通过 `addSuppressed()` 添加为抑制异常，不会覆盖原始异常。

### Q3：讲讲 Java 的反射机制，有什么应用场景？

**回答要点**：反射是在运行时动态获取类信息、创建实例、调用方法、访问字段的能力。通过 Class 对象获取 Method、Field、Constructor 等元数据。应用场景：Spring IoC 创建 Bean、MyBatis Mapper 代理、Jackson JSON 序列化、动态代理（AOP）、JDBC 加载驱动。反射的性能开销主要在方法查找和安全检查，可以通过缓存 Method 对象和 `setAccessible(true)` 优化。

**追问：反射的性能为什么差？**

一是 `getMethod` 需要遍历方法表做名称和参数类型匹配，二是 `invoke` 每次都要检查访问权限，三是 JIT 难以对反射调用做内联优化。JDK 9+ 可以用 MethodHandle 替代反射，性能更接近直接调用。

### Q4：什么是双亲委派模型？为什么要设计这个模型？

**回答要点**：类加载器收到加载请求时，先委派给父加载器加载，父加载器加载不了才自己加载。层次：Bootstrap → Platform（JDK 9+，原 Extension）→ Application → Custom。

设计目的：一是安全性，防止用户自定义类替换核心类（如自定义 `java.lang.String` 会被 Bootstrap 先加载到真的 String）；二是唯一性，同一类由同一加载器加载，保证 Class 对象全局唯一。

### Q5：有哪些场景破坏了双亲委派？为什么需要破坏？

**回答要点**：三个经典场景：

1. **SPI 机制（JDBC）**：接口 `java.sql.Driver` 在 rt.jar 中由 Bootstrap 加载，但实现类在 classpath 上，Bootstrap 加载不了。通过线程上下文类加载器（TCCL）让父加载器能"反向"使用子加载器加载实现类。

2. **Tomcat**：每个 Web 应用用独立的 `WebAppClassLoader`，优先加载自己的 classpath 而不委派给父加载器，实现应用间类隔离，不同应用可以用不同版本的库。

3. **OSGi / 热部署**：自定义 ClassLoader，不遵循双亲委派，实现模块化和类热替换。

### Q6：JDK SPI 机制是什么？跟 API 有什么区别？

**回答要点**：SPI 是服务发现机制，接口定义在核心库，实现在外部 jar 包中，运行时通过 `ServiceLoader` 动态发现。实现在 `META-INF/services/接口全限定名` 文件中声明。区别：API 是接口提供方定义、调用方使用；SPI 是接口定义方提供规范、实现方按需实现。典型应用：JDBC Driver、SLF4J 日志门面、Spring Boot 自动配置（`spring.factories`）。

### Q7：Java 8 的时间 API 为什么比 Date / Calendar 好？

**回答要点**：三个核心优势。一是不可变性，LocalDate/LocalDateTime/Instant 都是不可变对象，线程安全，而 SimpleDateFormat 内部有共享可变状态，多线程下会出问题。二是 API 设计清晰，日期时间操作语义明确（plusDays、minusMonths），Date 的方法大多已废弃，Calendar 的月份从 0 开始容易出错。三是时区处理完善，ZoneId / ZonedDateTime / Instant 三者关系清晰，Date 混用 UTC 和本地时区容易混乱。

### Q8：System.currentTimeMillis() 和 System.nanoTime() 的区别？

**回答要点**：currentTimeMillis 返回 UTC 1970-01-01 到现在的毫秒数，用于获取当前时间戳。nanoTime 返回纳秒级计时器，不与任何时间点关联，仅用于计算时间差。nanoTime 保证单调递增，而 currentTimeMillis 可能因系统时间被修改而回退。性能测试应该用 nanoTime。

### Q9：自定义 ClassLoader 需要重写哪个方法？

**回答要点**：重写 `findClass(String name)` 方法，而不是 `loadClass`。loadClass 中实现了双亲委派逻辑，如果重写它就破坏了委派模型。findClass 只在父加载器加载不了时被调用，在其中读取 class 文件字节流，调用 `defineClass` 将字节数组转为 Class 对象。

### Q10：类加载的初始化阶段什么时候会触发？

**回答要点**：六种情况会触发类初始化：创建实例（new）、访问静态字段（非 final 常量）、调用静态方法、反射（Class.forName）、初始化子类时父类先初始化、JVM 启动时的主类。不会触发初始化的情况：通过子类引用父类的静态字段（只初始化父类）、创建数组（`Test[] arr = new Test[10]` 不触发 Test 初始化）、访问 final 常量（编译期常量直接放入常量池）。

---

## 练习题

### 概念自测题

**1. 以下哪个异常属于受检异常？**
A. NullPointerException
B. ArrayIndexOutOfBoundsException
C. IOException
D. ClassCastException

**2. 关于 try-with-resources，以下说法正确的是？**
A. 资源类需要实现 Cloneable 接口
B. 资源类需要实现 AutoCloseable 接口
C. 只能声明一个资源
D. 关闭顺序与声明顺序一致

**3. 关于双亲委派模型，以下说法错误的是？**
A. 子加载器先尝试加载，加载不了再委派给父加载器
B. Bootstrap ClassLoader 由 C++ 实现，Java 中获取返回 null
C. 同一个类被不同 ClassLoader 加载，是两个不同的 Class 对象
D. 自定义 ClassLoader 推荐重写 findClass 而非 loadClass

**4. 以下代码的输出是什么？**
```java
static int x = 10;
static {
    x = 20;
    System.out.println("static block, x=" + x);
}
public static void main(String[] args) {
    System.out.println("main, x=" + x);
}
```
A. static block, x=20 → main, x=20
B. static block, x=10 → main, x=20
C. main, x=10 → static block, x=20
D. 编译错误

**5. 关于 Java 8 时间 API，以下说法正确的是？**
A. DateTimeFormatter 是线程不安全的
B. LocalDateTime 包含时区信息
C. Instant 是 UTC 时间线上的一个瞬时点
D. Duration 用于计算年月日级别的间隔

### 动手编码题

**1. 自定义异常 + 异常链**

编写一个用户注册服务，包含以下异常：`UserAlreadyExistsException`（用户已存在）、`InvalidEmailException`（邮箱格式错误）。在注册方法中，如果数据库操作失败，将 `SQLException` 包装成 `RegistrationException` 并保留原始异常链。

**2. 反射实现简易Bean拷贝**

使用反射编写一个 `BeanUtils.copy(source, target)` 方法，将 source 对象中同名字段的值拷贝到 target 对象中。注意处理类型不匹配、private 字段访问、null 值等情况。

**3. 自定义 ClassLoader 加密加载**

编写一个 ClassLoader，它能加载经过简单异或加密的 .class 文件。加密逻辑：原始字节 XOR 0xFF。包含一个加密工具方法负责加密 class 文件。

### 面试模拟题

**场景 1**：面试官说："你提到 Spring 用反射创建 Bean，那如果 Bean 的构造方法是 private 的，Spring 还能创建实例吗？如果能，原理是什么？"

> 追问：这种方式有没有什么问题？为什么 Singleton 模式中不推荐用反射破坏私有构造？

**场景 2**：面试官说："JDBC 加载驱动用到了 SPI 机制，你能讲讲 DriverManager 是怎么找到 MySQL Driver 的吗？如果我在 classpath 上放两个不同版本的 MySQL 驱动，会发生什么？"

> 追问：为什么不用 Class.forName("com.mysql.cj.jdbc.Driver") 了？（Hint：SPI 自动发现 vs 手动注册）

**场景 3**：面试官说："Tomcat 打破了双亲委派模型，你能详细讲讲 Tomcat 的类加载结构吗？为什么不遵循双亲委派？如果两个 Web 应用都用了 Spring，Spring 的类会被加载几次？"

> 追问：如果两个 Web 应用共享一些公共库，Tomcat 怎么处理？

---

## 答案要点

<details>
<summary>点击展开答案</summary>

### 概念自测题答案

1. **C** — IOException 是受检异常，其余三个都是 RuntimeException 的子类（非受检）。
2. **B** — try-with-resources 需要资源实现 AutoCloseable（或 Closeable）。关闭顺序与声明顺序**相反**（后声明的先关闭），所以 D 错误。可以声明多个资源，所以 C 错误。
3. **A** — 双亲委派是**先委派给父加载器**，父加载不了才自己加载。A 说反了。
4. **A** — 类初始化时先执行静态变量赋值 x=10，然后执行静态代码块 x=20 并打印，最后执行 main 打印 x=20。
5. **C** — DateTimeFormatter 线程安全（A 错），LocalDateTime 不含时区（B 错），Duration 用于时分秒级别（D 错），Instant 是 UTC 时间线上的瞬时点（C 对）。

### 动手编码题答案要点

**1. 自定义异常：**

```java
public class UserAlreadyExistsException extends RuntimeException {
    public UserAlreadyExistsException(String userId) {
        super("用户已存在: " + userId);
    }
}

public class InvalidEmailException extends RuntimeException {
    public InvalidEmailException(String email) {
        super("邮箱格式错误: " + email);
    }
}

public class RegistrationException extends RuntimeException {
    public RegistrationException(String message, Throwable cause) {
        super(message, cause);
    }
}

public class UserService {
    public void register(String userId, String email) {
        // 邮箱校验
        if (!email.matches("^[A-Za-z0-9+_.-]+@(.+)$")) {
            throw new InvalidEmailException(email);
        }
        // 检查用户是否存在
        if (userMapper.exists(userId)) {
            throw new UserAlreadyExistsException(userId);
        }
        // 写入数据库
        try {
            userMapper.insert(userId, email);
        } catch (SQLException e) {
            throw new RegistrationException("注册失败: 数据库异常", e); // 异常链
        }
    }
}
```

**2. 反射 Bean 拷贝：**

```java
public class BeanUtils {
    public static void copy(Object source, Object target) {
        if (source == null || target == null) return;

        Class<?> sourceClass = source.getClass();
        Class<?> targetClass = target.getClass();

        for (Field targetField : targetClass.getDeclaredFields()) {
            try {
                Field sourceField = sourceClass.getDeclaredField(targetField.getName());
                sourceField.setAccessible(true);
                targetField.setAccessible(true);

                Object value = sourceField.get(source);
                if (value != null && targetField.getType().isAssignableFrom(sourceField.getType())) {
                    targetField.set(target, value);
                }
            } catch (NoSuchFieldException e) {
                // target 有但 source 没有的字段，跳过
            } catch (IllegalAccessException e) {
                throw new RuntimeException("字段拷贝失败: " + targetField.getName(), e);
            }
        }
    }
}
```

**3. 加密 ClassLoader：**

```java
public class EncryptedClassLoader extends ClassLoader {
    private final String classDir;
    private final byte encryptKey = (byte) 0xFF;

    public EncryptedClassLoader(String classDir, ClassLoader parent) {
        super(parent);
        this.classDir = classDir;
    }

    // 加密工具方法
    public static void encryptClass(File classFile) throws IOException {
        byte[] data = Files.readAllBytes(classFile.toPath());
        for (int i = 0; i < data.length; i++) {
            data[i] ^= 0xFF;
        }
        Files.write(classFile.toPath(), data);
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        String path = classDir + "/" + name.replace('.', '/') + ".class";
        try (InputStream is = new FileInputStream(path);
             ByteArrayOutputStream bos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int len;
            while ((len = is.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
            byte[] encryptedData = bos.toByteArray();
            // 解密：XOR 还原
            for (int i = 0; i < encryptedData.length; i++) {
                encryptedData[i] ^= encryptKey;
            }
            return defineClass(name, encryptedData, 0, encryptedData.length);
        } catch (IOException e) {
            throw new ClassNotFoundException(name, e);
        }
    }
}
```

### 面试模拟题答案要点

**场景 1**：Spring 可以创建 private 构造方法的 Bean。通过 `clazz.getDeclaredConstructor()` 获取构造器，再调用 `constructor.setAccessible(true)` 突破 private 限制，然后 `newInstance()` 创建实例。

追问回答：反射破坏私有构造带来两个问题——一是破坏了单例的唯一性保证，攻击者可以通过反射创建第二个实例；二是破坏了封装性，私有构造的意图是不允许外部实例化，反射绕过了这个约束。枚举单例是唯一能在反射攻击下保持单例的方式，因为 JVM 规范保证枚举实例的唯一性，反射创建枚举实例会抛出 IllegalArgumentException。

**场景 2**：DriverManager 静态代码块调用 `ServiceLoader.load(Driver.class)`，ServiceLoader 通过线程上下文类加载器读取 classpath 上所有 jar 包中的 `META-INF/services/java.sql.Driver` 文件，找到实现类全限定名后用 TCCL 加载并实例化。如果放两个版本，两个 Driver 实现都会被加载注册，DriverManager 内部用 CopyOnWriteArrayList 管理所有注册的 Driver。实际查询时会遍历所有 Driver 尝试连接，URL 匹配的那个生效。

追问：Class.forName 是手动注册方式，Java 6 之前必须手动调用。Java 6+ SPI 机制自动发现，所以不需要手动 `Class.forName` 了。但很多教程仍在用，因为历史惯性。

**场景 3**：Tomcat 的类加载结构：Bootstrap → Platform → App → Common（共享库）→ Catalina（Tomcat 自身）和 WebApp（每个应用独立）。WebAppClassLoader 不遵循双亲委派，对于 Web 应用自己的类，优先自己加载而非委派给父加载器。但 Java 核心类（java.*）仍走双亲委派。

两个 Web 应用如果各自打包了 Spring，Spring 的类会被 WebAppClassLoader 分别加载两次，每个应用有独立的 Spring 容器。

追问：公共库可以放在 Tomcat 的 `lib` 目录下，由 CommonClassLoader 加载，所有 Web 应用共享。但版本必须统一，否则无法做到不同应用用不同版本。

</details>

---

## 小结 & 下节预告

```
本节五大模块 → 面试频率：

  异常体系     ████████████  每场必问
  反射机制     ████████████  理解框架的前提
  双亲委派     ██████████████ 中级vs高级分水岭
  SPI机制     ████████      区分度题
  时间API     ██████        常规高频
```

| 重点掌握 | 关键点 |
|----------|--------|
| 异常体系 | 异常链概念 + try-with-resources 原理 |
| 反射 | 核心操作 + 性能优化 |
| 双亲委派 | 核心逻辑 + 三种破坏场景 |
| SPI | 发现流程 |
| 时间 API | 线程安全优势 |

下一节 **1-3 JDK IO 与 NIO**：深入 InputStream/OutputStream 体系、Reader/Writer 字符流、NIO 的 Buffer/Channel/Selector 三大组件，以及 ByteBuffer 直接内存 vs 堆内存。NIO 是理解 Netty 和网络编程的基础，面试中"BIO vs NIO vs AIO""直接内存和堆内存的区别"也是高频考点，做好预习准备。
