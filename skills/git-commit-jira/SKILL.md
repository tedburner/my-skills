---
name: git-commit-jira
description: >
  带 Jira ID 的规范化 Git 提交技能 — 根据当前分支改动生成 `<jira_id> <type> <总结>` 格式的
  commit message，支持 Jira ID 上下文推断、精准 type 推断、冲突与敏感信息拦截，并以选项菜单确认后提交或推送。
  当用户使用 Jira 单号提交代码（如 `/git-commit-jira AIME-123`、带 Jira/单号提交、按分支单号提交、公司规范 `<JIRA-ID> <type>` 提交）时使用；
  不要用于 git log、git blame、git diff 等只读查看。
---

# Git Commit（Jira）生成器

以生成 **简洁、准确、符合 `<jira_id> <type> <总结>` 规范的 commit message** 为核心，展示改动点、message 与提交范围后通过选项菜单确认。

---

## 使用方式

用户输入：`/git-commit-jira [jira_id] [type]`

- `jira_id`：Jira 任务编号（如 `AIME-123`），必需（未传时尝试从当前分支或近期提交推断候选）。
- `type`：提交类型（如 `feat`、`fix`、`refactor` 等），可选；未提供时自动推断。
- 若目标仓库 `AGENTS.md` / `CLAUDE.md` 或用户明确指定了细微变体（如 `<jira_id>: <type> ...`），以用户确认的仓库/公司规范为准。

---

## 执行流程

### 1. 分阶段读取状态与 Jira ID 解析

先执行轻量只读命令，同时获取工作区状态、分支名、近期提交与改动规模（避免一开始全量输出大型 lockfile diff）：

```bash
git status --short
git branch --show-current
git log -n 5 --oneline
git diff --stat
git diff --cached --stat
```

- **无未提交改动时的处理**：
  - 若工作区与暂存区均干净，但用户意图是**推送**（如“推代码”“帮我推一下”“推送”）：检查本地是否有领先远程的未推送提交；若有则展示待推送提交摘要与目标远端分支，经用户确认后跳至「6. 推送」执行，不以“无需提交”直接退出。
  - 若只是常规提交请求且无未提交改动，直接告知工作区干净、无需提交。
- **Jira ID 解析**：
  - 用户已提供 `jira_id`：自动将字母前缀规范为大写（如 `aime-123` → `AIME-123`）。
  - 用户未提供 `jira_id`：从 `git branch --show-current` 和 `git log -n 5 --oneline` 中提取候选单号（如 `[A-Za-z]+-\d+`）；找到明确候选时作为推荐 Jira ID 一并展示（可在确认阶段修改），未找到候选时请用户补充后再继续。

### 2. 读取核心改动与阻断检查

- **按需读取详细改动**：根据 `--stat` 跳过 lockfile（如 `package-lock.json`、`pnpm-lock.yaml`、`Cargo.lock`、`go.sum`）、自动生成物或大快照的全文输出，对核心代码与配置执行 `git diff` / `git diff --cached`。
- **未跟踪新文件（`??`）**：`git diff` 不包含未跟踪文件正文，必须读取其关键内容以提炼改动意图并检查敏感信息，不能只看文件名猜测。

#### 合并冲突阻断

若 `git status` 出现 `Unmerged paths`、`both modified`、`both added`、`deleted by us`、`deleted by them` 等冲突状态，立即暂停并提示先解决冲突并 `git add` 后重试（放弃合并/变基可用 `git merge --abort` 或 `git rebase --abort`）。

#### 敏感信息与噪声文件

同时检查文件名、diff 与 `??` 未跟踪文件正文是否包含明显敏感信息：
- `.env`、`.env.*`、`credentials`、`service-account`、`*.pem`、`*.key`、`*.p12`、`id_rsa`、`id_ed25519`
- 内容中明显的 `password`、`secret`、`api_key`、`token`、`aws_access_key`、`aws_secret_key` 或带密码的数据库连接串

发现风险时暂停，指出具体文件/片段并询问是否继续；未获明确确认前不继续提交。若存在 `.DS_Store`、IDE 临时目录或本地调试产物等疑似无关文件，在展示提交范围时单独标出提醒。

### 3. Type 推断与改动归纳

#### Type 推断规则（按“纯辅助改动优先排除，业务改动按核心意图”判断）

1. **纯辅助/配置类（仅当不含生产业务代码改动时才匹配）**：
   - 仅新增或修改测试文件（`*Test.*`、`*.test.*`、`test_*` 等）→ `test`
   - 仅修改文档文件（`README`、`*.md`、`docs/` 等）→ `docs`
   - 仅修改 CI/CD 配置（`.github/`、`.gitlab-ci.yml`、`Jenkinsfile` 等）→ `ci`
   - 仅修改构建/依赖配置（`pom.xml`、`build.gradle*`、`package.json` 等）→ `build`
   - 仅代码格式调整（缩进、空格、格式化，无语义变化）→ `style`
2. **包含生产代码改动时（配套单测和文档随主意图归并，不抢占为 `test`/`docs`）**：
   - 回滚历史提交 → `revert`
   - 修复错误、缺陷或线上异常 → `fix`
   - 性能优化为主 → `perf`
   - 新增功能、接口、模块或新能力 → `feat`
   - 不改变外部行为的代码重构、结构整理或纯删除清理 → `refactor`
3. 无法明确判断时默认 `feat`。

#### 提炼改动意图

- 同一需求的 Controller、Service、Entity/DTO、配置与配套测试合并为一条，控制正文为 1–3 条（不按文件逐个罗列）。
- 若多个互不相关的改动混在一起，提醒用户是否拆开提交。
- 混有已暂存与未暂存改动时，默认说明将提交全部改动；若用户指定只提交已暂存内容或部分文件，按指定范围执行。

### 4. 生成 commit message 并用选项菜单确认

#### 格式规范

- **标准多行格式**：
  ```text
  <jira_id> <type> <改动点总结>

  1. <关键改动 1>
  2. <关键改动 2>
  ```
- **小改动单行格式**（单一且改动很小时，不硬凑多条）：
  ```text
  <jira_id> <type> <简洁总结>
  ```

#### 写法与示例对照

描述“做了什么/解决什么”，避免堆砌方法名、路径或参数细节；不写“修改若干文件”等空泛词：

```text
❌ 1. 新增 UserService 处理用户登录、注册、权限校验等逻辑，新增 UserController 暴露 /api/v1/user/register
✅ 1. 新增用户注册与登录鉴权服务
✅ 2. 暴露用户管理与认证接口
```

完整示例：

```text
AIME-18505 perf 优化 LangChain 查询性能

1. 使用 MongoDB 聚合查询替代逐条明细查询
2. 新增 Caffeine 本地缓存并完善异常日志
```

展示生成的 commit message（若推荐了推断的 `jira_id` 或 `type` 一并说明）以及本次将暂存/提交的文件摘要后，提供以下四项操作（先输出摘要与 message，再于同一轮直接弹出选择，不要只输出一句“请选择”而留空）：

- 仅提交 — 按展示范围完成本地提交
- 提交并推送 — 本地提交后检查远程并推送当前分支（若高优全局规则要求提交后单独确认推送，则本地提交后再确认一次）
- 继续修改 — 按反馈调整 Jira ID、type、描述或提交范围
- 取消 — 不做任何操作

**交互选择规则**：
- 若当前环境提供交互式单选工具（如 `ask_question`、`AskUserQuestion`、`request_user_input` 等）且允许使用，**必须在展示 message 与提交范围的同一轮直接调用该工具**，将上述四项作为单选选项传入并等待用户点击选择（若工具 UI 会自动编号，选项文本不要重复带 `1. 2.`）。
- 仅当环境没有可用单选工具、当前模式禁止调用、或调用失败时，才回退为在对话正文中完整列出 `1.`–`4.` 编号选项并等待用户文字回复。
- 不得把默认选中、超时或未回复当作授权；在用户通过菜单确认前，不执行 `git add`、`git commit` 或 `git push`。初始请求中的“帮我提交”仅代表启动流程，不跳过展示确认。
- **推送授权兼容**：默认「提交并推送」同时授权本地提交与推送；若当前会话存在更高优先级的用户全局规则明确要求“完成本地提交后须单独等待确认才可推送”，则遵从高优规则（本地提交完成后汇报 hash，再单独请用户确认推送）。

### 5. 暂存并提交

用户确认提交后，按确认范围暂存（默认全部改动 `git add -A`；指定部分文件 `git add <file1> ...`；仅提交已暂存内容时不额外 `git add`）：

```bash
git add -A
git status --short
```

- 若暂存时出现未说明的新文件、提交范围变化或敏感信息，即使已确认也要暂停并重新确认。
- 多行 commit message **必须使用多个 `-m`**，避免换行和反引号在 shell 中转义异常：

```bash
git commit -m "AIME-18505 perf 优化 LangChain 查询性能" -m "1. 使用 MongoDB 聚合查询替代逐条明细查询" -m "2. 新增 Caffeine 本地缓存并完善异常日志"
```

- 如果 `pre-commit`、`commit-msg` 等 Git hook 执行失败，暂停并原样报告错误，**禁止使用 `--no-verify` 绕过**。

提交成功后反馈：commit hash、分支名与 commit message。

### 6. 推送（当用户授权推送时）

执行推送前（若受高优全局规则约束尚未单独确认推送，须先请用户确认是否推送当前提交），先以跨平台安全方式检查当前分支与跟踪上游：

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name "@{u}"
```

> **跨平台注意**：务必给 `"@{u}"` 加上双引号（防止 Windows PowerShell 将未加引号的 `@{u}` 解析为哈希表字面量报错），且不要拼接 bash 专属的 `2>/dev/null || true`。若 `git rev-parse` 返回非零退出码，即代表当前分支尚未配置跟踪上游，按下方“未配置跟踪上游”处理。

- **Detached HEAD**（`git branch --show-current` 为空）：暂停推送，提示先切回或创建目标分支。
- **已配置跟踪上游**（记为 `<remote>/<upstream_branch>`）：执行 `git fetch <remote>` 与 `git rev-list --left-right --count "@{u}...HEAD"`：
  - `0 N`（`N > 0`）：执行 `git push <remote> HEAD:<upstream_branch>`（同名即 `git push <remote> <branch>`）。
  - `0 0`：本地与远程一致，无需 push。
  - `M N` 或 `M 0`（`M > 0`）：远程有新提交，暂停 push，提示先执行 `git pull --rebase <remote> <upstream_branch>`。
- **未配置跟踪上游**：先 `git fetch origin` 并检查 `origin/<branch>`；存在则按 `origin/<branch>...HEAD` 检查分歧（无分歧后 `git push -u origin <branch>`），不存在则直接 `git push -u origin <branch>`。
- 获取远程状态或分歧检查失败时，说明原因并暂停。

若只选择了「仅提交」，提交后告知：如需推送，直接说“推送”即可，无需重新确认 message。

---

## Type 类型参考

| Type | 说明 | 使用场景 |
|------|------|----------|
| `feat` | 新功能 | 新增功能、接口、模块（含配套单测/文档） |
| `fix` | Bug 修复 | 修复错误、缺陷（含配套回归测试） |
| `perf` | 性能优化 | 性能优化相关改动 |
| `refactor` | 重构 | 不改变外部行为的重构、结构整理或纯删除清理 |
| `docs` | 文档变更 | 仅 README、注释、文档更新 |
| `test` | 测试 | 仅新增或修改测试用例（无生产代码改动） |
| `style` | 代码格式 | 仅格式化、缩进、空白等无语义调整 |
| `build` | 构建 | 仅依赖管理、构建配置变更 |
| `ci` | CI/CD | 仅流水线、CI 脚本配置变更 |
| `revert` | 回滚 | 撤销之前的提交 |
