# Personal Skills

个人 Agent Skills 仓库（适用于 Claude Code / Codex / Antigravity），用于统一存储、维护和备份自定义技能配置。

## 技能列表

| 技能名称 | 命令 | 说明 |
|----------|------|------|
| Git Commit 生成器 | `/git-commit` | 分析改动与仓库规范生成 Gitmoji commit message；含冲突/敏感拦截、纯推送直通、选项菜单确认与跨平台上游分歧检查 |
| Git Commit（Jira）生成器 | `/git-commit-jira` | 支持 Jira ID 上下文推断与精准 type 判定，生成 `<jira_id> <type>` 规范 message；含冲突/敏感拦截、选项确认与跨平台远程同步检查 |
| Repo 架构图生成器 | `/repo-architecture-flow` | 跨语言扫描仓库或对比双方案，自动匹配 7 类架构/对比图型（支持工程标准风与 Excalidraw 手绘风），输出 `.svg` 与可编辑 `.drawio` 并内置几何防遮挡自检 |
| Shipyard 技术方案流程 | `/shipyard` | Spec 驱动开发全流程：支持轻量单文档与完整 HLD/LLD 模式、三档接口模板、本地交付与外部联调解耦验收、归档与跨会话恢复 |

---

## 备份说明

本仓库作为个人 Skills 的唯一维护源与备份存储。
