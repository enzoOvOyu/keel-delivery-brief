"""Authorized installation inventory and event-driven federated CMDB contracts."""


def extend(flows, add):
    add('H07', '装机硬件信息收集', '装机', '用户变更 2026-10-26；PRD §3.3、§3.15',
        '将 BMC 与操作系统看到的硬件分别留存，给验机提供可追溯的原始清单。',
        'bom host_ready model observations auth',
        '已授权 BMC Redfish／IPMI 与 SSH 只读采集；凭据仅保存引用。',
        '目标身份、执行权限及采集通道已核对；按通道记录可用性，不要求尚未产生的验机 PASS。',
        '按设备采集身份、位置、CPU、内存、GPU、网卡、磁盘、电源、固件和端口；保存原始响应、能力与缺失原因。',
        [('inventory', '装机硬件清单与采集质量记录')],
        '每个预期对象都有成功或缺失回执；清单已留存不代表硬件验收通过。',
        '单设备或单来源失败保留部分快照；缺失不补零；身份冲突隔离，不能自动合并。',
        '仅重采缺失或变化的对象，产生新采集修订；设备稳定 ID 不因重采变化。',
        '换件、重装、采集过期或型号变更要求重新核验相关记录。')
    inventory = flows.pop()
    flows.insert(next(i for i, f in enumerate(flows) if f['id'] == 'H01') + 1, inventory)
    validation = next(f for f in flows if f['id'] == 'H02')
    validation['inputs'].append('inventory')
    validation['resources'] += ' BMC 固件清单、nvidia-smi 只读查询、ethtool -i、已加载模块与软件包清单；实际能力按 OEM 和操作系统版本确认。'
    validation['actions'] = '复用 2.2 硬件清单；只读补采 BMC、BIOS、GPU VBIOS、NIC 固件，以及 NVIDIA GPU、NIC／RDMA 的已加载驱动和实际软件包版本。固件绑定稳定部件 ID；共享驱动按主机、驱动名称与内核去重，并列出覆盖部件。对照批准的 OEM／OS／内核／固件／驱动兼容基线，保存原始回执与分项差异；不安装、升级或改配置。'
    validation['failure'] += ' 必需固件或驱动版本缺测、读取冲突或批准基线缺失时，受影响项保留 BLOCKED；已确认版本不兼容为 FAIL；不适用必须有能力策略依据。'
    validation['retry'] += ' 对固件／驱动缺测只读重采并发布新快照；需要升级时转受控变更，核对重启后的实际加载版本，再复验受影响项。'
    validation['invalidation'] += ' 固件升级、驱动安装或加载版本变化、内核升级与重启使受影响的兼容性结果重新待核验。'
    validation['guards'] += ' 装机采集记录可定位；部分采集不自动通过验机。'
    # All source outputs are individually subscribable. This is an event catalog,
    # not an AND join, and never becomes a prerequisite of the source producers.
    subscribed = [a['id'] for f in flows for a in f['outputs']]
    subscribed += ['observations', 'window', 'readiness', 'human']
    add('C01', 'CMDB 自动沉淀与维护查询', '公共流程', '用户变更 2026-10-26；PRD §3.15',
        '每次源记录发布即更新资产索引；把五步数据连成设备档案，供维护查询。',
        ' '.join(subscribed),
        '源记录发布事件、源表只读访问、稳定对象目录、同步回执与可重放事件队列。',
        '每次只接收一种已落库源记录；核对项目、对象与不可变修订。无需等五步全部完成。',
        '按源记录身份幂等建索引；关联设备、部件、端口及项目；保留历史与质量。cleanup 已验证事件另行触发归档快照。',
        [('cmdb', 'CMDB 联邦索引、同步回执与归档引用')],
        '收到数=新建数+重复数+拒收数；每条索引可回到源修订。归档完成另有清单与引用一致性证明。',
        '未知对象、跨项目或同版本内容冲突隔离；同步延迟可见。同步成功不是业务 PASS，也不阻塞所有业务步骤。',
        '以原事件身份重放；迟到版本仅入历史，不覆盖较新投影；断链修复后对账。',
        '新采集更新索引可用性但不覆盖历史；cleanup 后停止带内动态监控，仅按需带外刷新静态资产。')
    flows[-1]['input_mode'] = 'per_source_event'
    flows[-1]['archive_trigger'] = 'verified_cleanup_event (external lifecycle boundary)'


def diagram(file, page, cell, edge):
    r = page(file, '06 公共 CMDB 数据流', 1640, 1160)
    cell(r, 'title', '<b>0.2 CMDB：每条源记录独立消费，全程自动沉淀</b><br>实线＝源记录发布后建立索引；虚线＝外部退出生命周期事件。没有等待五步齐备的全局门禁。', 60, 20, 1500, 100)
    groups = [
        ('network', '1.1～1.8 网络底座<br>物料／交换机身份／端口／配置／健康', 60, 180),
        ('install', '2.1 装机 · 2.2 硬件采集<br>BMC 与 OS 分源；完整与缺失均留存', 60, 380),
        ('inspect', '3.1～3.5 验机与配置<br>硬件／拓扑／双侧邻居／映射／配置', 60, 580),
        ('test', '4.1～4.7 与 5.1～5.8 测试<br>计划／原始结果／指标／报告／评审', 60, 780),
        ('repair', '0.1 修复；持续观测与人工确认<br>处置记录／窗口／就绪／确认记录', 530, 780),
    ]
    for id, label, x, y in groups:
        cell(r, id, label, x, y, 390, 130, '#EFF6FF')
    cell(r, 'C01', '0.2 CMDB 自动沉淀<br>核对项目与稳定身份 → 幂等索引<br>源表仍持有数据；缺测／失败同样可查', 560, 380, 440, 170)
    for id, *_ in groups:
        edge(r, 'to-' + id, id, 'C01', '源记录引用')
    cell(r, 'view', '设备 360°／项目查询／API 导出<br>按设备、端口、版本追到原始证据<br>当前可用性与历史结论分别展示', 1110, 380, 420, 170)
    edge(r, 'read', 'C01', 'view', '索引与质量状态')
    cell(r, 'cleanup', '外部：退出清理已核验<br>5.8 评审通过仅允许开始退出<br>清理回执确认后才转维护态', 560, 160, 440, 130, '#FFFBEB')
    edge(r, 'archive', 'cleanup', 'C01', '归档清单事件', True)
    cell(r, 'quality', '同步失败 → 对账并重放原事件<br>重复不重复建档；迟到不覆盖新版<br>自动字段与人工维保字段分列保存', 1110, 780, 420, 140, '#FFFBEB')
    edge(r, 'receipt', 'C01', 'quality', '逐项回执')
    cell(r, 'legend', '展开范围：所有流程的全部产物，加主机／交换机观测、负载窗口、动态就绪与人工确认。指标明细仍在源表／证据存储，CMDB 保存索引。', 60, 990, 1470, 100, '#F8FAFC')
