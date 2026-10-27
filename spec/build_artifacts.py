#!/usr/bin/env python3
"""Build the review model, human contract document and editable draw.io diagrams.
The model is a proposal for reviewing the supplied specification, not a production API.
"""
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
import json, hashlib, html

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source' / 'keel-delivery-fishbone.md'
MODEL_VERSION = '1.1-collection-review'
external = {
 'project': ('项目模板与商定基线', '客户／网络工程师／项目模板，原文§1、§3.1'),
 'model': ('独立型号与拓扑基线', 'DeviceModelVersion，原文§3.3'),
 'media': ('已审批介质与兼容矩阵', '介质库／参数目录，原文§3.2、§3.4'),
 'policy': ('已确认的判据与覆盖策略', '项目模板／参数目录／有权审批人；未定值见Q清单'),
 'auth': ('授权与资源约束', 'RBAC／执行器资源租约／审批记录，原文§8'),
 'readiness': ('FR-0.8.1动态就绪证明', '网络域接口；执行前刷新，默认TTL30s'),
 'observations': ('主机／交换机实时观测与能力标记', '主机采集／FR-0.8；须保留对象、时间和source'),
 'window': ('绑定本次负载的网络观测窗口', '持续网络采集；与打流实例关联方式为P建议，Q3待确认'),
 'human': ('人工处置与确认记录', 'NE／DL／现场人员，原文§1.2、§8.2'),
}
flows=[]
def add(id, name, group, source, purpose, inputs, resources, guards, actions, outputs, post, failure, retry, invalidation, decisions='', effect='read', note=''):
    flows.append(dict(id=id,name=name,group=group,source=source,purpose=purpose,
        inputs=inputs.split(),resources=resources,guards=guards,actions=actions,
        outputs=[dict(id=a,name=b) for a,b in outputs],post=post,failure=failure,
        retry=retry,invalidation=invalidation,decisions=decisions.split(),effect=effect,note=note))

add('F01','统一 BOM 导入／建模 · N-S1','网络底座','§3.1、§4.2','建立可引用的稳定对象与期望连接。',
 'project model auth','导入包、字段映射、型号版本、凭据引用；凭据值不入报告。',
 '包完整、引用可唯一解析、格式／一致性／工程校验无BLOCK；不得用单文件宽表冒充网络物料准备。',
 '只读预览→确认提交；标准包服务器与网络物料同事务提交；生成稳定实体与差异清单。',
 [('bom','BOM版本／稳定实体／期望端口连接')],
 '同版本同摘要幂等；同号异摘要不能覆盖；端口和breakout子口可在G3前被引用。',
 'BLOCK阻断提交，WARN进入问题清单；不写半套服务器／网络关系。',
 '修正后以新版本重导，不覆盖历史。','BOM／型号／位置关系变化影响下游相应对象。',effect='write')
add('F02','网络实施规划 · N-S2','网络底座','§3.1','把已经商定的网络方案转换成可执行批次和配置输入。',
 'project model bom policy','已发布模板、变量、IPAM规则、角色与breakout方案。',
 '商定基线可引用；模板和变量匹配，版本依赖齐备。','按导入规则绑定地址、命名、模板、角色与实施批次；不替客户设计网络。',
 [('plan','网络实施计划／模板与变量快照')],
 '每个配置变量可追溯到商定基线或允许的默认值；设备集合和顺序可解释。',
 '缺方案／变量拒绝渲染；禁止猜测DSCP或rail。','修正模板或绑定后重新渲染新版本。','模板／意图／角色／参数版本变化使相关渲染失效。',effect='write')
add('F03','环境就绪 · N-S3','网络底座','§3.1','证明引导、采集和分发依赖可用。',
 'plan media auth','Kea、引导服务、采集器、仓库与管理通道。','目标批次和已审批介质确定。',
 '执行环境自检，记录每个依赖的结果及时间。',[('env','环境自检记录')],
 '必需自检项全绿才可进入N-S4；检查完成不代表设备已开通。','缺服务／凭据／介质则阻断对应开通批次。','修复依赖后重查；不缓存永久ready。','环境／凭据／介质变化需重新检查。')
add('F04','零接触开通 · N-S4','网络底座','§3.1','使交换机身份可信且具备最小管理能力。',
 'bom plan env media auth','Kea／ZTP／SZTP、批准的引导脚本、网络设备凭据。',
 '环境就绪；身份匹配，无SN／MAC冲突；引导仅包含批准的最小隔离／管理配置。',
 '识别身份→下发引导数据→记录各步回执与可管理状态；ZTP完成与业务配置同步分开记录。',
 [('bootstrap','身份绑定／管理可达／ZTP阶段回执')],
 'ZTP完成只证明开通；NP-2还需要Golden配置证据。管理可达的中间事实可被后续预检读取，不等于整个N-S4已PASS。',
 '未命中隔离、冲突拒绝；失败保留阶段原因。','按引导策略有限重试；换SN走批准的换件身份流程。','身份／介质／设备替换影响后续证明。',effect='write')
add('F05','网络侧线缆预校验 · N-S5','网络底座','§3.1、§4.1、§5','检查当前可观测网络连接，保留尚未出现的服务器观测缺口。',
 'bom bootstrap observations','交换机LLDP／FDB／ARP／接口／DDM读取能力。',
 'BOM端口存在；本次应可观测交换机互联的采集能力可用。','对已可观测链路与BOM比较；未装OS的服务器接入口保持pending。',
 [('pre_cable','网络预校验／pending端口清单')],
 '服务器端口对不能在此获得NP-3 PASS；FDB／ARP不是三方LLDP的替代。','明确差异按T类开单；必需证据缺失标unknown。','受影响链路增量复采，不扩大到所有设备。','接线／端口／BOM改变使受影响预校验失效。')
add('F06','网络生产配置闭环 · N-S6','网络底座','§3.1、§4.1、§10 Q7','证明批准配置已在交换机生效。',
 'bom plan bootstrap media auth','Doublecheck、快照、结构化diff、分析／预演、审批、PushJob与独占设备租约。',
 '设备管理通道可用；首次开通检查身份与隔离态，不要求未装机服务器LLDP完整；未批准不得下发。',
 '渲染→Doublecheck→备份／比对→修复计划→分析／预演→预检与审批→灰度下发→复采验证。',
 [('net_config','intended／running快照及Golden比对证据')],
 '结合ZTP完成记录形成NP-2判断；命令成功不等于IN_SYNC；Major／Minor允许性按Q7待决策。','任一复核失败阻断；变更失败按能力恢复并保留真实设备状态。',
 '新计划或修改后的范围需要新审批；结果不明先对账，不盲重放。','意图／设备配置／规则变化影响G2准入及相关G4／G5／G6证据。','Q7',effect='write')
add('F07','全网健康与无损证据 · N-S7','网络底座','§3.1、§4.1、§7','提供网络准入事实和可被测试消费的观测证据。',
 'bom net_config observations policy','BGP／PTP／DDM、PFC／ECN／CNP／队列／缓冲／丢包能力与规则版本。',
 '配置闭环有效；目标fabric／pod范围已定义；采集来源与能力可识别。','检查BGP100%Up／光功率阈内／PTP锁定；评估无损能力和LL结论，记录unknown与新鲜度。',
 [('health','NP-5全网健康证明'),('lossless','NP-6能力／基线与LL证据索引')],
 '健康未过使G5／G6准入BLOCKED；明确降级不是自动允许PASS。运行期新观测仍须绑定本次测试。','不可采集为unknown，不能补0；全网范围、PTP适用性、降级规则仍需策略。',
 '恢复采集或处理异常后复核；不以规则停用消除unknown。','网络拓扑／配置／规则变化和新鲜度过期影响下游。','Q3 Q5 Q6 Q10',note='运行期采集持续存在，不等待G5结束才启动；具体窗口编排属于P建议与Q3。')
add('F08','网络验收与导出 · N-S8／N-S9','网络底座','§3.1','生成可核对的网络交付证据包。',
 'bom plan bootstrap pre_cable net_config health lossless human','快照索引、审批豁免、导出一致性复核。','适用N-S阶段证据完成或有有效豁免；引用和快照一致。',
 'N-S8确认验收证据；N-S9导出设备／端口／连接／地址／状态及配置版本。',[('network_export','网络验收包／交付基线')],
 '逐项引用一致率100%；被豁免问题仍保留原结论；该包不是G2启动的额外总门禁。','缺引用／版本不一致则拒绝导出完成。','补齐同一快照链后重生成新导出版本。','包保持历史不可变，新状态产生新版本。',effect='read')
add('H01','装机与SSH互信','装机','§3.2','把裸机变成身份已确认、可执行采集的服务器。',
 'bom model project media auth','UEFI HTTP Boot／Legacy PXE、HTTP分发、cloud-init、平台SSH公钥、回调令牌。',
 'BOM绑定型号、镜像已审批且兼容、hostname规则确定、装机硬件预检通过。','安装→启动→绑定请求与身份的注册回调→SSH首连验证。',
 [('host_ready','OS／驱动版本、注册回执、SSH established')],
 'OS启动与SSH信任分开确认；只有具备已验证执行通道才进入G1。','预检失败中断；互信失败进入受控修复，不能冒充装机后可执行。',
 '重装保留物理身份但使旧交付证据失效；bootstrap／repair只允许限定初始化动作。','重装、镜像、主机身份和信任变化影响后续。',effect='write')
add('H02','预收集 · G1','验机','§3.3','记录硬件与系统事实，为拓扑和线序提供输入。',
 'bom host_ready model observations','SSH或Agent采集；BMC为独立来源。','装机回调和SSH信任有效；必需字段与能力策略已定义。',
 '采GPU／NIC／系统／永久MAC／DOM／拓扑摘要；仅允许LLDP所需临时接口up及lldpd。',
 [('g1','预收集快照与G1证据')],
 '完整率100%、永久MAC与BOM一致；DOM降级接受策略不得擅自补齐。','缺必需数据BLOCKED；明确不一致FAIL；允许的豁免由DL记录。','按对象重采；不在此应用正式GPUrail／RoCE配置。','部件、OS、BOM／型号及策略变化影响拓扑和后续。','Q6')
add('H03','设备内PCIe拓扑 · FR-4.8','验机','§3.3、§5','证明GPU-NIC内部关系符合独立预期。',
 'g1 model observations','sysfs／lspci／nvidia-smi；审批的厂商或金样拓扑。','有效G1与独立型号预期在位。','核对上游路径、NUMA、NVLink、LnkCap／LnkSta；保留原始输出与差异。',
 [('topology','PciTopologySnapshot／TopologyDiff')],
 '实际拓扑不能反推“预期”再自证；型号槽位设计是判定基准。','差异T7；缺预期BLOCKED；不能一律刷BIOS。','按证据修复后定向重验；两次仍失败升级DL／厂商。','换卡、BIOS／固件、机型定义或拓扑变化影响G2／G3／G4／G6。')
add('H04','四步线序验证 · G2','验机','§4.1、§5','证明期望物理端口连接与两侧实测一致，并获最终确认。',
 'bom g1 topology pre_cable net_config bootstrap readiness observations human','lldpd／交换机回读／DOM；逐目标握手；DL确认。','G1和拓扑有效，NP-1／2／4满足，网络域在线；NP-3不是启动条件。',
 'Step1引用GPU-NIC关系→Step2双侧LLDP与MAC→Step3三方按端口对比对并写确认关系→Step4 DL确认。',
 [('g2','StepReport链／线序确认／G2／NP-3')],
 '各步版本化；Step3局部PASS不是整个G2完成；G2通过后才可发布G3。','任一步发现问题阻断后续；明确线缆差异T1～T6，缺测BLOCKED。',
 '一般从Step2增量重采；拓扑变更重走FR-4.8和Step1；工单关闭依赖重验PASS。','端口／线缆／部件／BOM／拓扑变化影响端口对及下游映射。','Q7 Q9',effect='read')
add('H05','发布映射 · G3','验机','§3.3、§4.2','发布所有后续配置和定位使用的同一映射版本。',
 'bom model g1 topology g2','PortModel查询视图、角色方案、版本化发布。','G2有效、NP-3存在；启用角色所需映射100%覆盖且无冲突。','关联物理端口、OS接口、永久MAC、BDF、交换机端口及GPU亲和。',
 [('mapping','不可变MappingRevision及G3')],
 '稳定实体不在此首次创建；批准后发布不可变映射，消费者冻结明确版本。','覆盖缺失／冲突阻断G4；不按BDF排序猜物理连接。','修正来源／关系后发布新版本，保留旧版。','新映射只使依赖旧关系的下游证据失效，不篡改历史。',effect='write')
add('H06','服务器基线配置 · G4','G4连接','§3.4','把确认后的关系转换为真实服务器配置并验证。',
 'mapping project model media net_config policy auth','ConfigSet、参数快照、角色绑定、恢复方案、设备独占。','有效G3；型号／角色／介质兼容；主机RoCE意图与网络意图一致。','GPUrail／分割／绑定／RoCE／驱动等配置→读回→按已确认策略抽检。',
 [('g4','ConfigSet应用／读回／抽检记录及G4')],
 '下发回执和配置验证分开；有效G4范围须可证明覆盖本次G5目标。','意图不一致拒绝导入；失败按组件能力恢复；不假定固件总可回滚。',
 '新配置新版本；失联先用回执和设备实况对账。','影响网络／拓扑的变更触发相应重新验证及G5／G6失效。','Q8',effect='write')
add('T00','网络测试准入与测试计划','网络测试','§3.5、§6.1、§8.3','固定本次测试范围和证明义务，避免范围在执行中漂移。',
 'g4 mapping health lossless readiness policy auth','测试工具、NIC／路径／rail、测试窗口及资源约束。','有效G4、映射和角色在位；NP-4／5／6有效；无阻断本次普通任务的告警。','冻结目标／路径／档位／版本，输出需要哪些层、哪些配对、哪些时间窗口的计划。',
 [('test_plan','冻结测试计划与准入记录')],
 '计划对象化是P建议；覆盖算法与层间调度尚需Q1～Q4确认；未定义策略不能默认为true。','缺前置BLOCKED；工单诊断只有限定例外。','仅对显式合格子集重新提交；不静默扩大。','版本／成员／资源／就绪变化需在消费时复核。','Q1 Q2 Q3 Q4',effect='read',note='P建议的计划对象是实现组织，不新增业务门禁编号。')
add('T01','L1 链路层测试','网络测试','§6.2 L1','核对所需端口的基础链路事实。',
 'test_plan mapping observations policy','PortModel／网口面板数据；host与switch的DOM分开。','本次端口和角色范围确定；必需观测新鲜。','检查up、协商速率、DOM基线，复用现有采集源。',[('l1','L1端口级结果／证据引用')],
 '按本次必需角色判定；unused不误报，必需compute不能关闭绕过。','明确异常FAIL；缺必需观测BLOCKED；DOM降级依Q6。','复采或修复后定向复测。','端口／角色／配置／采样过期影响有效性。','Q6')
add('T02','L2 IP／ARP可达性','网络测试','§6.2 L2','证明计划中的同rail NIC配对可达。',
 'test_plan mapping g4 policy','IPv4／IPv6档位、ping、配对抽样与批次策略。','有可执行配对计划与已确认超时／丢包等判据。','per-NIC网状探测；快速默认32对端/NIC，全量分批；保留实际测试集合。',[('l2','L2配对可达结果与覆盖集合')],
 '结果只证明已测配对；具体ARP检查与探测阈值不由开发猜测。','明确不可达FAIL；策略缺失／未覆盖项不能PASS。','只复测受影响配对；配对方向策略待Q4。','地址／VLAN／映射／档位改变影响结果。','Q1 Q2 Q4')
add('T03','L3 RDMA通路测试','网络测试','§6.2 L3、§7','证明RDMA写读与流量类／无损队列条件。',
 'test_plan mapping g4 lossless policy observations','ib_write_bw／ib_read_bw、FR-0.8.4计数。','RDMA目标与已批准流量类配置确定；能获得所需计数能力。','per-rail、per-NIC-pair写／读；核对RoCE v2映射及无损队列丢包；默认full，可选matrix-sample。',[('l3','L3写读／带宽／丢包／PFC及窗口上下文')],
 '队列无丢包需要可用证据；写读连通不自动证明性能合格。','映射错／实际无损drop／读写失败为异常；计数缺失unknown，必需证据不足BLOCKED。','按配对定向复测；读写结果分别保留。','配置／路径／规则／工具及档位变化使相关证据失效。','Q1 Q2 Q3 Q4')
add('T04','L4 端到端流量测试','网络测试','§6.2 L4','验证面向集合通信热点的多流网络表现。',
 'test_plan mapping g4 policy auth','iperf3／ib_send_bw、多流、DSCP／流量类、受控窗口与批次。','GPU-NIC映射与热点覆盖计划有效；互斥与测试资源满足。','按per-GPU关联NIC打流；快速30s／全量5min；记录负载计划与实际覆盖。',[('l4','L4吞吐／热点覆盖／负载时间上下文')],
 '“全带宽打流”是负载目标，不是合格百分比；性能合格值需策略提供。','执行错误或已定义阈值不达标为FAIL；无阈值或缺覆盖不伪造通过。','按受影响批次／路径重测，保留真实重试范围。','映射／流量矩阵／参数／网络配置变化影响基线。','Q1 Q2 Q3 Q4',effect='load')
add('T05','L5 PFC／死锁／拥塞验证','网络测试','§6.2 L5、§7','将负载上下文与网络规则观测合并为可解释结论。',
 'test_plan l3 l4 lossless window policy','watchdog状态、PFC／ECN／CNP／队列／缓冲／WJH、规则版本。','所需窗口、能力、路径和规则匹配；不能把缺采样补0。','核对watchdog；LL-01／02与暂停风暴，LL-03／04与ECN合理性；保留LL-05／06／07相关证据。',[('l5','L5规则交叉验证／窗口与降级记录')],
 '结果同时声明已判定内容和不可判定内容；LL告警级别到门禁映射待确认。','明确违反已定义判据时FAIL；必需窗口不完整或能力不足时BLOCKED。仅出现拥塞不能直接推定G5失败，warning是否阻断由策略决定。','先补能力或观测窗口再评估；不通过关闭规则“恢复正常”。','规则、配置、负载上下文、样本新鲜度变化影响可消费性。','Q1 Q3 Q5 Q6',note='L3／L4→L5为判定的数据依赖；建议观测与负载并行，不能解释成打流结束后才开始采样。')
add('T06','汇总网络门禁 · G5','网络测试','§6.1、§8.1、§8.3','发布本次范围可以支持哪些后续通信任务的证明。',
 'test_plan l1 l2 l3 l4 l5 policy human','按路径／档位的覆盖计算、规则聚合与DL豁免记录。','各必需结果持久化、引用版本有效、覆盖达到要求。','核对必需项与required_path_coverage；保留逐项FAIL／BLOCKED与豁免；形成报告。',[('g5','G5 GateEvidence／分层报告／网络基线')],
 '所需有效结果全PASS才为PASS；G5自身必需项被豁免则WAIVED；抽样不可外推。','混合结论优先级未定，保留明细；无覆盖和无证据禁止PASS。','修复后产生新结果与新证据；不改旧报告。','目标／版本／路径／档位／规则变化或证据过期阻断后续消费。','Q4 Q5 Q11 Q12',effect='write')
add('N01','NCCL环境预检 · S1','NCCL','§3.6、§9','证明这一个通信组可安全、可解释地发起测试。',
 'g5 mapping topology g4 health lossless readiness media policy auth','GroupRun成员／GPU／rank与网络接口，基线与软件版本。','跨机档要求G5覆盖组所需路径和档位；NP-5／6复验；GPU／驱动／RAS／P2P／NUMA／NVLink检查。','按冻结组逐项校验并建立准入记录。',[('nccl_admission','NCCL组准入记录')],
 '纯机内NVLink诊断可在有效G4与资源约束下先行，但该路径不产出G6交付通过。','缺基线、覆盖或必需诊断证据BLOCKED；不按机器状态放行。','只对新准入快照执行；修复组成员后重新预检。','组成员／接口／软件／配置／基线变化影响准入。','Q4 Q10 Q12')
add('N02','NCCL环境准备 · S2','NCCL','§3.6','使组内使用冻结且一致的软件环境。',
 'nccl_admission media g4 auth','已审批NCCL／nccl-tests包、缓存与校验和。','准确兼容组合确定；分发对象在当前组内。','分发／校验缓存，核对各节点驱动、NCCL和参数一致性。',[('nccl_environment','环境一致性／介质摘要回执')],
 '缓存命中不省略内容身份核验；准备成功不是测试通过。','分发或一致性失败阻断组启动。','同摘要幂等分发；损坏介质不能无限重传。','介质／参数／组成员变化需重新核验。',effect='write')
add('N03','通信组执行 · S3／S4／S5','NCCL','§3.6、§9','按机型和coverage_mode执行机内到跨机的通信测试。',
 'nccl_admission nccl_environment mapping topology policy auth','整组GPU／NIC资源预留、启动屏障、rank/world_size、rendezvous。','整组资源齐备；组成员、算子、消息大小、基线和coverage_mode已冻结。','S3机内→S4小组／rack→S5全目标分组或单通信组；组内统一启动。',[('group_results','GroupRun／GroupAttempt原始结果与诊断')],
 'grouped_coverage与single_communicator分别报告；完整组尝试才可用于对应组结论。','组内失败结束其余参与者并回收诊断；断线不能当终止成功。','新GroupAttempt整组重建，不只重跑失败rank。','成员／软件／基线／网络与配置变化使对比前提改变。',effect='load')
add('N04','结果回收与聚合 · S6','NCCL','§3.6、§9','将原始结果转换为保持测量粒度的指标。',
 'group_results policy observations','结果JSON、对象存储、DCGM及独立节点探针。','结果来源、单位、规模／算子／消息等对比条件可核对。','回收原始数据；对同条件GroupRun聚合P10／P50／P90；独立节点测量单独保存。',[('metrics','NCCL指标／SC场景矩阵')],
 '组级busbw不能复制为节点指标；独立数据缺失为unavailable；链路Gb/s与组级GB/s不混比较。','缺必需场景基线或独立数据按策略BLOCKED／显式豁免。','补测或重新回收有来源的数据；不从聚合结果伪造明细。','聚合规则／基线版本变化产生新计算版本，不覆盖原始观测。')
add('N05','报告生成 · S7','NCCL','§3.6','生成可追溯到具体测试规模和尝试的报告。',
 'metrics group_results policy','HTML／PDF／CSV报告生成与持久化。','报告所有引用可解析，coverage_mode与实际执行一致。','生成报告及原始数据索引，标注失败、缺失和场景判定。',[('report','NCCL基础报告与原始数据索引')],
 '报告生成成功不是G6评审通过；后续溯源／调优完成后引用同一证据链汇编。','缺结果／悬空引用不得标完整。','可从已冻结原始数据重生成，版本可追溯。','后续新尝试或新基线生成新报告，不修改旧报告事实。')
add('N06','失败溯源 · S8','NCCL','§3.6、§9','将异常关联到可处置对象及历史基线。',
 'report group_results metrics mapping topology g5 lossless observations','PortModel、DCGM、工单、FR-0.8无损与日志证据。','失败来源与端口／组身份可关联；比较指标语义一致。','关联端口、G5同路径历史、NUMA／HBM／温度和交换机LL证据。',[('trace','溯源章节／工单关联／证据包')],
 '找出交换机根因仍保留source=g6，另记responsible_domain=fabric；证据不足不宣称已确诊。','无法定位保留unknown与需补数据，不强制选硬件坏。','补诊断后添加新分析记录与引用。','映射／证据版本变化时按历史上下文解释旧异常。')
add('N07','调优建议 · S9','NCCL','§3.6、§9','形成可审查且能回流版本化配置的改进建议。',
 'report metrics trace policy','当前值、建议值、依据、风险、责任角色。','建议具有实测或规则依据，适用于当前型号／版本。','生成参数建议；服务器落地走ConfigSet，网络建议进入负责人修复计划。',[('tuning','调优清单／版本化变更入口')],
 '建议生成不直接改设备；建议被采纳后重新评估受影响证据。','无依据的值标待验证，不作为自动修复。','修改建议产生版本；实际变更复用H06／F06，不另开旁路。','变更后旧G5／G6依赖按影响范围失效。')
add('N08','报告评审 · G6','NCCL','§3.6、§9','确认本次交付测试达标并完成调优清单确认。',
 'report metrics trace tuning group_results policy human','DL评审、完整报告和SC判据。','必需场景有有效结论；报告覆盖与目标一致；调优清单已确认。','评审冻结报告版本，记录通过／失败／阻断／允许的豁免。',[('g6','G6评审与退出准入证据')],
 'G6解锁优雅退出，不代表cleanup已完成或项目delivered。','不达标定向重测；缺证据不可凭签字改PASS。','补测／调整后评审新报告版本；通信组仍整组恢复。','配置／软件／范围／基线变化影响后续使用。','Q11 Q12',effect='manual')
add('R01','受控修复与定向重验','恢复闭环','§8.2、§8.3','让失败可以被修复，同时不绕过无关门禁。',
 'human auth bom','issue.repair／issue.verify、原失败证据、冻结修复目标与动作。','工单、批准范围、信任、兼容与资源条件满足；只允许针对本故障的恢复例外。','登记实物或配置处理→按T类编排定向复验→PASS后提议关闭→NE／DL确认。',[('repair','修复／复验／关闭记录')],
 '维修登记不等于恢复；重验由原生产流程生成新版本证据；source不因责任域改变而改写。','复验失败reopened；两次失败升级；不能提前关闭工单消除告警。','恢复环属于显式控制回流，不加入普通前向证据DAG制造循环。','换件和配置变化触发相关拓扑／映射／测试失效。','Q9 Q11',effect='write')

from collection import extend
extend(flows, add)
from decision_forms import link_flows
link_flows(flows)

decisions=[
 ('Q1','G5层间调度与停止粒度','DE＋研发负责人','T00/T01～T05','明确逐层串行或按路径调度；L5观测需覆盖负载而不是结束后补采。','可先实现计划／调度接口与仿真，不发布未经定义的跳层逻辑。'),
 ('Q2','L2～L4阈值与watchdog判据','NE／NH＋DL','T02～T05','给定每档超时、成功标准、吞吐指标、地址族与watchdog状态集合；不从硬件标称自动算。','工具适配和结果采集可做；对应自动PASS须等待策略。'),
 ('Q3','规则窗口与打流绑定','NE／NH＋研发负责人','F07/T03～T05','决定历史窗口复用条件、时钟偏差、计数重置、缺采样和30s/300s/3600s关系。','可实现带时间和质量的原始结果；短窗口不能伪证长规则。'),
 ('Q4','required_path_coverage生成算法','网络工程师＋NCCL负责人','T00/T06/N01','定义成员到NIC、方向、rail、ECMP/热点、档位覆盖的映射和抽样可接受范围。','先做集合差异与可插拔覆盖计算；禁止机器级代替路径级。'),
 ('Q5','LL严重度到Gate映射','NH＋DL','F07/T05/T06','明确warning/observe/critical的门禁作用，LL-01升级动作及LL-07适用性。','保留逐规则结果，不能擅自用健康分代替门禁。'),
 ('Q6','DOM与近似证据的接受范围','NE／NH＋DL','H02/T01/T05','逐能力说明必需、可补证、可豁免的范围与证据；unknown绝非0。','能力矩阵与降级呈现可做；不可自动全放行。'),
 ('Q7','NP-2与N-S6时序／漂移口径','NH＋DL','F06/H04','确认Major/Minor是否允许；G2前最低配置闭环如何定义；G4并行复核的边界。','以G2前必须具备有效NP-2为不可突破约束。'),
 ('Q8','G4抽检如何覆盖各目标','DL＋服务器配置负责人','H06/T00','规定选样、比例、失败处置和抽检结论适用范围。','记录逐目标应用／读回；不得自行默认抽检比例。'),
 ('Q9','LLDP无邻居与采集缺测契约','NE＋适配器研发','H04/R01','用独立采集状态、观察窗口和返回值区分线路异常与无法观测。','先实现有类型的缺测原因，不能空数组即PASS或T1。'),
 ('Q10','全网范围与PTP适用性','NH＋DL','F07/N01','明确fabric/pod范围及PTP是否有批准的不适用策略。','现有判据仍保留PTP；不自行删项。'),
 ('Q11','混合结论与工单阻断范围','DL＋研发负责人','T06/N08/R01','确定FAIL/BLOCKED同时存在时主状态和明细；关联工单适用范围；T1复验模板。','逐项结果先保存，拒绝把项目无关工单变成全局锁。'),
 ('Q12','豁免传播与链路风险展示','DL＋项目负责人','T06/N01/N08','明确下游独立通过时如何保留上游豁免引用及风险，不新增第五门禁枚举。','消费时校验豁免范围、期限、理由；无关例外不能借用。'),
]
invariants=[
 ('INV-01','物理身份早于Mapping；G2不能等待G3。','K','§1.1、§3.3','H04 H05'),
 ('INV-02','NP-3由G2三方比对产生，不能作为G2启动前置。','K','§4.1、§5','H04 H05'),
 ('INV-03','ZTP完成、下发成功、配置生效是不同事实。','K','§3.1','F04 F06'),
 ('INV-04','任务成功、检测通过、证据可消费是三个判断。','K','§8.4','T06 N08'),
 ('INV-05','必需unknown／过期／缺覆盖不得产生PASS。','K','§7、§8.1','T06 N01'),
 ('INV-06','A–B与C–D通过不能证明A–C。','K','§6.3、§8.4','T06 N01'),
 ('INV-07','依赖版本改变只影响依赖它的下游，历史结果不得篡改。','K','§8.3','H05 H06 T06 N08'),
 ('INV-08','豁免不能改成PASS；只对批准范围、期限与理由有效。','K','§8.1','T06 N01 N08'),
 ('INV-09','采集来源、发现来源、责任域是不同维度。','K','§8.4','F07 N06 R01'),
 ('INV-10','维修登记不关闭工单，复验PASS才提议关闭。','K','§8.2','R01'),
 ('INV-11','NCCL通信组统一启动并整组恢复。','K','§3.6、§8.4','N03'),
 ('INV-12','临时诊断与修复权限不能解锁普通批量任务。','K','§8.2','R01 H06'),
 ('INV-13','来源字段完整不足以证明物理事实正确，仍须独立样本和现场核验。','D','§1、§10','F07 H03 H04'),
 ('INV-14','冻结后发生相关变更，旧尝试不能成为当前版本的有效证明。','D','§8.3失效规则＋§8.4判例','H06 T06 N08'),
 ('INV-15','短窗口无异常不能证明长窗口规则已验证；规则不触发也不等于整个G5通过。','K','§7、§8.4','T05 T06'),
 ('INV-16','管理通道可达不能代替被测计算通路可达。','K','§1.1、§6.3','H01 T02 T03'),
]

def assemble_model():
    artifacts={k:dict(id=k,name=v[0],producer='external',owner=v[1],consumers=[]) for k,v in external.items()}
    for f in flows:
        for a in f['outputs']:
            assert a['id'] not in artifacts
            artifacts[a['id']]={**a,'producer':f['id'],'consumers':[]}
    for f in flows:
        for a in f['inputs']: artifacts[a]['consumers'].append(f['id'])
    terminals={'network_export':'客户移交（外部读者）','cmdb':'设备与项目查询／维护人员／AIOps（外部读者）','g6':'优雅退出（边界外消费者）','repair':'原生产流程的受控恢复（显式回流）'}
    for a,v in terminals.items():artifacts[a]['terminal_consumer']=v
    return dict(version=MODEL_VERSION,source=dict(name=SOURCE.name,sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest()),
       disclaimer='评审模型；K=原文，D=约束推导，P=实现建议，Q=业务待决策。不是已确认生产API或现场验收结果。',
       flows=flows,artifacts=list(artifacts.values()),decisions=[dict(id=i,topic=t,owner=o,affects=a,recommendation=r,boundary=b) for i,t,o,a,r,b in decisions],
       invariants=[dict(id=i,text=t,status=s,source=ref,flows=fs.split()) for i,t,s,ref,fs in invariants])

def cell(root,id,label,x,y,w=230,h=90,color='#F3F0FF',style='rounded=1;whiteSpace=wrap;html=1;'):
    c=SubElement(root,'mxCell',id=id,value=label,style=style+'fillColor='+color+';strokeColor=#B8B4CA;fontSize=14;fontFamily=Arial;spacing=10;',vertex='1',parent='1')
    SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    return c
def edge(root,id,source,target,label='',dashed=False):
    c=SubElement(root,'mxCell',id=id,value=label,source=source,target=target,parent='1',edge='1',style='edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;strokeColor='+('#B07920' if dashed else '#7560A8')+';fontSize=12;labelBackgroundColor=#FFFFFF;'+('dashed=1;' if dashed else ''))
    SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
def page(file,name,w=1600,h=1200):
    d=SubElement(file,'diagram',id='page-'+str(len(file)+1),name=name)
    m=SubElement(d,'mxGraphModel',dx='1400',dy='900',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),math='0',shadow='0')
    r=SubElement(m,'root');SubElement(r,'mxCell',id='0');SubElement(r,'mxCell',id='1',parent='0');return r
def drawio(model):
    file=Element('mxfile',host='app.diagrams.net',modified='2026-10-26T00:00:00.000Z',agent='keel specification builder',version='24.7.17',type='device')
    r=page(file,'01 交付证据依赖',1700,1550)
    cell(r,'title','<b>keel · 交付证据依赖</b><br>实线＝产物消费；不是全局阶段串行。橙色虚线＝恢复／建议。所有节点ID对应流程契约。',80,25,1500,85,'#EDE9FE')
    nodes=[('F01',80,160),('F02',80,300),('F03',80,440),('F04',80,580),('F05',80,720),('F06',390,580),('F07',390,790),('F08',80,1000),('H07',570,170),('H01',950,160),('H02',950,300),('H03',950,440),('H04',950,620),('H05',950,790),('H06',950,960),('T00',950,1120),('T06',1320,1120),('N08',1320,1290)]
    byid={f['id']:f for f in flows}
    for id,x,y in nodes:
        f=byid[id];cell(r,id,f'<b>{id} · {f["name"]}</b><br>'+html.escape('产物：'+ '、'.join(a['name'] for a in f['outputs'])),x,y,280,110, '#EFF6FF' if id.startswith('H') else '#F3F0FF')
    pairs=[('F01','F02','BOM'),('F02','F03','计划'),('F03','F04','环境自检'),('F04','F05','可管理／可观测事实'),('F04','F06','管理可达；不等于生产同步'),('F02','F06','批准意图'),('F06','F07','复采配置'),('F07','F08','健康与无损'),('F01','H01','同一BOM'),('H01','H02','OS＋SSH信任'),('H02','H03','G1'),('H03','H04','拓扑'),('F05','H04','预校验；不是NP-3'),('F06','H04','NP-2配置部分'),('H04','H05','G2＋NP-3'),('H05','H06','MappingRevision'),('F06','H06','QoS意图一致性'),('H06','T00','有效G4'),('F07','T00','NP-5／NP-6'),('T00','T06','详见第3页五层子流'),('T06','N08','详见第5页NCCL子流')]
    for i,(a,b,l) in enumerate(pairs):edge(r,'e'+str(i),a,b,l)
    edge(r,'install-inventory','H01','H07','执行通道')
    edge(r,'inventory-validate','H07','H02','硬件原始清单')
    cell(r,'fresh','<b>动态接口依赖</b><br>G2／G5执行前刷新FR-0.8.1，默认TTL30s；G6预检复核网络就绪。网络与服务器侧可以并行。',410,1150,460,125,'#FFFBEB')
    cell(r,'boundary','<b>边界</b><br>N-S8/9导出不是G2/G5统一前置。G6仅解锁优雅退出，不等于交付完成。',80,1360,780,100,'#F8FAFC')

    r=page(file,'02 G2三方线序与Mapping',1600,1250)
    cell(r,'title','<b>G2控制顺序是已定义的；原始采集、端口对结论和整机门禁分别留存。</b>',80,20,1430,80,'#EDE9FE')
    for id,label,x,y in [('ready','启动握手<br>逐目标G1＋FR-4.8＋NP-1/2/4<br>网络域在线',80,160),('s1','Step1 GPU拓扑确认<br>GPU-NIC关系表版本',420,160),('s2','Step2 LLDP实测<br>主机快照＋交换机回读＋永久MAC',760,160),('s3','Step3 三方比对<br>BOM期望↔主机LLDP↔交换机LLDP',1100,160),('s4','Step4 DL确认<br>四步链＋关系表版本＋确认人／时间',1100,500),('g3','H05 / G3<br>覆盖100%且无冲突<br>发布不可变MappingRevision',1100,800)]:cell(r,id,label,x,y,290,130)
    for i,(a,b) in enumerate([('ready','s1'),('s1','s2'),('s2','s3'),('s3','s4'),('s4','g3')]):edge(r,'e'+str(i),a,b,'有效结果')
    cell(r,'blocked','缺任一侧必需证据<br>unknown → BLOCKED<br>不判空匹配成功',750,480,280,140,'#FFFBEB')
    cell(r,'fail','明确差异 → T类工单<br>原始证据＋期望/实际<br>不把采集超时直接判线缆坏',410,480,280,140,'#FFF1F2')
    cell(r,'repair','R01 受控处置／定向复验<br>PASS后提议关闭，NE/DL确认<br>普通重采从Step2；拓扑变更回FR-4.8',410,800,550,140,'#EFF6FF')
    edge(r,'eb','s3','blocked','缺测');edge(r,'ef','s3','fail','观测差异');edge(r,'er','fail','repair','处置');edge(r,'eback','repair','s2','显式范围重验',True)
    cell(r,'note','<b>必须保持：</b>NP-3由Step2/3产生，不能是启动G2的前置；Step3局部端口对PASS不等于Step4已确认；PhysicalPort早于G3存在。',80,1030,1430,130,'#F8FAFC')

    r=page(file,'03 G5数据与判定',1700,1500)
    cell(r,'title','<b>G5：五层是检查维度，不能未经决策画成五个串行硬门禁。</b><br>下图为证据消费图；Q1决定实际层间调度，Q3决定采样窗口。',70,20,1530,85,'#EDE9FE')
    cell(r,'plan','T00 准入／冻结计划<br>G4＋映射／角色＋NP-4/5/6<br>目标／路径／档位／版本／资源',630,160,390,140)
    layernodes=[('T01','L1 链路<br>up／速率／DOM',90),('T02','L2 IP/ARP<br>per-NIC配对／覆盖',400),('T03','L3 RDMA写读<br>流量类／无损drop',710),('T04','L4 多流热点<br>负载／吞吐／覆盖',1020),('T05','L5 无损交叉判定<br>watchdog／LL／窗口',1330)]
    for id,label,x in layernodes:
        cell(r,id,f'<b>{id}</b><br>{label}',x,410,250,135,'#EFF6FF');edge(r,'p'+id,'plan',id,'本次上下文')
    cell(r,'telemetry','网络域连续观测<br>source=switch／rule@version<br>能力、事件时间、窗口、质量<br>缺失不可补0',1030,690,520,150,'#FFFBEB')
    edge(r,'tt3','T03','telemetry','负载上下文关联：P建议',True);edge(r,'tt4','T04','telemetry','观测须覆盖打流：Q3',True);edge(r,'tt5','telemetry','T05','绑定窗口数据')
    cell(r,'merge','T06 汇总 G5<br>必需结果＋required_path_coverage<br>版本／有效期／DL豁免',630,940,420,140)
    for id,_,_ in layernodes:edge(r,'m'+id,id,'merge','结果及引用')
    cell(r,'pass','PASS<br>所需有效证据全PASS且覆盖满足',80,1200,330,120,'#ECFDF5')
    cell(r,'bad','FAIL / BLOCKED<br>明确违规 / 前置或必需证据不足<br>混合主状态Q11待定',470,1200,390,120,'#FFF1F2')
    cell(r,'waived','WAIVED<br>适用范围／期限／审批／整改<br>不得改写PASS',920,1200,330,120,'#F3E8FF')
    for i,t in enumerate(['pass','bad','waived']):edge(r,'o'+str(i),'merge',t)
    cell(r,'note','30s快速打流 ≠ 3600s LL-03验证；LL规则未触发 ≠ 整个G5通过；抽样通过 ≠ 全路径覆盖；下游按通信组重新检查证据适用性。',80,1370,1470,90,'#F8FAFC')

    r=page(file,'04 版本变化与故障恢复',1650,1300)
    cell(r,'title','<b>保留历史结论，重新计算可消费性。</b><br>以下CAS／租约／结果封装是P实现建议，不新增业务门禁枚举。',70,20,1500,85,'#EDE9FE')
    items=[('freeze','冻结请求上下文<br>目标hash／依赖版本／审批范围',80,170),('admit','派发前核验<br>权限／版本／就绪／资源租约',430,170),('run','执行尝试<br>TaskAttempt／动作幂等键<br>回执与原始结果',780,170),('commit','发布前复核版本<br>原始结果落库＋证据引用一致<br>禁止过时写覆盖当前状态',1130,170),('change','相关版本或物理对象变化<br>新ConfigSet／换卡／换线／规则更新',80,540),('history','旧结果仍保存<br>历史PASS可以成立<br>对当前任务不再可消费',430,540),('retry','受控重验／新尝试<br>普通重跑走新准入<br>issue.verify仅豁免本故障',780,540),('unknown','断线／超时／结果不明<br>先查回执和设备实际状态<br>不能直接重放高副作用动作',1130,540)]
    for id,label,x,y in items:cell(r,id,label,x,y,290,160,'#EFF6FF' if id in ['change','history'] else '#F3F0FF')
    for i,(a,b,l,d) in enumerate([('freeze','admit','',False),('admit','run','',False),('run','commit','',False),('change','history','影响依赖范围',False),('change','commit','变更导致发布前提不匹配',True),('history','retry','补足证明',True),('run','unknown','无最终回执',True),('unknown','retry','对账后安全恢复',True),('retry','freeze','新上下文',True)]):edge(r,'e'+str(i),a,b,l,d)
    cell(r,'ttl','<b>时间语义：</b>30s readiness TTL检查消费/派发时的就绪；它不是长任务必须30s内结束。LL观测窗口、指标新鲜度和GateEvidence有效期分别判断。',80,930,1420,140,'#FFFBEB')

    r=page(file,'05 NCCL整组语义与评审',1600,1400)
    cell(r,'title','<b>NCCL：准入是对通信组所需路径的证明；执行与重试以整组为单位。</b>',70,20,1450,85,'#EDE9FE')
    pos=[('N01',100,160),('N02',100,360),('N03',100,560),('N04',550,560),('N05',1000,560),('N06',1000,780),('N07',550,780),('N08',100,780)]
    for id,x,y in pos:
        f=byid[id];cell(r,id,f'<b>{id} · {f["name"]}</b><br>'+html.escape(f['purpose']),x,y,340,140)
    seq=['N01','N02','N03','N04','N05','N06','N07','N08']
    for i,(a,b) in enumerate(zip(seq,seq[1:])):edge(r,'e'+str(i),a,b)
    cell(r,'retry','组内失败<br>终止其余参与者并取诊断<br>新GroupAttempt整组重建',550,200,340,160,'#FFF1F2');edge(r,'failure','N03','retry','失败',True);edge(r,'back','retry','N01','重新核验',True)
    cell(r,'source','网络与映射证据<br>G5路径基线／FR-0.8 LL<br>PortModel／拓扑／DCGM',1000,200,340,160,'#EFF6FF');edge(r,'src','source','N06','溯源输入')
    cell(r,'boundary','<b>出口：</b>G6报告达标＋调优清单确认 → 解锁优雅退出。纯机内诊断不可沿此路径取得G6交付通过。分组覆盖不冒充全域单通信组。',100,1100,1250,140,'#F8FAFC')
    from collection import diagram
    diagram(file, page, cell, edge)
    ElementTree(file).write(ROOT/'keel-delivery.drawio',encoding='utf-8',xml_declaration=True)

def main():
    model=assemble_model()
    (ROOT/'contract-model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2))
    drawio(model)
    from reading import apply
    apply(model)
    print(json.dumps({'flows':len(flows),'artifacts':len(model['artifacts']),'decisions':len(decisions),'invariants':len(invariants),'drawio_pages':6,'source_sha256':model['source']['sha256']},ensure_ascii=False))
if __name__=='__main__':main()
