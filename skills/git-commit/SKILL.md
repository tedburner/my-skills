---
name: git-commit
description: >
  Git Commit 生成器 — 以生成简洁、准确的 Gitmoji commit message 为核心，分析当前改动并在用户确认后提交。
  当用户想要提交代码、生成 commit message、提交改动、解决提交前冲突、或提交后推送时使用。
  触发词包括但不限于：提交代码、git commit、commit、提交一下、帮我提交、生成commit、
  提交改动、保存改动、推代码、发commit、写commit message、提交并推送。
  即使用户只是说"提交"或"帮我推一下"，只要上下文涉及代码改动的 git 提交，都应该触发。
  不要用于查看 git log、git blame、git diff 等只读操作。
---

# Git Commit 生成器

这个技能的核心产物是 **简洁、准确、可直接使用的 commit message**。

先快速确认工作区是否可提交，再把主要精力放在提炼改动意图。除非发现风险，不要输出大段操作教程。

---

## 总原则

- Commit message 优先表达"为什么/做了什么"，不要堆文件清单。
- 标题要短，一眼能看懂；body 只保留关键改动。
- 小改动可以只有标题，不强行写编号列表。
- 用户确认 commit message 前，不执行 `git add` 或 `git commit`。
- 冲突、安全风险、远程分歧只做必要提示；提示要短，并给出下一步。

---

## 执行流程

### 1. 快速读取状态

执行最少命令了解当前状态：

```bash
git status --short
git status
git diff
git diff --cached
```

如果工作区没有未提交改动，直接告知用户无需提交。

### 2. 提交前阻断检查

先检查两类会影响提交安全性的情况。

#### 合并冲突

如 `git status` 出现 `Unmerged paths`、`both modified`、`both added`、`deleted by us`、`deleted by them` 等冲突状态，停止提交流程。

输出保持简短：

```text
检测到未解决冲突，先暂停提交。

冲突文件：
- path/to/file

请先解决冲突并 git add 已解决文件，然后再重新执行 /git-commit。
如需放弃当前合并/变基，可使用 git merge --abort 或 git rebase --abort。
```

#### 敏感信息

检查文件名和 diff 中是否出现明显敏感信息：

- `.env`、`.env.*`
- `credentials`、`service-account`
- `*.pem`、`*.key`、`*.p12`
- `id_rsa`、`id_ed25519`
- `password`、`secret`、`api_key`、`token`
- `aws_access_key`、`aws_secret_key`
- 带密码的数据库连接串

发现风险时暂停，指出具体文件/片段，并询问用户是否继续。只有用户明确确认后才能继续。

### 3. 提炼改动意图

把 diff 归纳成 1-3 个核心改动点，按"用户能从提交历史读懂什么"来写，不按文件逐个罗列。

归纳规则：

- 同一需求涉及的主代码、测试、配置，合并成一条。
- 只写结果和意图，不写琐碎实现步骤。
- 多个互不相关的改动要提醒用户考虑拆分提交。
- 如果已暂存和未暂存改动混在一起，说明当前将默认提交全部改动；用户可指定只提交部分文件。

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

- 标题优先控制在 30 个中文字符左右。
- body 控制在 1-3 条；超过 3 条时先考虑是否应该拆分提交。
- 不写"修改若干文件"、"优化代码"这类空泛描述。
- 不把测试、格式化、依赖升级写进标题，除非它们是本次提交的核心。
- Gitmoji 使用 `:name:` 格式。

#### Gitmoji 选择

优先按改动意图选择。完整映射见 [`references/gitmoji-mapping.md`](references/gitmoji-mapping.md) 和 [`references/gitmojis.md`](references/gitmojis.md)。

常用映射：

| 场景 | Gitmoji |
|------|---------|
| 新功能 | `:sparkles:` |
| Bug 修复 | `:bug:` |
| 文档/技能说明 | `:memo:` |
| 重构/流程整理 | `:recycle:` |
| 测试 | `:white_check_mark:` |
| 配置 | `:wrench:` |
| 依赖升级 | `:arrow_up:` |
| 删除 | `:fire:` |
| 安全 | `:lock:` |

展示 commit message 后询问用户是否确认。用户不满意时，根据用户反馈重写，不要争辩。

### 5. 暂存并提交

用户确认 commit message 后再执行：

```bash
git add -A
git status --short
```

展示将要提交的文件摘要，并确认是否继续。

用户确认后执行提交。多行 commit message 使用多个 `-m`，避免依赖特定 shell 的换行引用行为：

```bash
git commit -m ":memo: 精简 git-commit 技能流程" -m "1. 聚焦生成简洁 commit message" -m "2. 压缩冲突、安全检查和 push 提示"
```

提交成功后反馈：

- commit hash
- 分支名
- commit message

### 6. 可选 push

提交成功后询问是否推送。用户选择推送时，先做远程状态检查：

```bash
git fetch origin
git branch --show-current
git rev-list --left-right --count origin/<branch>...<branch>
```

处理规则：

- `0 N`：本地领先，可直接 `git push origin <branch>`。
- `0 0`：本地与远程一致，无需 push。
- `M N` 或 `M 0`：远程有新提交，暂停 push，提示用户先 pull/rebase。
- 如果远程分支不存在，使用 `git push -u origin <branch>`。

远程分歧提示保持简短：

```text
远程分支有新提交，先暂停 push。

建议先执行：
git pull --rebase origin <branch>

解决可能的冲突后，再重新 push。
```

---

## 输出风格

- 先给 commit message，再给简短理由。
- 不输出完整 diff 内容，除非用户要求。
- 不做长篇 Git 教程；只给当前下一步。
- 所有确认问题都围绕实际决策：message 是否可用、是否提交、是否 push。
