import * as React from 'react'
import { createRoot } from 'react-dom/client'
import { createPortal } from 'react-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Check, Download, ArrowUpRight, FileInput } from 'lucide-react'
import { affectedDownstream, confirmDecision, conflicts, contextFields, initialState, latest, normalizedContext, parseState, quantities, status, statusNames, summary, validateContext, validateFields, visible } from './decision-engine'
import type { Context, Decision, Field, Model, State, Values } from './decision-engine'
// @ts-expect-error The guide's existing controller is JavaScript.
import { presentation } from '@/legacy/app.js'

const STORE = 'keel:decision-workbench:v1'
function download(name: string, value: string, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([value], { type }))
  const a = document.createElement('a'); a.href = url; a.download = name; a.click()
  setTimeout(()=>URL.revokeObjectURL(url),1000)
}
function markdown(model: Model, state: State) {
  const line = (value: string) => value.replaceAll('|','\\|').replaceAll('\n',' ')
  const lines = ['# 项目业务规则确认摘要', '这是所列项目和范围内的规则确认记录，尚不代表现场设备已通过验收。',
    ...contextFields.map(f=>`- ${f.label}：${state.context[f.key] || '未填写'}`),
    `- 规格版本：${model.version}；表单版本：${model.decision_forms.version}`,
    '完整修订历史、来源摘要及可恢复的草稿见同时导出的 JSON 文件。']
  for (const d of model.decisions) {
    const current=status(d,state,model), record=latest(state,d.id)
    lines.push(`\n## ${d.topic}`, `状态：${statusNames[current]}${record ? `；最近确认修订 ${record.revision}，${record.confirmed_at}` : ''}`,
      `影响步骤：${d.flows.map(id=>model.flows.find(f=>f.id===id)).filter(Boolean).map(f=>`${f!.code} ${f!.title}`).join('、')}`,
      current==='confirmed' ? d.form.after : d.form.before,
      '| 项目 | 当前填写值 |\n|---|---|', ...summary(d,state.drafts[d.id] || {}).map(row=>`| ${line(row.label)} | ${line(row.value)} |`),
      ...quantities(d,state.drafts[d.id] || {}), `仍需现场证据：${d.form.proof}`)
  }
  const warnings=conflicts(model,state)
  if(warnings.length) lines.push('\n## 需要解决的交叉冲突',...warnings.map(w=>'- '+w.message))
  return lines.join('\n\n')+'\n'
}

function FieldControl({ field, value, onChange, error, prefix }: { field: Field; value: string | number | undefined; onChange: (value: string)=>void; error?: string; prefix: string }) {
  const id=`${prefix}-${field.key}`
  return <div className="decision-input">
    <label htmlFor={id}>{field.label}{field.unit && <span className="decision-unit">{field.unit}</span>}</label>
    {field.type==='select' ? <Select value={String(value ?? '')} onValueChange={onChange}>
      <SelectTrigger id={id} className="decision-select" aria-invalid={!!error} aria-describedby={field.help || error ? id+'-help' : undefined}><SelectValue placeholder="请选择" /></SelectTrigger>
      <SelectContent position="popper" className="decision-options">{field.options!.map(o=><SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
    </Select> : <Input id={id} type={field.type==='text'?'text':'number'} value={value ?? ''} min={field.min} max={field.max} step={field.type==='integer'?1:'any'}
      maxLength={field.type==='text'?2000:undefined} onChange={e=>onChange(e.target.value)} aria-invalid={!!error} aria-describedby={field.help || error ? id+'-help' : undefined} />}
    {(field.help || error) && <p id={id+'-help'} className={error?'decision-error':'decision-hint'}>{error || field.help}</p>}
  </div>
}
function FlowButton({ id, model }: { id: string; model: Model }) {
  const flow=model.flows.find(f=>f.id===id)
  return flow ? <Button type="button" variant="outline" size="sm" onClick={()=>presentation.act('flow',id)}>{flow.code} {flow.title}<ArrowUpRight aria-hidden="true" /></Button> : null
}
function ValueSummary({ decision, values }: { decision: Decision; values: Values }) {
  return <dl className="decision-values">{summary(decision,values).map(row=><div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
}
function Impact({ decision, model }: { decision: Decision; model: Model }) {
  const downstream=affectedDownstream(decision,model)
  return <div className="decision-impact">
    <div><span>未确认时</span><p>{decision.form.before}</p></div>
    <div><span>确认后怎样执行</span><p>{decision.form.after}</p></div>
    <div><span>现场还要提供什么</span><p>{decision.form.proof}</p></div>
    <div className="decision-step-links"><span>直接应用到这些步骤</span><div>{decision.flows.map(id=><FlowButton key={id} id={id} model={model}/>)}</div></div>
    {!!downstream.length && <details className="decision-downstream"><summary>规则改变后，还需检查 {downstream.length} 个后续步骤的已有证据</summary><p>沿实际产物引用核对受影响的对象和修订；不是把这些步骤全部停掉。CMDB 继续逐事件收集记录。</p><div className="decision-link-row">{downstream.map(f=><FlowButton key={f.id} id={f.id} model={model}/>)}</div></details>}
  </div>
}
function AppliedDecisions({ flowId, model, state, open, compact = false }: { flowId: string; model: Model; state: State; open: (id:string)=>void; compact?: boolean }) {
  const flow=model.flows.find(f=>f.id===flowId)
  const decisions=model.decisions.filter(d=>flow?.decisions.includes(d.id))
  const conflicting=new Set(conflicts(model,state).flatMap(c=>c.ids))
  const confirmed=decisions.filter(d=>status(d,state,model)==='confirmed' && !conflicting.has(d.id)).length
  if (!decisions.length) return null
  if (compact) return <div className="decision-flow-summary" data-ui-owned="true"><Badge variant="outline">本方案规则：{confirmed} / {decisions.length} 项已确认</Badge><Button type="button" variant="ghost" size="sm" onClick={()=>{const target=document.getElementById('decision-flow-impact');target?.scrollIntoView({block:'center'});target?.querySelector('details')?.setAttribute('open','')}}>查看参数与流程影响<ArrowUpRight aria-hidden="true"/></Button></div>
  return <section className="decision-applied" data-ui-owned="true" aria-label="本步骤的业务确认">
    <div className="decision-row"><strong>本步骤的业务确认</strong><Badge variant="outline">{confirmed} / {decisions.length} 项已确认</Badge></div>
    <p>{state.context.project ? `${state.context.project} · ${state.context.scope || '范围待填写'}` : '先在“校验与待确认”填写项目和适用范围。'} 确认的是判定规则，执行后仍需本步骤的实测证明。</p>
    {decisions.map(d=>{
      const current=status(d,state,model), record=latest(state,d.id), usable=current==='confirmed' && !conflicting.has(d.id)
      return <details key={d.id} className="decision-applied-item"><summary><span>{d.topic}</span><Badge variant={usable?'secondary':'outline'}>{conflicting.has(d.id)?'存在交叉冲突':statusNames[current]}</Badge></summary>
        <p>{usable?d.form.after:d.form.before}</p>
        {usable && record && <><p className="decision-hint">修订 {record.revision} · {record.context.reviewer} · {new Date(record.confirmed_at).toLocaleString()}</p><ValueSummary decision={d} values={record.values}/>{quantities(d,record.values).map(v=><p key={v}>{v}</p>)}</>}
        <Button type="button" variant="outline" size="sm" onClick={()=>open(d.id)}>{usable?'查看或修改确认':'填写并确认'}<ArrowUpRight aria-hidden="true"/></Button>
      </details>
    })}
  </section>
}

function Workbench() {
  const [model,setModel]=React.useState<Model|null>(presentation.data() || null)
  const [state,setState]=React.useState<State|null>(null)
  const [selected,setSelected]=React.useState('Q1')
  const [notice,setNotice]=React.useState('')
  const [checked,setChecked]=React.useState(false)
  const [showErrors,setShowErrors]=React.useState(false)
  const [contextOpen,setContextOpen]=React.useState(true)
  const [imported,setImported]=React.useState<State|null>(null)
  const [targets,setTargets]=React.useState<HTMLElement[]>([])
  const [clock,setClock]=React.useState(Date.now())
  const lastStored=React.useRef<string|null>(null)
  const unreadable=React.useRef<string|null>(null)
  const importInput=React.useRef<HTMLInputElement>(null)
  React.useEffect(()=>{
    const onModel=(event:Event)=>setModel((event as CustomEvent).detail.model)
    const onSelect=(event:Event)=>{setSelected((event as CustomEvent<string>).detail); requestAnimationFrame(()=>document.getElementById('decision-current')?.scrollIntoView({block:'start'}))}
    document.addEventListener('ui:decisions-model',onModel)
    document.addEventListener('ui:decision-select',onSelect)
    setModel(presentation.data() || null)
    const collect=()=>{
      const next=Array.from(document.querySelectorAll<HTMLElement>('#decision-flow-summary,#decision-flow-impact,#decision-layer-impact'))
      setTargets(previous=>previous.length===next.length && previous.every((el,i)=>el===next[i])?previous:next)
    }
    const observer=new MutationObserver(collect)
    for (const id of ['flow-detail','layer-detail']) observer.observe(document.getElementById(id)!,{childList:true,subtree:true})
    collect()
    const timer=setInterval(()=>setClock(Date.now()),15000)
    return ()=>{document.removeEventListener('ui:decisions-model',onModel);document.removeEventListener('ui:decision-select',onSelect);observer.disconnect();clearInterval(timer)}
  },[])
  React.useEffect(()=>{
    if (!model?.decision_forms) {setState(null);return}
    let next=initialState(model)
    unreadable.current=null
    try {
      const raw=localStorage.getItem(STORE);lastStored.current=raw
      if(raw) next=parseState(raw,model)
      setNotice(raw?'已恢复当前浏览器的方案；确认记录按范围、版本和有效期核对。':'填写会自动保存草稿；只有明确点击确认后才计入本方案。')
    } catch {unreadable.current=lastStored.current;setNotice('已有方案暂时无法读取，原文件仍保留。本次填写暂存内存，请导出保存；也可下载原文件备份。')}
    setState(next);setContextOpen(validateContext(next.context).length>0)
    const code=location.hash.split('/')[1]
    if(model.decisions.some(d=>d.id===code)) setSelected(code)
  },[model])
  React.useEffect(()=>{setChecked(false);setShowErrors(false)},[selected,model])
  const persist=(next:State, isConfirmation=false)=>{
    if (unreadable.current) {setState(next);setNotice('原方案仍保留，本次填写暂存内存，请导出 JSON 保存。');return true}
    try {
      const stored=localStorage.getItem(STORE)
      if (stored!==lastStored.current) {setNotice('另一个标签页已修改此方案。请先导出当前填写，再刷新以读取新版本。');if(isConfirmation)return false}
      else {const raw=JSON.stringify(next);localStorage.setItem(STORE,raw);lastStored.current=raw;setNotice(isConfirmation?'本项已确认；可回到对应步骤查看参数和影响。':'草稿已保存到当前浏览器。')}
    } catch {setNotice('浏览器存储不可用，本次填写只保留在内存；请导出 JSON 保存。')}
    setState(next);setClock(Date.now());return true
  }
  const open=(id:string)=>{
    if(!model?.decisions.some(d=>d.id===id))return
    presentation.act('decision',id)
    setSelected(id)
    requestAnimationFrame(()=>{const target=document.getElementById('decision-current');target?.scrollIntoView({block:'start'});target?.focus({preventScroll:true})})
  }
  if (!model?.decision_forms || !state) return <p className="empty">业务确认表尚未加载，请检查上方资料加载状态。</p>
  const decision=model.decisions.find(d=>d.id===selected) || model.decisions[0]
  const values=state.drafts[decision.id] || {}, fieldIssues=validateFields(decision,values), contextIssues=validateContext(state.context,clock)
  const activeFields=decision.form.fields.filter(f=>visible(f,values)), complete=activeFields.length-new Set(fieldIssues.map(i=>i.key)).size
  const groups=[...new Set(activeFields.map(f=>f.group))]
  const allConflicts=conflicts(model,state), badIds=new Set(allConflicts.flatMap(c=>c.ids))
  const confirmed=model.decisions.filter(d=>status(d,state,model,clock)==='confirmed'&&!badIds.has(d.id)).length
  const current=status(decision,state,model,clock), history=state.history[decision.id] || []
  const changeField=(key:string,value:string)=>{setChecked(false);persist({...state,drafts:{...state.drafts,[decision.id]:{...values,[key]:value}}})}
  const confirm=(event:React.FormEvent)=>{
    event.preventDefault();setShowErrors(true)
    if(contextIssues.length)setContextOpen(true)
    try {
      const next=confirmDecision(decision,state,model,checked)
      if(persist(next,true)) {setChecked(false);setShowErrors(false)}
    } catch(error){setNotice((error as Error).message);requestAnimationFrame(()=>document.querySelector<HTMLElement>('.decision-workbench [aria-invalid=true]')?.focus())}
  }
  return <div className="decision-workbench" data-ui-owned="true">
    <div className="decision-toolbar">
      <div><strong>{confirmed} / {model.decisions.length} 项已确认</strong><span>对应 {new Set(model.decisions.filter(d=>status(d,state,model,clock)!=='confirmed'||badIds.has(d.id)).flatMap(d=>d.flows)).size} 个步骤仍有规则待确认</span></div>
      <div className="decision-actions"><Button variant="outline" size="sm" onClick={()=>download('keel-project-decisions.json',JSON.stringify(state,null,2))}><Download/>导出 JSON</Button>
        <Button variant="outline" size="sm" onClick={()=>download('keel-project-decisions.md',markdown(model,state),'text/markdown')}><Download/>导出确认摘要</Button>
        <Button variant="outline" size="sm" onClick={()=>importInput.current?.click()}><FileInput/>导入方案</Button>
        {unreadable.current && <Button variant="outline" size="sm" onClick={()=>download('keel-unreadable-decisions.json',unreadable.current!)}>下载原文件备份</Button>}
        <input ref={importInput} type="file" accept="application/json,.json" hidden aria-label="导入业务确认方案" onChange={async event=>{
          const file=event.target.files?.[0];event.target.value='';if(!file)return
          try{if(file.size>5_000_000)throw new Error('文件超过 5 MB');setImported(parseState(await file.text(),model));setNotice('请核对导入方案的项目和范围后载入。')}catch(error){setNotice('无法导入：'+(error as Error).message)}
        }}/></div>
    </div>
    <p className="decision-storage" role="status">{notice}</p>
    {imported && <div className="decision-import"><strong>导入预览：{imported.context.project || '未填项目'}</strong><p>{imported.context.scope || '未填范围'} · {Object.values(imported.history).reduce((n,rows)=>n+rows.length,0)} 条历史确认。导入不会自动确认草稿；旧规格、已过期或已修改的记录继续标为待确认。</p>
      <Button size="sm" onClick={()=>{download('keel-decisions-before-import.json',unreadable.current || JSON.stringify(state,null,2));unreadable.current=null;if(persist(imported)){setImported(null);setChecked(false);setContextOpen(validateContext(imported.context).length>0)}}}>备份当前并载入</Button><Button variant="ghost" size="sm" onClick={()=>setImported(null)}>取消</Button></div>}
    <details className="decision-context" open={contextOpen} onToggle={event=>setContextOpen(event.currentTarget.open)}>
      <summary><strong>适用范围与确认信息</strong><span>{contextIssues.length ? `${contextFields.length-new Set(contextIssues.map(i=>i.key)).size} / ${contextFields.length} 项填写有效` : `${state.context.project} · ${state.context.profile}`}</span></summary>
      <p>所有确认仅适用于此范围。修改项目、对象、档位、型号或基线后须重新确认；确认人、决定依据和期限用于下一次确认，历史记录不改写。B300 / SN5610 为当前案例型号，尚未代替项目批准的配置和性能基线。</p>
      <div className="decision-fields">{contextFields.map(f=>{
        const error=showErrors?contextIssues.find(i=>i.key===f.key)?.message:undefined
        let value=state.context[f.key]
        if(f.key==='valid_until' && value.endsWith('Z')) {const d=new Date(value);value=new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16)}
        return <div className="decision-input" key={f.key}><label htmlFor={'decision-context-'+f.key}>{f.label}</label><Input id={'decision-context-'+f.key} type={f.key==='valid_until'?'datetime-local':'text'} value={value} maxLength={2000} aria-invalid={!!error} aria-describedby={'decision-context-help-'+f.key} onChange={e=>{setChecked(false);persist({...state,context:{...state.context,[f.key]:e.target.value}})}}/><p id={'decision-context-help-'+f.key} className={error?'decision-error':'decision-hint'}>{error || f.hint}</p></div>
      })}</div>
    </details>
    {!!allConflicts.length && <div className="decision-error-panel" role="alert"><strong>需要解决的交叉冲突</strong>{allConflicts.map(c=><p key={c.message}>{c.message}</p>)}</div>}
    <div className="decision-layout">
      <nav className="decision-navigation" aria-label="业务确认事项">{model.decisions.map((d,i)=>{
        const s=status(d,state,model,clock)
        return <button key={d.id} type="button" aria-current={d.id===decision.id?'true':undefined} onClick={()=>open(d.id)}><span className="decision-index">{String(i+1).padStart(2,'0')}</span><span><strong>{d.topic}</strong><small>{badIds.has(d.id)?'存在交叉冲突':statusNames[s]}</small></span>{s==='confirmed'&&!badIds.has(d.id)&&<Check aria-label="已确认"/>}</button>
      })}</nav>
      <article className="decision-current" id="decision-current" tabIndex={-1} aria-label={decision.topic}>
        <header><div className="decision-row"><Badge variant={current==='confirmed'?'secondary':'outline'}>{statusNames[current]}</Badge><span className="decision-hint">建议责任人：{decision.owner}</span></div><h3>{decision.form.question}</h3></header>
        <Impact decision={decision} model={model}/>
        <details className="decision-known"><summary>已明确的边界（{decision.form.fixed.length} 条）</summary><ul>{decision.form.fixed.map(rule=><li key={rule}>{rule}</li>)}</ul></details>
        <form noValidate onSubmit={confirm}>
          <div className="decision-row decision-form-heading"><h4>填写本范围的判定参数</h4><span>{Math.max(0,complete)} / {activeFields.length} 项填写有效</span></div>
          <p className="decision-hint">数字框不预填建议阈值。0 是实际选择，留空表示尚未决定；单位写在字段旁边。</p>
          {groups.map(group=><fieldset key={group}><legend>{group}</legend><div className="decision-fields">{activeFields.filter(f=>f.group===group).map(f=><FieldControl key={f.key} prefix={'decision-'+decision.id} field={f} value={values[f.key]} onChange={value=>changeField(f.key,value)} error={showErrors?fieldIssues.find(i=>i.key===f.key)?.message:undefined}/>)}</div></fieldset>)}
          {quantities(decision,values).length>0 && <div className="decision-calculation"><strong>按当前填写计算</strong>{quantities(decision,values).map(line=><p key={line}>{line}</p>)}</div>}
          <div className="decision-confirm">
            <label className="decision-ack"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)}/><span>我已核对以上数值、适用范围和流程影响，明确确认本项用于该方案。现场结果仍需另行测量和验收。</span></label>
            <div className="decision-actions"><Button type="submit" disabled={current==='confirmed'&&!badIds.has(decision.id)&&!checked}>{current==='confirmed'?'新增确认修订':'确认本项并用于本方案'}</Button><Button type="button" variant="outline" onClick={()=>{setShowErrors(true);if(contextIssues.length)setContextOpen(true);setNotice([...contextIssues,...fieldIssues].length?`还有 ${contextIssues.length+fieldIssues.length} 处需要填写或修正。`:'填写完整，请核对影响后勾选并确认。')}}>检查填写</Button></div>
            {current==='confirmed' && <p className="decision-hint">修订 {latest(state,decision.id)!.revision} 已确认；上方“直接应用到这些步骤”可返回流程查看。</p>}
          </div>
        </form>
        {!!history.length && <details className="decision-history"><summary>查看 {history.length} 次确认历史</summary>{[...history].reverse().map(r=><details key={r.revision}><summary>修订 {r.revision} · {r.context.reviewer} · {new Date(r.confirmed_at).toLocaleString()}</summary><p>{r.context.project} · {r.context.scope} · 有效至 {new Date(r.valid_until).toLocaleString()}</p><ValueSummary decision={decision} values={r.values}/></details>)}</details>}
      </article>
    </div>
    {targets.map(target=>createPortal(<AppliedDecisions compact={target.id==='decision-flow-summary'} flowId={target.dataset.flowContext!} model={model} state={state} open={open}/>,target,target.id))}
  </div>
}

export function mountDecisions() { createRoot(document.getElementById('decisions')!).render(<Workbench/>) }
