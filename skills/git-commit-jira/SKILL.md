---
name: git-commit-jira
description: "安全高效的Git提交技能 - 根据当前分支改动生成commit message，支持参数验证、智能type推断、冲突预防；展示改动点、message 与提交范围后以选项菜单一次确认，选择后直接提交或提交并推送"
---

# Git Commit 生成器

根据当前分支改动生成 git commit 内容，改动点、commit message 与提交范围展示后，通过选项菜单一次确认，选择后直接执行。

## 使用方式

用户输入：`/git-commit-jira <jira_id> <type>`

例如：
- `/git-commit-jira AIME-123 feat`
- `/git-commit-jira JIRA-456 fix`
- `/git-commit-jira PROJ-789 refactor`

如果用户忘记提供 Jira ID 或 type，技能会引导用户补充输入。

## 执行流程

### 阶段 1：参数解析与验证

首先检查用户是否提供了必需的参数：
- **jira_id**: Jira 任务 ID（如 AIME-123）- **必需**
- **type**: 提交类型（如 feat、fix 等）- **可选**

**参数处理逻辑**：

1. **如果缺少 jira_id**：
   - 礼貌地告知用户需要提供 Jira ID
   - 请用户补充提供
   - 用户补充后，继续执行后续步骤

2. **如果提供了 jira_id 但缺少 type**：
   - 告知用户将根据改动内容自动推断 type
   - 进入阶段 2 分析改动后，根据以下规则自动推断 type

**Type 自动推断规则**（按优先级判断）：

| 改动特征 | 推断 type |
|----------|----------|
| 新增文件以 `*Test.java`、`*.test.*`、`test_*` 等结尾 | `test` |
| 只修改了文档文件（README、*.md、docs/） | `docs` |
| 只修改了 CI/CD 配置（.github/、.gitlab-ci.yml、Jenkinsfile 等） | `ci` |
| 只修改了构建配置（pom.xml、build.gradle、package.json 等） | `build` |
| 删除文件为主 | `refactor` |
| 代码中新增类、方法、接口 | `feat` |
| 代码中包含修复、修复 bug 相关关键字 | `fix` |
| 仅代码格式调整（缩进、空格、格式化） | `style` |
| 不改变功能的代码重构 | `refactor` |
| 性能相关优化 | `perf` |

- 如果无法明确判断，默认使用 `feat`
- 推断出的 type 会展示给用户，用户可以要求修改

---

### 阶段 2：分析改动并列出改动点

执行命令分析当前工作状态：

```bash
# 查看工作状态
git status

# 查看未暂存的改动内容
git diff

# 如果已有暂存文件，也查看暂存的改动
git diff --cached
```

**输出改动点列表**，按**功能模块**分组展示（关键：将多个文件的相关改动归类到同一功能点）：

```
【当前分支改动分析】

改动的文件：
- src/main/java/UserService.java
- src/test/java/UserServiceTest.java
- src/main/java/UserController.java
- README.md

改动点总结（按功能归类，同一功能涉及的文件合并为一点）：
1. 新增用户管理模块（UserService、UserController）
2. 补充用户管理模块单元测试（UserServiceTest）
3. 更新 README 文档

【推断的提交类型】feat
```

**归类原则**：
- 同一功能/需求涉及的多个文件改动，合并为一条
- 例如：Service + Controller + DTO 都属于同一功能，归为一点
- 例如：主代码 + 对应测试文件，如测试是配套新增的，可合并；如测试是独立补充的，单独列出
- 跨模块的改动，按模块分组

**改动点与 type 的确认合并到阶段 3 的选项菜单中**：此处不做单独确认，改动点列表和推断的 type 会连同 commit message、将暂存的文件摘要一起展示，用户通过选项菜单一次决策；如需调整改动点或 type，选择「继续修改」并说明即可。

---

### 阶段 3：生成 commit message 并用选项菜单确认

根据确认后的改动点和 type 生成 commit message：

**格式**：
```
<jira_id> <type> <改动点总结>

1. <改动点 1>
2. <改动点 2>
3. <改动点 3>
```

**简洁化原则**：
- **改动点数量**：控制在 2-4 条，不要列出所有文件
- **抽象层次**：描述"做了什么"，而不是"怎么做的"
- **避免细节**：不要写具体方法名、参数、实现逻辑
- **合并同类**：同一功能的多个文件改动合并为一条
- **突出重点**：关注核心功能或优化效果

**错误示例**（过于详细）：
```
❌ 1. 新增 UserService 处理用户业务逻辑（注册、登录、权限校验）
❌ 2. 新增 UserController 提供 REST API 接口（/api/v1/user/register、/api/v1/user/login）
❌ 3. 新增 UserDTO 和 UserVO 数据传输对象，包含 username、password、email 等字段
```

**正确示例**（简洁明了）：
```
✅ 1. 新增用户业务逻辑层
✅ 2. 新增用户 REST API 接口
✅ 3. 新增用户数据传输对象
```

**示例 1**（性能优化 - perf）：
```
AIME-18505 perf LangChain查询性能优化

1. MongoDB 聚合查询替代明细查询，性能大幅提升
2. 新增 Caffeine Cache 本地缓存配置
3. 完善异常处理和日志记录
```

**示例 2**（新功能 - feat，简洁风格）：
```
AIME-18505 feat 风控敏感词趋势图接口

1. 新增趋势图数据转换方法
2. 新增趋势图查询接口
```

**示例 3**（新功能 - feat，多个改动）：
```
AIME-18505 feat 风控看板服务合并及敏感词统计功能

1. 合并风控统计服务到看板服务
2. 新增敏感词统计实体和定时任务
3. 优化 DTO/VO 字段结构
```

**示例 4**（Bug 修复 - fix）：
```
AIME-18432 fix 修复用户登录验证问题

1. 修复 Token 过期导致的登录失败
2. 添加登录失败次数限制
```

**展示 commit message 并用选项菜单一次确认**：

展示 commit message 时，同时列出改动点总结、推断的 type 和将暂存的文件摘要，然后给出以下选项：

```
【生成的 commit message】
AIME-18432 feat 新增用户管理模块

1. 新增 UserService 处理用户业务逻辑
2. 添加 UserController 提供 REST API 接口
3. 补充单元测试覆盖核心功能

【将暂存的文件】
- src/main/java/UserService.java
- src/main/java/UserController.java
- src/test/java/UserServiceTest.java

请选择后续操作：
1. 仅提交 — 暂存全部改动并完成本地提交
2. 提交并推送 — 本地提交后检查远程并推送当前分支
3. 继续修改 — 按反馈调整改动点、type 或描述后重新生成
4. 取消 — 不做任何操作
```

**选择方式**：先检查当前运行环境可用的交互工具及其使用限制。若有允许用于本次提交授权的选项组件，优先通过该工具展示上述四项并等待用户选择；工具名称和参数以当前环境为准，不假定一定存在 `AskUserQuestion`。若组件无法同时完整展示四项或可靠返回选择、没有合适的组件、当前模式不允许用于授权，或调用失败，则在对话中列出相同的编号选项并等待用户文字回复。不得使用不允许用于授权的工具，也不能把默认选中、超时或未回复当作授权。

**用户选择处理**：

1. **仅提交 / 提交并推送**：直接进入阶段 4（暂存并提交），不再重复确认。
2. **继续修改**：按用户反馈调整改动点、type 或描述，重新生成 commit message 后再次展示选项菜单。
3. **取消**：终止流程，不执行任何 git 操作。

**重要**：在用户通过选项菜单确认之前，不要执行任何 git add 或 git commit 命令。初始请求中的"帮我提交""提交一下"只表示启动流程，不能跳过本阶段的选项菜单。

---

### 阶段 4：暂存并提交

用户选择「仅提交」或「提交并推送」后，执行暂存：

```bash
git add -A
```

或者根据用户需求暂存特定文件：
```bash
git add <file1> <file2>
```

展示已暂存的文件列表，然后直接执行提交，不再重复确认：

```bash
git commit -m "<commit message>"
```

- 如果暂存时出现未说明的新文件、提交范围变化、敏感文件或其他风险，即使用户已选择提交/推送也要暂停并重新确认。
- 用户选「取消」时不暂存、不提交。

提交后展示结果：
- 提交是否成功
- 提交的简要信息（分支、文件数、commit hash 等）

---

### 阶段 5：推送前冲突预防检测（仅当用户选择「提交并推送」）

本地提交成功后先 `git fetch origin`，检查当前分支对应的远程分支和分歧：

```bash
git branch --show-current
git rev-list --left-right --count origin/<current-branch>...<current-branch>
```

- 远程分支存在且无远程新提交：继续推送；双方一致则无需推送。
- 远程有新提交：暂停推送，提示用户先同步并解决可能的冲突；不自动执行 rebase 或强推。
- 远程分支不存在：进入阶段 6，按新分支方式设置上游。
- 获取远程状态或分歧检查失败：说明原因并暂停，不将失败当成可以推送。

### 阶段 6：推送到远程

用户已在选项菜单中选择「提交并推送」，此处直接执行，不再询问：

```bash
git push origin <current-branch>
```

如果远程分支不存在，执行以下命令设置上游分支：
```bash
git push -u origin <current-branch>
```

若用户只选择了「仅提交」，提交后告知一句：如需推送，直接说"推送"即可，无需重新确认 commit message。

---

## Type 类型参考

| Type | 说明 | 使用场景 |
|------|------|----------|
| feat | 新功能 | 新增功能、接口、模块 |
| fix | Bug 修复 | 修复错误、缺陷 |
| docs | 文档变更 | README、注释、文档更新 |
| style | 代码格式 | 格式化、缩进、分号等不影响代码含义的改动 |
| refactor | 重构 | 代码重构、逻辑优化、不改变外部行为 |
| ci | CI/CD | 构建脚本、流水线配置变更 |
| test | 测试 | 新增或修改测试用例 |
| build | 构建 | 依赖管理、构建配置、pom.xml 等 |
| perf | 性能 | 性能优化相关改动 |
| revert | 回滚 | 撤销之前的提交 |

---

## 注意事项

- **一次确认**：改动点、type、commit message 和提交范围通过阶段 3 的选项菜单一次确认；选择后直接执行，不重复询问
- **敏感文件检查**：如发现 .env、credentials 等文件，提醒用户检查
- **无改动处理**：如工作目录干净，告知用户没有待提交的改动
- **灵活调整**：用户可以在任何阶段要求修改或取消
