# Draw.io 与 SVG 绘图、布局及双视觉主题规范

本规范定义 `.drawio`（mxGraph XML）与 `.svg` 双产物的结构、图层顺序、正交连线、网格几何标准，以及**「工程标准风」与「手绘科普风（Sketch / Excalidraw）」**两套视觉主题细则。

---

## 一、双产物一致性与文件结构

1. **双产物同步**：每次生成或更新必须同时产出 `.svg` 与 `.drawio`，两份文件的标题、层级、模块命名、胶囊标签与调用方向必须完全一致。
2. **`.drawio` 原生可编辑**：
   - XML 必须包含 `<mxfile>` -> `<diagram>` -> `<mxGraphModel>` -> `<root>` 以及真实可编辑的 `mxCell` 节点和连线。
   - **严禁伪编辑**：禁止在 `.drawio` 中使用 `shape=image` 或 `data:image/...` 嵌入整张图片充当架构图。
   - 节点使用稳定、可读的语义化 `id`：
     - 层级/容器：`layer-*`、`container-*`
     - 普通模块卡片：`card-*`、`domain-*`、`adapter-*`
     - **节点内嵌代码胶囊**：`badge-*` 或 `pill-*`（供校验脚本识别合规内嵌徽章）
     - **标题背景马克笔高亮色带**：`hl-*`（`value=""` 的纯色衬底块，置于对应标题文本之下）
3. **图形语义约定**：
   - 同属纵向主干的各主层级外框（或对比图的左右双容器总外沿与底部汇总框）保持**严格对齐的左右边界**。
   - 单系统图中，共享能力区/底部说明区/图例放在核心处理下方或边角；仅在 `架构/方案对比型（A vs B）` 的对比大容器内部，允许采用「左纵向主链路 + 浅竖分隔线 + 右侧 `特点` 列表」的双栏排版。

---

## 二、图层顺序（Z-Order）与调用链可见性（统一准则）

为彻底杜绝连线压盖卡片文字，统一采用**「背景层走线 + 空白通道穿行 + 线宽对比」**，固定渲染先后顺序如下（SVG DOM 顺序与 `.drawio` 的 `mxCell` 顺序完全一致）：

1. **第 1 层（最底）**：画布底板、主层级背景大框、对比方案大容器、虚线子分组外框、标题马克笔高亮衬底色块（`hl-*`）。
2. **第 2 层（连线层）**：**所有连接线（`edge="1"` 的 `mxCell` / SVG 主流程 `<path>`、`<line>`）**。严禁把 edge 堆在 XML 末尾压在卡片文字上方。
3. **第 3 层（卡片与文本层）**：层级标题条、容器说明文本、右侧特点栏文本、业务/步骤模块卡片（`card-*`）、底部对比维度卡片与图例。
4. **第 4 层（最顶微件层，按需）**：嵌在模块卡片右侧内部的代码/原语小胶囊（`badge-*` / `pill-*`，如 `delegate_task()`）及纯装饰短笔触。

**主调用链 vs 辅助依赖线的视觉区分**：
- **主调用链（实线）**：`stroke-width: 1.8~2.2`（Draw.io `strokeWidth=2`），颜色高对比，缩放到 75% 仍一眼看清流向；箭头面积不超过模块高度的 35%。
- **辅助链路（虚线，用于配置读取、依赖注入、初始化注册、缓存刷新、旁路闭环）**：`stroke-width: 1.3~1.6`，`dashed=1` / `stroke-dasharray="5,4"`，透明度 `0.6~0.7`。

---

## 三、正交连线与防穿插规则

1. **只允许正交走向，严禁跨层斜线**：
   - 所有主调用链和跨层/分叉连线只能沿水平或垂直方向延伸：
     - **工程标准风**：90 度直角折线（`M x1 y1 L x1 yMid L x2 yMid L x2 y2`，Draw.io `rounded=0`）。
     - **手绘科普风**：90 度圆角正交折线——直线段保持严格水平/垂直，在拐弯处使用半径 `r = 8~12px` 的二次贝塞尔圆弧过渡（`M x1 y1 L x1 (yMid-r) Q x1 yMid (x1+r) yMid ...`），Draw.io 使用 `rounded=1;arcSize=16;`。
   - 禁止生成起点到终点斜向跨越的连线（`x` 与 `y` 同时大幅变化）。
2. **外边界锚定与显式折点**：
   - 连线只能从上一层模块**底边**（`exitY=1`）出发，落到下一层模块**顶边**（`entryY=0`），**禁止连到模块中心**。
   - 一分二或一分三分叉时，先向下进入层间空白通道中线 `yMid`，再向左右水平延伸，最后垂直向下落入各子卡片顶边，并在 Draw.io `<Array as="points">` 中显式写出 `mxPoint` 折点。
3. **克制扇出与标签避让**：一对多调用优先合并为层间水平总线，连线标签只放空白通道，不压住任何卡片文字。

---

## 四、网格几何与文案防溢出标准

1. **禁止在含子元素的容器 `value` 中直接塞多行正文**：一律拆分为空白外框容器 + 顶部标题（可配 `hl-*` 衬底色块）+ 内部子卡片/独立文本框。
2. **最小安全间距（像素）**：
   - 层间纵向空白通道：`≥ 32`（有分叉折线时建议 `36~48`）
   - 同级并列卡片横向间距：`≥ 16`（大容器间距 `≥ 28`）；纵向间距：`≥ 18`；容器内边距：`≥ 18`
   - **内嵌代码胶囊（Inline Badge）布局规则**：当模块卡片右侧需内嵌代码胶囊（如 `Orchestrator MCP Server` + `delegate_task()`）时，外层卡片宽度须同时容纳「左侧主名称宽度 + 至少 `16px` 间距 + 右侧胶囊宽度 + 左右内边距」，外层卡片文字设置左对齐（`align=left;spacingLeft=16;`），避免居中文字与右侧胶囊相撞；胶囊 `id` 以 `badge-` 或 `pill-` 开头。
3. **字数与字号底线**：普通模块卡片最多 3 行，正文字号 `≥ 10px`，标题字号 `≥ 12px`；空间不足时优先精简文案或加大宽高，不强缩字号。

---

## 五、双视觉主题配置细则

### 主题 A：工程标准风（默认）

适用于单仓库研发架构文档、技术评审与 Confluence 长期维护：
- **画布与形状**：纯白或极浅冷灰底（`#FFFFFF` / `#F8FAFC`），标准规整圆角矩形（`rx="6"`～`"8"`，不加手绘抖动），实心三角箭头（`endArrow=block;endFill=1;rounded=0;`）。
- **字体**：系统无衬线工程字体（`Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif`）。

### 主题 B：手绘科普风（Sketch / Excalidraw 风格，按需启用）

适用于 `A vs B` 架构对比、公众号/X(Twitter) 技术科普配图、架构演讲分享或用户明确指定手绘/白板风格：

1. **柔和马卡龙色板（低饱和填充 + 协调彩色边框 + 深石板灰文字 `#1E293B`）**：

   | 语义角色 | 填充色 `fill` | 边框色 `stroke` | 马克笔标题衬底 `hl-*` |
   |---|---|---|---|
   | 画布背景 | `#FAFAF8`（暖白纸感） | — | — |
   | 暖杏橙（方案 A 容器 / 状态卡） | `#FFF5EC` | `#DF9A6C` | `#FCD9BD` |
   | 浅天蓝（方案 B 容器 / 入口栏 / 接口卡） | `#EEF6FF` | `#6FA3D8` | `#C3E0FD` |
   | 薄荷绿（编排层 / 核心执行图 / 差异汇总框） | `#EEF9F0` | `#74B882` | `#C6ECCF` |
   | 暖鹅黄（内嵌代码胶囊 `badge-*` / `特点` 标题 / 侧重卡） | `#FEF6D8` | `#D8A63A` | `#FDE68A` |
   | 云石灰（常规流程步骤条） | `#EFEFF1` | `#525E70` | — |
   | 丁香白（顶层/底层细粒度叶子芯片，如 `Codex`、`Run`） | `#F6F5FD` | `#5B6478` | — |

2. **Draw.io 手绘样式参数**：
   - 在容器与卡片 `style` 中加入：`rounded=1;arcSize=12;sketch=1;curveFitting=1;jiggle=2;comic=1;strokeWidth=1.6;fontColor=#1E293B;`。
   - 在连线 `style` 中加入：`edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=16;sketch=1;curveFitting=1;jiggle=2;endArrow=open;endFill=0;strokeWidth=1.8;strokeColor=#334155;`（开式 V 形箭头更具 Excalidraw 手绘呼吸感）。
   - 马克笔标题色带：在容器或栏目文字下方先放一个 `id="hl-<name>"`、`value=""`、`rounded=1;arcSize=40;strokeColor=none;fillColor=<衬底色>;opacity=80;` 的小圆角条，再在其上放置透明背景的粗体标题文本单元。

3. **SVG 原生手绘质感配方（无需外部依赖，文字保持高清锐利）**：
   - **仅对图形边框启用轻量手绘滤镜**（绝不对 `<text>` 使用滤镜，确保中英文与代码清晰锐利）：
     ```xml
     <filter id="sketch-roughen" x="-3%" y="-3%" width="106%" height="106%">
       <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="noise"/>
       <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.3" xChannelSelector="R" yChannelSelector="G"/>
     </filter>
     ```
     在容器、步骤卡片与分叉连线的 `<rect>` / `<path>` 上应用 `filter="url(#sketch-roughen)"` 与 `stroke-linecap="round" stroke-linejoin="round"`。
   - **字体搭配**：
     - 标题与正文：`'Virgil', 'Segoe Print', 'Comic Sans MS', 'STKaiti', 'KaiTi', 'PingFang SC', 'Microsoft YaHei', sans-serif`
     - 内嵌代码胶囊（`delegate_task()`、`worker-start`）：`'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace`（`11~12px`）
   - **点睛细节**：
     - 主标题与重要区块标题（如 `核心差异`）旁可点缀 2–3 根短小的暖黄/薄荷绿放射装饰线（长度控制在 `10~15px`，`stroke-linecap="round"`，添加 `data-role="decor"` 属性）。
     - 分叉连线使用半径 `8~10px` 的 `Q` 圆角折线 + 开式圆头箭头 `<marker>`（`d="M 1 1 L 8 5 L 1 9" fill="none" stroke="#334155" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`）。
