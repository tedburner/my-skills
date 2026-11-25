---
name: repo-architecture-flow
description: >
  扫描代码仓库并生成风格统一、可维护的自上而下架构流程图，同时输出 .svg 展示图与可编辑 .drawio 源文件（便于上传 Confluence 或在 diagrams.net 持续维护）。
  当用户要求生成、刷新、固化或标准化项目/服务架构图、代码分层图、调用链路图或模块逻辑图时使用；不用于纯服务器/K8s 物理部署拓扑（除非用户明确指定部署视角）。
---

# Repo Architecture Flow

将代码仓库转化为**真实有据、自上而下、原生可编辑**的流程架构图。每次交付必须同时生成并保持完全一致的两份文件：

- `docs/architecture/<project>-flow-architecture.svg`：用于直接预览、Markdown 引用与 Confluence 页面展示（用户指定路径时从其指定）。
- `docs/architecture/<project>-flow-architecture.drawio`：原生 mxGraph XML 源文件，供 diagrams.net 或 Confluence draw.io 宏继续编辑。

仅当用户额外要求时才附加生成 HTML 预览页；HTML 不可替代 `.drawio` 源文件。

---

## 跨平台命令准则

- 不要假设运行环境一定是 `bash`（Windows 默认常为 PowerShell）。避免在通用步骤中依赖 heredoc、`2>/dev/null`、`$(...)` 或 Linux 专属路径展开。
- 优先使用本技能自带的纯 Python 标准库脚本采集事实与校验产物（Windows / macOS / Linux 通用）。
- 搜索文件优先用 `rg --files`；不可用时在 PowerShell 用 `Get-ChildItem -Recurse` / `Select-String`，在 bash/zsh 用 `find` / `grep`。

---

## 工作流程

### 1. 扫描仓库并采集架构证据

1. 先浏览顶层目录、构建描述文件（`pom.xml`、`build.gradle*`、`pyproject.toml`、`package.json`、`go.mod`）、主配置以及 `AGENTS.md` / `CLAUDE.md` / `README.md`。
2. 运行跨平台事实采集脚本（自动识别单模块/多模块源码目录与 Java/Kotlin/Python/TS/Go 入口、消费者、定时任务、核心服务、出站客户端、存储适配及脱敏后的配置端点）：
   ```text
   python <skill-dir>/scripts/collect_architecture_facts.py --root <repo-root>
   ```
3. 脚本输出仅作为代码证据，不直接照抄成最终图。对包名宽泛、巨型 Service 或多链路交织的核心模块，继续人工阅读关键源码确认真实调用链。

### 2. 检查存量架构图（增量优先）

- 若仓库已有 `.drawio`，优先读取并沿用其整体层级、配色与模块命名习惯，做增量修订而非推倒重排（除非旧图方向混乱或用户要求重绘）。
- 若仅有 `.svg` 或参考图片，提取其业务语义后按本技能自上而下规范重新构建原生 `mxCell` 节点。

### 3. 选择流程图语义类型并抽象核心模块

1. 阅读 [`references/diagram-archetypes.md`](references/diagram-archetypes.md)，根据仓库特征从 6 种语义类型中选定唯一主图型：
   - **服务分层型**（完整后端 / DDD / 业务平台）
   - **代码逻辑分层型**（Python/FastAPI/Triton / 模型推理 / 算法引擎）
   - **中间件处理链路型**（网关 / 协议适配 / 数据组装与路由中心）
   - **业务泳道型**（端到端业务流 / 页面生成 / 训练标注评测闭环）
   - **组件/包逻辑型**（Maven/Gradle 多模块 / `provider-core-common` / 分词索引 SDK）
   - **双流程/状态机型**（RAG 搜索链路 + Agent/Graph 状态机双主线并存）
2. **提炼原则（高信噪比）**：
   - **统一自上而下**：所有图型主阅读方向一律从上到下（`外部触发源 -> 接入适配 -> 核心处理 -> 出站适配/共享能力 -> 基础设施与外部系统`），禁止左进右出或中心发散。
   - **中文职责 + 代码定位线索**：每个核心业务域、引擎或组件块必须有中文名称与一句职责说明，并附 **1–3 个承载核心逻辑的类名/文件名线索**（如 `OrderApplicationService`、`RecallEngine`）；入口层保持粗粒度协议分类，默认不罗列全部 Controller/Consumer/Job 文件名。
   - **摘要化而非目录化**：业务领域控制在 3–5 个，每个领域展示 2–4 个关键能力点；不堆砌全量子包清单、全量 Mapper/Feign 列表或“50+ 服务”类统计数字。
   - **过滤部署噪音**：Docker、K8s、JVM 参数、健康探针、CI/CD、构建插件与端口号默认不进主图（除非项目本身就是部署/运维编排平台或用户明确要求）。框架版本可放页脚小字。

### 4. 生成 `.drawio` 与 `.svg`

严格遵循 [`references/drawio-svg-spec.md`](references/drawio-svg-spec.md) 的几何与绘图细则生成两份文件，核心红线：

- **图层顺序固定**：背景层外框 → **所有连接线（edge）** → 标题条/说明文本/模块卡片（vertex），杜绝线条盖住卡片文字。
- **正交走线**：只允许垂直线、水平线和显式折点的 90 度直角折线，走层间空白通道并锚定模块上下外边界；**严禁斜线与中心连线**。主调用链用醒目实线（`strokeWidth=2`），配置/注入/刷新/旁路用轻量虚线。
- **网格防溢出**：带子卡片的容器拆分为外框 + 顶部标题条 + 说明区 + 子卡片网格，按文本行数与安全间距显式计算容器宽高，正文字号不低于 `10px`。

### 5. 运行脚本自检与修复闭环

生成或修改 `.svg` 与 `.drawio` 后，**必须执行几何与结构校验脚本**：

```text
python <skill-dir>/scripts/validate_diagram.py --svg <svg-path> --drawio <drawio-path>
```

- 脚本会自动检查：XML 合法性、占位符残留（`TODO` / `[PROJECT]` / 乱码）、`image;` 伪编辑嵌入、连线排在模块卡片之后的图层违规、斜向线段、容器越界、同层卡片重叠、文本框容量溢出以及双产物标题/模块一致性。
- 若脚本输出 `[ERROR]` 或高风险遮挡 `[WARN]`，按「删减次要文案 → 扩大卡片与层间距 → 改用层间总线 → 微调字号」优先级修复后重跑脚本，直至通过。
- 若当前环境支持浏览器可视化预览，可进一步打开 SVG 目视核对主调用链在 75% 缩放下的可读性；若未做浏览器/diagrams.net 视觉渲染检查，**必须在最终回复中如实说明已完成 XML 与几何防遮挡脚本校验**。

---

## Confluence 上传说明

本技能只生成本地 `.drawio` 与 `.svg` 文件，不自动调用 Confluence API 发布页面。向用户交付产物时，可按需指引参考 [`references/confluence-upload.md`](references/confluence-upload.md) 的手动导入与双文件维护步骤。
