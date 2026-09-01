---
name: nocode-e2e-dev
description: "NoCode 端到端自动化开发 Skill。通过沙箱远程执行后端代码修改（mc --code 代理 Claude Code）、Maven 编译、Cargo 部署，结合 NoCode 前端生成，实现用户只需描述需求即可完成全栈开发的自动化流水线。触发词：端到端开发、全栈开发、做一个页面后端需要、新增接口前端展示、e2e开发、NoCode全栈、前端后端一起做。"
metadata:
  skillhub.version: "V1"
  skillhub.source: "FRIDAY Skillhub"
  skillhub.high_sensitive: "false"
---

# NoCode 端到端自动化开发 Skill

## 概述

本 Skill 赋能 NoCode Agent 进行端到端（前端 + 后端）全流程自动化开发。用户只需用自然语言描述需求，Agent 自动完成后端代码修改、编译、部署、前端生成、联调验证、提交 PR 的全链路，中间不停顿。

核心理念：**用户只参与两件事 —— 描述需求和验收确认，其余全部自动。**

## 架构

```
用户（NoCode Webapp）
  │
  ├── 描述需求 ──→ Agent 加载本 Skill
  │
  ├── 阶段 0: 配置检查
  ├── 阶段 1: 需求理解 + 接口契约定义
  ├── 阶段 2: 后端开发（全自动）
  │     ├── sandbox exec → mc --code 自动改码
  │     ├── mvn clean package 编译
  │     └── cargo deploy 部署
  ├── 阶段 3: 前端开发（全自动）
  │     ├── nocode create 生成页面
  │     ├── nocode screenshot 截图预览
  │     └── nocode deploy 部署上线
  ├── 阶段 4: 联调验证（全自动）
  ├── 阶段 5: 用户验收 ← 用户参与
  └── 阶段 6: git commit + push / 修复
```

## 触发条件

当用户表达以下意图时触发本 Skill：
- "做一个 xxx 页面，后端需要 xxx"
- "新增 xxx 接口 + 前端展示"
- "端到端开发"
- "全栈开发"
- "前端后端一起做"
- 任何同时涉及前端和后端的需求描述
- 任何涉及后端代码修改的需求（即使前端已存在）

## ⛔ 核心约束

1. **全流程自动化**：配置已绑定后，一旦用户描述需求，Agent 自动跑完后端开发、前端开发、联调和验收；中间不要求普通用户做技术操作。
2. **配置与凭据分离**：项目资源定位信息从学城配置文档读取；Token、密码、私钥、数据库连接串等敏感凭据绝不写入学城文档。
3. **接口契约是前后端唯一通信协议**：Agent 自己定义接口契约，分别传给 mc --code 和前端。
4. **所有后端操作通过 sandbox CLI 完成**：不直接 SSH、不手动操作文件，全部通过封装脚本命令。
5. **仅管理员执行一次绑定**：普通用户无需配置。项目未绑定时，只向管理员请求一条学城配置文档链接，不要求其编辑脚本或填写环境变量。

## 运行环境依赖（Skill 提供方/平台管理员一次性部署）

普通用户无需关心本节。Skill 运行环境需包含：

1. **sandbox CLI**：`sandbox-cli/` 目录下的封装脚本（`bin/sandbox.mjs`）与 `@e2b/sdk` 依赖，由 `nocodeKit/preinstall.sh` 在 NoCode 容器初始化时安装。命令用法见 [references/sandbox-cli-reference.md](references/sandbox-cli-reference.md)。
2. **平台凭据**：沙箱平台 Token（`ME2B_API_KEY` / `ME2B_ACCESS_TOKEN`，e2b_ 格式）由 Skill 提供方在受控环境（如 `nocodeKit/run.sh`）中配置，端侧不暴露给用户。

## 项目配置与首次绑定

每个 NoCode 项目使用一份学城配置文档。配置文档只记录 `sandboxId`、Git 仓库、构建命令和 Cargo appkey 等资源定位信息；认证由平台受控运行环境提供。

配置文档格式见 [references/config-document-template.md](references/config-document-template.md)。项目管理员仅需完成两步：创建/填写该文档，然后在 NoCode 对话中发送：

```
绑定端到端开发配置：https://km.sankuai.com/collabpage/<配置文档ID>
```

收到绑定指令时，提取文档 ID，使用 Citadel 的 `getSimpleMarkdown` 读取并校验 YAML 配置，再将如下最小标记写入当前 NoCode 项目的 `.e2e-dev/config.json`：

```json
{"configDocumentId":"<配置文档ID>","version":1}
```

不得把学城文档正文、Token 或任何凭据写入该标记文件。绑定成功后只输出“已绑定，后续直接描述需求即可”。

## 阶段 0：读取配置并校验

**触发时机**：每次端到端开发需求开始时自动执行。

1. 读取当前项目 `.e2e-dev/config.json` 中的 `configDocumentId`。
2. 若不存在，说明“该项目尚未绑定端到端配置，请项目管理员发送配置文档链接”，然后停止；不要让普通用户处理沙箱、Git 或 Cargo。
3. 使用 Citadel `getSimpleMarkdown --contentId <configDocumentId>` 读取最新配置。只解析 YAML 代码块中的以下字段：

```yaml
sandbox.sandboxId
sandbox.workspaceRoot
repository.repoUrl
repository.defaultBranch
build.installCommand
build.buildCommand
runtime.apiBasePath
cargo.appKey
cargo.branch
workflow.branchPrefix
workflow.configureClaudePermissions
```

4. 校验 `sandboxId`、`repository.repoUrl`、`cargo.appKey` 均为非空且不是占位符；否则报告“项目管理员需要补充配置文档中的字段名”，不要向普通用户暴露凭据要求。
5. 从受控运行环境校验 `ME2B_API_KEY` 与 `ME2B_ACCESS_TOKEN` 可用；二者缺失或鉴权失败时报告“平台运行凭据不可用，请联系 Skill 管理员”，不得要求普通用户提交 Token。
6. 将解析结果仅保存在当前执行上下文，继续阶段 1。

## 阶段 1：需求理解 + 接口契约定义

**触发时机**：配置检查通过后，自动执行。

Agent 执行以下操作（不停顿，不问用户）：

1. **分析用户需求**：理解用户想要什么功能
2. **拆解为前端功能点 + 后端接口**：
   - 前端需要什么页面、组件、交互
   - 后端需要什么接口、数据模型
3. **定义接口契约**：

接口契约格式（Agent 在内部生成，不展示给用户）：
```
接口路径: GET /api/xxx
功能描述: xxx
请求参数:
  - param1: type, 描述
返回字段:
  - field1: type, 描述
```

4. **直接进入阶段 2**，不停下来问用户

## 阶段 2：后端开发（全自动）

**触发时机**：接口契约定义完成后，自动执行。

### Step 2.0：确保沙箱就绪 + 预配置 Claude Code 权限

优先使用配置文档指定的沙箱，而不是任选一个运行中的沙箱：

1. 记 `sandboxId = 配置中的 sandbox.sandboxId`。
2. 执行 `sandbox status <sandboxId>` 确认处于 running 状态。
3. 若状态异常或无法连接：如果管理员在配置文档中提供了备用沙箱 ID，切换备用沙箱；否则告知用户"沙箱不可用，请联系管理员"并停止，不要静默换用无关沙箱。
4. 若无 `sandbox.sandboxId`（兼容旧配置），才回退到 `sandbox list --format json` 并选择一个运行中的沙箱。

沙箱就绪后，首次使用需执行以下初始化（后续复用跳过）：

1. **配置 Claude Code 自动权限**（关键步骤，否则 mc --code 无法自动写文件）：
   ```bash
   sandbox exec <sandboxId> 'cat > ~/.claude/settings.json << '"'"'EOF'"'"'
   {
     "permissions": {
       "allow": [
         "Bash(*)",
         "Write(*)",
         "Read(*)",
         "Edit(*)",
         "MultiEdit(*)",
         "Glob(*)",
         "Grep(*)"
       ]
     }
   }
   EOF'
   ```

2. **Git clone 代码仓库**（如果沙箱中尚无代码；从配置文档的 `repository.repoUrl` 和 `repository.defaultBranch` 取值）：
  ```bash
  sandbox exec <sandboxId> "git clone <repoUrl> <workspaceRoot>/<项目目录> && cd <workspaceRoot>/<项目目录> && git checkout <defaultBranch>"
  ```

   若配置中 `workflow.branchPrefix` 非空，优先在每个 NoCode 项目对应的独立分支上工作：
  ```bash
  sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && git checkout -B <branchPrefix><NoCode项目标识> <defaultBranch>"
  ```

3. **安装 Maven 依赖**（命令来自配置文档 `build.installCommand`）：
  ```bash
  sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && <installCommand>" --timeout 300000
  ```

### Step 2.1：mc --code 修改代码

将接口契约 + 实现指令传给 mc --code（沙箱内已预装 CatPaw CLI，自动代理 Claude Code）：

```bash
sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && mc --code '在 ProductController 中新增 GET /api/products 接口，返回字段 id/name/price/stock，支持分页参数 page 和 size，默认每页20条'" --timeout 600000
```

等待执行完成。mc --code 会自动修改代码文件，无需人工授权（已通过 settings.json 预配置权限）。

### Step 2.2：编译构建

```bash
sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && <buildCommand>" --timeout 300000
```

检查返回的 exitCode：
- **exitCode == 0**：编译成功，继续 Step 2.3
- **exitCode != 0**：编译失败，把 stderr 错误日志传给 mc --code 修复：
  ```bash
  sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && mc --code '编译报错了，错误信息如下：<stderr 内容>，请修复'" --timeout 600000
  ```
  然后重新编译。最多重试 3 次。3 次仍失败 → 告知用户错误信息，停止。

### Step 2.3：部署到 Cargo

```bash
sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && cargo deploy --app <cargo.appKey> --branch <cargo.branch>" --timeout 300000
```

- 部署成功 → 记录 Cargo 泳道域名，继续阶段 3
- 部署失败 → 重试 1 次，仍失败 → 告知用户

### Step 2.4（可选）：联调验证后端

```bash
sandbox exec <sandboxId> "curl -s http://localhost:8080/api/products" --timeout 30000
```

确认后端接口返回正常。如果不正常，把错误传给 mc --code 修复：
```bash
sandbox exec <sandboxId> "cd /home/user/project && mc --code '接口测试失败了，curl 返回非 200，请修复'" --timeout 600000
```

### 进入阶段 3

不停顿，直接进入前端开发。

## 阶段 3：前端开发（全自动）

**触发时机**：后端部署完成后，自动执行。

Agent 将接口契约 + Cargo API 地址组织为前端需求描述，通过 NoCode 能力生成前端：

### Step 3.1：生成前端页面

用自然语言描述前端需求给 NoCode Agent（包含接口信息）：

```
创建一个商品列表页面，展示商品名称、价格、库存。
数据来源：调用 GET https://xxx.test.sankuai.com/api/products 接口，
返回字段：id, name, price, stock。
支持分页，每页20条。
```

### Step 3.2：截图预览

```bash
nocode screenshot <chatId>
```

### Step 3.3：部署上线

```bash
nocode deploy <chatId>
```

获取前端访问地址。

### 进入阶段 4

不停顿，直接进入联调验证。

## 阶段 4：联调验证（全自动）

**触发时机**：前端部署完成后，自动执行。

### Step 4.1：验证后端 API

```bash
sandbox exec <sandboxId> "curl -s -o /dev/null -w '%{http_code}' https://xxx.test.sankuai.com/api/products" --timeout 30000
```

- HTTP 200 → 后端正常
- 非 200 → 排查问题，尝试修复

### Step 4.2：确认前端正常

通过截图确认前端页面正常渲染，数据正常展示。

### 进入阶段 5

不停顿，直接进入用户验收。

## 阶段 5：用户验收（用户参与）

**触发时机**：联调验证完成后，自动展示。

Agent 输出以下内容：

---

✅ 端到端开发完成，请验收：

**前端页面**：
- 截图预览：[截图]
- 访问地址：https://xxx.mynocode.host

**后端 API**：
- 接口地址：https://xxx.test.sankuai.com/api/products
- 接口文档：GET /api/products，返回 id, name, price, stock

**验收功能点**：
1. [ ] 商品列表页面正常展示
2. [ ] 商品名称、价格、库存正确显示
3. [ ] 分页功能正常
4. [ ] 前端成功调用后端 API

请确认功能是否符合预期：
- 回复 **"没问题"** → 我将提交代码并提 PR
- 回复 **具体问题** → 我将排查并修复

---

等待用户回复。

## 阶段 6：根据用户反馈处理

### 6a：用户回复"没问题"

**触发条件**：用户说"没问题"、"可以"、"OK"、"通过"等确认语。

自动执行：

```bash
# Git 提交（在配置文档指定的仓库与项目分支上）
sandbox exec <sandboxId> "cd <workspaceRoot>/<项目目录> && git add . && git commit -m 'feat: <需求摘要>' && git push" --timeout 60000
```

然后提 PR（根据团队实际方式，可能是 git push 触发 CI/CD，或调用 Code 平台 API）。

告知用户：
> ✅ 代码已提交并推送，PR 链接：xxx

流程结束。

### 6b：用户回复"有问题"

**触发条件**：用户描述了具体问题。

Agent 执行：
1. 分析用户描述的问题
2. 判断是前端问题还是后端问题
3. 前端问题 → 通过 NoCode 修复（回到阶段 3）
4. 后端问题 → 通过 mc --code 修复 → 重新编译 → 重新部署（回到阶段 2 的 Step 2.1）
5. 修复后重新走到阶段 5 验收

## 异常处理

| 异常场景 | 处理方式 |
| --- | --- |
| 沙箱操作返回错误 | `sandbox status <id>` 检查沙箱状态，如沙箱失联则自动创建新沙箱 + git clone 恢复代码 |
| mc --code 执行超时 | 重试 1 次，仍超时则告知用户 |
| 编译失败（3 次重试后） | 告知用户错误日志，停止流程 |
| 部署失败（1 次重试后） | 告知用户，停止流程 |
| 联调验证失败 | 自动排查并尝试修复，修复后重新验证 |
| git push 失败 | 告知用户，可能是权限问题 |
| NoCode 前端生成失败 | 告知用户，建议重试或调整需求描述 |

## 沙箱自动恢复机制

当 sandbox exec 返回错误时，先检查沙箱状态：

```bash
sandbox status <sandboxId>
```

如果沙箱状态异常或无法连接：
1. 创建新沙箱：
   ```bash
   sandbox create --permanent
   ```
2. 等待就绪：
   ```bash
   sandbox ready <newSandboxId>
   ```
3. 预配置 Claude Code 权限：
   ```bash
   sandbox exec <newSandboxId> 'cat > ~/.claude/settings.json << '"'"'EOF'"'"'
   {
     "permissions": {
       "allow": ["Bash(*)", "Write(*)", "Read(*)", "Edit(*)", "MultiEdit(*)", "Glob(*)", "Grep(*)"]
     }
   }
   EOF'
   ```
4. 恢复代码：
   ```bash
   sandbox exec <newSandboxId> "git clone $GIT_REPO_URL /home/user/project && cd /home/user/project && git checkout $GIT_BRANCH"
   ```
5. 安装依赖：
   ```bash
   sandbox exec <newSandboxId> "cd /home/user/project && mvn install -DskipTests" --timeout 300000
   ```
6. 更新 sandboxId，告知用户沙箱已恢复
7. 继续执行被打断的操作

## 进度反馈

在自动执行过程中，Agent 在关键节点输出简短进度信息：

- 📋 需求分析完成，定义接口契约：GET /api/products...
- 🔧 后端开发中：mc --code 正在修改代码...
- ✅ 后端代码修改完成，开始编译...
- ✅ 编译成功，部署到 Cargo...
- ✅ 后端已部署：https://xxx.test.sankuai.com/api/products
- 🎨 前端开发中：NoCode 生成页面...
- ✅ 前端已部署：https://xxx.mynocode.host
- 🔗 联调验证中...
- ✅ 联调通过，等待验收

这些进度信息帮助用户了解当前状态，但不需要用户回复。
