"""Reviewable policy questions; values remain unset until an explicit user decision.

Engineering form choices are P, existing bounds are K/D, answers remain Q until
confirmed for a named project/scope. This module adds no execution dependency.
"""
import hashlib
import json
from pathlib import Path

VERSION = "1.0"

def number(key, label, unit, group, minimum=0, maximum=None, integer=False, help="", when=None, positive=False):
    field = dict(key=key, label=label, type="integer" if integer else "number", unit=unit,
                 group=group, min=minimum, required=True, help=help)
    if maximum is not None: field["max"] = maximum
    if when: field["when"] = when
    if positive: field["exclusiveMin"] = True
    return field

def text(key, label, group, help="", when=None):
    field = dict(key=key, label=label, type="text", group=group, required=True, help=help)
    if when: field["when"] = when
    return field

def choice(key, label, group, options, help="", when=None):
    field = dict(key=key, label=label, type="select", group=group, required=True,
                 options=[dict(value=v, label=l) for v,l in options], help=help)
    if when: field["when"] = when
    return field

def pos(key, label, unit, group, **kwargs):
    return number(key, label, unit, group, positive=True, **kwargs)

def count(key, label, unit, group, minimum=1, **kwargs):
    return number(key, label, unit, group, minimum=minimum, integer=True, **kwargs)

FORMS = {
"Q1": dict(
    question="每批同时测几对网卡，哪个范围失败后需要停止？",
    before="可以保存测试计划和原始结果；尚不能自动决定批次调度、停止和重试范围。",
    after="4.1 冻结调度参数；4.2～4.5 按批次执行，4.6 的采集覆盖负载前、中、后。失败只暂停选定范围。",
    proof="每个配对的开始／结束时间、尝试次数、停止对象清单；观测窗口与负载窗口的关联。",
    fixed=["4.6 的观测必须与 RDMA／多流负载重叠，不能等打流结束后才开始采样。", "取消指令发出后，仍须确认执行已终止，才能释放资源或开始重试。"],
    fields=[
      choice("schedule","测试推进方式","调度",[("per_pair","每对独立推进：链路 → IP → RDMA → 多流"),("batch_barrier","同批完成当前检查后，再进行下一类检查"),("ready","各项满足原有前置即可调度，无资源冲突时并行")]),
      count("parallel_pairs","同时运行的网卡配对上限","对","调度",help="上限还受可用资源和冲突检查约束；不是必须同时启动的数量。"),
      choice("stop_scope","一个配对失败时暂停谁","失败与恢复",[("pair","该配对"),("rail","同 rail 的本批配对"),("batch","当前测试批次")]),
      count("extra_attempts","最多额外重试次数","次","失败与恢复",minimum=0,help="0 表示不自动重试；总尝试次数 = 1 + 此值。认证失败或确定不兼容不自动重试。"),
      number("retry_delay_s","重试前最短等待","s","失败与恢复"),
      pos("attempt_timeout_s","单次执行超时上限","s","失败与恢复",help="超时代表结果待核对，不代表设备动作已停止。"),
      number("lead_s","负载前提前采样","s","采样起止"),
      number("tail_s","负载结束后继续采样","s","采样起止"),
    ]),
"Q2": dict(
    question="IP、RDMA 写读、多流测试各需要达到什么数值？",
    before="可以运行工具并保留测量值；没有对应档位的批准阈值时，不能自动给出性能合格结论。",
    after="4.3 按丢包和时延判定；4.4 分别比较写／读吞吐和时延；4.5 分开发流目标与实测下限；4.6 核对 watchdog。",
    proof="逐配对、方向、地址族及写／读的原始结果，实际负载时长、样本次数、工具版本和判据修订。",
    fixed=["本表只适用于顶部指定的型号、测试档位和基线版本。800 Gb/s 线速不是应用吞吐阈值。", "所有最低吞吐用 ≥；最高时延和最大丢包率用 ≤。缺测不参与通过率分子。", "这里只配置网络测试；不能把网络吞吐阈值直接当作 NCCL 组 busbw 阈值。"],
    fields=[
      count("ip_probes","每个方向发包数量","包","IP 可达性"),
      count("ip_bytes","每个探测包的载荷","byte","IP 可达性"),
      pos("ip_timeout_ms","单包等待上限","ms","IP 可达性"),
      number("ip_loss_pct","允许的最大丢包率","%","IP 可达性",maximum=100,help="丢包率 = 未收到应答的包数 ÷ 发包数 × 100%；与时延同时满足才合格。"),
      choice("ip_latency_stat","时延采用哪种统计","IP 可达性",[("max","最大值"),("p95","95% 分位数"),("p99","99% 分位数")],help="百分位按实际有效样本升序取第 ceil(p×N) 项；报告仍保留样本量。"),
      pos("ip_latency_ms","允许的最高往返时延","ms","IP 可达性"),
      pos("write_gbps","RDMA 写吞吐最低值","Gb/s","RDMA 写／读"),
      pos("read_gbps","RDMA 读吞吐最低值","Gb/s","RDMA 写／读"),
      pos("write_latency_us","RDMA 写最大时延上限","μs","RDMA 写／读"),
      pos("read_latency_us","RDMA 读最大时延上限","μs","RDMA 写／读"),
      count("rdma_bytes","RDMA 单条消息大小","byte","RDMA 写／读"),
      count("qp_count","每个配对的队列对数量","个","RDMA 写／读"),
      pos("rdma_duration_s","每次 RDMA 有效测量时长","s","RDMA 写／读"),
      number("warmup_s","每次测量前的预热时长","s","RDMA 写／读"),
      count("repetitions","每个配置重复测量次数","次","RDMA 写／读",help="各次结果分别保存，逐次满足上述阈值；不得只选最好的一次。"),
      pos("load_target_gbps","每个配对的发流目标","Gb/s","多流负载",help="工具要产生的负载，不是实测合格阈值。"),
      pos("load_min_gbps","每个配对的实测吞吐下限","Gb/s","多流负载"),
      count("streams","每个配对并行流数量","条","多流负载"),
      pos("load_duration_s","有效多流负载时长","s","多流负载"),
      number("imbalance_pct","各必测路径吞吐不均衡上限","%","多流负载",help="(最高值 − 最低值) ÷ 平均值 × 100%；平均值为 0 或路径缺测时不能判合格。"),
      text("watchdog_states","watchdog 允许的运行状态名称","watchdog",help="填写已核对 NOS 版本的原始状态值，以逗号分隔；配置启用与实际运行状态分别核验。"),
      count("watchdog_events","负载窗口内允许的恢复事件数","次","watchdog",minimum=0),
    ]),
"Q3": dict(
    question="数据多久采一次，最多允许多旧，长窗口如何与本次负载对应？",
    before="可以保存带时间与质量的数据；尚不能决定旧窗口能否参与本次判定。",
    after="1.7 提供有时间界限的观测；4.4～4.6 按同一负载、版本和时钟条件选择样本，缺口进入补采。",
    proof="采样时间、接收时间、原始计数及重置事件；负载起止、规则窗口、样本缺口和版本引用。",
    fixed=["当前判据包含 60 / 300 / 3600 s 窗口。ECN 恒零规则必须有完整 3600 s 及同窗口拥塞证据，不能缩短。", "PFC／ECN／CNP 周期 ≤60 s、新鲜度 ≤90 s；队列／缓冲周期 ≤10 s、新鲜度 ≤30 s。这里可确认更严格的项目值。", "计数重置、缺样、分母为零不补 0、不取绝对值；先标记不可判定，再补采。30 s 就绪有效期不是任务最长运行时间。"],
    fields=[
      pos("counter_period_s","PFC／ECN／CNP 采样间隔","s","采样与新鲜度",maximum=60),
      pos("counter_fresh_s","上述计数最大数据年龄","s","采样与新鲜度",maximum=90),
      pos("queue_period_s","队列／缓冲采样间隔","s","采样与新鲜度",maximum=10),
      pos("queue_fresh_s","队列／缓冲最大数据年龄","s","采样与新鲜度",maximum=30),
      number("clock_skew_ms","不同采集源允许的最大时钟偏差","ms","窗口对齐"),
      number("arrival_delay_s","等待迟到样本的最长时间","s","窗口对齐",help="按采样时间归属窗口，等待到期后有缺口仍不得判完整。"),
      choice("history","是否允许复用历史长窗口","历史复用",[("never","不复用，重新采足所需窗口"),("same_context","同对象、配置、规则和可比负载条件，逐次复核后复用")]),
      pos("history_age_s","历史窗口结束距本次负载开始的上限","s","历史复用",when={"history":"same_context"}),
      text("history_basis","证明历史负载条件可比的记录／规则版本","历史复用",when={"history":"same_context"},help="时间够近不等于条件相同；必须能追到原始样本和拥塞证据。"),
      count("resample_attempts","缺样或计数重置后最多补采次数","次","缺口处理",minimum=0),
    ]),
"Q4": dict(
    question="需要覆盖多少配对、方向和地址族，旧报告可以用到哪里？",
    before="可以列出已有证据与缺口；没有批准的覆盖清单时，4.7 和 5.1 不能按机器状态放行。",
    after="4.1 冻结具体路径清单；4.7 逐条核对覆盖；5.1 只消费与本次通信组、档位相符的有效证据。",
    proof="实际成员／NIC／rail／方向／地址族清单及版本；每一项的证据引用、未覆盖项与适用档位。",
    fixed=["配对数量已包含所有 rail，计算方向数时不再乘一次 rail。B300 教学案例：8 对 × 双向 × IPv4 = 16 项；写／读为 32 项。", "上面的数量只是清单核对数；必须保存稳定对象清单。A–B 与 C–D 的结果不能证明 A–C。", "端点配对不证明所有 ECMP 路径。抽样结果只能支持明确批准的样本范围。"],
    fields=[
      count("members","本次服务器数量","台","目标范围",minimum=2),
      count("rails","本次 rail 数量","个","目标范围"),
      count("pairs","同 rail 的唯一网卡配对数（已含全部 rail）","对","目标范围"),
      choice("directions","每对测几个方向","目标范围",[("both","双向"),("one","单向，方向写入清单")]),
      choice("families","本次地址族","目标范围",[("v4","仅 IPv4"),("v6","仅 IPv6"),("both","IPv4 与 IPv6")]),
      text("coverage_ref","批准的成员与路径清单版本","覆盖证明",help="例如测试计划的稳定 ID 与修订；包含具体对象，不能只提交一个总数。"),
      choice("coverage_mode","这份清单代表什么范围","覆盖证明",[("full","本次批准范围的全量配对"),("sample","批准抽样，仅对清单列出的对象有效")]),
      choice("ecmp","是否要求实际 ECMP 路径证明","覆盖证明",[("endpoint","只声明端点配对覆盖"),("routes","还需逐条实际路由／ECMP 路径证明")]),
      count("ecmp_paths","必须证明的实际路径总数","条","覆盖证明",when={"ecmp":"routes"}),
      text("ecmp_ref","实际路径枚举与观测方法版本","覆盖证明",when={"ecmp":"routes"}),
      choice("profiles","不同测试档位之间如何使用报告","下游消费",[("exact","仅相同档位可用"),("matrix","按另行批准的档位兼容表")]),
      text("compatibility_ref","档位兼容表版本","下游消费",when={"profiles":"matrix"}),
      pos("evidence_age_h","网络报告最长有效时间","h","下游消费",help="还必须匹配当前依赖版本；报告未到期不代表变更后仍可用。"),
    ]),
"Q5": dict(
    question="哪些无损告警只记录，哪些需要停止发布验收结论？",
    before="可以发布逐项规则观测；尚不能把告警等级直接转换成整个网络测试的通过或失败。",
    after="4.6 逐规则产生判定，4.7 按已确认映射汇总；风险记录与最终门禁分别保留。",
    proof="每条启用规则的原始值、完整窗口、规则版本、命中结果、质量和人工复核记录。",
    fixed=["本表确认规则到验收结论的映射；下列数值为当前内置建议判据，经审批的作用域规则版本优先，不能只修改界面显示值。", "持续暂停：60 s 内增量 ≥1；连续 3 窗口或 ≥100 帧/60 s 时执行所选升级动作。", "风暴／死锁：300 s 内 XOFF ≥90 s；同 fabric ≥3 端口同时命中时升级。", "ECN 恒零：完整 3600 s、ECN 恒零且同窗口有拥塞，三个条件同时满足才命中。", "ECN 过度标记：>5% 为 warning；2% < 比例 ≤5% 仅观察记录。明确 QoS 错配、无损队列非零丢包不能判通过。", "ECN 最大阈值所占 XOFF 缓冲比例 ≥60% 是余量风险；缓冲量不可直读时保留 estimated。当前未自动成为必须独立通过的一项。未知和规则停用不等于正常。"],
    fields=[
      choice("pfc_gate","持续暂停命中后","规则判定",[("fail","本范围判失败"),("review","人工复核前不发布结论")]),
      choice("storm_gate","暂停风暴／死锁命中后","规则判定",[("fail","本范围判失败"),("review","人工复核前不发布结论")]),
      choice("ecn_zero_gate","完整证据确认 ECN 恒零后","规则判定",[("fail","本范围判失败"),("review","人工复核前不发布结论")]),
      choice("ecn_high_gate","ECN 标记比例 >5% 后","规则判定",[("record","保留告警，由其余必需判据决定结论"),("fail","本范围判失败"),("review","人工复核前不发布结论")]),
      choice("headroom_gate","缓冲余量风险是否加入本项目验收","规则判定",[("record","只记录风险和调优建议"),("review","作为必需复核项，未复核不发布结论")]),
      choice("escalation","达到持续／多端口升级条件后","升级动作",[("pause","暂停受影响负载并通知负责人"),("ticket","保留证据并升级工单，按本范围门禁处理")]),
      pos("response_min","负责人确认告警的最长时间","min","升级动作"),
      text("escalation_owner","升级交给哪个角色／人员","升级动作"),
    ]),
"Q6": dict(
    question="哪些数据缺失必须补采，哪些需要独立补证或单独豁免？",
    before="可以展示设备能力和原始缺口；不能把近似值、缺测或不支持自动当作正常。",
    after="3.1、4.2、4.6 按具体缺口选择补采／补证／申请豁免；原始质量标记一直保留。",
    proof="每个对象的缺失能力、替代来源、适用要求、原始质量、补证结论或独立豁免记录。",
    fixed=["对端 DOM 不能证明本端全部光学指标；缓冲趋势不能冒充精确队列深度。", "无 per-XOFF 时，近似预警为发送暂停帧 ≥1000 帧/60 s 且连续 3 窗口命中；仍保留原始 unknown 与 approximation，不能冒充实测 XOFF 时长。无 WJH 且无接口 drop 时不能证明无丢包。", "这里批准的是处理办法，不是给任何设备签发豁免。每次豁免仍需具体对象、理由、审批人与期限。"],
    fields=[]),
"Q7": dict(
    question="接线核验开始前，允许留下几项配置差异，哪些差异必须先修复？",
    before="可以保存配置下发和读回；配置同步口径未确认时，不能据此给 3.3 的配置前置放行。",
    after="1.6 按差异等级、数量与白名单生成配置就绪证明；3.3 在开始前消费；3.5 的相关配置变化触发复核。",
    proof="期望和实际配置版本、逐字段差异、级别、白名单依据、读回时间和就绪证明。",
    fixed=["3.3 开始前必须已有有效的配置就绪证明。下发成功、管理可达都不能代替它。", "Critical 漂移必须先解决。允许的其他差异也不能破坏本次必需网络能力。", "不新增两个配置阶段；这里确定原有 1.6、3.3、3.5 之间的消费时点与变更复核办法。"],
    fields=[
      count("major_max","允许的 Major 差异最多几项","项","差异口径",minimum=0),
      text("major_allowlist","Major 差异白名单及批准版本","差异口径",when={"major_max":">0"}),
      count("minor_max","允许的 Minor 差异最多几项","项","差异口径",minimum=0),
      text("minor_allowlist","Minor 差异白名单及批准版本","差异口径",when={"minor_max":">0"}),
      pos("readback_timeout_s","配置下发后等待读回的上限","s","消费时点"),
      pos("config_age_s","3.3 开始时配置证明最大年龄","s","消费时点"),
      choice("recheck","3.5 的配置变化与未完成接线检查如何配合","变更复核",[("pause_affected","暂停受影响对象，完成变更和复核后继续"),("isolate_unrelated","仅无共同依赖的对象并行，受影响对象复核后继续")]),
      text("dependency_ref","配置字段与受影响对象的对应表版本","变更复核"),
    ]),
"Q8": dict(
    question="每组配置目标抽多少个，抽样通过后允许覆盖哪些目标？",
    before="可以逐台记录应用和读回；没有抽样覆盖规则时，不能把样本通过推广到其他服务器。",
    after="3.5 保存逐目标回执、抽样清单和适用范围；4.1 逐目标核验有效基线证明。",
    proof="全部目标清单、配置版本、各目标应用与读回、确定的样本 ID、检查结果和扩检范围。",
    fixed=["应用和读回仍按每个目标记录，抽检只减少额外检查，不省略这些回执。", "样本数 = min(本组目标数, max(向上取整(目标数 × 比例), 最少样本数))。分组不同应分别计算。", "有一项实际配置不合格就保留失败，不能用总体通过率冲掉。未被批准覆盖的目标仍需自己的证明。"],
    fields=[
      choice("stratum","按什么条件分成相同配置组","抽样对象",[("model_config","相同机型和配置版本"),("rack_model_config","相同机柜、机型和配置版本")]),
      count("targets","当前这组的目标数量","台","抽样对象"),
      pos("sample_pct","本组抽检比例","%","抽样数量",maximum=100),
      count("sample_min","本组至少抽检数量","台","抽样数量"),
      choice("selection","样本如何确定","选样与证明",[("seeded","固定随机种子选样，并保存最终 ID 清单"),("explicit","使用已批准的具体目标清单")]),
      text("sample_ref","选样清单版本／随机种子与算法版本","选样与证明",help="仅有台数不够；实现仍必须产生稳定目标 ID 清单。"),
      choice("applies","样本通过后的证明适用范围","失败与使用",[("sample_only","只适用于实际抽检目标"),("stratum","按批准规则扩展到本组同配置目标")]),
      text("extrapolation_ref","同组推及其他目标的批准依据","失败与使用",when={"applies":"stratum"}),
      choice("sample_failure","发现一项失败后如何扩检","失败与使用",[("full_stratum","本组全部目标扩检，修复后逐项复验"),("all_same_config","同一配置版本的全部目标扩检，修复后逐项复验")]),
    ]),
"Q9": dict(
    question="持续观察多久才能认定无邻居，采集出错最多重试几次？",
    before="可以区分有邻居、无邻居和采集错误；没有观察窗口时，空列表不能直接成为接线结论。",
    after="3.3 按双侧有效观察判断连接差异；采集失败保持无法判定；0.1 使用同范围窗口复验。",
    proof="主机和交换机每次请求状态、原始返回、观察起止、邻居 TTL、永久 MAC 与期望端口关系。",
    fixed=["双侧均采集成功、窗口完整仍无邻居，才形成链路异常线索；权限错误／超时属于无法观测。", "无邻居不直接证明是线缆、模块或网卡损坏。局部配对合格仍需完成接线四步及组长确认。"],
    fields=[
      pos("window_s","每侧有效观察窗口","s","观察窗口"),
      pos("interval_s","相邻观察间隔","s","观察窗口"),
      count("observations","每侧至少成功观察次数","次","观察窗口",minimum=2),
      pos("lldp_max_age_s","允许使用的邻居记录最大年龄","s","观察窗口",help="还需满足设备返回的邻居 TTL；配置值不能延长已经过期的记录。"),
      number("side_skew_s","两侧采样允许的最大时间差","s","双侧对齐"),
      pos("request_timeout_s","单次采集请求超时","s","失败重试"),
      count("retries","可重试采集错误的额外次数","次","失败重试",minimum=0),
      number("backoff_s","重试之间最短间隔","s","失败重试"),
      choice("empty_action","完整观察后仍无邻居时","结果处理",[("ticket","创建该端口对的链路异常工单"),("review","暂停该端口对确认并交现场复核")]),
    ]),
"Q10": dict(
    question="“全网”具体包括哪些设备和连接，时钟要同步到什么程度？",
    before="可以采集健康数据；未明确范围或 PTP 适用性时，不能宣称整个网络已健康。",
    after="1.7 按批准范围核对网络和时钟；5.1 校验通信组涉及的网络范围确实被这些证明覆盖。",
    proof="网络范围清单、预期设备／会话／端口数、逐项状态，以及时钟源、偏差和稳定窗口。",
    fixed=["当前要求包括必需 BGP 会话全部 Up、必需端口光功率合格、PTP 锁定。unused 端口不混入必需端口分母。", "只有明确批准的项目不适用决定才能免去对应范围的 PTP 检查；不使用 PTP 不能自动当成已批准。"],
    fields=[
      choice("network_scope","网络范围按什么划定","网络覆盖",[("fabric","整个指定 fabric"),("pod","指定 pod 及其全部必需上联"),("project","项目全部必需 fabric")]),
      text("network_ref","范围内对象与必需连接清单版本","网络覆盖"),
      count("devices","必需网络设备数量","台","网络覆盖"),
      count("bgp_sessions","必需 BGP 会话数量","条","网络覆盖"),
      count("ports","必需计算网络端口数量","个","网络覆盖"),
      choice("ptp","本范围是否要求 PTP","时钟同步",[("required","要求，必须锁定并满足以下数值"),("not_applicable","项目已明确决定该范围不适用")]),
      count("clock_targets","必须检查的时钟目标数量","个","时钟同步",when={"ptp":"required"},help="包含本范围需要时钟证明的主机／交换机，清单须逐一对应。"),
      number("offset_ns","最大绝对时钟偏差","ns","时钟同步",when={"ptp":"required"}),
      number("jitter_ns","窗口内偏差峰峰值上限","ns","时钟同步",when={"ptp":"required"},help="峰峰值 = 窗口内最大偏差 − 最小偏差。"),
      pos("stable_s","连续稳定观察时长","s","时钟同步",when={"ptp":"required"}),
      text("clock_source","指定时钟源及配置版本","时钟同步",when={"ptp":"required"}),
      text("ptp_exemption_basis","不适用的具体理由与批准记录","时钟同步",when={"ptp":"not_applicable"}),
    ]),
"Q11": dict(
    question="同时有失败和缺测时显示什么，哪些未关闭工单影响本次任务？",
    before="可以保存各项真实状态；尚不能只用一个总状态代替完整失败和缺口清单。",
    after="4.7、5.8 保留全部分项并按所选优先级显示总状态；0.1 只对关联对象进行受控复验。",
    proof="预期数、有效数、PASS／FAIL／BLOCKED／WAIVED 数及缺失项；关联工单、依赖版本和复验回执。",
    fixed=["必需项存在失败或缺证据时不能汇总为 PASS；空目标或未生成覆盖计划不能通过。", "无关项目／对象的工单不阻断本任务。本故障未关闭时允许限定范围复验，复验通过后再提议并确认关闭。", "同故障两次复验失败按已有流程升级；手工关闭工单不能抹去失败证据。"],
    fields=[
      choice("mixed","同范围同时存在 FAIL 与 BLOCKED 时","结果汇总",[("fail_first","总状态显示 FAIL，同时列出缺证据项"),("blocked_first","总状态显示 BLOCKED，同时列出已失败项")]),
      choice("issue_scope","工单影响范围如何关联","工单范围",[("dependency","与本次任务实际依赖的对象／路径相交"),("explicit","按工单列明的对象／路径及受影响任务清单")]),
      text("issue_policy_ref","工单与对象／任务关联规则版本","工单范围"),
      choice("critical_issues","范围内 Critical 告警如何处理","工单范围",[("block","修复并复验前暂停相关普通任务"),("check_requirements","逐项核对本次必需前置，缺证据时暂停并复核")]),
      choice("major_issues","范围内 Major 告警如何处理","工单范围",[("block","修复并复验前暂停相关普通任务"),("check_requirements","逐项核对本次必需前置，缺证据时暂停并复核")]),
      choice("minor_issues","范围内仅有 Minor 告警时","工单范围",[("record","记录告警；仍按必需验收证据判定"),("review","负责人复核之前暂停普通任务")]),
      pos("ack_h","阻断工单要求响应的最长时间","h","恢复时限"),
      pos("verify_timeout_min","一次定向复验的超时上限","min","恢复时限",help="超时先对账，不视为动作已停止或可以直接重跑。"),
      text("recovery_template","断链定向复验模板及版本","恢复时限",help="限定端口对、重采窗口和期望连接；仍核对无关前置。"),
    ]),
"Q12": dict(
    question="允许豁免多大范围、多久有效，下游如何保留这项风险？",
    before="可以保存豁免记录；没有传播策略时，不能据此自动放行所有后续通信任务。",
    after="4.7、5.1、5.8 逐次核验范围、期限和依赖版本；下游独立结论与上游豁免引用同时保存。",
    proof="被豁免要求、对象／路径、版本、审批人、理由、生效与失效时间、整改计划及每次消费记录。",
    fixed=["本项确认只定义豁免政策，不签发任何具体豁免。执行仍须有独立、有效的审批记录。", "上游 WAIVED 不改写为 PASS；权限、缺失路径和未批准缺口不能借用别的豁免。", "上游规则或对象版本变化时重新核验适用性；到期保留历史，不继续消费。"],
    fields=[
      choice("waivers","本范围是否允许走豁免审批","豁免范围",[("deny","不接受豁免，先补齐验收要求"),("bounded","允许按以下上限逐次审批")]),
      pos("validity_h","单次豁免最长有效时间","h","豁免范围",when={"waivers":"bounded"}),
      count("path_limit","单次豁免最多涉及多少必需路径","条","豁免范围",when={"waivers":"bounded"}),
      pos("path_pct","豁免路径占本次必需路径的最大比例","%","豁免范围",maximum=100,when={"waivers":"bounded"},help="同时受数量上限与比例上限约束；仍须逐条列出实际路径。"),
      pos("remediation_h","整改完成期限上限","h","整改与传播",when={"waivers":"bounded"}),
      choice("downstream","下游独立测量合格但引用了上游豁免时","整改与传播",[("independent","保留下游独立结论，同时强制展示上游豁免与风险"),("waived","按已批准传播规则汇总为 WAIVED，保留独立测量结论")],when={"waivers":"bounded"}),
      text("approval_roles","每次豁免必须由哪些角色确认","整改与传播",when={"waivers":"bounded"}),
    ]),
}

CAPABILITIES = [("dom","本端 DOM 无法读取"), ("xoff","缺少精确 XOFF 时长"),
                ("queue","缺少队列深度"), ("drop","硬件丢包遥测和接口 drop 都缺失"),
                ("buffer","缓冲量只能估算"), ("disabled","必需规则被停用")]
for key, label in CAPABILITIES:
    group = label
    FORMS["Q6"]["fields"] += [
        choice(key, "处理方式", group, [("block","补齐原始能力前保持无法判定"),("corroborate","提供独立补证，经复核后再判断"),("waiver","不自动通过，逐次申请具体豁免")]),
        text(key+"_basis", "独立补证内容与验收方法版本", group, when={key:"corroborate"}),
        count(key+"_limit", "本范围允许进入替代处理的对象上限", "个", group, when={key:"!block"}),
        pos(key+"_age_h", "替代证据或审批最长有效时间", "h", group, when={key:"!block"}),
    ]

# These associations were already described by the Q definitions but omitted
# from individual cards. They are annotations, not new producer/consumer edges.
EXTRA_LINKS = {"Q1": ["T01"], "Q2": ["T05"], "Q7": ["H06"], "Q8": ["T00"]}

def link_flows(flows):
    for q, ids in EXTRA_LINKS.items():
        for flow in flows:
            if flow["id"] in ids and q not in flow["decisions"]:
                flow["decisions"].append(q)

def attach(reader):
    payload = {"version": VERSION, "definitions": FORMS}
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    reader["decision_forms"] = {"version": VERSION, "fingerprint": digest,
        "scope": "项目范围内的业务规则确认；不是设备验收、生产执行或身份认证。",
        "source_kind": "P：确认表单及数量计算；既有约束保留；填写值未经明确确认仍为 Q。",
        "source_fingerprint": hashlib.sha256(json.dumps({"flows": reader["flows"], "rules": reader["rules"],
            "inputs": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                       for name in ["source/PRD.md", "source/DESIGN-SYSTEM.md", "source/keel-delivery-fishbone.md", "DEVELOPMENT-REQUIREMENTS.md"]}}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    for d in reader["decisions"]:
        d["form"] = FORMS[d["id"]]

def markdown(reader):
    lines = ["\n## 可填写的业务确认表", "每一项先绑定项目、对象范围、测试档位和独立基线版本，再由确认人明确确认。空值没有默认阈值。确认规则不会自动生成现场 PASS；变更规则后，旧证据需按真实依赖重新评估。"]
    for d in reader["decisions"]:
        f=d["form"]
        lines += [f"\n### {d['topic']}", f["question"], "未确认时："+f["before"], "确认后："+f["after"], "现场仍须提供："+f["proof"], "\n".join("- "+v for v in f["fixed"]),
                  "| 分组 | 要填写的项目 | 单位／选择 | 范围与说明 |\n|---|---|---|---|"]
        for field in f["fields"]:
            unit=field.get("unit") or " / ".join(o["label"] for o in field.get("options",[])) or "文本／版本引用"
            bounds=(">" if field.get("exclusiveMin") else "≥")+str(field["min"]) if "min" in field else "非空"
            if "max" in field: bounds += "，≤"+str(field["max"])
            if "when" in field: bounds += "；仅在对应处理方式启用时填写"
            lines.append("| "+" | ".join([field["group"],field["label"],unit,bounds+"。"+field.get("help","")])+" |")
    return "\n\n".join(lines)

def verify(reader, model):
    checks=[]
    def check(name, passed): checks.append(dict(name=name, passed=bool(passed)))
    check("原有 12 项问题完整保留且顺序稳定", [d["id"] for d in reader["decisions"]] == [f"Q{i}" for i in range(1,13)])
    fs={f["id"]:f for f in reader["flows"]}
    check("确认事项与流程卡双向关联", all(set(d["flows"]) == {f["id"] for f in fs.values() if d["id"] in f["decisions"]} for d in reader["decisions"]))
    check("补齐调度、watchdog、配置变更和抽检消费关联", all(all(q in fs[f]["decisions"] for f in ids) for q,ids in EXTRA_LINKS.items()))
    for d in reader["decisions"]:
        f=d["form"]; fields=f["fields"]; keys={a["key"] for a in fields}
        check(d["topic"]+"：字段可填写且有具体影响", bool(fields) and len(keys)==len(fields) and all(f.get(k) for k in ["before","after","proof","fixed"]))
        check(d["topic"]+"：类型、单位、条件与空值无默认", all(a["required"] and "default" not in a and (a["type"] not in ["number","integer"] or bool(a.get("unit"))) and all(k in keys for k in a.get("when",{})) for a in fields))
    check("规则长窗口与 ECN 边界未被表单改写", "3600" in "".join(FORMS["Q3"]["fixed"]) and "2% < 比例 ≤5%" in "".join(FORMS["Q5"]["fixed"]))
    check("确认不会自动签发豁免", "不签发任何具体豁免" in "".join(FORMS["Q12"]["fixed"]))
    return dict(scope="仅检查表单定义、约束说明和流程引用；不验证用户填值、设备性能或实际批准权限。",
                topics=len(FORMS), fields=sum(len(f["fields"]) for f in FORMS.values()), checks=checks)
