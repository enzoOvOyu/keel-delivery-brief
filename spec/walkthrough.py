"""Concrete, explicitly simulated action/data/comparison cards, kept beside field contracts."""
import copy


HARDWARE = {
    "title": "贯穿案例：2 台 B300 GPU 服务器 + 1 台 SN5610",
    "scope": "采用 DGX B300 公布配置作为 B300 服务器参考：每台 8 GPU、8 个 ConnectX-8 集群端口。SN5610 提供 64 个 800GbE 端口；案例启用其中 16 个，其余 48 个不参与本次计算网络验收。",
    "boundary": "这是讲解用的两机单交换机拓扑，所有采样值均为模拟。其他 B300 整机须绑定其 OEM 型号版本；线缆／光模块兼容性、内部拓扑、生产冗余、固件与性能基线仍需实际方案确认。",
    "identities": [
        ["项目", "project-demo", "所有案例记录的项目范围"],
        ["设备", "machine-b300-a / machine-b300-b / machine-sn5610-1", "A、B、SW 是展示简称；序列号用于核对，设备 ID 保持稳定"],
        ["端口", "port-a-c1…c8 / port-b-c1…c8 / port-sw-c01…c64", "示例稳定 ID，不能用 OS 接口名或 PCIe 地址替代"],
        ["连接", "A.c1…c8 ↔ SW.c01…c08；B.c1…c8 ↔ SW.c09…c16", "16 条线缆、32 个端点；端口标记是案例标签，适配器映射到实际面板标识"],
        ["测试范围", "rail-1…rail-8；A.ci ↔ B.ci；IPv4", "案例计划：8 个无向配对、16 个有向检查；rail 是逻辑配对，不表示 8 套独立交换网络，也不证明所有 ECMP 路径"],
        ["版本", "BOM r1 / 型号 r1 / 映射 r1 / 配置 r1 / 策略 r1", "均为模拟的已批准输入；生产必须引用实际审批版本"],
        ["采样", "2026-10-26T08:00:00Z", "案例时间；每条记录独立保存 collected_at、received_at、source、quality、raw_ref"],
    ],
    "quantities": "数量看集合：预期、已收到、有效、匹配、缺失、重复、额外分别统计。质量看来源、身份、版本、时间和采集能力。16 条记录不一定覆盖 16 个不同对象；unknown、过期或缺测不能记为合格。",
    "sources": [
        {"title": "NVIDIA DGX B300 官方配置", "url": "https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html"},
        {"title": "NVIDIA SN5610 官方硬件说明", "url": "https://networking-docs.nvidia.com/sn5000hw/introduction"},
        {"title": "NVIDIA NCCL 指标定义", "url": "https://github.com/NVIDIA/nccl-tests/blob/master/doc/PERFORMANCE.md"},
    ],
    "checked_on": "2026-10-26",
}


def raw(name, kind, value, source):
    return dict(name=name, type=kind, value=value, source=source)


def compare(item, expected, observed, result, rule):
    return dict(item=item, expected=expected, observed=observed, result=result, rule=rule)


def card(actor, action, raw_rows, comparisons, output, use, recovery):
    return dict(actor=actor, action=action, raw=raw_rows, comparisons=comparisons,
                output=output, use=use, recovery=recovery)


CARDS = {
    "F01": card("客户提供清单；网络工程师确认；平台建模", "导入两台 B300、一台 SN5610 及端口接线计划，为设备、部件和端口分配稳定身份。",
        [raw("machine_id / model_version_ref", "ID / VersionRef", "A、B → DGX-B300 r1；SW → SN5610 r1", "批准物料表与独立型号"), raw("port_pairs", "PortPair[]", "A.c1↔SW.c01 … B.c8↔SW.c16，共 16 对", "批准连接计划"), raw("serial_number / rack_position", "string / object", "SIM-A、SIM-B、SIM-SW；机柜与 U 位按物料记录", "客户清单；模拟序列号")],
        [compare("设备与连接数量", "3 台设备；16 条线缆；32 个启用端点", "3 / 16 / 32，按稳定 ID 去重", "PASS", "不能按导入行数直接计数"), compare("引用质量", "每个端点唯一绑定设备和物理端口", "32/32 可解析，无重复或悬空", "PASS", "位置／角色符合型号，禁止从待测接线反写期望")],
        "BOM r1：设备／部件／端口实体、型号版本、期望连接。未采集的数据仍标待观测。", "后续步骤使用稳定 ID 和期望集合；CMDB 建立资产索引。", "重复身份或悬空端点先修导入包，发布新物料修订。"),
    "F02": card("网络工程师制定；有权角色审批", "把案例接线方案转换成交换机端口、地址、角色和配置批次。",
        [raw("enabled_ports / unused_ports", "ID[] / ID[]", "SW.c01…c16 / SW.c17…c64", "BOM r1"), raw("rail / address_plan", "object[]", "8 个 rail；每个 rail 关联 A、B 各一端点", "批准网络设计"), raw("config_intent_ref", "VersionRef", "network-intent r1", "批准模板与变量")],
        [compare("端口覆盖", "64 个集群端口分类明确", "16 enabled + 48 unused = 64", "PASS", "管理口、存储口单独分类；不能混入计算端口分母"), compare("配置质量", "同 rail 地址、VLAN、MTU 与 QoS 意图无冲突", "已批准计划内无重复地址或角色冲突", "PASS", "具体值由项目策略决定，不能靠硬件型号猜测")],
        "plan r1：实施批次、地址与角色表、模板摘要、批准意图。", "开通与配置按批次执行，验机与测试按端口角色选择对象；CMDB 保存计划引用。", "冲突时退回网络工程师修订并重新审批受影响范围。"),
    "F03": card("平台检查；交付工程师补齐环境", "从执行节点探测引导、镜像下载、名称解析、时间同步和采集入口。",
        [raw("checks", "object[]", "引导／HTTP／DNS／时钟／采集通道，共 5 项示例检查", "执行节点探测"), raw("response / checked_at", "object / Time", "HTTP 200；摘要匹配；时间戳已保存", "探测原始回执")],
        [compare("检查覆盖", "本批计划定义的 5 项必需检查", "5/5 有回执", "PASS", "生产检查清单由所选引导方式决定"), compare("结果质量", "服务可达且内容、时钟满足已批准要求", "5/5 符合本案例配置", "PASS", "仅有 ping 或 HTTP 200 不证明镜像内容正确")],
        "env：各探测项、目标、时间、响应摘要与失败原因。", "交换机开通消费实际可用的引导与分发能力；CMDB 关联实施环境证据。", "按失败项修环境并复测，不伪装为设备故障。"),
    "F04": card("平台开通；网络工程师确认设备身份", "给 SN5610 下发最小管理配置，读取序列号并验证管理通道。",
        [raw("machine_id / serial_number", "ID / string", "machine-sn5610-1 / SIM-SW", "设备回读与批准物料"), raw("boot_receipt / management_probe", "object / object", "开通完成；管理地址可达；认证通过", "引导器与独立管理探测")],
        [compare("开通覆盖", "1 台目标交换机", "1/1 身份确认并有回执", "PASS", "收到回调还要核对请求与设备绑定"), compare("可用性边界", "管理配置读回一致", "管理通道可用；生产端口尚未证明", "PASS", "管理可达不能自动判计算网络通过")],
        "bootstrap：身份绑定、开通回执、管理探测及配置版本。", "接线采集与生产配置使用管理通道；CMDB 关联交换机身份与开通历史。", "失败先核对实际配置与回执；避免超时后盲目重放初始化。"),
    "F05": card("平台读取；现场工程师处理差异", "读取 SN5610 的 LLDP 邻居与端口状态，对照计划标记已观察和待服务器上线的连接。",
        [raw("neighbors / source", "object[] / enum", "16 个计算端口中 8 个读到邻居；source=switch", "SN5610 LLDP 回读"), raw("collection_status", "enum", "success；另外 8 个当前窗口没有邻居", "有效采集回执")],
        [compare("观测覆盖", "16 个计划连接", "已观测 8，待观测 8", "BLOCKED", "未上线端口保留缺口，不产生最终接线通过"), compare("采集质量", "超时与成功但无邻居分别记录", "成功读取后无邻居，不是采集超时", "PASS", "这条质量检查通过不等于接线通过")],
        "pre_cable：每端口的期望、交换机实测、差异及待核验列表。", "3.3 补齐主机与交换机双侧证据后正式比对；CMDB 收录包括缺口在内的预校验记录。", "待服务器上线后重采；确认接错才登记接线差异，不能凭无邻居猜断线。"),
    "F06": card("网络工程师审批；平台应用并读回", "应用 SN5610 生产配置，再独立读取运行配置和硬件生效状态。",
        [raw("intended_ref / running_ref", "VersionRef / RecordRef", "network-intent r1 / running-snapshot r1", "批准意图与设备读回"), raw("enabled_ports / qos_bindings", "ID[] / object[]", "16 个计算端口的 MTU、速率、队列、PFC／ECN 绑定", "配置解析与硬件回读")],
        [compare("应用覆盖", "计划中的 16 个启用端口", "16/16 有应用及读回记录", "PASS", "48 个 unused 不当作本次失败端口"), compare("意图一致性", "批准值 = 运行值 = 适用硬件状态", "16/16 本案例一致", "PASS", "意图、配置、硬件必须来自相应证据，不能重复读取同一份模板")],
        "net_config：预期／实际快照、差异、应用回执与版本。", "3.3 核对配置就绪；3.5 核对主机与网络 QoS 意图；CMDB 保留配置版本链。", "按端口与字段定位漂移；配置同步时序未决项仍保留，不增加隐含门禁。"),
    "F07": card("平台持续采集；网络工程师核验", "读取端口健康、告警和无损能力，形成测试前能力与状态证据。",
        [raw("port_state / negotiated_speed", "enum / Metric", "16 个端口 up；800 Gb/s", "SN5610 端口回读"), raw("capabilities / samples", "object / object[]", "ECN、PFC、队列深度等分别标 supported／unsupported", "设备能力发现与遥测")],
        [compare("基础链路", "16 个启用端口", "16/16 up 且速率符合案例计划", "PASS", "up 不证明带负载无损"), compare("能力完整性反例", "被启用规则需要队列深度", "采集器不支持队列深度", "BLOCKED", "unsupported 留作能力缺口；不补 0，不自动判正常")],
        "health 与 lossless 分别记录基础健康、能力矩阵、观测窗口、质量与规则结论。", "4.1 消费准入能力；4.6 结合实际负载判定；CMDB 索引观测与趋势。", "缺能力时按已批准替代或豁免策略处理；不存在策略则保留阻断范围。"),
    "F08": card("网络工程师组织；交付组长确认", "汇总网络设备、端口、接线、地址、配置与健康证据，生成可追溯交付包。",
        [raw("device_refs / cable_refs", "ObjectRef[]", "SW 1 台、16 条启用连接", "BOM 与网络域源记录"), raw("snapshot_refs / waiver_refs", "RecordRef[]", "每项引用明确修订；豁免原样保留", "配置／健康／审批记录")],
        [compare("清单数量", "1 台交换机、16 条启用连接", "1/1；16/16", "PASS", "设备全部端口清单仍保留角色与 unused 状态"), compare("引用一致率", "全部导出引用都能解析到指定快照", "匹配引用数 / 应核引用数 = 100%", "PASS", "分母不得为空；有豁免也不改写原始 FAIL 或 BLOCKED")],
        "network_export：交付基线、清单、快照索引、审批与一致性复核结果。", "客户交接及 CMDB 维护查询消费；不是装机和测试的统一前置。", "修复缺失引用或补齐适用证据，再生成新的导出修订。"),
    "H01": card("交付工程师发起；平台执行", "对 A、B 安装批准镜像，完成首次启动、身份注册与 SSH 信任验证。",
        [raw("install_request_id / machine_id", "ID / ID", "install-a → A；install-b → B", "装机请求"), raw("image_ref / boot_receipt / ssh_verified", "VersionRef / object / boolean", "批准镜像 r1；启动成功；true", "介质库、注册回调、SSH 实测")],
        [compare("装机数量", "2 台目标服务器", "2/2 启动与注册完成", "PASS", "回调须绑定请求、项目、序列号和一次性令牌"), compare("通道质量", "两台均完成独立 SSH 验证", "2/2 verified", "PASS", "系统启动成功不能代替 SSH 成功")],
        "host_ready：镜像与驱动版本、注册回执、主机身份和 SSH 验证结果。", "2.2 凭通道采集硬件；3.1 继续核对执行条件；CMDB 保留装机历史。", "身份冲突先隔离；通道失败走受控修复，重装不更换设备 ID。"),
    "H07": card("交付工程师发起；平台分源采集", "对 A、B 读 BMC 静态资产，再读 OS、GPU 与网卡清单；保留两个来源及冲突，不提前做验机验收。",
        [raw("serial_number / location / firmware", "string / object / object[]", "SIM-A；机柜 U 位；BMC、BIOS 与部件固件版本", "BMC Redfish／IPMI；位置以批准资产记录为准"), raw("cpu / memory / storage / psu", "object[]", "逐部件保存槽位、型号、序列号、容量／额定值及状态", "BMC；OS 可读项作为独立来源"), raw("gpus / compute_nics", "object[]", "A：8 GPU + 8 集群 NIC；B：8 GPU + 8 集群 NIC", "OS、GPU 驱动与网卡工具"), raw("permanent_mac / bdf / interface_name", "string", "永久 MAC、PCIe 地址、当前接口别名分别记录", "NIC 身份与 OS 回读"), raw("quality / collected_at / raw_ref", "enum / Time / RecordRef", "known；08:00:00Z；原始响应引用", "各次采集回执")],
        [compare("对象覆盖", "2 台设备；16 GPU；16 集群 NIC", "2/2；16/16；16/16，稳定键去重", "PASS", "存储／管理 NIC 另列，不能塞入 16 个计算 NIC 的分母"), compare("采集质量反例", "GPU 必需身份字段可读", "16 条记录中 1 条 UUID 缺失", "BLOCKED", "收到 16 不等于有效 16；保存 15 known + 1 unknown，交 3.1 判定"), compare("其他部件", "CPU、内存、磁盘、电源按批准整机 BOM", "全部记录槽位；未知预期明确列出", "待确认", "B300 是 GPU 型号，不能据此推定所有 OEM 的其他部件数量")],
        "inventory：每设备／部件的原始值、来源、采集修订、能力、质量、缺失原因。允许部分采集记录发布，不生成验机 PASS。", "3.1 比较批准期望与实测；0.2 将完整、部分、失败采集都索引到设备。", "按缺失字段重采并新建修订；BMC 与 OS 冲突并列保存，不能互相覆盖。"),
    "H02": card("平台只读采集与比对；交付工程师处理差异", "读取 2.2 快照；补采 BMC／BIOS、GPU VBIOS、NIC 固件及 GPU／NIC／RDMA 驱动。按稳定部件关联固件，按主机与内核记录已加载驱动；与批准兼容基线比对，不在此升级。",
        [raw("inventory_ref / bom_ref / model_ref", "RecordRef / VersionRef / VersionRef", "inventory r2 / BOM r1 / DGX-B300 r1", "2.2 清单与批准目录"),
         raw("gpu_ids / nic_ids / permanent_mac", "ID[] / ID[] / string[]", "16 GPU、16 集群 NIC，各自身份可解析", "分源采集快照"),
         raw("firmware_items", "object[]", "逐项：subject_ref、firmware_kind、version；BMC／BIOS 按设备，VBIOS／NIC 固件按部件。版本填设备回读值；此处不预设版本号。", "BMC Redfish 固件清单；GPU 的 nvidia-smi -q；NIC 的 ethtool -i；按能力分源保存"),
         raw("driver_items", "object[]", "逐项：machine_ref、driver_name、loaded_version、package_version、kernel_release、component_refs；GPU 驱动可关联该机 8 GPU，不复制为 8 次安装。", "主机已加载模块、nvidia-smi 与软件包查询；NIC／RDMA 按已启用能力读取"),
         raw("collection_scope_ref / compatibility_baseline_ref", "VersionRef / VersionRef", "批准采集清单决定必需版本项与分母；批准兼容矩阵约束 OEM、OS、内核、固件和驱动组合。缺失时标明缺口。", "独立批准目录；不能从本次实测生成预期"),
         raw("source / collected_at / raw_ref / quality", "enum / Time / RecordRef / enum", "每条记录保留来源、采集时间、原始输出引用；known / unknown / unavailable；异常附 reason。", "各采集器只读回执；多来源不一致分别留存")],
        [compare("硬件数量", "2×8 GPU；2×8 集群 NIC", "16/16；16/16", "PASS", "按唯一实体计数；重复行和额外部件分别报出"),
         compare("固件采集覆盖", "GPU VBIOS、NIC 固件按部件逐项覆盖；BMC／BIOS及其他必需项按批准清单", "示例：16/16 GPU、16/16 NIC 有版本回执；其他必需项另列 expected / observed / missing", "PASS", "此例只说明已列部件的数量覆盖，不能据此声明整个固件目录齐备或版本兼容"),
         compare("驱动采集覆盖", "2 台目标主机的必需 GPU、NIC／RDMA 驱动条目及部件引用齐备", "示例：GPU 驱动 2/2 主机；NIC 关联 16/16；RDMA 按批准能力列必需项", "PASS", "共享模块按 machine_ref＋driver_name＋kernel_release 去重；内核内置驱动按内核及发行包标识，不填虚构独立版本"),
         compare("版本与兼容性", "实测固件、已加载驱动及 OS／内核组合符合批准基线", "未提供实际批准版本矩阵；不使用演示版本号补齐", "BLOCKED", "采集数量完整不能证明兼容；必需缺测／冲突／缺基线为 BLOCKED，有效证据确认不兼容为 FAIL"),
         compare("质量与符合性", "必需字段完整、新鲜、身份与 BOM 一致", "16/16 GPU、16/16 NIC 有效且匹配", "PASS", "分项结果保留；某项 PASS 不代表整步 PASS；光模块降级仍按既有待确认范围处理")],
        "g1：不可变硬件核验快照；增加 firmware_items、driver_items、分项覆盖计数、兼容基线引用、差异与缺口；保留原始清单修订及当前可消费范围。",
        "3.2 按有效硬件与固件范围核对拓扑；3.3 使用稳定端口与永久 MAC；3.4 消费本次 g1 的设备与版本证据。CMDB 按 g1 发布事件索引全部固件、驱动和缺测记录，源表仍权威；不增加全局前置或新的跨步骤依赖。",
        "优先在 3.1 补采固件／驱动缺口；2.2 原始硬件清单缺失时回 2.2。升级转受控变更，核对实际加载版本再重验；换件新建部件身份并重验，不从实测修改预期。"),
    "H03": card("平台采集；工程师确认独立型号基线", "读取机内 GPU、NIC、PCIe 路径、NUMA 和 NVLink 关系，与批准整机拓扑比较。",
        [raw("gpu_id / nic_id / pcie_path / numa", "ID / ID / string[] / integer", "逐 GPU、NIC 保存上游桥路径和 NUMA", "sysfs／lspci／nvidia-smi"), raw("expected_topology_ref", "VersionRef", "approved-oem-topology r1", "厂商或经批准金样")],
        [compare("设备覆盖", "2 台共 16 GPU 与 16 集群 NIC", "16/16 GPU、16/16 NIC 有路径证据", "PASS", "有记录不代表 GPU 与 NIC 必然一对一"), compare("拓扑质量", "独立批准的槽位与连接关系", "若未提供 OEM 拓扑则无法比较", "BLOCKED", "不从 PCIe 排序或本次实测构造预期再自证")],
        "topology：机内路径快照、差异、批准基线引用及核验结果。", "3.3.1 确认 GPU–NIC 关系；3.4 发布关联映射；CMDB 保存拓扑历史。", "缺基线由负责人补齐；差异按部件／固件定位，修复后重新采集。"),
    "H04": card("平台三方比对；现场工程师改线；交付组长确认", "按四个子步骤核验 16 条线缆：先确认机内关系，再读双侧邻居，三方比对，最后人工确认。",
        [raw("expected_pairs", "PortPair[]", "A.c1↔SW.c01 … B.c8↔SW.c16，共 16 对", "BOM r1"), raw("host_neighbors / switch_neighbors", "object[] / object[]", "主机 16 条；交换机 16 条，均绑定采样时间与稳定端口", "两侧 LLDP 与永久 MAC"), raw("confirmation_ref", "RecordRef", "DL 对本次四步报告与关系版本的确认", "交付组长")],
        [compare("三方覆盖", "16 个期望端口对双侧都有有效观测", "16/16 端口对、32/32 端点可核对", "PASS", "不能将一侧 16 行当作双侧完整"), compare("明确接错反例", "A.c1 ↔ SW.c01", "双侧一致证明 A.c1 ↔ SW.c02", "FAIL", "双侧相互一致仍可能与物料期望不符"), compare("最终确认反例", "三步通过且 DL 确认当前修订", "端口对通过，未确认", "BLOCKED", "局部 PASS 不生成最终接线通过")],
        "g2：四步报告、逐对差异、确认连接与 DL 确认；各报告固定依赖版本。", "3.4 仅消费最终有效确认；CMDB 保留双侧原始数据、差异与确认链。", "缺测补采；接错修线后从 3.3.2 重验；拓扑变化先重做 3.2。"),
    "H05": card("平台生成；按批准流程发布", "把已确认物理端口与当前 OS 接口、永久 MAC、PCIe 地址、GPU 亲和和对端交换机端口关联。",
        [raw("physical_port_uid / interface_name / bdf", "ID / string / string", "port-a-c1 / 本次 OS 别名 / 本次 PCIe 地址", "3.1、3.2 与 3.3 确认结果"), raw("mapping_revision", "VersionRef", "mapping r1", "不可变映射发布记录")],
        [compare("映射覆盖", "16 个启用主机端口及各自对端", "16/16 完整；无端口身份冲突", "PASS", "稳定端口早已存在，本步骤只发布关联"), compare("版本质量", "连接确认、硬件与拓扑均适用于当前范围", "引用明确修订且仍可消费", "PASS", "接口改名更新关联修订，不换物理端口 ID")],
        "mapping r1：稳定实体间关系、当前接口别名、所依据证据与发布记录。", "3.5 根据映射配置；第 4、5 步定位实际接口和路径；CMDB 查询映射历史。", "冲突退回来源步骤修正，再发布新修订，不能覆盖旧版。"),
    "H06": card("工程师审批；平台应用、读回与验证", "按映射对 A、B 应用基线，核对驱动、端口角色、MTU 与 RoCE/QoS 意图，并记录验证范围。",
        [raw("config_set_ref / mapping_ref", "VersionRef / VersionRef", "host-config r1 / mapping r1", "批准配置与 3.4 映射"), raw("apply_receipts / readback", "object[] / object[]", "2 台主机、16 个计算端口逐项回执", "执行器与独立读回")],
        [compare("应用与读回", "2 台主机及所需 16 端口", "2/2、16/16 有回执并一致", "PASS", "下发成功不替代读回正确"), compare("验证范围", "覆盖策略批准的验证对象", "示例抽检 2/16 端口", "待确认", "仅测 2 个不能声称 16 个全通过，外推规则未批准则不发布全范围证明")],
        "g4：ConfigSet、逐项应用／读回／抽检报告，分别保存目标与实际验证集合。", "4.1 核对所需范围是否被有效基线覆盖；CMDB 保存配置历史和回执。", "失败按组件恢复能力处理；变更新建配置版本并重验受影响证据。"),
    "T00": card("交付工程师选择范围；平台准入", "冻结本轮两机、八 rail 的 IPv4 有向检查集合，核对版本、就绪、权限和资源。",
        [raw("required_pairs / directions", "TestPair[] / enum[]", "8 个 A.ci↔B.ci 配对；A→B、B→A 共 16 项", "案例测试计划"), raw("mapping_ref / config_ref / readiness", "VersionRef / VersionRef / object", "均为 r1；派发时就绪未过期", "3.4、3.5 与网络域")],
        [compare("计划数量", "2 台、8 rail、1 地址族、2 方向", "16 项唯一有向检查", "PASS", "不是 16 条物理线缆的另一种叫法；不能据此声称所有 ECMP 路径"), compare("准入质量", "当前版本、范围、权限、租约与就绪均满足", "所有必需项有明确引用", "PASS", "空计划、缺版本、过期就绪不得自动通过")],
        "test_plan：冻结目标、配对、方向、档位、依赖版本与证明义务。", "4.2～4.6 按各自维度执行；4.7 按同一计划汇总；CMDB 保存计划。", "补齐缺口后创建新尝试；层间是否严格串行仍需决策。"),
    "T01": card("平台读取双侧链路", "检查 16 条线缆的 32 个启用端点，分别读取 up 状态、协商速率和光模块诊断。",
        [raw("physical_port_uid / link_state / speed", "ID / enum / Metric", "32 个端点 up；800 Gb/s", "主机与 SN5610 端口回读"), raw("dom / quality / capability", "object / enum / enum", "模块温度、光功率等；缺能力标 unsupported", "模块诊断；按介质是否适用")],
        [compare("端点覆盖", "32 个必需端点", "32/32 有链路与速率读数", "PASS", "unused 端口不进入分母"), compare("速率差异反例", "案例批准速率 800 Gb/s", "port-a-c1 为 400 Gb/s", "FAIL", "有效观测与批准值不同；不能只看 up"), compare("诊断质量", "适用模块的必需 DOM 数据", "1 个必需项 unknown", "BLOCKED", "不适用需由介质能力说明，未知不能伪装不适用")],
        "l1：每端点链路、速率、DOM、能力、时间与判据版本。", "4.7 消费端点覆盖和结果；CMDB 索引链路与模块观测。", "按端点查模块／介质／协商配置，修复后复测受影响集合。"),
    "T02": card("平台按指定源接口发探测", "针对冻结计划逐方向进行 IPv4、ARP／邻居及可达性测试。",
        [raw("src / dst / rail / address_family", "ID / ID / ID / enum", "A.c1→B.c1；rail-1；IPv4", "冻结计划与映射"), raw("sent / received / loss", "integer / integer / Metric", "每项发 10 收 10；丢包 0%（案例数据）", "探测工具原始结果")],
        [compare("方向覆盖", "16 个有向检查", "16/16 完成", "PASS", "A→B 的成功不能替代 B→A"), compare("通信质量", "案例批准策略：探测无丢包且走指定接口", "16/16 满足", "PASS", "策略值是示例；ping 成功不证明 RDMA 或性能")],
        "l2：实际配对、源接口、方向、地址族、包数与结论。", "4.7 使用可达覆盖集合；CMDB 保留配对结果与原始引用。", "缺方向补测；已确认失败按地址、邻居或网络路径定位。"),
    "T03": card("平台执行 RDMA 工具并关联遥测", "按 16 个方向分别执行 RDMA 写、读，核对实际接口、流量类和无损队列。",
        [raw("pair / operation / traffic_class", "TestPair / enum / integer", "16 方向 × write/read = 32 项", "冻结计划与 RDMA 工具"), raw("throughput / duration / raw_ref", "Metric / Metric / RecordRef", "每项保存数值和 Gb/s 或 GB/s 单位", "工具原始输出"), raw("queue_deltas / window_ref", "object / RecordRef", "同负载窗口的队列／丢包变化", "交换机与主机观测")],
        [compare("读写覆盖", "32 项：方向与操作的组合", "32/32 有工具回执", "PASS", "仅 write 完成不能代替 read"), compare("性能判定", "同条件且经批准的性能下限", "有吞吐值但未提供批准基线", "BLOCKED", "800Gb/s 线速不是 RDMA 合格阈值"), compare("无损数据质量", "窗口重合、计数未重置、能力足够", "示例 1 项发生计数重置", "BLOCKED", "不能把负差值取绝对值或填零")],
        "l3：逐配对与操作的执行结果、性能、队列、丢包与窗口引用。", "4.6 关联负载与无损观测；4.7 汇总；CMDB 保存摘要与原始引用。", "缺基线补批准条件；计数重置需新窗口重测，保留原失败记录。"),
    "T04": card("平台打流；工程师确认负载计划", "按计划在八 rail 同时产生多流负载，记录 GPU–NIC 选择、持续时间、并发和热点。",
        [raw("load_id / rail / stream_count", "ID / ID / integer", "load-demo；8 rail；每 rail 4 流，共 32 流", "案例负载计划"), raw("elapsed / throughput / selected_interfaces", "Metric / Metric / ID[]", "实际运行 60 s；逐流保存吞吐及接口", "负载工具原始输出")],
        [compare("负载覆盖", "8 rail × 4 流 = 32 流，60 s", "32/32；实际 60 s", "PASS", "这些是示例执行参数，不是性能及长窗口验收阈值"), compare("性能质量", "同规模／拓扑／软件／参数的批准基线", "尚无可比基线", "BLOCKED", "达到发流目标不等于性能达标，60 s 不能代替 3600 s")],
        "l4：实际流集合、热点、吞吐、映射与负载窗口。", "4.6 消费负载上下文，4.7 消费覆盖与性能结论；CMDB 索引结果。", "只补测缺失或不满足条件的负载范围；不能把短窗结果外推长窗。"),
    "T05": card("平台按规则版本交叉判定", "关联同一负载、端口、优先级和时间窗的 PFC、ECN、CNP、队列与丢包。",
        [raw("load_ref / priority / window", "ID / integer / Window", "load-demo；批准优先级；连续 3600 s", "负载记录与观测窗口"), raw("ecn_delta / pfc_delta / queue_depth", "Metric", "ECN 全窗为 0；PFC 增量 > 0；队列峰值 > 0", "能力充分且未重置的计数与队列观测")],
        [compare("窗口完整性", "规则要求 3600 s 且所有必需样本齐备", "3600 s，缺样 0，重置 0", "PASS", "持续时长和采样完整性分别核对"), compare("ECN 规则反例", "拥塞条件下按规则应有 ECN 响应", "全窗 ECN=0 且同窗有拥塞证据", "命中异常", "这是单项规则结果；不自动当作整体门禁结论"), compare("缺测反例", "该规则要求的计数能力可用", "ECN 不可采集", "BLOCKED", "unknown 不能被当作数值 0")],
        "l5：每条适用规则的结果、观测引用、质量、严重度与降级原因。", "4.7 按批准汇总策略判断；CMDB 保存规则结果与趋势引用。", "补齐同窗观测或按批准替代策略处理；混合主状态待决时显式留空。"),
    "T06": card("平台汇总；交付组长审批允许的豁免", "核对五类结果是否满足本轮计划，再发布限定范围、版本和有效期的网络证明。",
        [raw("layer_refs / required_pairs", "RecordRef[] / TestPair[]", "5 类结果引用；16 个有向检查的覆盖义务", "4.1 与 4.2～4.6"), raw("coverage / missing / verdict", "object / ID[] / Result", "有效覆盖 15/16；缺 B.c8→A.c8", "按稳定配对键汇总")],
        [compare("覆盖反例", "16/16 必需方向有效", "15/16 = 93.75%", "BLOCKED", "五份报告齐全不代表计划覆盖齐全"), compare("证据质量", "版本、时间、规则与范围均一致", "旧配置下 PASS 仍保留历史，但当前不可消费", "BLOCKED", "不将旧报告和新报告随意拼成全覆盖")],
        "g5：适用目标／路径、分层引用、结果、豁免、版本与有效期。", "5.1 按通信组重新核对适用性；5.6 用于溯源；CMDB 保存历史证明。", "补测缺口再汇总；有效豁免保留 WAIVED 与审批范围，不改 PASS。"),
    "N01": card("交付工程师选通信组；平台核对", "冻结 A、B 的 16 个 GPU rank 及所用接口，核对适用的网络证据和资源。",
        [raw("members / ranks / world_size", "ID[] / object[] / integer", "2 台；rank 0…15；world_size=16", "通信组计划与实际 GPU 清单"), raw("required_paths / network_evidence_ref", "TestPair[] / RecordRef", "本组需用路径；当前可消费的网络证明", "映射、运行参数与 4.7")],
        [compare("参与者数量", "16 个唯一 rank 覆盖 0…15", "16/16，GPU 身份不重复", "PASS", "不能只看 world_size 字段"), compare("准入质量", "本组所需路径、版本、期限与档位全部匹配", "案例正向分支全部匹配", "PASS", "机器 tested 字符串或无关网络 PASS 不能替代")],
        "nccl_admission：冻结成员、rank、GPU/NIC、参数、证据和准入记录。", "5.2 准备同一环境；5.3 以整组启动；CMDB 关联通信组与设备。", "缺一成员或必要路径即补齐；不自动退化成单机交付测试。"),
    "N02": card("平台准备；工程师维护批准介质", "给 A、B 准备兼容且一致的 CUDA、NCCL、驱动、测试工具与运行参数。",
        [raw("software_manifest / media_hash", "object / string", "驱动、CUDA、NCCL、nccl-tests 均固定版本与摘要", "批准介质与节点实测"), raw("node_receipts", "object[]", "A、B 各一份实际环境清单", "执行器回执")],
        [compare("环境覆盖", "2 台均有实际清单", "2/2", "PASS", "镜像标签相同不代表内容相同"), compare("兼容与一致", "满足批准兼容矩阵及本轮冻结参数", "A、B 清单与批准修订匹配", "PASS", "仅比较两台相等仍不足，可能两台都装错")],
        "nccl_environment：逐节点软件版本、介质摘要、环境参数及验证回执。", "5.3 依据本次环境启动；5.6 对比失败条件；CMDB 保留测试环境历史。", "差异节点修复后重验整组环境一致性。"),
    "N03": card("平台统一启动并管理全组", "全组资源齐备后，通过启动屏障运行集合通信；冻结算子、消息大小和覆盖模式。",
        [raw("group_run_id / group_attempt_id", "ID / ID", "run-demo / attempt-01", "执行调度记录"), raw("rank_ready / operator / message_bytes", "object[] / enum / integer", "16 ranks；all_reduce；1073741824 B（1 GiB）", "案例运行计划与参与者回执")],
        [compare("启动屏障", "16 个 rank 同轮就绪", "16/16，全部租约有效", "PASS", "15/16 就绪不能启动部分通信组"), compare("运行完整性反例", "16 个 rank 正常结束且结果正确", "rank 7 退出；其余需停止并确认", "FAIL", "新 GroupAttempt 整组重试，不能只重跑 rank 7")],
        "group_results：每次整组尝试、rank 日志、工具原始结果、退出码和诊断。", "5.4 从原始结果取指标；CMDB 保留失败尝试及重试关系。", "确认所有参与进程终止后释放资源，重新核验并启动新尝试。"),
    "N04": card("平台解析；工程师核对场景适用性", "按工具版本提取指标与正确性结果，保持组级、节点级、消息档位和检测场景的粒度。",
        [raw("algbw / busbw / unit", "number / number / enum", "模拟 all_reduce：algbw=100；busbw=187.5；GB/s", "16 ranks 的工具原始输出"), raw("sample_key / correctness", "object / object", "group_attempt + operator + bytes + mode；错误数=0", "解析器与工具输出")],
        [compare("样本覆盖", "本次计划的算子×消息档位×模式", "示例 1×1×1=1 条组级样本", "PASS", "生产按完整计划统计，不能把单样本说成全场景通过"), compare("单位与粒度", "all_reduce 因子 2×(16−1)/16", "100×1.875=187.5 GB/s", "PASS", "这是组 busbw，不是每节点带宽；不能与 800 Gb/s 线速直接验收"), compare("性能质量", "条件可比的批准基线", "没有批准基线时仅可报告测量", "BLOCKED", "正确性与性能分别判定")],
        "metrics：组级指标、单位、原始行引用、适用场景、缺项与比较基线。", "5.5 生成报告；5.6 定位异常；CMDB 保留指标摘要与原始引用。", "解析失败保留工具原始输出；节点指标 unavailable 不可从组指标复制。"),
    "N05": card("平台生成；交付工程师核对", "将本次成员、实际覆盖、性能、正确性和未完成项组合为可复核报告。",
        [raw("report_version_ref / metric_refs", "VersionRef / RecordRef[]", "report r1；绑定 attempt-02 的结果", "5.3 与 5.4"), raw("planned / completed / missing", "object", "每个测试场景分别列计划数、完成数和缺口", "冻结测试计划与实际结果")],
        [compare("引用完整性", "每个报告结论有原始证据", "本次全部结论可定位", "PASS", "来源修订和样本键必须精确"), compare("覆盖诚实性", "分组覆盖与单通信组分别说明", "示例仅证明 2 台 / 16 GPU", "PASS", "不得外推到未参与的机柜或集群")],
        "report r1：范围、版本、原始证据、基线、测量、差异及缺口。后续分析另发修订。", "5.6 溯源、5.7 调优与 5.8 评审使用；CMDB 将报告关联每台参与设备。", "缺引用先补数据，不能靠补一句结论修复证明链。"),
    "N06": card("平台关联证据；对应工程师确认根因", "从失败组和 rank 定位 GPU、NIC、物理端口，再查看同窗网络与硬件证据。",
        [raw("failure_ref / object_refs / window_ref", "RecordRef / ObjectRef[] / RecordRef", "rank 7 → GPU → 相关 NIC → 交换机端口", "报告、映射与遥测"), raw("source / responsible_domain / confidence", "enum / enum / enum", "发现环节=NCCL；责任域=fabric；待证实或已证实", "原始失败事件与处置证据")],
        [compare("关联覆盖", "本次全部失败事件", "示例 1/1 有原始事件与对象链", "PASS", "无法定位到唯一对象时明确候选集合"), compare("根因质量", "因果证据足以支持结论", "仅同窗端口告警", "待确认", "时间相关不等于因果；不能直接判交换机损坏")],
        "trace：现象、假设、支持／反驳证据、责任域、工单与待补采项。", "0.1 定向修复、5.7 调优与 5.8 评审消费；CMDB 保存发现来源与责任域。", "缺因果证据安排受控复验；不改写最早发现环节。"),
    "N07": card("工程师提出；授权角色评审", "把已支持的瓶颈转成明确参数、目标、预期改善与验证计划。",
        [raw("recommendation_id / proposed_change", "ID / object", "recommendation-01；明确字段的旧值与建议值", "溯源证据"), raw("applicable_scope / review_status", "object / enum", "指定设备／配置修订；pending 或已确认", "审批与适用范围")],
        [compare("建议数量", "每项异常均有处置状态", "示例 1 个建议、1 个明确负责人", "PASS", "无建议也应记录确认无待办，而非漏填"), compare("变更质量", "依据、影响、回退能力及验证计划明确", "尚未批准实施", "待确认", "形成建议不直接下发设备")],
        "tuning：建议、依据、范围、负责人、采纳／拒绝／待定及版本化变更入口。", "5.8 核对清单；采纳后按配置变更流程重验；CMDB 保存调优案例。", "证据不足退回溯源；参数修改后旧性能证明按依赖重新判断可用性。"),
    "N08": card("交付组长评审并确认", "核对报告覆盖、基线、豁免与调优清单，决定本次范围是否允许进入优雅退出。",
        [raw("report_ref / tuning_ref / approval", "RecordRef / RecordRef / object", "冻结 report r2；调优清单；DL 确认人和时间", "报告、调优与人工评审"), raw("required_scope / evidence_refs", "object / RecordRef[]", "2 台 / 16 GPU；适用交付场景有有效证明", "交付计划与验证记录")],
        [compare("交付覆盖", "本次全部必需场景与目标", "逐场景核对，未执行项不能计通过", "待确认", "现场性能基线与必要场景未批准前不能给真实交付 PASS"), compare("出口边界", "评审通过后才允许清理退出", "评审确认 ≠ cleanup 已完成", "PASS", "维护态转换必须另有清理核验与归档回执")],
        "g6：报告修订、评审人、时间、结论、豁免与允许退出的范围。", "外部退出流程消费准入；CMDB 先保存评审，待 cleanup 核验事件再归档。", "不通过则回到缺口所属步骤；不能跳过清理直接标维护态。"),
    "R01": card("现场工程师修复；网络工程师或交付组长确认关闭", "对工单指定端口修线或换件，保存实际动作，然后由原验证流程生成新证据。",
        [raw("issue_id / scope / action_receipt", "ID / object / object", "issue-01；A.c1↔SW.c01；重新插线回执", "工单与现场操作"), raw("verification_ref / closure_record", "RecordRef / object", "3.3.2～3.3.4 新记录；确认人和时间", "定向复验与人工确认")],
        [compare("复验范围", "本次受影响连接及其依赖", "1/1 目标连接已复验，其余依赖重新核对", "PASS", "本故障复验例外不豁免无关阻断"), compare("关闭质量", "复验 PASS 后提议并确认关闭", "仅填‘已修复’，没有复验", "BLOCKED", "登记修复不等于修复完成")],
        "repair：动作、换件、新旧身份、复验尝试、证据与关闭确认分别保存。", "原步骤重建受影响证明；CMDB 保存完整工单与换件历史。", "复验不通过仍保持工单开放；按新证据继续处置。"),
    "C01": card("各模块自动发布；平台同步；维护人员查询", "每收到一条源记录便核对对象并建立索引。BMC、OS、邻居、配置、窗口和测试原始明细继续由源模块保存。",
        [raw("event_id / source_kind / source_ref", "ID / enum / RecordRef", "evt-inventory-a-r2；inventory；snapshot-a r2", "源记录落库后的发布事件"), raw("project_id / subject_refs / source_sequence", "ID / ObjectRef[] / integer", "project-demo；A 与其部件；2", "源模块提供的作用域与单调修订序号"), raw("source_quality / source_hash / received_at", "enum / string / Time", "known 或 unknown；内容摘要；接收时间", "源采集质量与同步回执"), raw("archive_trigger / archive_refs", "enum / RecordRef[]", "仅清理已核验事件触发最终快照；带上清理回执", "外部退出生命周期")],
        [compare("同步数量", "每条事件都有确定回执", "收到 3：新建 2 + 重复 1 + 拒收 0", "PASS", "2 个源记录不代表只有 2 个资产；对象数另算"), compare("引用质量", "项目、对象、修订、摘要都可核对", "全部索引能返回源记录", "PASS", "跨项目、未知对象、同修订不同内容必须隔离"), compare("乱序与缺测", "迟到不覆盖新版；unknown 不变正常", "r2 后到 r1：r1 入历史；当前仍 r2", "PASS", "新 unknown 记录必须显示当前未知及最后一次有效值的时间，不能保留旧绿色"), compare("维护态", "cleanup 核验后才归档并停止带内动态采集", "仅有 5.8 评审通过", "BLOCKED", "仅阻断归档完成标记，不阻断其他源模块发布")],
        "cmdb：联邦索引、逐事件回执、同步水位、隔离原因、源记录与归档快照引用。自动与人工字段分列。", "设备 360°、项目资料与 API 导出按身份追到原始证据；维护态只按需带外刷新静态资产。", "同步失败保留待同步状态，以原事件重放；源记录不丢失，CMDB 不成为全流程串行门禁。"),
}


# Nested steps have their own concrete cards, not a repeat of the parent description.
SUBCARDS = {
    "2.1.1": card("交付工程师核对；平台检查", "核对 A、B 身份、镜像兼容性、安装盘与安装前硬件状态。", [raw("machine_id / image_hash / disk_id", "ID / string / ID", "2 台明确身份、批准镜像摘要、目标启动盘", "BOM、介质与安装前探测")], [compare("预检", "2/2 身份与兼容性满足", "2/2", "PASS", "目标盘不明不得执行安装")], "装机请求内的 precheck 记录，保留检查项与版本。", "2.1.2 消费预检；通过装机源记录同步 CMDB。", "缺兼容依据或身份冲突先补齐。"),
    "2.1.2": card("平台安装；现场处理引导异常", "按已核对的目标盘安装镜像并等待首次启动。", [raw("install_receipt / os_version / boot_time", "object / string / Time", "A、B 均返回安装与首次启动回执", "引导器和主机")], [compare("安装覆盖", "2 台", "2/2 启动", "PASS", "启动只完成安装，不意味着已注册或可信")], "安装与首次启动记录，固定镜像和驱动版本。", "2.1.3 用启动回执绑定注册；CMDB 留装机历史。", "超时先核对是否已安装，不能直接重复擦盘。"),
    "2.1.3": card("主机回调；平台注册", "用一次性令牌校验注册请求、设备身份与项目。", [raw("request_id / serial_number / token_ref", "ID / string / ID", "install-a / SIM-A / 一次性凭据引用", "装机请求与注册回调")], [compare("注册一致性", "2 个请求各对应唯一设备", "2/2 匹配，令牌不重复使用", "PASS", "凭据值不入清单、报告或 CMDB")], "注册回执、稳定 machine_id 与请求绑定。", "2.1.4 按绑定身份验证 SSH；CMDB 收注册回执。", "拒绝身份冲突或重复令牌，回到可信注册。"),
    "2.1.4": card("平台验证 SSH", "校验主机指纹与执行身份，运行已授权只读探测。", [raw("host_key / ssh_probe / checked_at", "string / object / Time", "2 台指纹已核对且探测成功", "SSH 实际连接")], [compare("可执行通道", "2 台身份正确且可执行", "2/2", "PASS", "端口 22 可达不等于认证与执行成功")], "host_ready 中的 SSH 验证记录。", "2.2 开始 OS 采集；CMDB 记录通道验证历史。", "互信失败进入受控初始化修复。"),
    "3.3.1": card("平台引用；交付工程师核对", "引用 3.2 的独立拓扑核验，确认本次 GPU–NIC 关系集合。", [raw("topology_ref / gpu_nic_relations", "RecordRef / object[]", "2 台、16 GPU 与 16 集群 NIC 的关联集合", "3.2 有效拓扑证据")], [compare("关系覆盖", "全部参与 GPU、NIC 的关系有依据", "16/16 GPU、16/16 NIC 被覆盖", "PASS", "关系数量由型号决定，不强制一 GPU 对一 NIC")], "接线 step1 报告，固定拓扑修订。", "3.3.2 使用端口集合；CMDB 索引步骤报告。", "缺独立拓扑则回 3.2，不能继续猜接线。"),
    "3.3.2": card("平台双侧采集", "在有效观测时间内读取主机 LLDP、永久 MAC 与交换机邻居表。", [raw("host_rows / switch_rows / collection_status", "object[] / object[] / enum", "16 条主机记录、16 条交换机记录，分别成功", "主机与 SN5610 两个来源")], [compare("双侧覆盖", "16 对、32 个端点", "32/32 有有效观测", "PASS", "一侧 timeout 与成功但无邻居是不同事实")], "接线 step2 报告，保留原始值、端口身份、时间与采集质量。", "3.3.3 做三方比对；CMDB 索引两侧原始记录。", "缺哪一侧补哪一侧；不以单侧观测替代。"),
    "3.3.3": card("平台按稳定端点比对", "逐对比较 BOM 期望、主机看到的对端和交换机看到的对端。", [raw("expected / host_seen / switch_seen", "PortPair / PortPair / PortPair", "期望 A.c1↔SW.c01；两侧均报告 A.c1↔SW.c02", "独立期望与双侧实测")], [compare("明确接错", "三方同一端口对", "15/16 匹配，1/16 双侧一致但接错", "FAIL", "两侧相互吻合不能替代与 BOM 匹配")], "接线 step3 逐对结果、差异与候选确认关系。", "3.3.4 仅在所需结果通过后确认；CMDB 保存差异；0.1 处理明确接错。", "改线后重做 3.3.2、3.3.3，不能手改结论。"),
    "3.3.4": card("交付组长确认", "核对前三步、差异复验与关系修订，在当前有效版本上确认。", [raw("step_refs / relation_ref / reviewer_id", "RecordRef[] / VersionRef / ID", "3 份步骤报告；关系 r2；DL 身份", "步骤记录与人工确认")], [compare("最终完成", "16/16 所需连接通过且当前修订获确认", "16/16，通过；DL 已确认", "PASS", "未确认或确认后依赖变化均不能放行旧证明")], "最终接线证明与四步链、确认人、确认时间。", "3.4 才可发布映射；CMDB 索引不可变确认链。", "确认前变化回到受影响步骤，重新确认新修订。"),
    "1.8.1": card("交付组长核对", "检查所有适用网络阶段证据及有效豁免。", [raw("evidence_refs / waiver_refs", "RecordRef[]", "逐项当前修订与审批范围", "网络域与审批记录")], [compare("适用项覆盖", "批准清单内全部必需项", "无缺项、无过期引用", "PASS", "清单为空或未批准不能视为完成")], "网络验收确认记录，原结论与豁免分列。", "1.8.2 生成导出包；CMDB 收确认记录。", "补齐对应阶段缺口后重新核对。"),
    "1.8.2": card("平台导出并复核", "生成交付包，逐项复核源对象、修订与快照摘要。", [raw("manifest / references", "object[] / RecordRef[]", "交换机 1 台、16 条启用连接及全部端口角色清单", "验收确认与源表")], [compare("引用一致率", "100%", "匹配数等于应核数，分母非零", "PASS", "少一条或版本错一条均不满足")], "network_export 及一致性复核回执。", "客户交接与 CMDB 查询消费。", "修复引用后生成新导出修订。"),
    "5.3.1": card("平台运行机内诊断", "分别对 A、B 的 8 GPU 运行机内通信档，检查正确性与机内连接。", [raw("members / world_size / mode", "ID[] / integer / enum", "2 个独立的 8-rank 组；intra-node", "型号允许的机内计划")], [compare("机内覆盖", "2 台各 8 GPU", "2/2 组，各 8/8 rank", "PASS", "两个组结果不能拼成一个 16-rank 结果")], "各自的机内 GroupAttempt 原始结果。", "5.4 单独标机内诊断；CMDB 按设备关联。", "失败整组重试；机内通过不能取代跨机交付证明。"),
    "5.3.2": card("平台启动跨机通信组", "将 A、B 的 GPU 按批准计划组成 16-rank 组，使用确认的网络接口。", [raw("ranks / interfaces / operator", "object[] / ID[] / enum", "rank 0…15；冻结接口集合；all_reduce", "运行计划与映射")], [compare("跨机参与者", "2 台、16 rank", "16/16 就绪并统一启动", "PASS", "缺节点不能静默降成单机")], "跨机尝试、rank 回执、原始输出和诊断。", "5.4 计算本组指标；CMDB 保留组与设备关系。", "任何 rank 失败均确认全组停止后新建尝试。"),
    "5.3.3": card("平台执行批准覆盖模式", "对当前全部交付目标执行计划；本案例全目标仅为 A、B 两台。", [raw("coverage_mode / planned_members / actual_members", "enum / ID[] / ID[]", "single_communicator；计划 16 GPU；实际 16 GPU", "冻结交付范围和执行回执")], [compare("全目标覆盖", "当前批准目标 16 GPU", "16/16，单一通信组", "PASS", "若改为分组覆盖，必须另报 grouped_coverage，不能叫全域单组")], "全目标模式、实际成员与对应尝试结果。", "5.4、5.5 保持覆盖模式；CMDB 关联交付范围。", "未覆盖目标明确列出，不从子组通过推导其他规模通过。"),
}


def attach(reader):
    assert set(CARDS) == {f['id'] for f in reader['flows']}
    reader['hardware_example'] = copy.deepcopy(HARDWARE)
    artifacts = {a['id']: a for a in reader['artifacts']}
    for f in reader['flows']:
        f['walkthrough'] = copy.deepcopy(CARDS[f['id']])
        f['walkthrough']['output_refs'] = f['outputs']
        f['walkthrough']['routes'] = [dict(artifact_id=a, consumers=artifacts[a]['consumers'], terminal=artifacts[a]['terminal_consumer']) for a in f['outputs']]
        for sub in f['substeps']:
            sub['walkthrough'] = copy.deepcopy(SUBCARDS[sub['code']])
    assert set(SUBCARDS) == {s['code'] for f in reader['flows'] for s in f['substeps']}


def card_markdown(c):
    out = ['**现场动作** — ' + c['actor'] + '：' + c['action'], '**原始数据（模拟值）**', '| 字段 | 格式 | 示例 | 来源 |', '|---|---|---|---|']
    out += ['| ' + ' | '.join(r[k].replace('|', '／') for k in ['name', 'type', 'value', 'source']) + ' |' for r in c['raw']]
    out += ['\n**比对判定（逐项结论，不代表整步已通过）**', '| 项目 | 期望 | 观测 | 判定 | 规则 |', '|---|---|---|---|---|']
    out += ['| ' + ' | '.join(r[k].replace('|', '／') for k in ['item', 'expected', 'observed', 'result', 'rule']) + ' |' for r in c['comparisons']]
    out += ['\n**输出产物** — ' + c['output'], '\n**下游使用** — ' + c['use'], '\n**失败继续** — ' + c['recovery']]
    return '\n\n'.join(out[:2]) + '\n\n' + '\n'.join(out[2:])


def context_markdown(reader):
    h = reader['hardware_example']
    return '\n\n'.join(['## ' + h['title'], h['scope'], h['boundary'], h['quantities']] + ['- ' + '：'.join(r) for r in h['identities']] + ['核对日期：' + h['checked_on']] + ['- [' + s['title'] + '](' + s['url'] + ')' for s in h['sources']])
