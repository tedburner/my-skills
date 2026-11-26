---
name: repo-architecture-flow
description: >
  扫描代码仓库或根据技术方案生成风格统一、可维护的自上而下架构流程图与方案对比图，同时输出 .svg 展示图与可编辑 .drawio 源文件（支持严谨工程风与 Excalidraw 手绘科普风）。
  当用户要求生成、刷新、标准化项目架构图、代码分层图、调用链路图、多方案/竞品架构对比图（A vs B），或按手绘信息图风格绘制架构图时使用；不用于纯服务器/K8s 物理部署拓扑（除非用户明确指定部署视角）。
---

# Repo Architecture Flow

将代码仓库或技术方案转化为**真实有据、自上而下、原生可编辑**的流程架构图。每次交付必须同时生成并保持完全一致的两份文件：

- `docs/architecture/<project>-flow-architecture.svg`：用于直接预览、文档/推文展示与 Confluence 页面插入（用户指定路径时从其指定）。
- `docs/architecture/<project>-flow-architecture.drawio`：原生 mxGraph XML 源文件，供 diagrams.net 或 Confluence draw.io 宏继续编辑。

仅当用户额外要求时才附加生成 HTML 预览页；HTML 不可替代 `.drawio` 源文件。

---

## 跨平台命令准则

- 不要假设运行环境一定是 `bash`（Windows 默认常为 PowerShell）。避免在通用步骤中依赖 heredoc、`2>/dev/null`、`$(...)` 或 Linux 专属路径展开。
- 优先使用本技能自带的纯 Python 标准库脚本采集事实与校验产物（Windows / macOS / Linux 通用）。
- 搜索文件优先用 `rg --files`；不可用时在 PowerShell 用 `Get-ChildItem -Recurse` / `Select-String`，在 bash/zsh 用 `find` / `grep`。

---

## 工作流程

### 1. 采集架构证据

1. **单仓库 / 双仓库代码扫描**：浏览顶层目录、构建文件、`AGENTS.md` / `CLAUDE.md` / `README.md`，并对每个本地目标仓库运行事实采集脚本（自动识别多语言入口、消费者、定时任务/状态图、核心服务、出站客户端、存储适配并脱敏配置）：
   ```text
   python <skill-dir>/scripts/collect_architecture_facts.py --root <repo-root>
   ```
   脚本输出仅作为代码证据；边界不清时继续人工阅读核心源码确认真实调用链。
2. **方案/竞品对比场景（无单一本地仓库时）**：若用户提供的是两套框架/方案资料、设计文档或参考图做 `A vs B` 架构对比，基于已核实的源码、官方文档或用户输入提炼双边核心链路与差异维度，不凭空编造未证实的组件。

### 2. 检查存量架构图（增量优先）

- 若已有 `.drawio`，优先沿用其整体层级、配色与模块命名习惯做增量修订（除非旧图方向混乱或用户要求切换主题/重绘）。
- 若仅有 `.svg` 或参考图片，理解其结构语义与视觉风格需求后重新构建原生可编辑 `mxCell` 节点。

### 3. 选择「语义图型」与「视觉主题」

1. **选择唯一语义图型**（阅读 [`references/diagram-archetypes.md`](references/diagram-archetypes.md) 获取对应分层细则）：
   - **服务分层型**（完整后端 / DDD / 业务平台）
   - **代码逻辑分层型**（Python/FastAPI/Triton / 模型推理 / 算法引擎）
   - **中间件处理链路型**（网关 / 协议适配 / 数据组装与路由中心）
   - **业务泳道型**（端到端业务流 / 页面生成 / 训练标注评测闭环）
   - **组件/包逻辑型**（Maven/Gradle 多模块 / `provider-core-common` / 分词索引 SDK）
   - **双流程/状态机型**（单服务内同步检索链路 + 异步/Agent 状态机双主线并存）
   - **架构/方案对比型（A vs B）**（两套框架、竞品或重构前后方案并列对比：顶层公共入口 → 左右双容器「左调用栈 + 右侧特点栏」→ 底部核心差异维度卡片）
2. **选择视觉主题**（详见 [`references/drawio-svg-spec.md`](references/drawio-svg-spec.md) 第五节）：
   - **工程标准风（默认）**：规整圆角框、直角正交线（`rounded=0`）、克制企业配色，适合研发设计文档与 Confluence 归档。
   - **手绘科普风（Sketch / Excalidraw 风格，按需启用）**：当用户提及“手绘风 / Excalidraw 风 / 白板风 / 技术科普 / 推文配图 / 参考手绘图风格”，或在做 `A vs B` 方案对比信息图且希望视觉生动时启用——采用纸感暖白底、马卡龙柔和色块、马克笔高亮标题色带、圆角正交分叉线（`rounded=1`）、draw.io 原生 `sketch=1` 手绘描边以及节点内嵌代码胶囊（如 `delegate_task()`）。
3. **高信噪比提炼原则**：
   - 所有图型主阅读方向统一**自上而下**，禁止左进右出或中心发散主干。
   - 单系统工程图中，每个核心业务域（控制在 3–5 个）展示中文名、一句职责、**1–3 个核心类名/文件线索**与 2–4 个关键能力点；对比图中聚焦双边核心机制、代表原语/接口胶囊与底部差异对照，不堆砌全量目录或统计数字。
   - 默认过滤 Docker、K8s、JVM、CI/CD、端口号等部署噪音（除非项目本身即运维/调度平台或用户明确指定）。

### 4. 生成 `.drawio` 与 `.svg`

严格遵循 [`references/drawio-svg-spec.md`](references/drawio-svg-spec.md) 生成两份结构与文案完全一致的文件：

- **图层顺序固定**：背景层外框与高亮底块 → **所有连接线（edge）** → 标题条/说明文本/模块卡片 → 节点内嵌胶囊徽章（`badge-*`），杜绝线条盖住文字。
- **正交走线**：只允许垂直、水平和 90 度正交折线（手绘风可在折角处用小圆角过渡），走层间空白通道并锚定模块上下外边界；**严禁斜向跨层连线与中心穿字连线**。
- **网格防溢出**：按文本行数与安全间距显式计算容器宽高，正文字号不低于 `10px`。

### 5. 运行脚本自检与修复闭环

生成或修改 `.svg` 与 `.drawio` 后，**必须执行几何与结构校验脚本**：

```text
python <skill-dir>/scripts/validate_diagram.py --svg <svg-path> --drawio <drawio-path>
```

- 脚本自动检查：XML 合法性、占位符残留、`shape=image` 伪编辑嵌入、连线排在模块卡片之后的图层违规、非正交斜线、父容器越界、同级卡片重叠（兼容合规内嵌 `badge-*` 胶囊与 `hl-*` 标题高亮底条）、文本容量溢出及双产物术语一致性。
- 若存在 `[ERROR]` 或遮挡 `[WARN]`，按「删减次要文案 → 扩大卡片与层间距 → 改用层间总线 → 微调字号」优先级修复后重跑脚本直至通过；未做浏览器/diagrams.net 视觉渲染检查时，须在最终回复中如实说明已完成 XML 与几何防遮挡脚本校验。

---

## Confluence 上传说明

本技能只生成本地 `.drawio` 与 `.svg` 文件，不自动调用 Confluence API 发布页面。交付时可按需指引参考 [`references/confluence-upload.md`](references/confluence-upload.md)。
