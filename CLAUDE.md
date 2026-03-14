# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 仓库概述

这是一个 **Claude Code Skills 个人仓库**，用于存储和管理自定义技能（Skills）配置。每个技能可以通过 `/技能名` 命令在 Claude Code 中触发。

---

## 技能结构

### 目录规范

```
<技能名>/
├── skill.md           # 技能定义和执行流程（必需）
└── references/        # 参考资料（可选）
    └── *.md           # 技能相关的参考文档
```

### 当前技能

| 技能 | 命令 | 说明 |
|------|------|------|
| Git Commit 生成器 | `/git-commit` | 分析代码改动，生成带 Gitmoji 的 commit message |

---

## Git Commit 技能要点

触发命令：`/git-commit`

**执行流程**：
1. 分析改动 → `git status`, `git diff`, `git diff --cached`
2. 安全检查 → 检测敏感文件（.env, credentials, *.key 等）和敏感代码模式（password, secret, api_key 等）
3. 生成 commit message → 格式：`:emoji-name: 改动总结` + 编号列表
4. 用户确认后执行 `git add`
5. 用户确认后执行 `git commit`
6. 可选：询问是否 `git push`

**Gitmoji 映射**：完整参考见 `git-commit/references/gitmojis.md`

---

## 常用命令

```bash
# 查看技能列表
ls -d */

# 查看技能定义
cat <技能名>/skill.md
```
