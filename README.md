# Keel 交付流程开发讲解

面向懂开发、不了解机房实施的工程师，将 GPU 集群交付拆成可追踪、可核对的数据流程。

仓库：<https://github.com/enzoOvOyu/keel-delivery-brief>

## 当前定版

**发布版本：`v1.4.0`，定版日期：2026-10-26。** 页面数据版本为 `1.4-actions`，业务评审模型版本为 `1.1-collection-review`。版本与已验证环境见 [release.json](release.json)，发布文件摘要见 [release-manifest.json](release-manifest.json)。Git 标签 `v1.4.0` 固定本次提交，后续开发从该版本继续。

当前包含 32 个流程、13 个内部子步骤、42 类输入／产物、6 张流程图。每个流程及子步骤的对应卡片展示：

**现场动作 → 原始数据 → 比对判定 → 输出产物 → 下游使用**

五个主步骤：网络底座、装机、验机与基线配置、网络测试、NCCL 测试与评审。装机包含 `2.2 硬件信息收集`；公共流程包括 `0.1 修复与定向复验`、`0.2 CMDB 自动沉淀与维护查询`。

贯穿案例使用两台 B300 GPU 服务器与一台 SN5610。B300 整机参考 DGX B300 的公开配置；页面样例均标识为模拟。该项目提供讲解站、数据契约、图纸与有限验证模型，真实采集器、设备配置执行器及 CMDB 后端需后续实现。待确认的验收规则继续保留。

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
| `dist/index.html`、`dist/style.css`、`dist/app.js` | 页面、样式和浏览器交互 |
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
python3 spec/publish.py
node --check dist/app.js
node --check server.mjs
```

生成链只使用 Python 标准库，依次生成模型、讲解、draw.io、SVG，运行验证，再同步 `dist/` 和下载 ZIP。只想复核已经生成的模型时执行：

```bash
python3 spec/verify_contracts.py
```

不要只改生成后的 JSON、SVG 或下载 Markdown，否则下次生成会覆盖。原始需求定位与内部编号保存在 `spec/traceability.json`，正文和图纸使用统一阅读编号。

## 更新本地容器

当前容器使用镜像内文件。修改 `dist/` 后需重新构建并重建容器：

```bash
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
