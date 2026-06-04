---
name: repo-architecture-flow
description: 扫描代码仓库并生成可维护的流程架构图。适用于用户要求生成、刷新、固化、标准化项目架构图，尤其是需要同时输出 SVG 图片和可编辑 .drawio 源文件，并手动上传到 Confluence 或 diagrams.net 后续维护的场景。
---

# Repo Architecture Flow

使用本技能把代码仓库转换为稳定、可维护的流程架构图。最终必须生成：

- `.svg` 图片：用于直接预览、文档展示、手动上传 Confluence。
- `.drawio` 源文件：用于 diagrams.net 或 Confluence draw.io 插件中继续编辑。

如果用户额外要求 HTML 预览，可以在 SVG 与 drawio 之后再生成。HTML 只是预览或导出辅助，不作为后续维护的源文件。

## 工作流程

1. 先扫描仓库，再绘图。
   - 优先使用 `rg --files`；如果遇到权限拒绝或不可用，改用 `Get-ChildItem`。
   - 阅读项目指导文件，例如 `AGENTS.md`、`CLAUDE.md`、README、构建文件、主配置文件。
   - Java/Spring 项目重点检查 `interfaces`、`domain`、`application`、`infrastructure` 等包。

2. 收集架构证据。
   - 对 Java/Spring 或类似结构项目，运行事实采集脚本。
   - 如果技能在项目内：`python .agents/skills/repo-architecture-flow/scripts/collect_architecture_facts.py --root .`
   - 如果技能在全局目录：`python <skill-dir>/scripts/collect_architecture_facts.py --root <repo-root>`
   - 该脚本只依赖 Python 标准库，适用于 Windows、macOS、Linux。
   - 脚本输出只作为证据，不直接等同于最终架构模型。
   - 对包名容易误导、服务类过大、模块边界不清的地方，要继续人工阅读关键文件。

3. 如果已有架构图，先读取现有产物。
   - 如果存在 `.drawio`，优先把它作为源文件参考，尽量保留整体布局、层级顺序、配色和命名风格。
   - 如果只存在 `.svg` 或 `.html`，把它作为视觉参考，但重新生成 `.drawio` 时必须使用可编辑 mxGraph 单元格。
   - 除非用户要求重绘，否则不要让布局大幅漂移；优先做增量更新和命名修正。

4. 识别分层。
   - 触发器层 / 入口层：HTTP API、MQ Consumer、定时任务、Health/Actuator。它们属于同一层级，但要用虚线框物理隔离不同入口类型。
   - 业务领域层：按业务价值流划分领域，每个领域必须有中文名称和一句中文职责说明。
   - 数据访问与底层适配层：持久化适配、外部调用适配、MQ Producer 等业务层向下的出站适配。
   - 基础设施与外部系统层：只放边界外系统或中间件，并用虚线框区分基础设施和外部系统依赖。

5. 抽象业务领域。
   - 不要机械照搬包名，除非包名已经准确表达业务边界。
   - 优先按价值流划分。对于 query-quality 类平台，默认使用以下抽象，除非扫描证据明显不支持：
     - `质量评测域`：负责产生质检数据，是核心高价值资产来源。
     - `度量看板域`：负责消费并展示质检数据，支撑监控、告警、统计。
     - `任务管理域`：负责质检生命周期控制，包括 PK 任务、版本、调度、进度。
   - 每个模块都要有中文功能说明，不要只放类名。

6. 绘图原则。
   - 所有主层级外框保持相同左右边界。
   - 同层不同入口类型使用虚线子框隔离。
   - 尽量减少交叉箭头，优先使用纵向箭头或总线式连线。
   - 跨层连线必须走层间空白通道；不要在入口虚线框内部画横线，也不要让线条穿过模块卡片、标题或说明文字。
   - 如果入口到领域存在一对多关系，优先用少量代表性纵向箭头表达主流向，或使用层间总线说明“按请求/消息/调度分发”；不要为了穷尽调用关系画出大面积 fan-out。
   - 连接线必须作为背景层绘制：SVG 中先画线再画卡片；drawio 中 edge `mxCell` 要排在 vertex `mxCell` 之前，确保卡片和文字在视觉上盖在线条之上。
   - 如果某条线不能同时满足“走空白通道”和“背景层不遮挡”，就删除该线，改用层级说明或少量主箭头表达流向。
   - Feign、OkHttp、RestTemplate、WebClient 等统一归入 `外部调用适配`。
   - 外部 RPC 系统默认统一画成 `外部系统依赖`，不要逐个列出，除非用户明确要求。
   - 不要把 VO/DTO/Assembler 单独画到底层；如需表达，只说明它们内聚在 API 与 Service 的交互边界。
   - 最上层统一使用 `外部触发源`，不要使用 `外部刺激`。
   - 领域层建议控制在 3-5 个核心业务域，避免把每个包都画成一个领域。

7. 生成产物。
   - SVG 默认输出到 `docs/architecture/<project>-flow-architecture.svg`，除非用户指定路径。
   - drawio 默认输出到 `docs/architecture/<project>-flow-architecture.drawio`。
   - drawio 必须可编辑：使用原生 mxGraph 图形、文本和连接线，不能只嵌入一张图片。
   - SVG 与 drawio 必须表达同一套层级、同一批模块、同一套命名；不要出现 SVG 是新版而 drawio 还是旧版的情况。
   - 如同时生成 HTML，HTML 可以引用或内嵌 SVG，但不要替代 `.drawio` 源文件。

## 输出规范

每张最终架构图必须包含：

- 项目或服务名称作为标题。
- 四个对齐的主层级：
  - `1. 触发器层 / 入口层（Inbound / Trigger Layer）`
  - `2. 业务领域层（Domain / Service Layer）`
  - `3. 数据访问与底层适配层（Infrastructure / Outbound Adapters）`
  - `4. 基础设施与外部系统（Infrastructure & External Services）`
- 每个业务域和模块的中文标签或中文职责说明。
- 第 1 层中至少区分：
  - `HTTP API 入口`
  - `MQ 消息入口`
  - `定时任务入口`
- 第 4 层中必须有左右两个虚线隔离区：
  - `基础设施（Infrastructure）`
  - `外部系统依赖（External Services）`
- 同时生成 `.svg` 与 `.drawio` 两份文件。

## Draw.io 生成要求

`.drawio` 文件使用 XML 格式，包含 `<mxfile>`、`<diagram>`、`<mxGraphModel>`。

图形约定：

- 主层级外框：浅色圆角矩形。
- 子分组边界：虚线圆角矩形。
- 普通模块：圆角矩形。
- 存储组件：可使用 cylinder 形状。
- 连接线：使用 `endArrow=block;html=1;rounded=0;`。
- 有子模块的容器不要直接在容器 `value` 里写大段文字；应拆成：
  - 空白容器外框。
  - 顶部标题条。
  - 独立说明文本。
  - 子模块卡片。
- drawio 容器文字默认容易居中覆盖子模块；如必须在容器上写文字，设置 `verticalAlign=top`、`spacingTop`，并预留足够顶部空间。
- 连接线不要从模块内部斜穿文字；优先使用层间总线、直角线、短垂直线。
- 入口层到领域层的连线优先从具体入口模块或入口分组底边出发，落到领域分组顶边；不要从大容器中心自动路由。
- 对跨列连接线设置明确折点，例如：先垂直到层间空白区，再水平移动，再垂直到目标边界。不要依赖 drawio 自动路由决定穿过哪个模块。
- 当 drawio 中 `edgeStyle=orthogonalEdgeStyle` 仍会穿过卡片时，必须改用显式 `mxPoint` 折点，或者减少为代表性主箭头。
- drawio 文件中连接线的 `mxCell` 必须放在对应模块卡片之前，作为底层线条；不要把所有 edge 放在 XML 末尾，否则 diagrams.net 会把线画在卡片和文字上方。
- 连线端点只允许落在分组或模块的外边界，不要落到模块中心；从模块中心出发通常会造成线条穿过内部文字。

尽量使用稳定、可读的 ID，例如 `layer-inbound`、`domain-quality`、`adapter-rpc`。

## 视觉验收标准

生成前后都要按以下标准自检：

- 主层级外框左右边界一致，整体方正。
- 第 1 层入口类型是同层并列关系，不要画成上下游关系。
- 第 1 层不同入口类型必须有物理隔离，例如虚线框。
- 第 2 层每个业务域都有中文名称和中文职责说明。
- 第 3 层只表达出站适配类型，不堆叠每个 Mapper、Feign 或 Producer 类名。
- 第 4 层左右隔离 `基础设施` 与 `外部系统依赖`，外部依赖默认聚合。
- 箭头数量克制，避免大面积交叉；必要时用少量主干箭头表达方向。
- 所有模块文字应能在框内完整显示，不要溢出或遮挡。
- drawio 中标题、说明、模块卡片、连线不得互相遮挡；容器标题必须位于顶部标题条或独立文本框。
- 入口层、领域层内部卡片上方不得出现跨层横线；横向线段只允许放在两个主层级之间的空白带，或放在明确标注的总线位置。
- 在 diagrams.net 中打开时，任意线条都不能压在中文标题、说明文字、模块卡片文字上方；如果做不到，优先减少线条数量，而不是保留完整调用线。

## Confluence 使用方式

只提供手动上传方式，不自动调用 Confluence API，不自动发布页面。

推荐方式：

1. 将 `.drawio` 作为可编辑源文件上传或导入 Confluence draw.io / diagrams.net 宏。
2. 将 `.svg` 作为展示图片上传到页面。
3. 页面中注明 `.drawio` 是源文件，`.svg` 是展示版本。

详细步骤见 `references/confluence-upload.md`。

## 校验

完成前必须检查：

- 生成文件中没有 `TODO`、`[PROJECT]`、乱码或模板占位符。
- SVG 包含真实 `<svg>` 内容，可以独立打开。
- drawio 包含 `<mxfile`、`<mxGraphModel` 和可编辑的 `mxCell` 元素。
- drawio 不包含 `image;` 或 `data:image` 这类嵌入整图的伪编辑内容。
- SVG 和 drawio 中的核心标题、领域名称、模块名称保持一致。
- 如果没有做浏览器视觉检查，要在最终回复中说明。
