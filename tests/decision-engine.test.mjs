import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { initialState, validateFields, validateContext, quantities, percentCount, confirmDecision, status, parseState, conflicts } from '../src/ui/decision-engine.ts'

const model=JSON.parse(readFileSync(new URL('../spec/reading-model.json',import.meta.url)))
const decision=id=>model.decisions.find(d=>d.id===id)
const now=Date.now()
const context={project:'project-test',scope:'fabric-test@7',profile:'dual-host@2',baseline:'approved-baseline@3',server:'B300',switch:'SN5610',reviewer:'测试确认人',role:'交付组长',basis:'测试用的独立评审记录@1',valid_until:new Date(now+86400000).toISOString()}
const q8={stratum:'model_config',targets:16,sample_pct:25,sample_min:2,selection:'explicit',sample_ref:'sample-plan@2',applies:'sample_only',sample_failure:'full_stratum'}
function ready(id, values) {const s=initialState(model);s.context={...context};s.drafts[id]={...values};return s}

test('空值不转为 0；零次重试是明确选择；未知选项不能确认',()=>{
  const values={schedule:'per_pair',parallel_pairs:2,stop_scope:'pair',extra_attempts:0,retry_delay_s:0,attempt_timeout_s:300,lead_s:0,tail_s:10}
  assert.deepEqual(validateFields(decision('Q1'),values),[])
  assert(validateFields(decision('Q1'),{...values,extra_attempts:''}).some(e=>e.key==='extra_attempts'))
  assert(validateFields(decision('Q1'),{...values,schedule:'anything'}).some(e=>e.key==='schedule'))
  assert(validateFields(decision('Q1'),{...values,parallel_pairs:1.5}).some(e=>e.key==='parallel_pairs'))
})
test('教学覆盖清单展开 8 对 × 双向 × IPv4 = 16；写读 32；不重复乘 rail',()=>{
  const lines=quantities(decision('Q4'),{pairs:8,rails:8,directions:'both',families:'v4'})
  assert.match(lines[0],/16 项.*32 项/)
  assert.match(quantities(decision('Q4'),{pairs:8,rails:8,directions:'both',families:'both'})[0],/32 项.*64 项/)
  assert(validateFields(decision('Q4'),{pairs:0,rails:8}).some(e=>e.key==='pairs'))
})
test('抽样向上取整、最小量及总量封顶；十进制边界不多抽一台',()=>{
  assert.match(quantities(decision('Q8'),q8)[0],/4 \/ 16 台/)
  assert.match(quantities(decision('Q8'),{...q8,targets:3,sample_pct:10,sample_min:5})[0],/3 \/ 3 台/)
  assert.equal(percentCount(100,29,true),29)
  assert.equal(percentCount(1000,0.7,true),7)
  assert.equal(percentCount(16,20,true),4)
  assert.equal(percentCount(16,20,false),3)
  assert.match(quantities(decision('Q8'),q8)[1],/样本外 12 台不由/)
})
test('LLDP 四次观察间隔 10 s：30 s 可容纳，29 s 不可容纳；采集超时不能跨周期',()=>{
  const values={window_s:30,interval_s:10,observations:4,lldp_max_age_s:20,side_skew_s:2,request_timeout_s:5,retries:1,backoff_s:1,empty_action:'ticket'}
  assert.deepEqual(validateFields(decision('Q9'),values),[])
  assert(validateFields(decision('Q9'),{...values,window_s:29}).some(e=>e.key==='window_s'))
  assert(validateFields(decision('Q9'),{...values,request_timeout_s:11}).some(e=>e.key==='request_timeout_s'))
  assert.match(quantities(decision('Q9'),values)[0],/4 次观察／侧/)
})
test('既有采样上限不能被填值突破；负载目标与验收下限独立且不能倒置',()=>{
  assert(validateFields(decision('Q3'),{counter_period_s:61}).some(e=>e.key==='counter_period_s'))
  assert(validateFields(decision('Q3'),{queue_period_s:15}).some(e=>e.key==='queue_period_s'))
  assert(validateFields(decision('Q2'),{load_target_gbps:100,load_min_gbps:200}).some(e=>e.key==='load_min_gbps'))
  assert(validateFields(decision('Q2'),{ip_loss_pct:100}).some(e=>e.key==='ip_loss_pct'))
  assert(validateFields(decision('Q2'),{watchdog_states:'running,unknown'}).some(e=>e.key==='watchdog_states'))
})
test('填写完整仍是草稿；明确确认后生成不可变修订；改值、改范围、到期或依据改变须重确认',()=>{
  const s=ready('Q8',q8)
  assert.equal(status(decision('Q8'),s,model,now),'draft')
  assert.throws(()=>confirmDecision(decision('Q8'),s,model,false,now),/明确确认/)
  const first=confirmDecision(decision('Q8'),s,model,true,now)
  assert.equal(status(decision('Q8'),first,model,now),'confirmed')
  assert.equal(s.history.Q8,undefined)
  assert.match(first.history.Q8[0].record_id,/^decision-[0-9a-f]{32}$/)
  assert.equal(status(decision('Q8'),{...first,context:{...context,reviewer:'另一名确认人',valid_until:new Date(now+172800000).toISOString()}},model,now),'confirmed')
  const edited={...first,drafts:{...first.drafts,Q8:{...q8,sample_pct:50}}}
  assert.equal(status(decision('Q8'),edited,model,now),'changed')
  const second=confirmDecision(decision('Q8'),edited,model,true,now+1)
  assert.equal(second.history.Q8.length,2)
  assert.equal(second.history.Q8[0].values.sample_pct,25)
  assert.equal(second.history.Q8[1].values.sample_pct,50)
  assert.equal(status(decision('Q8'),{...first,context:{...context,scope:'other-fabric@1'}},model,now),'changed')
  assert.equal(status(decision('Q8'),first,model,Date.parse(context.valid_until)),'expired')
  assert.equal(status(decision('Q8'),first,{...model,decision_forms:{...model.decision_forms,source_fingerprint:'changed'}},now),'stale')
})
test('同义字段重排不改变确认；导入保留修订，不自动确认草稿',()=>{
  const state=confirmDecision(decision('Q8'),ready('Q8',q8),model,true,now)
  const reordered=JSON.parse(JSON.stringify(state))
  reordered.history.Q8[0].values=Object.fromEntries(Object.entries(reordered.history.Q8[0].values).reverse())
  const imported=parseState(JSON.stringify(reordered),model)
  assert.equal(status(decision('Q8'),imported,model,now),'confirmed')
  imported.drafts.Q8.targets=32
  assert.equal(status(decision('Q8'),parseState(JSON.stringify(imported),model),model,now),'changed')
})
test('拒绝未知字段、未知事项、无效时间与跳号确认；不借导入伪造完整状态',()=>{
  const state=confirmDecision(decision('Q8'),ready('Q8',q8),model,true,now)
  for(const mutate of [s=>{s.drafts.Q99={}},s=>{s.history.Q8[0].values.pass=true},s=>{s.history.Q8[0].revision=3},s=>{s.history.Q8[0].values.targets=null},s=>{s.history.Q8[0].confirmed_at='bad'},s=>{s.context.extra='x'}]){
    const s=structuredClone(state);mutate(s);assert.throws(()=>parseState(JSON.stringify(s),model))
  }
  assert(validateContext({...context,baseline:'latest'},now).some(e=>e.key==='baseline'))
})
test('缺测走豁免与禁止豁免相冲突，拒绝把冲突方案确认为可用',()=>{
  const values={dom:'waiver',dom_limit:1,dom_age_h:1,xoff:'block',queue:'block',drop:'block',buffer:'block',disabled:'block'}
  let s=confirmDecision(decision('Q6'),ready('Q6',values),model,true,now)
  s={...s,drafts:{...s.drafts,Q12:{waivers:'deny'}}}
  assert.throws(()=>confirmDecision(decision('Q12'),s,model,true,now),/不接受豁免/)
  assert.deepEqual(conflicts(model,s),[])
})
test('条件隐藏值不进入批准记录；豁免政策确认不是一次具体豁免',()=>{
  const s=confirmDecision(decision('Q12'),ready('Q12',{waivers:'deny',validity_h:12,path_limit:3}),model,true,now)
  assert.deepEqual(s.history.Q12[0].values,{waivers:'deny'})
  assert.equal('gate_result' in s.history.Q12[0],false)
  assert.equal('waiver_id' in s.history.Q12[0],false)
})

test('执行超时与负载窗口交叉检查：60+10 秒需要至少 70 秒，边界允许相等',()=>{
  const q1={schedule:'ready',parallel_pairs:1,stop_scope:'pair',extra_attempts:0,retry_delay_s:0,attempt_timeout_s:60,lead_s:0,tail_s:0}
  const q2={ip_probes:10,ip_bytes:64,ip_timeout_ms:100,ip_loss_pct:0,ip_latency_stat:'max',ip_latency_ms:50,
    write_gbps:10,read_gbps:10,write_latency_us:100,read_latency_us:100,rdma_bytes:1024,qp_count:1,
    rdma_duration_s:60,warmup_s:10,repetitions:1,load_target_gbps:20,load_min_gbps:10,streams:2,
    load_duration_s:30,imbalance_pct:5,watchdog_states:'running',watchdog_events:0}
  let s=confirmDecision(decision('Q1'),ready('Q1',q1),model,true,now)
  s={...s,drafts:{...s.drafts,Q2:q2}}
  assert.throws(()=>confirmDecision(decision('Q2'),s,model,true,now),/超时短于/)
  s={...s,drafts:{...s.drafts,Q1:{...q1,attempt_timeout_s:70}}}
  s=confirmDecision(decision('Q1'),s,model,true,now+1)
  s=confirmDecision(decision('Q2'),s,model,true,now+2)
  assert.deepEqual(conflicts(model,s),[])
})
