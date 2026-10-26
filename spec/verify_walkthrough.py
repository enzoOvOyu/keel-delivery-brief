"""Focused executable checks of new collection/CMDB examples and presentation coverage."""
import copy
import json
from pathlib import Path
from collection_model import compare_inventory, compare_wiring, CMDBReview, envelope_valid

ROOT = Path(__file__).resolve().parent


def event(sequence=1, **updates):
    item = dict(schema_version='1', event_id=f'evt-{sequence}', project_id='project-demo',
                subject_refs=[dict(kind='machine', id='machine-b300-a')], source_kind='inventory',
                source_ref=dict(record_id='inventory-a', revision=f'r{sequence}'), source_sequence=sequence,
                source_hash='sha256:' + str(sequence % 10) * 64, source_quality='known',
                collected_at='2026-10-26T08:00:00Z', received_at='2026-10-26T08:00:01Z')
    item.update(updates)
    return item


def run(model, reader):
    results = []
    def check(name, actual, expected=True):
        results.append(dict(name=name, passed=actual == expected, actual=actual, expected=expected))
    expected_ids = [f'gpu-{n}' for n in range(16)]
    rows = [dict(id=x, quality='known', fresh=True, identity_verified=True) for x in expected_ids]
    compare = lambda data, **kw: compare_inventory(expected_ids, data, **kw)
    check('16 个唯一且有效对象通过数量与质量核验', compare(rows)['verdict'], 'PASS')
    check('收到 16 行但重复一个对象不能通过', compare(rows[:-1] + [rows[0]])['verdict'], 'BLOCKED')
    check('部分采集缺一个对象为缺证据', compare(rows[:-1])['verdict'], 'BLOCKED')
    check('已证明完整枚举但少一个实物为明确不符', compare(rows[:-1], complete_snapshot=True)['verdict'], 'FAIL')
    bad = copy.deepcopy(rows); bad[-1]['quality'] = 'unknown'
    check('16 条收到中一条未知：有效数为 15', compare(bad)['valid'], 15)
    check('未知质量不自动通过', compare(bad)['verdict'], 'BLOCKED')
    stale = copy.deepcopy(rows); stale[0]['fresh'] = False
    check('过期数据不作为有效证据', compare(stale)['verdict'], 'BLOCKED')
    foreign = copy.deepcopy(rows); foreign[0]['identity_verified'] = False
    check('身份未核实不作为有效证据', compare(foreign)['verdict'], 'BLOCKED')
    check('额外有效实物不静默忽略', compare(rows + [dict(rows[0], id='extra')], complete_snapshot=True)['verdict'], 'FAIL')
    check('空预期集合不自动通过', compare_inventory([], [])['verdict'], 'BLOCKED')
    pair = ['port-a-c1', 'port-sw-c01']
    check('物理线缆交换端点顺序仍是同一对', compare_wiring(pair, pair[::-1], pair), 'PASS')
    wrong = ['port-a-c1', 'port-sw-c02']
    check('双侧一致但违背 BOM 仍是接错', compare_wiring(pair, wrong, wrong), 'FAIL')
    check('缺少交换机实测不能通过', compare_wiring(pair, pair, []), 'BLOCKED')
    check('端点重复不是有效线缆', compare_wiring(['a', 'a'], ['a', 'a'], ['a', 'a']), 'BLOCKED')
    fs = {f['id']: f for f in model['flows']}
    sources = set(fs['C01']['inputs'])
    def new(second_quality='known'):
        records = {}
        for row in [event(), event(2, source_quality=second_quality)]:
            key = (row['project_id'], row['source_kind'], row['source_ref']['record_id'], row['source_ref']['revision'])
            records[key] = {k: v for k, v in row.items() if k not in {'received_at', 'event_id'}}
        return CMDBReview('project-demo', [('machine', 'machine-b300-a')], sources, records)
    cmdb = new('unknown')
    check('首条合法源记录独立建索引', cmdb.ingest(event()), 'indexed')
    check('重复事件幂等返回且不重复建索引', cmdb.ingest(event()), 'duplicate')
    check('另一个事件引用同源修订也幂等', cmdb.ingest(event(event_id='different-event')), 'duplicate')
    check('重复后只有一个历史索引', len(cmdb.history), 1)
    check('同事件不同内容拒收', cmdb.ingest(event(source_hash='sha256:' + 'a' * 64)), 'quarantined')
    check('同源修订不同内容拒收', cmdb.ingest(event(event_id='conflict', source_hash='sha256:' + 'b' * 64)), 'quarantined')
    check('跨项目拒收', new().ingest(event(project_id='other-project')), 'quarantined')
    check('未知对象拒收', new().ingest(event(subject_refs=[dict(kind='machine', id='unknown-machine')])), 'quarantined')
    check('格式合法但源记录不存在时拒收', new().ingest(event(source_ref=dict(record_id='missing-record', revision='r1'))), 'quarantined')
    check('摘要与权威源记录不匹配时拒收', new().ingest(event(source_hash='sha256:' + 'f' * 64)), 'quarantined')
    check('新质量未知仍可索引', cmdb.ingest(event(2, source_quality='unknown')), 'indexed')
    chain = ('project-demo', 'inventory', 'inventory-a')
    check('新未知替换当前状态，不延续旧绿色', cmdb.current[chain]['source_quality'], 'unknown')
    check('最后有效记录另存，不冒充最新', cmdb.last_known[chain]['source_sequence'], 1)
    ordered = new(); ordered.ingest(event(2)); ordered.ingest(event(1))
    check('乱序旧修订仅入历史', len(ordered.history), 2)
    check('迟到旧修订不覆盖新投影', ordered.current[chain]['source_sequence'], 2)
    check('同序号不同修订拒收', ordered.ingest(event(2, event_id='collision', source_ref=dict(record_id='inventory-a', revision='different-r2'))), 'quarantined')
    totals = cmdb.totals()
    check('同步回执数量守恒', totals['received'], totals['indexed'] + totals['duplicate'] + totals['quarantined'])
    for title, changes in [
        ('未知版本', dict(schema_version='2')), ('非法质量', dict(source_quality='PASS')),
        ('序号布尔值', dict(source_sequence=True)), ('空对象集合', dict(subject_refs=[])),
        ('无效日期', dict(collected_at='2026-02-30T08:00:00Z')), ('未声明字段', dict(unexpected=True)),
        ('未知源类别', dict(source_kind='invented')), ('不固定修订', dict(source_ref=dict(record_id='x', revision='latest'))),
    ]:
        check(title + '拒收', envelope_valid(event(**changes), sources), False)
    missing = event(); del missing['source_ref']
    check('缺必填引用拒收', envelope_valid(missing, sources), False)
    allcards = [f['walkthrough'] for f in reader['flows']] + [s['walkthrough'] for f in reader['flows'] for s in f['substeps']]
    check('全部 32 流程与 13 内部子步骤有五段动作数据', len(allcards), 45)
    check('每张卡有动作、原始数据、数量质量比较、输出和消费', all(all(c.get(k) for k in ['actor','action','raw','comparisons','output','use','recovery']) for c in allcards))
    check('新增采集位于装机且被验机消费', reader['stages'][1]['flows'] == ['H01','H07'] and 'inventory' in fs['H02']['inputs'])
    produced = {a['id'] for f in model['flows'] if f['id'] != 'C01' for a in f['outputs']}
    check('全部流程产物及原始观测进入 CMDB', sources, produced | {'observations','window','readiness','human'})
    check('CMDB 是逐事件消费，不是全局前置', fs['C01'].get('input_mode') == 'per_source_event' and all('cmdb' not in f['inputs'] for f in model['flows']))
    schema = json.loads((ROOT/'collection-event.schema.json').read_text())
    check('事件 Schema 源类别与订阅目录双向一致', set(schema['properties']['source_kind']['enum']), sources)
    check('事件 Schema 必填与有限模型一致', set(schema['required']), set(event()))
    ars = {a['id']: a for a in reader['artifacts']}
    check('动作卡消费按钮与模型一致', all(all(route['consumers'] == ars[route['artifact_id']]['consumers'] for route in f['walkthrough']['routes']) for f in reader['flows']))
    # JSON-compatible diagnostics, including set comparisons above.
    for result in results:
        for key in ['actual', 'expected']:
            if isinstance(result[key], set): result[key] = sorted(result[key])
    return dict(passed=all(r['passed'] for r in results), cards=len(allcards), checks=results,
                scope='有限模拟数据与事件模型；未连接硬件，未实现生产 CMDB，未运行 TLC。')


if __name__ == '__main__':
    result = run(json.loads((ROOT/'contract-model.json').read_text()), json.loads((ROOT/'reading-model.json').read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
