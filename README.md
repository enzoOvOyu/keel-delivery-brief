# Keel 交付流程开发讲解

面向懂开发、不了解机房实施的工程师，将 GPU 集群交付拆成可追踪、可核对的数据流程。

仓库：<https://github.com/enzoOvOyu/keel-delivery-brief>

## 历史定版与当前工作区

**历史定版：`v1.4.0`，日期：2026-10-26。** 当时页面数据为 `1.4-actions`；[release.json](release.json)、[release-manifest.json](release-manifest.json) 和 Git 标签记录该历史版本。当前工作区的页面数据为 `1.5-decisions`，包含 UI 优化、draw.io 编辑入口及业务确认工作台；尚未创建新的 Git 发布标签。业务评审模型版本仍为 `1.1-collection-review`。

当前包含 32 个流程、13 个内部子步骤、42 类输入／产物、6 张流程图。每个流程及子步骤的对应卡片展示：

**现场动作 → 原始数据 → 比对判定 → 输出产物 → 下游使用**

五个主步骤：网络底座、装机、验机与基线配置、网络测试、NCCL 测试与评审。装机包含 `2.2 硬件信息收集`；公共流程包括 `0.1 修复与定向复验`、`0.2 CMDB 自动沉淀与维护查询`。

3.1 同时展示 BMC／BIOS、GPU VBIOS、NIC 固件及 GPU／NIC／RDMA 驱动采集，按批准范围核对覆盖数与兼容矩阵，随 g1 事件进入既有 CMDB。缺测、冲突或缺基线保留阻断，不预设生产版本号。

贯穿案例使用两台 B300 GPU 服务器与一台 SN5610。B300 整机参考 DGX B300 的公开配置；页面样例均标识为模拟。该项目提供讲解站、数据契约、图纸与有限验证模型，真实采集器、设备配置执行器及 CMDB 后端需后续实现。待确认的验收规则继续保留。

## 前端开发与构建

当前 UI 使用 React、Vite、Tailwind CSS 与 shadcn/ui；流程数据、文案和判定继续复用既有生成器及控制器。正文与标题使用系统 UI 字体，代码和 ID 使用等宽字体。

```bash
npm ci
npm run dev          # 开发预览：5174
npm run check       # 类型、语法和规格检查
npm run build       # 生成规格并构建到 dist/
```

仅修改样式时可执行 `npm run build:frontend`，使用已有 `public/` 数据构建，不重新生成规格。`public/` 为生成目录；全新检出先运行一次 `npm run build`。容器仍只运行构建后的静态文件，监听 8080。流程图直接读取现有 `.drawio`，使用本地保存的官方查看器，支持左键／触摸拖动、滚轮缩放及适应宽度；查看操作不写回图纸。查看器版本、来源及 Apache-2.0 许可位于 `src/vendor/drawio/`。

流程图页的“编辑流程图”内嵌 [draw.io 官方编辑器](https://www.drawio.com/docs/reference/embed-mode/)，支持节点、文字、连线、多图页、撤销和全屏。完整编辑器由 `https://embed.diagrams.net` 提供（在线版本，由官方更新），浏览器需要能访问该服务；加载失败可重试或返回本地查看。按官方 JSON/postMessage 协议传递图纸，只接受该编辑器窗口及精确来源的消息。

编辑器的“保存”会下载 `keel-delivery-edited.drawio`。自动草稿只保存在当前浏览器，按发布源文件隔离；清理浏览器数据会删除草稿。编辑不会更新仓库、流程契约、SVG 或交付包；如需发布编辑结果，应回到规格生成链核对依赖并同步所有产物。

## 使用 Docker 启动

安装 Docker 后，在项目根目录执行：

```bash
git clone git@github.com:enzoOvOyu/keel-delivery-brief.git
cd keel-delivery-brief
git checkout v1.4.0
docker build -t keel-delivery-brief:v1.4.0 .
docker run -d --name keel-delivery-brief-web \
  --restart unless-stopped \
  -p 8080:8080 \
  keel-delivery-brief:v1.4.0
```

访问 **<http://localhost:8080>**。Dockerfile 已固定当前 Node Alpine 基础镜像摘要；容器直接运行 Node 标准库静态服务器，不需要 npm 安装或前端构建。容器内服务监听 `0.0.0.0:8080`，发布目录为 `dist/`。

本次验证环境：Node.js `22.23.3`、Alpine `3.24.2`、Docker Engine `29.9.0`；规格生成使用 Python `3.14.4`。Docker 本地镜像标签 `keel-delivery-brief:local` 为开发更新入口，`keel-delivery-brief:v1.4.0` 为本次定版标签。

只预览静态页面，也可以使用 Python：

```bash
python3 -m http.server 8080 --directory dist
```

两种方式选择一种，避免端口冲突。页面通过 HTTP 读取 JSON，应通过服务地址访问。

## 修改内容与重新生成

先阅读 [AGENTS.md](AGENTS.md) 和 [DEVELOPMENT-REQUIREMENTS.md](DEVELOPMENT-REQUIREMENTS.md)。页面、字段表、消费关系、图纸和下载包必须保持同一版本。

| 位置 | 维护内容 |
|---|---|
| `index.html`、`src/main.tsx` | 页面入口与布局装配 |
| `src/ui/layout.css`、`src/styles.css` | 全站视觉规范、响应式布局及主题 |
| `src/ui/presentation.tsx`、`src/components/ui/` | shadcn/ui 控件与展示适配 |
| `src/ui/density.ts`、`src/ui/density.css` | 全站信息密度、动作分段查看与待确认事项折叠 |
| `src/ui/wiring.ts`、`src/ui/wiring.css` | 接线核验主题、子步骤及动作数据在共用卡片内切换 |
| `src/ui/drawio.ts`、`src/vendor/drawio/` | 本地 draw.io 官方查看器 v32.3.0；`src/ui/drawio-editor.ts` 接入在线官方编辑器与草稿／下载协议 |
| `src/legacy/app.js` | 既有业务文案渲染和浏览器控制器，UI 优化不改变业务语义 |
| `spec/build_artifacts.py`、`spec/collection.py` | 流程模型、装机采集与公共 CMDB 关系 |
| `spec/reading.py` | 唯一阅读编号、名称与生成文档 |
| `spec/walkthrough.py` | 各流程及子步骤的动作、原始数据、比对与交接案例 |
| `spec/data_contracts.py` | ID、字段类型、必需性、单位与关联约束 |
| `spec/guide.py` | 五步首屏说明和 3.3 接线核验样板 |
| `spec/collection-event.schema.json` | CMDB 同步事件封装的评审 Schema |
| `spec/verify_contracts.py`、`spec/verify_walkthrough.py` | 结构、规则、数量质量和 CMDB 反例验证 |
| `spec/source/` | 需求来源快照 |
| `dist/diagrams/`、`dist/downloads/` | 发布图纸、Markdown、校验报告与交付 ZIP |

修改规格源定义后执行：

```bash
npm run build
node --check src/legacy/app.js
node --check server.mjs
```

生成链只使用 Python 标准库，依次生成模型、讲解、draw.io、SVG，运行验证，再同步 `public/` 和下载 ZIP，由 Vite 构建至 `dist/`。只想复核已经生成的模型时执行：

```bash
python3 spec/verify_contracts.py
```

不要只改生成后的 JSON、SVG 或下载 Markdown，否则下次生成会覆盖。原始需求定位与内部编号保存在 `spec/traceability.json`，正文和图纸使用统一阅读编号。

## 更新本地容器

当前容器使用镜像内文件。修改前端源码后需重新构建页面并重建容器：

```bash
npm run build
docker build -t keel-delivery-brief:local .
docker stop keel-delivery-brief-web
docker rm keel-delivery-brief-web
docker run -d --name keel-delivery-brief-web \
  --restart unless-stopped \
  -p 8080:8080 \
  keel-delivery-brief:local
```

可用以下命令查看状态与日志：

```bash
docker ps --filter name=keel-delivery-brief-web
docker logs --tail 50 keel-delivery-brief-web
```

恢复本次定版时，从 `v1.4.0` 标签构建镜像，按上述停止、移除、启动步骤替换容器即可。

## 本次验证与交付内容

- 47 个既有固定用例通过，15 项结构检查通过。
- 48 项动作数据与 CMDB 有限检查通过，6 个注入错误均被发现。
- 浏览器验证覆盖 45 张卡片、42 类数据、6 张图纸、字段切换、子步骤展开、深链接、下载、加载失败及 390px 窄屏；未发现浏览器脚本错误。
- 已核对 8080 服务返回内容与本地发布文件一致，并从交付 ZIP 独立重新生成成功。

自动验证结果位于 [spec/verification-report.md](spec/verification-report.md)。浏览器核查是本次本地验证记录，未提供预装浏览器的 CI。有限模型与模拟数据检查不代表真实 B300／SN5610 已通过现场验收，也未运行 TLC；性能阈值、覆盖与豁免等业务决策在页面中继续明确标记。

页面侧栏可下载完整流程讲解、后续开发约束、可编辑 draw.io 和 `keel-development-handoff.zip`。Git 同时保存源定义与发布文件，便于直接运行及复现。

## 提交约定

当前目录是独立 Git 仓库，远端仅为 `enzoOvOyu/keel-delivery-brief`。提交前确认 `git rev-parse --show-toplevel` 返回当前项目目录。

deploy key、环境凭据、依赖目录、缓存及原始导入 ZIP 已加入忽略规则。访问 GitHub 使用本机凭据配置；仓库和下载包不携带私钥。`.openai/hosting.json` 保留原有 Sites 标识，独立 Docker 服务的访问控制由部署环境配置。

后续发布使用新版本与新 Git 标签，记录对应的页面数据版本、验证结果及文件摘要。

## 业务确认工作台

“校验与待确认”提供 12 项可填写的规则确认。先填写项目、范围清单、档位、独立基线、确认人与有效期，再逐项填写数值／处理方式并明确确认。流程卡和网络测试详情显示同一份方案的状态、参数和修订；修改参数或范围、确认到期、源规格变化后需重新确认。确认规则不会产生现场通过结论。

草稿和历史仅存于当前浏览器，可导出 JSON（含完整修订历史）或 Markdown 摘要，也可预览并导入方案。更换浏览器或交给开发前请导出；导入不会自动批准未确认的填写。姓名和角色是确认记录，不是登录认证。

定义位于 `spec/decision_forms.py`，由规格生成器同步到阅读数据、讲解、追溯和交付 ZIP；交互与校验位于 `src/ui/decisions.tsx`、`src/ui/decision-engine.ts`。

```bash
npm run build           # 同步规格、图纸、报告、交付包并构建前端
npm run test:decisions  # 确认、数量边界、失效、导入和冲突的独立用例
```

表单定义检查写入实际校验报告，范围仅为字段与流程引用；前端用例不验证设备能力、网络性能或用户批准权限。
