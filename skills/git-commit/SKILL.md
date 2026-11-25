---
name: git-commit
description: >
  Git Commit 生成器 — 以生成简洁、准确的 Gitmoji commit message 为核心，分析当前改动；
  展示 message 与提交范围后提供选项菜单（仅提交 / 提交并推送 / 继续修改 / 取消），用户选择后执行。
  当用户想要提交代码、生成 commit message、提交改动、解决提交前冲突、或提交后推送时使用。
  触发词包括但不限于：提交代码、git commit、commit、提交一下、帮我提交、生成commit、
  提交改动、保存改动、推代码、发commit、写commit message、提交并推送。
  即使用户只是说"提交"或"帮我推一下"，只要上下文涉及代码提交或本地提交推送都可触发；
  若用户显式给出 Jira 单号或要求按 Jira 规范提交则优先使用 git-commit-jira；不要用于 git log、git blame、git diff 等只读查看。
---

# Git Commit 生成器

这个技能的核心产物是 **简洁、准确、可直接使用的 commit message**。

先快速确认工作区状态与仓库既有提交规范，再把主要精力放在提炼改动意图。除非发现风险，不要输出大段操作教程。

---

## 总原则

- Commit message 优先表达"为什么/做了什么"，不要堆文件清单；标题简短一眼能懂，小改动可只写单行标题。
- **尊重公司与仓库规范优先级**：默认生成 `:gitmoji:` 格式；若用户全局规则、仓库 `AGENTS.md` / `CLAUDE.md` 或近期 `git log` 已固定公司/项目提交规范（如 `<JIRA-ID> <type> <总结>` 或 Conventional Commits），或当前分支名含明确 Jira 单号且近期提交遵循 Jira 格式，优先沿用该规范并在展示时一句话说明。
- 用户确认 commit message 与暂存范围前，不执行 `git add`、`git commit` 或 `git push`。
- message 与提交范围展示后，用选项菜单让用户一次决策：仅提交 / 提交并推送 / 继续修改 / 取消。
- **推送授权规则**：仅选择「仅提交」时不得自动推送；用户在确认菜单中明确选择「提交并推送」即视为已同时授权本地提交与推送，本地提交成功后直接检查远端并推送，无需二次追问。远程有分歧时一律暂停提示，不强推。
- 冲突、安全风险、远程分歧或 hook 失败只做简短提示并给出下一步。

---

## 执行流程

### 1. 分阶段读取状态与仓库上下文

先执行轻量只读命令了解工作区、当前分支与近期提交风格，避免一上来把巨型 lockfile 全量 diff 打入上下文：

```bash
git status --short
git branch --show-current
git log -n 5 --oneline
git diff --stat
git diff --cached --stat
```

- **无未提交改动时的处理**：
  - 若工作区与暂存区均干净，但用户的请求意图是**推送**（如“推代码”“帮我推一下”“推送”）：不要以“无需提交”直接结束，直接跳到「6. 推送」前检查本地是否有领先远程的未推送提交；若有则展示待推送提交摘要与目标远端分支，经用户确认后执行推送；若本地与远程一致再告知无需推送。
  - 若只是常规提交请求且无任何未提交改动，直接告知工作区干净、无需提交。
- **按需读取详细改动**：根据 `--stat` 跳过 lockfile（如 `package-lock.json`、`pnpm-lock.yaml`、`Cargo.lock`、`go.sum`）、自动生成物或大快照的全文输出，对核心源码与配置文件执行 `git diff` / `git diff --cached`。
- **未跟踪新文件（`??`）**：`git diff` 不包含未跟踪文件正文，必须读取其关键内容以提炼改动意图并扫描敏感信息，不要只凭文件名猜测。

### 2. 提交前阻断检查

#### 合并冲突

如 `git status` 出现 `Unmerged paths`、`both modified`、`both added`、`deleted by us`、`deleted by them` 等冲突状态，停止提交流程：

```text
检测到未解决冲突，先暂停提交。

冲突文件：
- path/to/file

请先解决冲突并 git add 已解决文件，然后再重新执行 /git-commit。
如需放弃当前合并/变基，可使用 git merge --abort 或 git rebase --abort。
```

#### 敏感信息与噪声文件

检查文件名、diff 以及 `??` 未跟踪新文件中是否出现明显敏感信息：

- `.env`、`.env.*`、`credentials`、`service-account`、`*.pem`、`*.key`、`*.p12`、`id_rsa`、`id_ed25519`
- `password`、`secret`、`api_key`、`token`、`aws_access_key`、`aws_secret_key` 或带密码的数据库连接串

发现敏感信息风险时暂停，指出具体文件/片段并询问用户是否继续；只有用户明确确认后才能继续。

若工作区包含 `.DS_Store`、IDE 临时目录或本地调试产物等疑似无关的未跟踪文件，在展示提交范围时单独标出，提醒用户是否排除。

### 3. 提炼改动意图

把 diff（含已读取的 `??` 新文件）归纳成 1–3 个核心改动点，按"用户能从提交历史读懂什么"来写，不按文件逐个罗列：

- 同一需求涉及的主代码、测试、配置合并成一条，只写结果与意图。
- 多个互不相关的改动提醒用户考虑拆分提交。
- 如果已暂存和未暂存改动混在一起，默认说明将提交全部改动；若用户手动暂存了部分文件并要求只提交已暂存内容，或指定排除部分文件，按指定范围执行。

输出示例：

```text
我看到这次改动主要是：
1. 简化 git-commit 技能流程，让 commit message 成为核心产物
2. 保留冲突、安全检查和 push 前同步检查，但压缩提示噪音

建议使用 :memo:。
```

### 4. 生成 commit message

#### 默认格式

```text
:emoji-name: 简洁标题

1. 关键改动
2. 关键改动
```

#### 小改动格式

如果改动很小，只输出一行：

```text
:memo: 精简 git-commit 技能流程
```

#### 写法约束

- 标题优先控制在 30 个中文字符左右；body 控制在 1–3 条，超过 3 条时先考虑是否拆分提交。
- 不写"修改若干文件"、"优化代码"这类空泛描述。
- 不把测试、格式化、依赖升级写进标题，除非它们是本次提交的核心。
- Gitmoji 默认使用 `:name:` 格式（若仓库/用户规范要求其他格式，从其规范）。

#### Gitmoji 选择

优先按改动意图选择。完整映射见 [`references/gitmoji-mapping.md`](references/gitmoji-mapping.md) 和 [`references/gitmojis.md`](references/gitmojis.md)。

| 场景 | Gitmoji |
|------|---------|
| 新功能 | `:sparkles:` |
| Bug 修复 | `:bug:` |
| 性能优化 | `:zap:` |
| 文档/技能说明 | `:memo:` |
| 重构/流程整理 | `:recycle:` |
| 测试 | `:white_check_mark:` |
| 配置 | `:wrench:` |
| 依赖升级 | `:arrow_up:` |
| 删除 | `:fire:` |
| 安全 | `:lock:` |

展示 commit message 时，同时列出本次将暂存/提交的文件摘要，然后提供以下操作（先输出摘要与 message，再于同一轮直接弹出选择，不要只输出一句“请选择”而留空）：

- 仅提交 — 按展示范围完成本地提交
- 提交并推送 — 本地提交成功后直接检查远程并推送当前分支
- 继续修改 — 按反馈重写 message 或调整提交范围
- 取消 — 不做任何操作

**交互选择规则**：
- 若当前环境提供交互式单选工具（如 `ask_question`、`AskUserQuestion`、`request_user_input` 等）且允许使用，**必须在展示 message 与提交范围的同一轮直接调用该工具**，将上述四项作为单选选项传入并等待用户点击选择（若工具 UI 会自动编号，选项文本不要重复带 `1. 2.`）。
- 仅当环境没有可用单选工具、当前模式禁止调用、或调用失败时，才回退为在对话正文中完整列出 `1.`–`4.` 编号选项并等待用户文字回复。
- 不得把默认选中、超时或未回复当作授权。初始请求中的“帮我提交”“提交一下”只表示启动流程，不能跳过展示确认；用户选「继续修改」时按反馈重写，不要争辩。

### 5. 暂存并提交

用户确认提交后，按确认范围执行暂存（默认全部改动 `git add -A`；指定部分文件 `git add <file1> ...`；仅提交已暂存内容时不额外 `git add`）：

```bash
git add -A
git status --short
```

- 如果暂存时出现未说明的新文件、提交范围变化、敏感信息或其他风险，立即暂停并重新确认。
- 用户选「取消」时不暂存、不提交。
- 多行 commit message 使用多个 `-m`，避免依赖特定 shell 的换行引用或反引号转义：

```bash
git commit -m ":memo: 精简 git-commit 技能流程" -m "1. 聚焦生成简洁 commit message" -m "2. 压缩冲突、安全检查和 push 提示"
```

- 如果仓库配置了 `pre-commit`、`commit-msg` 等 Git hook 并导致提交失败，暂停并原样报告 hook 错误，**禁止使用 `--no-verify` 绕过**。

提交成功后反馈：commit hash、分支名与 commit message。

### 6. 推送（当用户授权推送时）

用户选择「提交并推送」（或在已提交后明确要求推送）时，先以跨平台安全方式检查当前分支与跟踪上游：

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name "@{u}"
```

> **跨平台注意**：务必给 `"@{u}"` 加上双引号（防止 Windows PowerShell 将未加引号的 `@{u}` 解析为哈希表字面量报错），且不要拼接 bash 专属的 `2>/dev/null || true`。若 `git rev-parse` 返回非零退出码，即代表当前分支尚未配置跟踪上游，直接走下方“未配置跟踪上游”分支。

- **Detached HEAD**（`git branch --show-current` 为空）：暂停推送，提示用户先切回或创建目标分支。
- **已配置跟踪上游**（记为 `<remote>/<upstream_branch>`）：执行 `git fetch <remote>` 与 `git rev-list --left-right --count "@{u}...HEAD"`：
  - `0 N`（`N > 0`）：本地领先，执行 `git push <remote> HEAD:<upstream_branch>`（同名时即 `git push <remote> <branch>`）。
  - `0 0`：本地与远程一致，无需 push。
  - `M N` 或 `M 0`（`M > 0`）：远程有新提交，暂停 push，提示用户先 `git pull --rebase <remote> <upstream_branch>`。
- **未配置跟踪上游**：先 `git fetch origin` 并检查 `origin/<branch>` 是否存在：
  - 远端存在同名分支时先按 `origin/<branch>...HEAD` 检查分歧，无分歧再用 `git push -u origin <branch>`，有分歧则暂停提示先 pull/rebase。
  - 远端分支不存在时，直接 `git push -u origin <branch>`。
- 获取远程状态或分歧检查失败时，说明原因并暂停。

远程分歧提示保持简短：

```text
远程分支有新提交，先暂停 push。

建议先执行：
git pull --rebase <remote> <upstream_branch>

解决可能的冲突后，再重新 push。
```

若用户只选择了「仅提交」，提交后告知一句：如需推送，直接说“推送”即可，无需重新确认 message。

---

## 输出风格

- 先给 commit message，再给简短理由。
- 不输出完整 diff 内容，除非用户要求。
- 不做长篇 Git 教程；只给当前下一步。
