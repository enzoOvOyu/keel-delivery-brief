# Keel 交付流程讲解与复现材料

先阅读 `keel-developer-contracts.md`，或使用静态站。两者与六页流程图采用同一套阅读编号：1 网络底座、2 装机、3 验机与基线配置、4 网络测试、5 NCCL 测试与评审。0.1 是按需修复流程，0.2 是全过程 CMDB。2.2 收集装机硬件；3.1 复用并核验。编号表示阅读位置；用户授权新增的实际消费关系在模型中明示。

## 数据与展示

- `build_artifacts.py` 定义原有流程、输入输出与依赖，生成 `contract-model.json`。
- `reading.py` 定义唯一的阅读编号、名称、术语展开和页面说明，生成 `reading-model.json`、完整讲解及图纸标签。内部流程 ID 与业务判断保持原义。
- `guide.py` 定义五步首屏的六项交接说明和 3.3 接线核验完整样板，页面与下载讲解使用同一份内容。样板关联现有接线用例，并明确未自动验证的覆盖、版本和恢复条件；说明性情景不作为新的执行器或业务判定器。
- `data_contracts.py` 为全部 42 类数据提供 ID 规划、字段含义、格式、必填条件及关联约束。右侧详情卡的“信息类别”按原有输入／输出关系展示；已有字段与建议命名分别标记，不代表已批准的生产接口 Schema。
- `render_diagrams.py` 将同一 draw.io 的节点与连线生成 SVG，并同步可编辑路径。
- `acceptance-cases.json` 和 `verify_contracts.py` 提供固定用例、结构检查、错误注入及有限模型；运行结果写入校验报告。
- `traceability.json` 和 `source/keel-delivery-fishbone.md` 保存内部 ID、出处与输入快照。`narrative.md`、`validation-notes.md` 保留第一版论证材料，供维护时追溯，不作为当前页面的编号来源。
- 3.3 样板的逐项要求、证据信息和用例对应关系记录在 `traceability.json`，其依据快照位于 `source/PRD.md`、`source/DESIGN-SYSTEM.md` 和鱼骨文档；原文编号只用于内部追溯。

## 生成与发布

仅需 Python 3 标准库。从本目录执行：

```bash
python3 publish.py --output ../dist
```

此命令依次生成模型与阅读内容、绘制图纸、运行现有校验，再同步静态数据、图纸、下载文档与完整交付 ZIP。页面 HTML、CSS 和 JavaScript 由主项目维护，不由规格生成器覆盖。

单独检查已生成的模型：

```bash
python3 verify_contracts.py
```

这些检查针对评审模型，不能证明真实设备、生产系统或现场性能已经验收；12 项业务待确认仍须由相应责任方决定。

## 动作数据与后续约束

先读 `DEVELOPMENT-REQUIREMENTS.md`。`collection.py` 定义新增采集与 CMDB 关系；`walkthrough.py` 维护 32 流程与 13 内部子步骤的模拟案例。`collection_model.py`、`verify_walkthrough.py` 提供有限反例检查，随 `verify_contracts.py` 执行；它们不连接真实硬件或数据库。`collection-event.schema.json` 只约束同步事件封装。所有 Markdown 与示例从相同源定义发布。

## 可填写的业务规则确认

`decision_forms.py` 保留 12 项原有问题，定义量化字段、条件必填、单位、已知边界和流程影响；生成到阅读模型、讲解与交付包。表单不提供未经确认的默认业务阈值。确认策略仍需实测执行，不会将旧报告改为通过。浏览器内确认历史及导入／导出由前端维护，见根目录 README；填写值不写回本目录的发布基线。
