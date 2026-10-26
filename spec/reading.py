"""Presentation vocabulary only. Original flow IDs, edges and predicates are retained."""
import copy
import html
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
VERSION = "1.4-actions"
STAGES = [
    {"id": "1", "name": "网络底座", "summary": "建立物料、配置与网络证据", "flows": [f"F{i:02}" for i in range(1, 9)]},
    {"id": "2", "name": "装机", "summary": "安装系统、验证通道并收集硬件清单", "flows": ["H01", "H07"]},
    {"id": "3", "name": "验机与基线配置", "summary": "核验硬件、接线、映射和配置", "flows": [f"H{i:02}" for i in range(2, 7)]},
    {"id": "4", "name": "网络测试", "summary": "按范围验证链路与负载表现", "flows": [f"T{i:02}" for i in range(7)]},
    {"id": "5", "name": "NCCL 测试与评审", "summary": "运行通信组并评审交付证据", "flows": [f"N{i:02}" for i in range(1, 9)]},
]
COMMON = {"id": "0", "name": "公共流程", "summary": "修复按需进入；CMDB 全过程消费源记录", "flows": ["R01", "C01"]}
TITLES = {
    "F01": "导入物料与连接计划", "F02": "制定网络实施计划", "F03": "检查开通环境",
    "F04": "开通交换机管理通道", "F05": "预校验网络侧接线", "F06": "应用并核对网络配置",
    "F07": "检查网络健康与无损能力", "F08": "验收并导出网络交付包",
    "H01": "安装系统并建立 SSH 互信",
    "H07": "收集装机硬件信息", "C01": "CMDB 自动沉淀与维护查询",
    "H02": "核验硬件与系统信息", "H03": "验证机内 GPU–NIC 拓扑", "H04": "核对并确认物理接线",
    "H05": "发布已验证映射", "H06": "应用并验证服务器基线配置",
    "T00": "确认准入并冻结测试计划", "T01": "检查链路、速率与光模块", "T02": "验证 IP 可达性",
    "T03": "验证 RDMA 写读通路", "T04": "验证多流负载与热点覆盖", "T05": "交叉验证无损与拥塞",
    "T06": "汇总网络测试并发布证明",
    "N01": "检查通信组运行条件", "N02": "准备一致的测试环境", "N03": "执行通信组测试",
    "N04": "回收结果并核对检测场景", "N05": "生成测试报告", "N06": "追踪失败原因",
    "N07": "汇总调优建议", "N08": "评审报告与退出条件", "R01": "修复与定向复验",
}
INDEX = {fid: {"code": f"{stage['id']}.{i}", "stage": stage["id"], "title": TITLES[fid]}
         for stage in STAGES + [COMMON] for i, fid in enumerate(stage["flows"], 1)}
SUBSTEPS = {
    "H01": [
        ("安装前检查", "核对目标身份、已审批镜像、兼容性和硬件预检结果；预检失败时中断安装。"),
        ("安装系统并首次启动", "执行镜像安装，保留操作系统与驱动版本；系统启动后进入注册。"),
        ("完成身份注册", "注册回执绑定装机请求、设备序列号／MAC 与项目，校验一次性令牌。"),
        ("验证 SSH 互信", "完成首次连接验证后才允许硬件采集；失败进入受控互信修复。"),
    ],
    "H04": [
        ("确认 GPU–NIC 关系", "使用已通过的机内拓扑结果，保存每个 GPU 对应的网卡、PCIe 路径和 NUMA 归属。"),
        ("采集双侧邻居与 MAC", "采集主机和交换机两侧 LLDP 邻居，并核对永久 MAC。采集缺失与真实无邻居分别记录。"),
        ("进行三方比对", "按物理端口对比较物料连接计划、主机实测与交换机回读；保存差异、工单及已确认关系。"),
        ("交付组长最终确认", "前三项通过且差异完成复验与关闭确认后，保存完整步骤记录、关系版本、确认人和时间。"),
    ],
    "F08": [
        ("确认网络验收证据", "核对适用阶段的完成证据及有效豁免，保留原始结论。"),
        ("导出并移交", "导出设备、端口、互联、地址、状态及配置快照索引，逐项核对引用一致性。"),
    ],
    "N03": [
        ("运行机内通信档", "按型号定义执行机内通信域测试，保留本次通信组与尝试的原始结果。"),
        ("运行跨机通信档", "按型号定义运行小通信组及机柜档位；每个通信组统一启动，失败按整组恢复。"),
        ("运行全目标档", "按选定模式执行分组覆盖或全域单通信组；两类覆盖分别报告，组内不能滚动启动。"),
    ],
}
ARTIFACT_TITLES = {
    "project": "项目模板与商定基线", "model": "独立型号与拓扑基线", "media": "已审批介质与兼容矩阵",
    "policy": "已确认的判据与覆盖策略", "auth": "授权与资源条件", "readiness": "动态网络就绪证明",
    "observations": "主机／交换机观测与能力标记", "window": "本次负载对应的网络观测窗口", "human": "人工处置与确认记录",
    "bom": "物料版本、稳定实体与期望连接", "plan": "网络实施计划、模板与变量快照", "env": "环境自检记录",
    "bootstrap": "身份绑定、管理可达与开通回执", "pre_cable": "网络接线预校验与待核验端口清单",
    "net_config": "预期／实际配置快照与比对证明", "health": "网络健康证明", "lossless": "无损能力、基线与规则证据",
    "network_export": "网络验收包与交付基线", "host_ready": "系统版本、注册回执与 SSH 互信证明",
    "inventory": "装机硬件清单与采集质量记录", "cmdb": "CMDB 联邦索引与同步回执",
    "g1": "硬件核验快照与完整性证明", "topology": "机内拓扑快照与差异记录",
    "g2": "四步接线记录、确认关系与验收证明", "mapping": "不可变映射版本与发布证明",
    "g4": "配置版本、应用回执与基线验证证明", "test_plan": "冻结测试计划与准入记录",
    "l1": "端口链路检查结果", "l2": "网卡配对可达结果与覆盖集合", "l3": "RDMA 写读、带宽、丢包与窗口记录",
    "l4": "多流吞吐、热点覆盖与负载窗口", "l5": "无损规则交叉判定与降级记录",
    "g5": "网络测试证明、分层报告与路径基线", "nccl_admission": "通信组准入记录",
    "nccl_environment": "测试环境一致性与介质摘要回执", "group_results": "通信组各次尝试的原始结果与诊断",
    "metrics": "NCCL 指标与检测场景矩阵", "report": "测试报告与原始数据索引",
    "trace": "失败分析、工单关联与证据包", "tuning": "调优清单与版本化变更入口",
    "g6": "报告评审与退出准入证明", "repair": "修复、复验与关闭记录",
}
OWNERS = {
    "project": "客户与网络工程师商定，项目模板保存版本。",
    "model": "已审批的设备型号版本；预期拓扑独立于本次待验数据。",
    "media": "介质库与参数目录提供已审批版本及兼容关系。",
    "policy": "项目模板、参数目录及有权审批人提供；未确定的策略保留待确认。",
    "auth": "项目权限、批准动作范围与执行资源预留记录。",
    "readiness": "网络证据接口在执行前刷新；默认有效期为 30 秒。",
    "observations": "主机与网络采集器提供；每项记录对象、时间、采集来源及质量。",
    "window": "持续网络采集提供，与本次负载关联；精确窗口绑定方式仍待确认。",
    "human": "网络工程师、交付组长及现场人员的处置、审批与确认记录。",
}
TERMS = {
    "N-S0": "项目立项与标准", "N-S1": "物料建模", "N-S2": "网络实施规划", "N-S3": "环境就绪",
    "N-S4": "交换机开通", "N-S5": "网络侧接线预校验", "N-S6": "网络配置闭环",
    "N-S7": "网络健康检查", "N-S8": "网络验收", "N-S9": "结果导出",
    "NP-1": "交换机与端口已建模", "NP-2": "交换机开通与配置就绪", "NP-3": "已确认接线关系",
    "NP-4": "新鲜的网络就绪证明", "NP-5": "网络健康证明", "NP-6": "无损能力与基线",
    "G1": "硬件采集验收", "G2": "物理接线验收", "G3": "映射发布验收", "G4": "基线配置验收",
    "G5": "网络测试验收", "G6": "NCCL 报告评审",
    "L1": "链路检查", "L2": "IP 可达性检查", "L3": "RDMA 写读检查", "L4": "多流负载检查", "L5": "无损交叉验证",
    "LL-01": "持续暂停规则", "LL-02": "暂停风暴／死锁规则", "LL-03": "ECN 恒不标记规则",
    "LL-04": "ECN 过度标记规则", "LL-05": "配置意图一致性规则", "LL-06": "无损队列丢包规则", "LL-07": "缓冲余量规则",
    "S1": "通信组预检", "S2": "测试环境准备", "S3": "机内测试", "S4": "跨机测试", "S5": "全目标测试",
    "S6": "结果回收", "S7": "报告生成", "S8": "失败溯源", "S9": "调优建议",
    "T1": "断链", "T2-rail": "错轨布线", "T2": "布线误操作", "T3": "模块损坏",
    "T4": "线缆损坏", "T5": "网卡故障", "T6": "配置异常", "T7": "机内拓扑异常",
    "FR-0.8.1": "网络就绪接口", "FR-0.8.2": "交换机邻居回读接口", "FR-0.8.4": "无损计数与证据接口",
    "FR-0.8": "网络证据接口", "FR-4.8": "机内拓扑验证", "FR-4.7": "受控修复与复验",
    "FR-11": "网络测试", "FR-0": "网络底座", "FR-6": "NCCL 测试",
    "SC-1": "机内带宽检查", "SC-2": "机内互联检查", "SC-3": "节点性能差异检查", "SC-4": "GPU–NIC 亲和检查",
    "SC-5": "显存带宽检查", "SC-6": "显存纠错检查", "SC-7": "温度与功耗检查", "SC-8": "跨机带宽检查",
    "SC-9": "计算结果检查", "SC-10": "初始化时长检查",
}
DECISION_TITLES = [
    "测试调度与停止范围", "测试阈值与 watchdog 判据", "观测窗口与负载绑定",
    "路径覆盖生成与档位适用", "无损规则到验收结论的映射", "缺测与近似证据的接受范围",
    "配置就绪标准与并行时序", "基线配置抽检的适用范围", "邻居缺失与采集失败的区分",
    "网络健康范围与时钟同步适用性", "混合结论与工单阻断范围", "豁免风险在后续步骤中的保留",
]
DECISIONS = {f"Q{i}": title for i, title in enumerate(DECISION_TITLES, 1)}
RULES = [
    ("持续 PFC 暂停", "60 秒窗口内暂停计数增量 ≥1；连续三个窗口非零或达到 100 帧／60 秒时升级。具体升级动作仍待确认。"),
    ("暂停风暴或死锁", "300 秒内 XOFF 累计 ≥90 秒；同一网络中至少三个端口同时命中时升级。无 XOFF 事件时保留 unknown；替代估算为发送暂停帧 ≥1000 帧／60 秒且连续三个窗口命中，结果标为 approximation。"),
    ("ECN 恒不标记", "完整 3600 秒窗口内 ECN 恒零，且同窗口有队列水位大于零或 PFC 增量 ≥1 的拥塞证据，才命中此规则。"),
    ("ECN 过度标记", "300 秒内标记比例 >5% 为告警；2% < 比例 ≤5% 仅观察记录。"),
    ("配置意图不一致", "分别核对批准意图、设备配置态与可比较的硬件事实。缺少可比较字段时记录 unknown。"),
    ("无损队列丢包", "应无损的队列出现非零丢包时命中。硬件丢包遥测和接口丢包计数都不可用时，结果为 unknown。"),
    ("ECN 与 PFC 缓冲余量不足", "ECN 最大阈值对应缓冲占位 ≥0.6 时命中；无法直接读取 XOFF 缓冲量时，按配置比例与池大小估算，并标记 estimated。"),
]
GLOSSARY = [
    ("物料清单（BOM）", "设备、部件、端口与预期连接的版本化清单。预期连接必须与本次实际观测分开保存。"),
    ("物理端口与系统接口", "物理端口是稳定的实物身份；操作系统接口名和 PCIe 地址可能变化，需要通过已验证映射关联。"),
    ("机内拓扑与外部接线", "机内拓扑描述 GPU 到网卡的 PCIe／NUMA 关系；外部接线描述主机端口到交换机端口的实际连接。"),
    ("LLDP／DOM", "LLDP 采集实际邻居；DOM 是光模块温度、光功率等遥测。主机与交换机的数据分别保留。"),
    ("rail／网卡配对", "rail 是批准网络方案中的分组。同一组内实际测试的网卡对、方向与覆盖范围必须保留。"),
    ("RDMA／NCCL", "RDMA 写读验证网卡间的数据通路；NCCL 验证指定 GPU 通信组的集合通信表现。两者的性能指标不能互相替代。"),
    ("PFC／ECN／CNP", "分别表示按优先级暂停、拥塞标记、RoCE 拥塞通知。需要结合配置、计数能力、负载与时间窗口判断。"),
    ("证明与当前可用性", "历史通过结果继续保留；新任务仍须核对项目、目标、路径、档位、依赖版本和有效期。"),
    ("验收结论与数据质量", "PASS 为通过，FAIL 为违反判据，BLOCKED 为前置或必需证明不足，WAIVED 为批准的例外。unknown、降级、近似和估算属于质量标记，不能直接当作通过。"),
    ("执行角色", "交付组长负责最终确认与允许的豁免；网络工程师、网络负责人和交付工程师按各自动作权限执行、审批或处置。"),
]
NCCL_CHECKS = [
    ("机内通信带宽", "AllReduce 总线带宽至少达到同配置、同规模实测基线的 92%。不达标按规定重测两次，仍失败时检查机内链路并建单。"),
    ("机内互联链路", "型号要求的 NVLink 链路全部处于 active；缺失时进入机内拓扑故障处理。"),
    ("节点性能差异", "有独立来源的同条件节点指标，相对同组中位数的落后偏差不超过 15%。缺节点测量时标 unavailable；该检查为必需项时阻断或按批准豁免处理。"),
    ("GPU–NIC 亲和", "满足已审批的 GPU–NIC 路径与 NUMA 亲和方案；不符时进入配置修复。"),
    ("显存带宽", "单 GPU 实测显存带宽至少达到同型号、工具与参数基线的 85%；缺基线时阻断或批准豁免。"),
    ("显存纠错", "测试窗口内不可纠正错误为零；可纠正错误增量默认不超过 10。超限时进入 GPU 个体故障评估。"),
    ("温度与功耗", "按型号登记的厂商温度阈值、功率上限与测量窗口判断；缺阈值按基线缺失处理。"),
    ("跨机通信带宽", "相对同规模、拓扑、软件与参数的跨机实测基线，衰减不超过 30%。超限时结合网络路径基线与无损规则溯源。"),
    ("计算结果正确性", "结果校验失败数为零。失败时保存证据并终止该通信组；重试创建新的整组尝试。"),
    ("初始化时长", "初始化默认不超过 60 秒；超时后按诊断配置重跑采集并分析原因。"),
]

def flow_label(fid):
    x = INDEX[fid]
    return f"{x['code']} {x['title']}"

def plain(text):
    """Expand notation before replacing individual IDs, with no predicate edits."""
    text = str(text or "")
    # Slash/range shorthand must be expanded as a unit (NP-1/2/4, LL-01/02 etc.).
    def expand(m):
        prefix, first, tail = m.group(1), m.group(2), m.group(3)
        if not tail:
            return m.group(0)
        nums = re.findall(r"\d+", tail)
        width = len(first) if first.startswith("0") else 0
        if re.match(r"[～~–—-]", tail):
            nums = [str(i) for i in range(int(first) + 1, int(nums[-1]) + 1)]
        return "、".join(prefix + (str(n).zfill(width) if width else str(n)) for n in [first] + nums)
    text = re.sub(r"(?<![A-Za-z0-9])((?:NP-|N-S|LL-|SC-|Q|G|L|S|T))(\d+)((?:(?:[/／、]|[～~–—-])\d+)*)", expand, text)
    replacements = {
        "source=g2": "发现环节为物理接线核验", "source=g5": "发现环节为网络测试",
        "source=g6": "发现环节为 NCCL 测试", "source=fabric": "发现环节为网络底座",
        "responsible_domain=fabric": "责任域为网络侧", "source=host": "采集来源为主机",
        "source=switch": "采集来源为交换机", "source=bmc": "采集来源为带外管理",
        "P建议": "实现建议", "P实现建议": "实现建议", "P建议的": "建议的",
        "Q清单": "待确认清单", "原文要求": "已明确要求", "原文": "已明确要求",
        "StepReport": "步骤报告", "MappingRevision": "已验证映射版本", "ConfigSet": "配置版本",
        "GateEvidence": "验收证明", "GroupAttempt": "整组执行尝试", "GroupRun": "通信组",
        "TaskAttempt": "执行尝试", "DeviceModelVersion": "设备型号版本",
        "PciTopologySnapshot": "机内拓扑快照", "TopologyDiff": "拓扑差异",
        "required_path_coverage": "本次所需路径覆盖", "test_profile": "测试档位",
        "PortModel": "端口模型", "Doublecheck": "配置预校验", "PushJob": "配置下发任务",
        "LL规则": "无损规则", "LL结论": "无损规则结论", "LL证据": "无损规则证据",
        "LL告警": "无损规则告警", "N-S阶段": "网络阶段",
        "SC场景": "检测场景", "SC判据": "检测场景判据", "T类": "分类故障", "INV": "约束",
    }
    for a, b in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(a, b)
    lookup = {**TERMS, **DECISIONS, **{fid: flow_label(fid) for fid in INDEX}}
    pattern = r"(?<![A-Za-z0-9_-])(" + "|".join(re.escape(k) for k in sorted(lookup, key=len, reverse=True)) + r")(?![A-Za-z0-9_-])"
    text = re.sub(pattern, lambda m: lookup[m[0]], text)
    text = re.sub(r"(?<![A-Za-z])(NH|NE|DL|DE)(?![A-Za-z])", lambda m: {"NH": "网络负责人", "NE": "网络工程师", "DL": "交付组长", "DE": "交付工程师"}[m[0]], text)
    text = re.sub(r"Step\s*([1-4])", lambda m: "3.3." + m[1], text)
    # Section-only references have no explanatory value in the reader.
    text = re.sub(r"(?:附件|已明确要求)?§[\d.]+(?:[、／][§\d.]+)*", "", text)
    return text.strip()

FLOW_TEXT = {
    "F04": {"post": "ZTP 开通完成证明设备已开通；配置就绪还须有预期与实际配置的比对证据。管理可达的中间事实可以供后续预检读取，不等于整个开通流程通过。"},
    "F06": {"post": "结合交换机开通记录与配置复采结果判断配置就绪。命令成功不等于配置同步；Major／Minor 级漂移是否允许，仍待确认。"},
    "F07": {"note": "运行期采集持续进行，观测需要与本次测试关联。具体窗口绑定与采样编排方式仍待确认。"},
    "F08": {"actions": "先确认网络验收证据，再导出设备、端口、连接、地址、状态与配置版本。",
            "post": "逐项引用一致率 100%；豁免保留原始结论。本交付包不是启动物理接线核验的额外总门禁。"},
    "H02": {"post": "采集字段完整率 100%，永久 MAC 与物料清单一致。光模块遥测不可读时保留降级标记；接受范围仍待确认。"},
    "H04": {
        "actions": "按下方四个子步骤执行：确认 GPU–NIC 关系 → 采集双侧邻居与 MAC → 三方按物理端口对比对 → 交付组长最终确认。每步保存版本化报告。",
        "post": "3.3.3 的单个端口对通过，只代表该连接已确认；完整四步通过并完成最终确认后，才能进入 3.4 发布已验证映射。",
        "retry": "通常从 3.3.2 增量重采。机内拓扑发生变化时，先重新完成 3.2 验证机内 GPU–NIC 拓扑，再更新 3.3.1；工单关闭仍须复验通过。",
    },
    "T00": {"post": "冻结计划是建议的数据组织方式。调度、阈值、观测窗口与路径覆盖策略仍待确认；缺少定义时不能默认满足。",
            "note": "这里将准入条件与测试范围集中说明；计划对象的组织方式属于实现建议。"},
    "T01": {"failure": "已观测到的明确异常为 FAIL；必需观测缺失为 BLOCKED。光模块遥测降级的具体接受范围仍待确认。"},
    "T02": {"retry": "只复测受影响的网卡配对；配对是否区分方向及对应覆盖策略仍待确认。"},
    "T05": {"note": "RDMA 写读和多流负载向本步骤提供判定数据；观测需要覆盖负载窗口。具体采样编排仍待确认。",
            "actions": "核对 watchdog 状态；交叉核查持续暂停、暂停风暴／死锁、ECN 恒不标记和 ECN 过度标记规则，同时保留配置意图、无损丢包与缓冲余量的相关证据。"},
    "N01": {"post": "纯机内 NVLink 诊断在有效基线配置证明与资源条件满足时可先行；它只提供机内诊断证据，不能作为 NCCL 交付评审通过的依据。"},
    "N03": {"actions": "按下方三个子步骤，从机内到跨机，再到选定的全目标档执行。每个通信组统一启动；分组覆盖与全域单通信组分别报告。",
            "retry": "创建新的整组执行尝试，重建全部成员；不能只重跑失败的参与者。"},
    "N05": {"post": "报告生成后仍须完成评审；后续溯源与调优章节引用同一证据链，汇编为完整报告。"},
    "N08": {"post": "报告评审通过只解锁优雅退出；后续仍须完成清理、撤权、归档等交付步骤。"},
    "R01": {"retry": "修复后回到原来的生产步骤重新核验，并生成新版本证明。公共流程按故障范围调用，不加入正常前向依赖链。",
            "actions": "登记实物或配置处理 → 按故障类别定向复验 → 通过后提议关闭 → 网络工程师／交付组长确认。",
            "post": "维修登记不代表恢复完成。复验由原生产流程生成新版本证明；发现故障的环节与定位后的责任域分别保留。"},
}

def build(model):
    reader = {"version": VERSION, "stages": copy.deepcopy(STAGES), "common": COMMON, "flows": [], "artifacts": [],
              "rules": [{"name": a, "description": b} for a, b in RULES],
              "glossary": [{"name": a, "description": b} for a, b in GLOSSARY]}
    for original in model["flows"]:
        f = {k: plain(original[k]) for k in ["purpose", "resources", "guards", "actions", "post", "failure", "retry", "invalidation", "note"]}
        f.update(FLOW_TEXT.get(original["id"], {}))
        f.update(INDEX[original["id"]])
        f.update(id=original["id"], inputs=original["inputs"], outputs=[a["id"] for a in original["outputs"]],
                 decisions=original["decisions"])
        f["substeps"] = [{"code": f["code"] + "." + str(i), "title": a, "description": b}
                        for i, (a, b) in enumerate(SUBSTEPS.get(f["id"], []), 1)]
        f["checks"] = [{"name": a, "description": b} for a, b in NCCL_CHECKS] if f["id"] == "N04" else []
        reader["flows"].append(f)
    for a in model["artifacts"]:
        reader["artifacts"].append({**{k: a[k] for k in ["id", "producer", "consumers"]},
                                   "name": ARTIFACT_TITLES[a["id"]],
                                   "owner": OWNERS.get(a["id"], ""),
                                   "terminal_consumer": plain(a.get("terminal_consumer", ""))})
    reader["decisions"] = [{**{k: plain(d[k]) for k in ["owner", "recommendation", "boundary"]},
                            "id": d["id"], "topic": DECISIONS[d["id"]],
                            "flows": [f["id"] for f in model["flows"] if d["id"] in f["decisions"]]}
                           for d in model["decisions"]]
    reader["invariants"] = {i["id"]: plain(i["text"]) for i in model["invariants"]}
    suite = json.loads((ROOT / "acceptance-cases.json").read_text())
    reader["case_names"] = {c["id"]: plain(c["name"]) for c in suite["cases"]}
    from guide import attach
    attach(reader)
    from data_contracts import attach as attach_data_contracts
    attach_data_contracts(reader)
    from walkthrough import attach as attach_walkthrough
    attach_walkthrough(reader)
    return reader

def markdown(reader):
    from guide import brief_markdown, sample_markdown
    from data_contracts import markdown as data_markdown
    from walkthrough import card_markdown, context_markdown
    fs = {f["id"]: f for f in reader["flows"]}
    ars = {a["id"]: a for a in reader["artifacts"]}
    out = ["# Keel 交付流程讲解\n\n阅读版 " + VERSION,
           "五个大步骤：网络底座 → 装机 → 验机与基线配置 → 网络测试 → NCCL 测试与评审。",
           "编号表示阅读位置。网络与服务器侧可并行，具体任务按所需产物、范围、版本和有效期准入。0.1 是公共恢复流程；0.2 是全过程接收数据的公共 CMDB 流程。",
           "每个步骤说明输入、资源、允许条件、动作、产物、完成证明、失败、恢复与失效。标为待确认的业务策略仍需明确决定；演示与模型检查不代表现场验收。",
           "## 阅读前的必要概念"]
    out.append(context_markdown(reader))
    out += [f"- **{g['name']}：** {g['description']}" for g in reader["glossary"]]
    for stage in reader["stages"] + [COMMON]:
        out.append(f"\n## {stage['id'] + ' ' if stage['id'] != '0' else ''}{stage['name']}\n\n{stage['summary']}")
        if "brief" in stage:
            out += [brief_markdown(stage["brief"]), stage["brief"]["boundary"]]
        for fid in stage["flows"]:
            f = fs[fid]
            out += [f"\n<!-- contract:{fid} -->\n### {f['code']} {f['title']}\n\n{f['purpose']}", "| 契约字段 | 说明 |\n|---|---|"]
            inputs = "；".join(ars[a]["name"] + "（" + (OWNERS[a] if ars[a]["producer"] == "external" else flow_label(ars[a]["producer"])) + "）" for a in f["inputs"])
            outputs = "；".join(ars[a]["name"] + " → " + ("、".join([flow_label(c) for c in ars[a]["consumers"]] + ([ars[a]["terminal_consumer"]] if ars[a]["terminal_consumer"] else []))) for a in f["outputs"])
            for title, value in [("输入及生产方", inputs), ("所需资源", f["resources"]), ("开始条件", f["guards"]),
                                  ("执行动作", f["actions"]), ("产物及消费者", outputs), ("完成证明", f["post"]),
                                  ("失败与阻断", f["failure"]), ("恢复与重试", f["retry"]), ("失效条件", f["invalidation"])]:
                out.append("| " + title + " | " + value.replace("|", "／").replace("\n", " ") + " |")
            out.append(card_markdown(f["walkthrough"]))
            for sub in f["substeps"]:
                out.append(f"\n#### {sub['code']} {sub['title']}\n\n{sub['description']}")
                out.append(card_markdown(sub["walkthrough"]))
            if f["checks"]:
                out.append("\n**报告中的检测场景：** 数值为默认判据或型号基线要求，实际消费已批准的参数版本；缺少必需基线时不能默认通过。")
                out += [f"- **{c['name']}：** {c['description']}" for c in f["checks"]]
            if f["note"]: out.append("\n" + f["note"])
            if f["decisions"]: out.append("\n**待确认：** " + "；".join(DECISIONS[q] for q in f["decisions"]))
            out.append("\n**信息类别：** 字段格式见下文“开发数据简表”。")
            out.append("输入：" + "；".join(ars[a]["data_contract"]["category"] for a in f["inputs"]) + "。")
            out.append("产出：" + "；".join(ars[a]["data_contract"]["category"] for a in f["outputs"]) + "。")
    out.append(sample_markdown(reader["wiring_sample"]))
    out.append(data_markdown(reader))
    out += ["\n## 无损规则说明", "以下为建议默认值。商定基线与经审批生效的规则版本优先；告警级别与最终验收结论分别保存。"]
    out += [f"\n### {r['name']}\n\n{r['description']}" for r in reader["rules"]]
    out.append("\n## 待确认事项\n\n责任角色为建议分工。业务决定不会因模型检查通过而自动关闭。")
    for d in reader["decisions"]:
        out.append(f"\n### {d['topic']}\n\n{d['recommendation']}\n\n未决边界：{d['boundary']}\n\n建议责任人：{d['owner']}。\n\n相关步骤：" + "、".join(flow_label(f) for f in d["flows"]))
    out.append("\n## 校验范围\n\n交付包提供固定用例、结构检查、错误注入与有限状态枚举。实际结果见随包校验报告；其范围不包含真实设备、生产系统及现场性能验收。")
    return "\n\n".join(out) + "\n"

def rewrite_diagrams(reader):
    tree = ET.parse(ROOT / "keel-delivery.drawio")
    pages = list(tree.getroot())
    titles = ["五步交付与产物依赖", "3.3 核对并确认物理接线", "4 网络测试", "0.1 修复与定向复验", "5 NCCL 测试与评审", "0.2 CMDB 全过程数据流"]
    # Labels are deliberately short enough for the retained geometry.
    overrides = {
        0: {
            "title": "<b>五步交付与产物依赖</b><br>编号为阅读位置；实线为产物消费。网络与服务器侧按需并行。",
            "fresh": "<b>执行前刷新就绪证明</b><br>3.3 接线核验与 4.1 测试准入前刷新网络状态<br>默认有效期 30 秒；5.1 通信组预检再次核对",
            "boundary": "<b>阅读边界</b><br>1.8 验收导出不额外阻断装机或测试。5.8 报告评审通过，只解锁退出流程。",
            "e0": "物料与连接计划",
            "e12": "预校验与待核验端口",
            "e13": "生产配置同步证据",
            "e17": "基线配置验证证明",
            "e18": "健康与无损能力证明",
        },
        1: {
            "title": "<b>3.3 核对并确认物理接线</b><br>实线表示已定义的控制或判定分支；虚线表示定向复验回流。",
            "ready": "3.3 开始条件<br>硬件采集与机内拓扑有效<br>端口已建模、配置就绪、邻居可读",
            "s1": "3.3.1 确认 GPU–NIC 关系<br>保存机内路径与亲和关系版本",
            "s2": "3.3.2 采集双侧邻居与 MAC<br>主机实测＋交换机回读",
            "s3": "3.3.3 进行三方比对<br>期望连接 ↔ 主机实测 ↔ 交换机回读",
            "s4": "3.3.4 交付组长最终确认<br>完整步骤链＋关系版本＋确认记录",
            "g3": "3.4 发布已验证映射<br>所需映射覆盖 100%，无冲突<br>发布不可变版本",
            "repair": "0.1 修复与定向复验<br>复验通过后提议关闭，网络工程师／交付组长确认<br>通常回到 3.3.2；拓扑变化先重做 3.2",
            "note": "连接确认由本次三方比对产生；3.3.3 局部通过不能代替 3.3.4 最终确认。稳定物理端口在映射发布前已存在。",
        },
        2: {
            "title": "<b>4 网络测试：按检查维度提供证据</b><br>实线为上下文、观测或结果消费；虚线为负载与观测关联。层间调度仍待确认。",
            "plan": "4.1 确认准入并冻结测试计划<br>配置与映射有效、网络就绪<br>目标／路径／档位／版本／资源",
            "T01": "4.2 检查链路、速率与光模块",
            "T02": "4.3 验证 IP 可达性",
            "T03": "4.4 验证 RDMA 写读通路",
            "T04": "4.5 验证多流负载与热点覆盖",
            "T05": "4.6 交叉验证无损与拥塞",
            "telemetry": "网络侧持续观测<br>采集来源、规则版本、能力与质量<br>观测窗口覆盖相关负载；缺测不能补零",
            "merge": "4.7 汇总网络测试并发布证明<br>必需检查结果＋所需路径覆盖<br>版本／有效期／批准的豁免",
            "bad": "FAIL / BLOCKED<br>已证明违反判据／必需证明不足<br>混合结论汇总策略待确认",
            "note": "30 秒打流不能单独证明 3600 秒 ECN 规则已验证；未触发规则不能代替网络验收；抽样通过不能外推全路径。",
            "tt3": "关联负载上下文（建议）", "tt4": "观测覆盖负载（窗口待确认）",
        },
        3: {
            "title": "<b>公共流程：版本变化与 0.1 修复复验</b><br>实线为处理或影响关系；虚线为变更、异常或恢复分支。事务与租约属于实现建议。",
            "retry": "0.1 修复与定向复验<br>重新核验当前条件<br>受控复验只豁免本故障的阻断",
            "ttl": "<b>时间语义</b><br>30 秒就绪有效期用于消费或派发时检查，不要求长任务 30 秒内结束。观测窗口、采样新鲜度与验收证明有效期分别核对。",
        },
        4: {
            "title": "<b>5 NCCL 测试与评审</b><br>实线为处理顺序或证据消费，虚线为整组失败后的恢复。步骤编号与流程卡一致。",
            "N01": "<b>5.1 检查通信组运行条件</b><br>确认本通信组可安全启动测试<br>并具备解释结果所需的证据",
            "N03": "<b>5.3 执行通信组测试</b><br>按型号与覆盖模式<br>执行机内、跨机和全目标通信测试",
            "retry": "通信组执行失败<br>终止其余参与者并保存诊断<br>新尝试整组重建，再做 5.1 预检",
            "source": "网络与映射证据<br>网络路径基线、无损规则结果<br>端口、拓扑与 GPU 遥测",
            "boundary": "<b>5.8 评审出口</b><br>报告达标并确认调优清单后，解锁优雅退出。机内诊断不能直接证明交付通过；分组覆盖与全域单通信组分别报告。",
        },
    }
    byid = {f["id"]: f for f in reader["flows"]}
    for i, page in enumerate(pages):
        page.set("name", titles[i])
        for cell in page.findall(".//mxCell"):
            if "value" not in cell.attrib: continue
            cid = cell.get("id")
            value = plain(cell.get("value"))
            if cid in byid and cell.get("vertex") == "1":
                f = byid[cid]
                value = f"<b>{f['code']} {f['title']}</b><br>" + html.escape(f["purpose"])
            value = overrides.get(i, {}).get(cid, value)
            if i == 0 and cid == "e19": value = "分层证据汇总，详见网络测试图"
            if i == 0 and cid == "e20": value = "经 5.1～5.8 预检、测试与评审"
            cell.set("value", value)
    tree.write(ROOT / "keel-delivery.drawio", encoding="utf-8", xml_declaration=True)
    reader["diagrams"] = titles

def report_markdown(report, reader):
    out = ["# 可复现校验结果", "状态：" + report["status"],
           "此结果来自交付包的评审模型检查。它不代表生产系统、真实设备或现场性能已通过验收。",
           "| 检查项 | 数量 |\n|---|---|"]
    for k, name in [("flows", "流程"), ("artifacts", "输入与产物"), ("drawio_pages", "图纸"),
                    ("structural_checks", "结构检查"), ("cases", "固定用例"), ("passed_cases", "通过用例"),
                    ("mutations", "注入错误"), ("killed_mutations", "发现错误")]:
        out.append(f"| {name} | {report['summary'][k]} |")
    out += ["## 固定用例", "| 用例 | 场景 | 结果 |\n|---|---|---|"]
    out += [f"| {i:02} | {reader['case_names'][c['id']]} | {c['status']} |" for i, c in enumerate(report["cases"], 1)]
    if "walkthrough" in report:
        out += ["## 动作数据与 CMDB 有限检查", report["walkthrough"]["scope"], "| 检查 | 结果 |\n|---|---|"]
        out += ["| " + c["name"] + " | " + ("通过" if c["passed"] else "失败") + " |" for c in report["walkthrough"]["checks"]]
    race = report["version_race"]
    out += ["## 版本竞争与恢复",
            f"在 {race['states']} 个可达状态、{race['transitions']} 条转移中，保留发布前版本核验时未发现旧结果成为当前有效证明。删除核验后发现：准入 → 完成执行 → 配置变化 → 旧结果发布。",
            "在修复获授权、无关条件满足且复验成功时，存在“登记修复 → 定向复验 → 通过 → 关闭”的路径。移除限定复验入口后无法到达关闭。这是有限模型中的条件可达性。",
            "## 验证边界", "尚未验证真实执行器、设备适配器、现场网络、完整并发及全部业务策略。路径采用显式有向集合，档位采用精确相等；测试调度、覆盖算法、窗口和豁免传播等待确认事项仍然保留。",
            "仍需进一步审查的约束：" + "；".join(reader["invariants"][i] for i in report["other_invariants_require_review"])]
    return "\n\n".join(out) + "\n"

def apply(model):
    import hashlib
    from guide import WIRING
    reader = build(model)
    rewrite_diagrams(reader)
    (ROOT / "reading-model.json").write_text(json.dumps(reader, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "keel-developer-contracts.md").write_text(markdown(reader))
    # Source attribution stays in the machine model and this archive-only index.
    trace = {"reading_version": VERSION, "source": model["source"],
             "steps": [{"display": flow_label(f["id"]), "flow_id": f["id"], "source": f["source"]} for f in model["flows"]]}
    trace["wiring_sample"] = {"flow_id": "H04", "checks": WIRING["checks"],
                              "view": "dist/app.js:renderWiringSample", "guide": "guide.py:WIRING"}
    trace["sample_sources"] = [{"name": name, "sha256": hashlib.sha256((ROOT / "source" / name).read_bytes()).hexdigest()}
                               for name in ["PRD.md", "DESIGN-SYSTEM.md", "keel-delivery-fishbone.md"]]
    trace["data_contracts"] = {"definition": "data_contracts.py", "status": "Developer-facing naming and format proposals; no production API implementation; collection and CMDB edges are explicitly authorized.",
                               "basis": ["PRD.md §3.4.3、§3.4.4、附录 A.1、A.2、A.6、A.7", "keel-delivery-fishbone.md §1.1、§4.2、§8.3"],
                               "artifact_ids": [a["id"] for a in reader["artifacts"]]}
    trace["collection_change"] = {"authority": "用户 2026-10-26 新增装机采集与公共 CMDB，并要求每卡五段动作数据", "flows": ["H07", "C01", "H02"], "basis": "PRD.md §3.3、§3.15", "definitions": ["collection.py", "walkthrough.py", "collection-event.schema.json", "DEVELOPMENT-REQUIREMENTS.md"], "verification": "verify_walkthrough.py", "hardware_sources": reader["hardware_example"]["sources"]}
    trace["collection_change"]["definition_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in trace["collection_change"]["definitions"]}
    (ROOT / "traceability.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n")
