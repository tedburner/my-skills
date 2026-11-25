# AGENTS.md

本文件为当前自定义技能仓库（支持 Claude Code / Codex / Antigravity，`CLAUDE.md` 通过 `@AGENTS.md` 共享本文件）的维护指南。

---

## 仓库概述

这是一个 **个人 Agent Skills 仓库**，用于集中编写、演进和备份可复用的自定义技能（Skills）。每个技能均可通过 `/技能名` 显式调用，也可根据 `SKILL.md` frontmatter 的 `description` 按语义触发。

---

## 技能结构与编写约定

### 目录规范

```text
skills/<技能名>/
├── SKILL.md           # 技能触发条件、核心原则与主流程（必需，建议控制在 300 行内）
├── references/        # 按需加载的细分规范、模板与映射表（可选）
│   └── *.md
├── scripts/           # 跨平台确定性采集或校验脚本，优先使用 Python 标准库（可选）
│   └── *.py
└── agents/            # 特定客户端扩展元数据，如 Codex 的 openai.yaml（可选）
    └── openai.yaml
```

### 质量准则

1. **渐进式披露**：`SKILL.md` 只放每次执行都必需的流程与红线；多分支图型、大段模板或长映射表下沉到 `references/` 并写明读取时机。
2. **确定性检查脚本化**：重复性的仓库扫描、XML/坐标重叠检测、格式校验优先封装到 `scripts/`（仅依赖 Python 标准库），避免让模型靠心算做机械校验。
3. **跨平台 Shell 兼容**：命令示例须兼容 Windows PowerShell 与 macOS/Linux bash/zsh（例如 Git `@{u}` 必须加引号写作 `"@{u}"`，不在通用命令中硬编码 `2>/dev/null || true` 或 bash heredoc）。
4. **安全与授权边界**：涉及 Git 提交/推送、外部发布的技能必须保留敏感信息扫描与显式确认门禁，并兼容用户更高优先级的全局安全规则。

---

## 当前技能

| 技能名称 | 命令 | 说明 |
|----------|------|------|
| Git Commit 生成器 | `/git-commit` | 分析改动与仓库规范生成 Gitmoji commit message；含冲突/敏感拦截、纯推送直通、选项菜单确认与跨平台上游分歧检查 |
| Git Commit（Jira）生成器 | `/git-commit-jira` | 支持 Jira ID 上下文推断与精准 type 判定，生成 `<jira_id> <type>` 规范 message；含冲突/敏感拦截、选项确认与跨平台远程同步检查 |
| Repo 架构图生成器 | `/repo-architecture-flow` | 跨语言扫描仓库结构并自动匹配 6 类流程图语义，生成风格统一的自上而下 `.svg` 展示图与原生可编辑 `.drawio` 源文件，内置几何防遮挡自检 |
| Shipyard 技术方案流程 | `/shipyard` | Spec 驱动开发全流程：支持轻量单文档与完整 HLD/LLD 模式、三档接口模板、本地交付与外部联调解耦验收、归档与跨会话恢复 |

---

## 开发规范

### 新增或更新技能后

1. **必须同步更新 `README.md` 与 `AGENTS.md` 中的技能列表表格**，保持 `技能名称`、`命令`、`说明` 三列一致。
2. 核对技能内部所有相对 Markdown 链接（`references/*.md`、`scripts/*.py`）均指向真实存在的文件，无断链或过期引用。
3. 若修改了 `scripts/*.py`，交付前必须运行语法与功能自测（含正常样本与异常拦截样本）。
