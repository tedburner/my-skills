# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

---

## 仓库概述

这是一个 **Codex Skills 个人仓库**，用于存储和管理自定义技能（Skills）配置。每个技能可以通过 `/技能名` 命令在 Codex 中触发。

---

## 技能结构

### 目录规范

```
skills/<技能名>/
├── SKILL.md           # 技能定义和执行流程（必需）
└── references/        # 参考资料（可选）
    └── *.md           # 技能相关的参考文档
```

### 当前技能

| 技能 | 命令 | 说明 |
|------|------|------|
| Git Commit 生成器 | `/git-commit` | 分析代码改动，生成带 Gitmoji 的 commit message，选项式一次确认后直接提交或提交并推送 |
| Git Commit（Jira）生成器 | `/git-commit-jira` | 生成带 Jira ID 和 type 的 commit message，选项式一次确认后直接提交或提交并推送 |
| Repo 架构图生成器 | `/repo-architecture-flow` | 分析仓库结构并生成 Mermaid 架构图，支持导出 SVG/PNG/PDF |
| Shipyard 技术方案流程 | `/shipyard` | Spec 驱动开发全流程：概要设计 → 详细设计 → 任务拆解 → 逐任务实施，状态落盘、跨会话可恢复 |

---

## Git Commit 技能要点

触发命令：`/git-commit`

**执行流程**：
1. 分析改动 → `git status`, `git diff`, `git diff --cached`
2. 提交前阻断检查 → 合并冲突、敏感文件（.env, credentials, *.key 等）和敏感代码模式（password, secret, api_key 等）
3. 生成 commit message → 格式：`:emoji-name: 改动总结` + 编号列表，同时展示将暂存的文件摘要
4. 选项菜单 → 仅提交 / 提交并推送 / 继续修改 / 取消，用户选择后直接执行，不再重复确认
5. 执行 → `git add -A` + `git commit`（多行 message 用多个 `-m`）；选「提交并推送」时先检查远程分歧再 push
6. 防线 → 暂存范围变化或敏感信息时暂停重确认；远程有新提交时暂停 push 并提示先 pull --rebase

**Gitmoji 映射**：完整参考见 `skills/git-commit/references/gitmojis.md`

---

## 常用命令

```bash
# 查看技能列表
ls -d skills/*/

# 查看技能定义
cat skills/<技能名>/SKILL.md
```

---

## 开发规范

### 新增/更新技能后

**必须同步更新 `README.md` 中的技能列表表格**，保持以下字段一致：

| 字段 | 说明 |
|------|------|
| 技能名称 | 技能的中文/英文名称 |
| 命令 | 触发命令，如 `/git-commit` |
| 说明 | 一句话描述技能功能 |

**示例**：
```markdown
| 技能名称 | 命令 | 说明 |
|----------|------|------|
| Git Commit 生成器 | `/git-commit` | 自动分析代码改动，生成规范化的 git commit message |
| 新技能 | `/new-skill` | 新技能的功能描述 |
```
