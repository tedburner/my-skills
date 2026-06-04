# Confluence 手动上传教程

本技能只提供手动上传方式，不自动调用 Confluence API，不自动创建或更新页面。

推荐维护原则：

- `.drawio` 是可编辑源文件。
- `.svg` 是展示图片。
- 两份文件应一起保存，避免后续只剩图片无法编辑。

## 情况一：Confluence 已安装 Draw.io / Diagrams.net 插件

1. 打开目标 Confluence 页面。
2. 点击编辑页面。
3. 插入 draw.io / diagrams.net 图表宏。
4. 选择导入或上传已有图表。
5. 上传 `docs/architecture/<project>-flow-architecture.drawio`。
6. 在 draw.io 编辑器中确认图形可编辑。
7. 保存图表。
8. 发布 Confluence 页面。

后续修改时，直接在 Confluence 页面中打开 draw.io 图表宏编辑即可。

## 情况二：Confluence 没有 Draw.io / Diagrams.net 插件

1. 将 `docs/architecture/<project>-flow-architecture.svg` 上传为页面附件。
2. 在页面中插入该 SVG 图片作为展示图。
3. 同时将 `docs/architecture/<project>-flow-architecture.drawio` 上传为附件。
4. 在图片旁边或页面下方注明：`可编辑源文件：<project>-flow-architecture.drawio`。

后续修改流程：

1. 从 Confluence 附件下载 `.drawio`。
2. 使用 diagrams.net 打开并编辑。
3. 导出新的 SVG。
4. 替换 Confluence 页面中的 SVG 附件。
5. 同步上传更新后的 `.drawio` 源文件。

## 推荐仓库文件约定

将两份文件放在同一目录：

- `docs/architecture/<project>-flow-architecture.svg`
- `docs/architecture/<project>-flow-architecture.drawio`

把 `.drawio` 当作源文件，把 `.svg` 当作由源文件导出的展示产物。
