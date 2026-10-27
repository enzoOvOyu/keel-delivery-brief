export type Value = string | number
export type Values = Record<string, Value>
export type Field = {
  key: string; label: string; type: 'number' | 'integer' | 'select' | 'text'; group: string
  required: boolean; unit?: string; min?: number; max?: number; exclusiveMin?: boolean
  help?: string; when?: Record<string, string>; options?: { value: string; label: string }[]
}
export type Decision = {
  id: string; topic: string; owner: string; flows: string[]
  form: { question: string; before: string; after: string; proof: string; fixed: string[]; fields: Field[] }
}
export type Flow = { id: string; code: string; title: string; decisions: string[]; inputs: string[]; outputs: string[] }
export type Model = {
  version: string; decisions: Decision[]; flows: Flow[]
  decision_forms: { version: string; fingerprint: string; source_fingerprint: string }
}
export type Context = {
  project: string; scope: string; profile: string; baseline: string
  server: string; switch: string; reviewer: string; role: string; basis: string; valid_until: string
}
export const contextFields: { key: keyof Context; label: string; hint: string }[] = [
  { key: 'project', label: '项目 ID', hint: '填写真实项目的稳定标识' },
  { key: 'scope', label: '适用对象清单及版本', hint: '具体 fabric / pod / 设备清单，不能只写“全部”' },
  { key: 'profile', label: '测试档位及版本', hint: '同一方案只适用于这套测量条件' },
  { key: 'baseline', label: '独立基线 ID 与版本', hint: '包含机型、拓扑、固件／驱动、NOS 和工具版本；不由本次实测反推' },
  { key: 'server', label: '服务器型号', hint: '案例为 B300；填写实际整机型号' },
  { key: 'switch', label: '交换机型号', hint: '案例为 SN5610' },
  { key: 'reviewer', label: '本次确认人', hint: '姓名或组织内可识别的标识' },
  { key: 'role', label: '确认角色', hint: '按每项所列建议责任人安排' },
  { key: 'basis', label: '决定依据', hint: '会议纪要、基线评审或其他批准记录及版本' },
  { key: 'valid_until', label: '本次确认有效至', hint: '按当前设备本地时间填写，导出使用 UTC' },
]
export type Confirmation = {
  id: string; record_id: string; revision: number; confirmed_at: string; valid_until: string
  definition: string; source: string; context: Context; values: Values
}
export type State = {
  schema_version: '1'; context: Context; drafts: Record<string, Values>
  history: Record<string, Confirmation[]>; definition: string; source: string
}
export function initialState(model: Model): State {
  return { schema_version: '1', definition: model.decision_forms.fingerprint, source: model.decision_forms.source_fingerprint,
    context: Object.fromEntries(contextFields.map(f => [f.key, f.key === 'server' ? 'B300' : f.key === 'switch' ? 'SN5610' : ''])) as Context,
    drafts: {}, history: {} }
}
export function visible(field: Field, values: Values) {
  return Object.entries(field.when || {}).every(([key, expected]) => {
    const value = values[key]
    if (value === undefined || value === '') return false
    if (expected === '>0') return Number(value) > 0
    return expected.startsWith('!') ? value !== expected.slice(1) : value === expected
  })
}
export function normalized(decision: Decision, values: Values): Values {
  return Object.fromEntries(decision.form.fields.filter(f => visible(f, values)).map(f => {
    const raw = values[f.key]
    return [f.key, raw === undefined || String(raw).trim() === '' ? '' : f.type === 'number' || f.type === 'integer' ? Number(raw) : String(raw).trim()]
  }))
}
export type Issue = { key: string; message: string }
export function validateFields(decision: Decision, values: Values): Issue[] {
  const issues: Issue[] = []
  const add = (key: string, message: string) => issues.push({ key, message })
  for (const f of decision.form.fields.filter(f => visible(f, values))) {
    const raw = values[f.key]
    if (raw === undefined || String(raw).trim() === '') { add(f.key, `请填写${f.label}`); continue }
    if (f.type === 'number' || f.type === 'integer') {
      const n = Number(raw)
      if (!Number.isFinite(n) || (typeof raw !== 'number' && !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw))) add(f.key, `${f.label}须为有限数字`)
      else if (f.type === 'integer' && !Number.isSafeInteger(n)) add(f.key, `${f.label}须为可精确表示的整数`)
      else if (f.min !== undefined && (f.exclusiveMin ? n <= f.min : n < f.min)) add(f.key, `${f.label}须${f.exclusiveMin ? '大于' : '不小于'} ${f.min} ${f.unit || ''}`)
      else if (f.max !== undefined && n > f.max) add(f.key, `${f.label}不能超过 ${f.max} ${f.unit || ''}`)
    } else if (f.type === 'select' && !f.options?.some(o => o.value === raw)) add(f.key, `${f.label}请选择列出的选项`)
    else if (String(raw).length > 2000) add(f.key, `${f.label}最多填写 2000 个字符`)
  }
  const n = (key: string) => Number(values[key])
  const has = (...keys: string[]) => keys.every(k => values[k] !== undefined && values[k] !== '' && Number.isFinite(n(k)))
  if (decision.id === 'Q2') {
    if (has('load_target_gbps','load_min_gbps') && n('load_min_gbps') > n('load_target_gbps')) add('load_min_gbps','实测合格下限不能高于本次发流目标')
    if (has('ip_loss_pct') && n('ip_loss_pct') >= 100) add('ip_loss_pct','IP 可达性不能允许 100% 丢包')
    if (String(values.watchdog_states || '').split(/[,，\s]+/).some(s => /^(unknown|disabled|failed|stopped|null)$/i.test(s))) add('watchdog_states','未知、禁用或失败状态不能列为 watchdog 正常运行状态')
  }
  if (decision.id === 'Q3') {
    for (const [period,fresh] of [['counter_period_s','counter_fresh_s'],['queue_period_s','queue_fresh_s']]) {
      if (has(period,fresh) && n(period) > n(fresh)) add(fresh,'数据允许年龄不能短于约定采样间隔，否则周期中会持续出现过期缺口')
    }
  }
  if (decision.id === 'Q4') {
    if (has('pairs','rails') && n('pairs') < n('rails')) add('pairs','每个已纳入的 rail 至少要有一对；配对数不能小于 rail 数')
    if (has('pairs') && !Number.isSafeInteger(n('pairs') * 8)) add('pairs','展开方向、地址族和写读后的数量超出可精确计算范围')
    if (values.ecmp === 'routes' && has('ecmp_paths','pairs') && n('ecmp_paths') < n('pairs')) add('ecmp_paths','每个必需配对至少需要一条实际路径证明')
  }
  if (decision.id === 'Q9') {
    if (has('window_s','interval_s','observations') && (n('observations') - 1) * n('interval_s') > n('window_s')) add('window_s','窗口装不下要求的观察次数：至少需要（次数 − 1）× 间隔')
    if (has('request_timeout_s','interval_s') && n('request_timeout_s') > n('interval_s')) add('request_timeout_s','本表采用逐次采集，请求超时不能长于观察间隔')
    if (has('side_skew_s','window_s') && n('side_skew_s') > n('window_s')) add('side_skew_s','两侧允许时间差不能超过本次观察窗口')
  }
  if (decision.id === 'Q12' && values.waivers === 'bounded' && has('remediation_h','validity_h') && n('remediation_h') > n('validity_h')) add('remediation_h','整改期限须在本次豁免有效期内；延期需另行批准')
  return issues
}
export function validateContext(context: Context, now = Date.now()): Issue[] {
  const issues: Issue[] = []
  for (const { key, label } of contextFields) {
    if (typeof context[key] !== 'string' || !context[key].trim()) issues.push({ key, message: `请填写${label}` })
    else if (context[key].length > 2000) issues.push({ key, message: `${label}最多填写 2000 个字符` })
  }
  for (const key of ['baseline','scope','profile'] as const) if (/^(latest|current|全部|所有)$/i.test(context[key]?.trim() || '')) issues.push({key,message:'请填写具体对象清单或基线修订，不能使用“全部”或 latest 代替版本'})
  const expiry = Date.parse(context.valid_until)
  if (context.valid_until && (!Number.isFinite(expiry) || expiry <= now)) issues.push({ key: 'valid_until', message: '有效截止时间必须晚于当前时间' })
  return issues
}
export function normalizedContext(context: Context): Context {
  return Object.fromEntries(contextFields.map(({ key }) => [key, key === 'valid_until' && Number.isFinite(Date.parse(context[key])) ? new Date(context[key]).toISOString() : context[key].trim()])) as Context
}
const stable = (value: unknown): string => value && typeof value === 'object' && !Array.isArray(value) ? JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,stable(v)]))) : JSON.stringify(value)
const same = (a: unknown, b: unknown) => stable(a) === stable(b)
export function latest(state: State, id: string) { return state.history[id]?.at(-1) }
export function status(decision: Decision, state: State, model: Model, now = Date.now()) {
  const record = latest(state, decision.id)
  if (!record) return Object.keys(state.drafts[decision.id] || {}).length ? 'draft' : 'pending'
  if (record.definition !== model.decision_forms.fingerprint || record.source !== model.decision_forms.source_fingerprint) return 'stale'
  if (Date.parse(record.valid_until) <= now) return 'expired'
  const scopeKeys: (keyof Context)[] = ['project','scope','profile','baseline','server','switch']
  const context = normalizedContext(state.context)
  if (scopeKeys.some(k=>record.context[k] !== context[k]) || !same(record.values, normalized(decision, state.drafts[decision.id] || {}))) return 'changed'
  return 'confirmed'
}
export const statusNames = { pending: '待填写', draft: '草稿', changed: '修改后待确认', expired: '确认已到期', stale: '依据变化待确认', confirmed: '本方案已确认' }
// Decimal arithmetic avoids an extra sample caused by floating-point rounding at integer boundaries.
export function percentCount(total: number, percent: number, ceil: boolean) {
  const [mantissa, exponent = '0'] = String(percent).toLowerCase().split('e')
  const decimals = mantissa.split('.')[1]?.length || 0
  let numerator = BigInt(mantissa.replace('.', '')) * BigInt(total)
  let denominator = 100n
  const power = Number(exponent) - decimals
  if (power >= 0) numerator *= 10n ** BigInt(power)
  else denominator *= 10n ** BigInt(-power)
  return Number((numerator + (ceil ? denominator - 1n : 0n)) / denominator)
}
export function quantities(decision: Decision, values: Values): string[] {
  const n = (key: string) => Number(values[key])
  const has = (...keys: string[]) => keys.every(k => values[k] !== undefined && values[k] !== '' && Number.isFinite(n(k)) && n(k) >= 0)
  if (decision.id === 'Q1' && has('extra_attempts') && Number.isSafeInteger(n('extra_attempts'))) return [`每个可重试执行最多 ${1+n('extra_attempts')} 次尝试（含首次）。`]
  if (decision.id === 'Q4' && has('pairs') && n('pairs') > 0 && Number.isSafeInteger(n('pairs')*8) && ['both','one'].includes(String(values.directions)) && ['v4','v6','both'].includes(String(values.families))) {
    const paths = n('pairs') * (values.directions === 'both' ? 2 : 1) * (values.families === 'both' ? 2 : 1)
    return [`本计划 ${paths} 项有向地址族检查；RDMA 写／读共 ${paths * 2} 项。`, '仅为范围数量核对，仍需逐项对象与证据；不能从这个数量证明 ECMP 全覆盖。']
  }
  if (decision.id === 'Q8' && has('targets','sample_pct','sample_min') && Number.isSafeInteger(n('targets')) && n('targets') > 0 && n('sample_pct') > 0 && n('sample_pct') <= 100 && Number.isSafeInteger(n('sample_min')) && n('sample_min') > 0) {
    const sample = Math.min(n('targets'),Math.max(percentCount(n('targets'),n('sample_pct'),true),n('sample_min')))
    return [`当前同配置组需抽检 ${sample} / ${n('targets')} 台；全部 ${n('targets')} 台仍需应用与读回。`, values.applies === 'stratum' ? '其他目标只有满足批准的同组覆盖条件时才可使用样本结论。' : `样本外 ${n('targets')-sample} 台不由这份抽检结论覆盖。`]
  }
  if (decision.id === 'Q9' && has('window_s','interval_s') && n('interval_s') > 0) return [`从窗口起点开始，包含终点，最多安排 ${Math.floor(n('window_s')/n('interval_s'))+1} 次观察／侧；仍需实际收到完整有效样本。`]
  if (decision.id === 'Q10' && has('bgp_sessions','ports')) return [`要求 ${n('bgp_sessions')} / ${n('bgp_sessions')} 条必需 BGP 会话 Up，逐一核验 ${n('ports')} 个必需端口。`]
  return []
}
export function conflicts(model: Model, state: State): { ids: string[]; message: string }[] {
  const active: Record<string, Values> = {}
  for (const d of model.decisions) if (status(d,state,model) === 'confirmed') active[d.id] = latest(state,d.id)!.values
  const result: { ids: string[]; message: string }[] = []
  if (active.Q1 && active.Q4 && Number(active.Q1.parallel_pairs) > Number(active.Q4.pairs)) result.push({ ids: ['Q1','Q4'], message: '同时运行的配对上限大于本方案的全部配对数，请核对调度与覆盖范围。' })
  if (active.Q1 && active.Q2 && Number(active.Q1.attempt_timeout_s) < Math.max(Number(active.Q2.rdma_duration_s),Number(active.Q2.load_duration_s)) + Number(active.Q2.warmup_s)) result.push({ ids: ['Q1','Q2'], message: '单次执行超时短于预热加有效负载时长，无法按该计划完成测量。' })
  if (active.Q6 && active.Q12?.waivers === 'deny' && ['dom','xoff','queue','drop','buffer','disabled'].some(k => active.Q6[k] === 'waiver')) result.push({ ids: ['Q6','Q12'], message: '缺测处理选择了申请豁免，但本方案的豁免政策不接受豁免。' })
  return result
}
export function confirmDecision(decision: Decision, state: State, model: Model, acknowledged: boolean, now = Date.now()): State {
  const issues = [...validateContext(state.context,now),...validateFields(decision,state.drafts[decision.id] || {})]
  if (!acknowledged) issues.push({ key: 'acknowledged', message: '请先核对本项参数和流程影响，再勾选明确确认' })
  if (issues.length) throw new Error(issues.map(i => i.message).join('；'))
  const previous = state.history[decision.id] || []
  const context = normalizedContext(state.context)
  const recordId = 'decision-' + Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('')
  const record: Confirmation = { id: decision.id, record_id: recordId, revision: (previous.at(-1)?.revision || 0)+1,
    confirmed_at: new Date(now).toISOString(), valid_until: context.valid_until,
    definition: model.decision_forms.fingerprint, source: model.decision_forms.source_fingerprint,
    context, values: normalized(decision,state.drafts[decision.id] || {}) }
  const next = { ...state, definition: model.decision_forms.fingerprint, source: model.decision_forms.source_fingerprint,
    history: { ...state.history, [decision.id]: [...previous,record] } }
  const overlap = conflicts(model,next).filter(c=>c.ids.includes(decision.id))
  if (overlap.length) throw new Error(overlap.map(c=>c.message).join('；'))
  return next
}
export function summary(decision: Decision, values: Values) {
  return decision.form.fields.filter(f => visible(f,values) && values[f.key] !== undefined && values[f.key] !== '').map(f => ({
    label: f.group+' · '+f.label, value: f.options?.find(o => o.value === values[f.key])?.label || `${values[f.key]}${f.unit ? ' '+f.unit : ''}`,
  }))
}
export function affectedDownstream(decision: Decision, model: Model): Flow[] {
  const seen = new Set(decision.flows), outputs = new Set(model.flows.filter(f => seen.has(f.id)).flatMap(f=>f.outputs))
  let changed = true
  while (changed) {
    changed = false
    for (const f of model.flows) if (f.id !== 'C01' && f.id !== 'R01' && !seen.has(f.id) && f.inputs.some(i=>outputs.has(i))) {
      seen.add(f.id); f.outputs.forEach(o=>outputs.add(o)); changed = true
    }
  }
  return model.flows.filter(f=>seen.has(f.id) && !decision.flows.includes(f.id))
}
function plainObject(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value) }
function exactKeys(value: Record<string, unknown>, keys: string[]) { return Object.keys(value).every(k=>keys.includes(k)) }
export function parseState(raw: string, model: Model): State {
  if (raw.length > 5_000_000) throw new Error('确认文件过大，请使用本站导出的方案文件')
  const input: unknown = JSON.parse(raw)
  if (!plainObject(input) || input.schema_version !== '1' || !exactKeys(input,['schema_version','context','drafts','history','definition','source'])) throw new Error('不支持的确认文件格式或额外字段')
  if (typeof input.definition !== 'string' || typeof input.source !== 'string' || !plainObject(input.context) || !plainObject(input.drafts) || !plainObject(input.history)) throw new Error('确认文件缺少范围、草稿或历史记录')
  const checkContext = (value: unknown) => {
    if (!plainObject(value) || Object.keys(value).length !== contextFields.length || !exactKeys(value,contextFields.map(f=>f.key)) || !contextFields.every(f=>typeof value[f.key] === 'string' && (value[f.key] as string).length <= 2000)) throw new Error('范围信息格式不正确')
  }
  checkContext(input.context)
  const ids=model.decisions.map(d=>d.id)
  if (!exactKeys(input.drafts,ids) || !exactKeys(input.history,ids)) throw new Error('文件包含未知的确认事项')
  const recordIds = new Set<string>()
  for (const d of model.decisions) {
    const draft=input.drafts[d.id]
    const checkValues = (value: unknown) => {
      if (!plainObject(value) || !exactKeys(value,d.form.fields.map(f=>f.key)) || !Object.values(value).every(v=>(typeof v === 'string' && v.length<=2000) || (typeof v==='number' && Number.isFinite(v)))) throw new Error('填写值包含未知字段或非法类型')
    }
    if (draft !== undefined) checkValues(draft)
    const records=input.history[d.id]
    if (records !== undefined) {
      if (!Array.isArray(records) || records.length>1000) throw new Error('确认历史格式不正确')
      let revision=0, time=0
      for (const r of records) {
        if (!plainObject(r) || !exactKeys(r,['id','record_id','revision','confirmed_at','valid_until','definition','source','context','values']) || r.id !== d.id || !Number.isSafeInteger(r.revision) || Number(r.revision) !== revision+1 || typeof r.definition !== 'string' || typeof r.source !== 'string') throw new Error('确认修订不连续或来源缺失')
        if (typeof r.record_id !== 'string' || !/^decision-[0-9a-f]{32}$/.test(r.record_id) || recordIds.has(r.record_id)) throw new Error('确认记录 ID 无效或重复')
        recordIds.add(r.record_id)
        checkContext(r.context); checkValues(r.values)
        const at=Date.parse(String(r.confirmed_at)), until=Date.parse(String(r.valid_until))
        if (!Number.isFinite(at) || !Number.isFinite(until) || at<time || at>Date.now()+60_000 || until<=at || (r.context as Context).valid_until!==r.valid_until) throw new Error('确认时间或有效期不正确')
        if (validateContext(r.context as Context,at).length || validateFields(d,r.values as Values).length || !same(normalized(d,r.values as Values),r.values)) throw new Error('历史确认包含未完成、非法或不适用的参数')
        revision=Number(r.revision); time=at
      }
    }
  }
  return input as unknown as State
}
