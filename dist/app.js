'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const READING_VERSION = '1.4-actions';
let model, report, selected = 'F01', view = 'contracts', zoom = 1, diagram = 0;
let detailMode = 'action', dataSide = 'outputs', dataArtifact = null;
const flow = id => model.flows.find(f => f.id === id);
const label = f => `${f.code} ${f.title}`;
const stageName = id => [...model.stages, model.common].find(s => s.id === id)?.name ?? '';
const decision = id => model.decisions.find(d => d.id === id);

function toast(message) {
  $('toast').textContent = message;
  $('toast').classList.add('visible');
  setTimeout(() => $('toast').classList.remove('visible'), 2200);
}
function writeHash(hash, replace = false) {
  if (location.hash !== '#' + hash) history[replace ? 'replaceState' : 'pushState'](null, '', '#' + hash);
}
function showView(id, updateHash = true) {
  if (!$('view-' + id)) id = 'contracts';
  view = id;
  document.body.dataset.view = id;
  document.querySelectorAll('.view').forEach(n => n.classList.toggle('active', n.id === 'view-' + id));
  document.querySelectorAll('.nav').forEach(n => {
    const active = n.dataset.flow ? id === 'contracts' && selected === n.dataset.flow : n.dataset.view === id;
    n.classList.toggle('active', active);
    if (active) n.setAttribute('aria-current', 'page');
    else n.removeAttribute('aria-current');
  });
  if (updateHash) writeHash(id === 'contracts' && selected ? 'contracts/' + flow(selected).code : id);
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function flowButton(id) {
  const f = flow(id);
  return f ? `<button class="inline-chip" data-flow="${esc(id)}">${esc(label(f))}</button>` : '';
}
function decisionLinks(ids) {
  return ids.map(id => `<button class="decision-link" data-decision="${esc(id)}">${esc(decision(id).topic)}</button>`).join('');
}
function briefCards(brief) {
  return `<dl class="brief-grid">${model.questions.map(q => `<div class="brief-card"><dt>${esc(q.title)}</dt><dd>${esc(brief[q.key])}</dd></div>`).join('')}</dl>`;
}
function renderStageOverview() {
  const id = $('group-filter').value || flow(selected)?.stage;
  const stage = model.stages.find(s => s.id === id);
  $('stage-overview').hidden = !stage;
  if (!stage) { $('stage-overview').innerHTML = ''; return; }
  $('stage-overview').innerHTML = `<div class="brief-heading"><div><span class="eyebrow">本步交接说明</span><h3>第 ${stage.id} 步 · ${esc(stage.name)}</h3></div>${stage.id === '3' ? '<button class="button primary small" data-go="wiring">打开 3.3 完整样板 ↗</button>' : `<button class="button small" data-jump="contract-toolbar">阅读本步流程 ↓</button>`}</div>${briefCards(stage.brief)}<p class="brief-boundary">${esc(stage.brief.boundary)}</p>`;
}
function sampleTable(headings, rows) {
  return `<div class="table-scroll sample-table"><table><thead><tr>${headings.map(h => `<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map((cell, i) => i === 0 ? `<th scope="row">${cell}</th>` : `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function renderWiringSample() {
  const sample = model.wiring_sample;
  $('wiring-overview').innerHTML = `<p class="sample-lead">${esc(sample.intro)}</p>${briefCards(sample.brief)}<p class="brief-boundary">沿用既有四步控制顺序；最终确认后，3.4 继续独立检查映射覆盖与冲突。</p>`;
  const roles = sampleTable(['责任主体', '负责的动作', '责任边界'], sample.roles.map(r => [esc(r.actor), esc(r.action), esc(r.boundary)]));
  const admission = sampleTable(['开始条件', '应具备的证明与提供方', '不满足时'], sample.admission.map(r => [esc(r.condition), `<p>${esc(r.evidence)}</p><div>${r.producer.map(flowButton).join('')}</div>`, esc(r.gap)]));
  const steps = sample.steps.map(s => `<article class="wiring-step"><div class="wiring-step-title"><span class="substep-code">${esc(s.code)}</span><h4>${esc(s.title)}</h4></div><dl>${[['input', '输入'], ['action', '执行动作'], ['output', '留下的证明'], ['finish', '何时继续'], ['failure', '失败后续']].map(([key, name]) => `<div><dt>${name}</dt><dd>${esc(s[key])}</dd></div>`).join('')}</dl><details class="wiring-action-example"><summary>B300 / SN5610 动作与数据对比</summary>${actionCard(flow('H04').substeps.find(x => x.code === s.code).walkthrough)}</details></article>`).join('');
  const evidence = sampleTable(['证据信息', '必须表达什么', '消费时核对什么'], sample.evidence_fields.map(r => [esc(r.name), esc(r.meaning), esc(r.check)]));
  const handoff = sampleTable(['当前完成事实', '证明了什么', '后续允许做什么'], sample.handoff.map(r => [esc(r.event), esc(r.meaning), esc(r.next)]));
  const recoveries = sampleTable(['问题', '处置内容', '回到哪里继续'], sample.recoveries.map(r => [esc(r.problem), esc(r.action), esc(r.return)]));
  const checks = sample.checks.map(check => {
    const results = check.cases.map(id => report.cases.find(c => c.id === id));
    const complete = results.length > 0 && results.every(Boolean);
    const passed = complete && results.every(c => c.status === 'pass');
    const state = !results.length ? '待补自动验证' : !complete ? '关联结果缺失' : passed ? `${results.length} 个模型用例通过` : '模型用例未通过';
    return `<article class="sample-check"><div class="row"><h4>${esc(check.name)}</h4><span class="pill ${passed ? 'sample-pass' : 'sample-pending'}">${state}</span></div><p>${esc(check.scope)}</p><p class="muted">对应证据信息：${check.fields.map(esc).join('、')}</p>${results.length ? `<details><summary>查看关联用例与本次结果</summary><ul>${check.cases.map((id, i) => `<li>${esc(model.case_names[id] || '用例未定义')} <b class="${results[i]?.status === 'pass' ? 'pass' : 'failed'}">${!results[i] ? '结果缺失' : results[i].status === 'pass' ? '通过' : '未通过'}</b></li>`).join('')}</ul></details>` : ''}</article>`;
  }).join('');
  $('wiring-content').innerHTML = `
    <section class="sample-section" aria-labelledby="wiring-roles"><h3 id="wiring-roles" tabindex="-1">责任与开始条件</h3><p class="section-description">业务职责与程序检查分别说明；每次对选定对象逐项核验。</p>${roles}<h4 class="sample-subheading">开始前逐项核对</h4>${admission}<div class="callout amber"><strong>开始条件不依赖本步尚未产生的结果</strong><p>${esc(sample.admission_boundary)}</p></div></section>
    <section class="sample-section" aria-labelledby="wiring-steps"><div class="section-heading"><div><h3 id="wiring-steps" tabindex="-1">四个子步骤，按顺序留下证明</h3><p>前一步不满足时阻断后续。每次重验保留新的步骤记录和依赖版本。</p></div><button class="button small" data-open-diagram="1">打开接线流程图 ↗</button></div><div class="wiring-timeline">${steps}</div></section>
    <section class="sample-section" aria-labelledby="wiring-evidence"><h3 id="wiring-evidence" tabindex="-1">证据包与下游交接</h3><p class="section-description">以下是产物必须表达的语义。字段命名与存储组织可以继续设计；必需内容、范围与版本不能省略。</p>${evidence}<h4 class="sample-subheading">逐级完成，逐级交接</h4>${handoff}<div class="sample-links">${['H04', 'H05', 'H06', 'T00'].map(flowButton).join('')}</div></section>
    <section class="sample-section" aria-labelledby="wiring-scenarios"><h3 id="wiring-scenarios" tabindex="-1">同一个端口对，五种不同的后续</h3><p class="section-description">${esc(sample.scenario_context)}</p><div class="tabs scenario-tabs" role="group" aria-label="选择说明情景">${sample.scenarios.map(s => `<button class="tab" data-scenario="${esc(s.id)}" aria-pressed="false">${esc(s.name)}</button>`).join('')}</div><div id="wiring-scenario" aria-live="polite"></div></section>
    <section class="sample-section" aria-labelledby="wiring-recovery"><h3 id="wiring-recovery" tabindex="-1">失败后如何继续</h3><p class="section-description">先定位问题和影响范围，再选择复验入口。</p>${recoveries}<div class="recovery-sequence" aria-label="工单恢复顺序"><span>登记与分派</span><span>维修处置</span><span>限定范围复验</span><span>通过后提议关闭</span><span>确认关闭</span></div><p class="reading-note">${esc(sample.recovery_boundary)}</p>${flowButton('R01')}</section>
    <section class="sample-section" aria-labelledby="wiring-verification"><h3 id="wiring-verification" tabindex="-1">哪些条件已有检查，哪些还需要补证</h3><p class="section-description">下列结果引用本次校验报告。八个现有用例仅检查局部模型；本页说明情景不计入测试通过数量。</p><div class="sample-checks">${checks}</div><div class="callout amber"><strong>业务待确认仍然保留</strong><p>${esc(sample.decision_note)}</p><div class="decision-links">${decisionLinks(sample.decisions)}</div></div><button class="button small" data-go="verification">查看完整校验与待确认清单 ↗</button></section>`;
  renderWiringScenario('confirmed');
}
function renderWiringScenario(id) {
  const s = model.wiring_sample.scenarios.find(item => item.id === id);
  if (!s) return;
  document.querySelectorAll('[data-scenario]').forEach(b => {
    const active = b.dataset.scenario === id;
    b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active));
  });
  $('wiring-scenario').innerHTML = `<div class="scenario-observations"><article><h4>批准的期望连接</h4><p>${s.id === 'changed' ? '原期望为 p1 ↔ p17；当前该端口对的期望版本已变更，需要重新核对。' : '服务器物理端口 p1 ↔ 交换机物理端口 p17。'}</p></article><article><h4>主机侧观测</h4><p>${esc(s.host)}</p></article><article><h4>交换机侧观测</h4><p>${esc(s.switch)}</p></article></div><div class="scenario-outcome ${esc(s.tone)}"><dl><div><dt>端口对结果</dt><dd>${esc(s.pair)}</dd></div><div><dt>整步是否完成</dt><dd>${esc(s.completion)}</dd></div><div><dt>当前能否使用</dt><dd>${esc(s.usable)}</dd></div></dl><p><strong>下一步：</strong>${esc(s.next)}</p></div>`;
}
function focusFlow(id, updateHash = true) {
  if (!flow(id)) return;
  selected = id;
  $('search').value = '';
  $('group-filter').value = flow(id).stage;
  renderFlows();
  showView('contracts', updateHash);
  document.querySelector('.flow-card.active')?.scrollIntoView({ block: 'nearest' });
  $('flow-detail').focus({ preventScroll: true });
}
function filteredFlows() {
  const query = $('search').value.trim().toLowerCase();
  const group = $('group-filter').value;
  return model.flows.filter(f => (!group || f.stage === group) && (!query || [
    f.code, f.title, f.purpose, f.resources, f.guards, f.actions, f.post, f.failure, f.retry, f.invalidation,
    ...f.substeps.map(s => `${s.code} ${s.title} ${s.description}`),
    JSON.stringify(f.walkthrough), ...f.substeps.map(s => JSON.stringify(s.walkthrough)),
    ...f.inputs.concat(f.outputs).map(id => model.artifacts.find(a => a.id === id).name),
    ...f.inputs.concat(f.outputs).flatMap(id => model.artifacts.find(a => a.id === id).data_contract.fields.map(field => `${field.name} ${field.label}`)),
  ].join(' ').toLowerCase().includes(query)));
}
function renderFlows() {
  const rows = filteredFlows();
  if (!rows.some(f => f.id === selected)) selected = rows[0]?.id ?? null;
  $('result-count').textContent = `${rows.length} / ${model.flows.length} 个流程`;
  const stages = [...model.stages, model.common];
  $('flow-list').innerHTML = rows.length ? stages.map(stage => {
    const items = rows.filter(f => f.stage === stage.id);
    if (!items.length) return '';
    return `<div class="flow-group-heading">${stage.id === '0' ? '全过程 · 公共流程' : `第 ${stage.id} 步 · ${esc(stage.name)}`}</div>` + items.map(f =>
      `<button class="flow-card ${f.id === selected ? 'active' : ''}" data-select="${esc(f.id)}" aria-pressed="${f.id === selected}"><div class="row"><span class="flow-id">${esc(f.code)}</span><span class="flow-group">${esc(stage.name)}</span></div><h3>${esc(f.title)}</h3><p>${esc(f.purpose)}</p></button>`).join('');
  }).join('') : '<div class="empty">没有匹配的步骤。可尝试“映射”“路径”或步骤编号。</div>';
  document.querySelectorAll('.spine-item').forEach(b => {
    const active = b.dataset.group === ($('group-filter').value || flow(selected)?.stage);
    b.classList.toggle('selected', active);
    b.setAttribute('aria-pressed', String(active));
  });
  renderStageOverview(); renderDetail();
  document.querySelectorAll('.nav[data-flow]').forEach(n => { const active = view === 'contracts' && n.dataset.flow === selected; n.classList.toggle('active', active); if (active) n.setAttribute('aria-current', 'page'); else n.removeAttribute('aria-current'); });
}
function fieldTable(rows) {
  return `<table class="data-field-table"><thead><tr><th scope="col">字段 / 含义</th><th scope="col">格式</th><th scope="col">要求 / 关联约束</th></tr></thead><tbody>${rows.map(r => `<tr><th scope="row">${r.name.split(' / ').map(name => `<code>${esc(name)}</code>`).join('<span class="field-separator"> / </span>')}<small>${esc(r.label)} <span class="field-status">${esc(r.status)}</span></small></th><td class="field-format">${esc(r.type)}</td><td><span class="field-required">${esc(r.required)}</span>${esc(r.rule)}</td></tr>`).join('')}</tbody></table>`;
}
function actionCard(c) {
  const resultClass = result => result === 'PASS' ? 'pass' : result === 'FAIL' || result === '命中异常' ? 'failed' : 'pending-result';
  return `<div class="action-chain"><section><h4>现场动作</h4><p class="action-owner">${esc(c.actor)}</p><p>${esc(c.action)}</p></section>
    <section><h4>原始数据</h4><p class="muted">以下为模拟值。每条观测保存来源、采集时间、质量与原始记录引用。</p><div class="action-table-wrap"><table class="action-data-table"><thead><tr><th scope="col">字段 / 格式</th><th scope="col">示例数据 / 采集来源</th></tr></thead><tbody>${c.raw.map(r => `<tr><th scope="row"><code>${esc(r.name)}</code><small>${esc(r.type)}</small></th><td>${esc(r.value)}<small>${esc(r.source)}</small></td></tr>`).join('')}</tbody></table></div></section>
    <section><h4>比对判定</h4><p class="muted">数量与质量分开核对；正向示例和异常反例独立展示。逐项结论不代表整步通过。</p><div class="comparison-list">${c.comparisons.map(r => `<article class="comparison"><div class="row"><strong>${esc(r.item)}</strong><span class="${resultClass(r.result)}">${esc(r.result)}</span></div><dl><div><dt>期望</dt><dd>${esc(r.expected)}</dd></div><div><dt>实测示例</dt><dd>${esc(r.observed)}</dd></div></dl><p>${esc(r.rule)}</p></article>`).join('')}</div></section>
    <section><h4>输出产物</h4><p>${esc(c.output)}</p>${c.output_refs ? `<div class="action-output-links">${c.output_refs.map(id => `<button class="inline-chip" data-output-format="${esc(id)}">${esc(model.artifacts.find(a => a.id === id).data_contract.category)} · 字段格式 ↗</button>`).join('')}</div>` : ''}</section>
    <section><h4>下游使用</h4><p>${esc(c.use)}</p>${c.routes ? c.routes.map(r => `<div class="action-handoff"><strong>${esc(model.artifacts.find(a => a.id === r.artifact_id).data_contract.category)}</strong><div>${r.consumers.map(flowButton).join('')}${r.terminal ? `<span class="muted">${esc(r.terminal)}</span>` : ''}</div></div>`).join('') : ''}</section>
    <p class="action-recovery"><strong>失败后继续</strong>${esc(c.recovery)}</p></div>`;
}
function renderActionInformation(f) {
  const h = model.hardware_example;
  return `<div class="action-context"><span class="tag p">模拟案例 · 开发约定建议</span><h4>${esc(h.title)}</h4><p>${esc(h.scope)}</p><details><summary>对象 ID、数量口径与硬件依据</summary><p>${esc(h.boundary)}</p><dl>${h.identities.map(r => `<div><dt>${esc(r[0])}</dt><dd><code>${esc(r[1])}</code><p>${esc(r[2])}</p></dd></div>`).join('')}</dl><p>${esc(h.quantities)}</p><div class="hardware-sources">${h.sources.map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`).join('')}</div><small>硬件资料核对日期：${esc(h.checked_on)}</small></details></div>
    <div class="action-path" aria-label="动作数据链">现场动作 → 原始数据 → 比对判定 → 输出产物 → 下游使用</div>
    ${f.id === 'C01' ? '<p class="callout amber">这里的输入类别是逐事件订阅目录，每条记录可独立同步。无需等待全部输入齐备；同步回执不等于业务验收通过。</p>' : ''}
    ${actionCard(f.walkthrough)}${f.substeps.length ? `<section class="nested-actions"><h4>逐个子步骤展开</h4>${f.substeps.map(s => `<details id="action-${esc(s.code)}"><summary>${esc(s.code)} ${esc(s.title)}</summary>${actionCard(s.walkthrough)}</details>`).join('')}</section>` : ''}`;
}
function renderDataContracts() {
  const f = flow(selected);
  if (!f || !$('data-information')) return;
  const ids = f[dataSide];
  if (!ids.includes(dataArtifact)) dataArtifact = ids[0];
  const a = model.artifacts.find(item => item.id === dataArtifact);
  const guide = model.data_guide, c = a.data_contract;
  const route = dataSide === 'inputs'
    ? `<div class="data-route"><strong>由谁提供</strong><div>${a.producer === 'external' ? esc(a.owner) : flowButton(a.producer)}</div></div>`
    : `<details class="data-routing" ${a.consumers.length <= 3 ? 'open' : ''}><summary>交给谁使用${a.consumers.length ? ` · ${a.consumers.length} 个流程` : ''}</summary><div>${a.consumers.map(flowButton).join('')}${a.terminal_consumer ? `<span class="muted">${esc(a.terminal_consumer)}</span>` : ''}</div></details>`;
  $('data-information').innerHTML = `
    <div class="data-intro"><h4>ID 规划与数据格式</h4><p>${esc(guide.note)}</p></div>
    <details class="data-rules"><summary><span>ID 规划</span><small>对象稳定 · 版本固定 · 重试另建尝试</small></summary><dl>${guide.id_rules.map(r => `<div><dt>${esc(r.name)}<small>${esc(r.status)}</small></dt><dd><code>${esc(r.fields)}</code><p>${esc(r.rule)}</p></dd></div>`).join('')}</dl></details>
    <div class="data-direction" role="group" aria-label="输入与产出类别"><button data-data-side="inputs" aria-pressed="${dataSide === 'inputs'}">前置输入 <b>${f.inputs.length}</b></button><span aria-hidden="true">→</span><button data-data-side="outputs" aria-pressed="${dataSide === 'outputs'}">可消费产物 <b>${f.outputs.length}</b></button></div>
    <label class="data-select-label" for="data-artifact">选择${dataSide === 'inputs' ? '输入' : '产出'}类别</label><select id="data-artifact">${ids.map(id => { const item = model.artifacts.find(x => x.id === id); return `<option value="${esc(id)}" ${id === a.id ? 'selected' : ''}>${esc(item.data_contract.category)}</option>`; }).join('')}</select>
    <div class="data-record-heading"><h4>${esc(c.category)}</h4><p>${esc(a.name)}</p></div>
    <div class="data-fields">${fieldTable(c.fields)}</div>
    <p class="data-condition"><strong>${dataSide === 'inputs' ? '使用前核对' : '交接条件'}</strong>${esc(c.rule)}</p>${route}
    <details class="data-rules"><summary><span>业务产物通用字段</span><small>标识、范围、版本与执行来源</small></summary>${fieldTable(guide.common_fields)}</details>
    <details class="data-rules"><summary><span>类型与格式速查</span><small>ID · 引用 · 时间 · 数组 · 指标</small></summary><dl>${guide.formats.map(r => `<div><dt>${esc(r.name)}</dt><dd><code>${esc(r.shape)}</code><p>${esc(r.rule)}</p></dd></div>`).join('')}</dl></details>`;
}
function setDetailMode(mode) {
  detailMode = mode;
  document.querySelectorAll('[data-detail-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.detailMode === mode)));
  $('contract-information').hidden = mode !== 'contract';
  $('data-information').hidden = mode !== 'data';
  $('action-information').hidden = mode !== 'action';
}
function renderDetail() {
  const f = flow(selected);
  if (!f) {
    $('flow-detail').innerHTML = '<div class="empty">当前筛选没有结果，请调整关键词或步骤范围。</div>';
    return;
  }
  const ars = new Map(model.artifacts.map(a => [a.id, a]));
  const inputs = f.inputs.map(id => {
    const a = ars.get(id);
    return `<div class="artifact-row"><strong>${esc(a.name)}</strong><div>${a.producer === 'external' ? `<span class="muted">${esc(a.owner)}</span>` : flowButton(a.producer)}</div></div>`;
  }).join('');
  const outputs = f.outputs.map(id => {
    const a = ars.get(id);
    return `<div class="artifact-row"><strong>${esc(a.name)}</strong><div>${a.consumers.map(flowButton).join('')}${a.terminal_consumer ? `<span class="muted">交给：${esc(a.terminal_consumer)}</span>` : ''}</div></div>`;
  }).join('');
  const fields = [['输入与生产方', inputs], ['所需资源', esc(f.resources)], ['开始条件', esc(f.guards)],
    ['执行动作', esc(f.actions)], ['产物与消费者', outputs], ['完成证明', esc(f.post)],
    ['失败与阻断', esc(f.failure)], ['恢复与重试', esc(f.retry)], ['失效条件', esc(f.invalidation)]];
  const substeps = f.substeps.length ? `<section class="substeps"><h4>本步骤的执行顺序</h4><ol>${f.substeps.map(s => `<li id="step-${esc(s.code)}"><span class="substep-code">${esc(s.code)}</span><div><h5>${esc(s.title)}</h5><p>${esc(s.description)}</p></div></li>`).join('')}</ol></section>` : '';
  const checks = f.checks.length ? `<section class="substeps"><h4>报告需要解释的检测场景</h4><p>以下为默认判据或型号基线要求。实际使用已批准的参数版本；缺少必需基线时不能默认通过。</p><dl class="scenario-list">${f.checks.map(c => `<div><dt>${esc(c.name)}</dt><dd>${esc(c.description)}</dd></div>`).join('')}</dl></section>` : '';
  const ordered = model.flows.filter(x => x.stage !== '0');
  const at = ordered.findIndex(x => x.id === f.id);
  const readingNav = at < 0 ? '' : `<div class="reading-nav">${at > 0 ? `<button class="button small" data-flow="${ordered[at - 1].id}">← 阅读 ${ordered[at - 1].code}</button>` : '<span></span>'}${at < ordered.length - 1 ? `<button class="button small" data-flow="${ordered[at + 1].id}">阅读 ${ordered[at + 1].code} →</button>` : '<span></span>'}</div>`;
  $('flow-detail').innerHTML = `<div class="detail-top"><div class="row"><span class="tag p">${f.stage === '0' ? '贯穿五步 · 公共流程' : `第 ${f.stage} 步 · ${esc(stageName(f.stage))}`}</span><span class="flow-id">${esc(f.code)}</span></div><h3>${esc(label(f))}</h3><p>${esc(f.purpose)}</p>${f.id === 'H04' ? '<button class="button primary small sample-entry" data-go="wiring">阅读 3.3 完整样板 ↗</button>' : ''}</div><div class="detail-switch" role="group" aria-label="详细信息类别"><button data-detail-mode="action" aria-controls="action-information" aria-pressed="false">动作与数据 <small>案例 / 比对</small></button><button data-detail-mode="contract" aria-controls="contract-information" aria-pressed="false">流程契约</button><button data-detail-mode="data" aria-controls="data-information" aria-pressed="false">信息类别 <small>ID / 格式</small></button></div><section id="action-information" aria-label="现场动作与数据对比">${renderActionInformation(f)}</section><section id="data-information" aria-label="信息类别与数据格式"></section><section id="contract-information" aria-label="流程契约"><dl class="contract-fields">${fields.map(([k, v]) => `<div class="field"><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>${substeps}${checks}</section>${f.note || f.decisions.length ? `<div class="detail-note">${f.note ? `<p>${esc(f.note)}</p>` : ''}${f.decisions.length ? `<strong>这些业务细节仍待确认</strong><div class="decision-links">${decisionLinks(f.decisions)}</div>` : ''}</div>` : ''}${readingNav}`;
  renderDataContracts(); setDetailMode(detailMode);
}
function renderArtifact() {
  const a = model.artifacts.find(x => x.id === $('artifact-select').value);
  $('artifact-detail').innerHTML = `<h3>${esc(a.name)}</h3><p>由谁提供</p><div>${a.producer === 'external' ? esc(a.owner) : flowButton(a.producer)}</div><p>后续交给</p><div>${a.consumers.map(flowButton).join('')}${a.terminal_consumer ? `<span class="muted">${esc(a.terminal_consumer)}</span>` : ''}</div>`;
}
const diagramDescriptions = [
  ['全图按步骤编号定位，箭头表达现有产物消费关系。网络底座与装机可并行；网络验收导出不会额外阻断装机。网络测试与 NCCL 子流程在对应专图展开。', ['F01', 'H01', 'H04', 'H05', 'H06', 'T00', 'T06', 'N01', 'N08']],
  ['3.3.1～3.3.4 是明确的控制顺序。单个端口对通过后，仍需交付组长最终确认，才能发布映射；差异沿公共修复流程回到受影响步骤重验。', ['H03', 'H04', 'H05', 'R01']],
  ['4.1 冻结准入与测试范围；4.2～4.6 提供五类检查证据，4.7 汇总。各检查之间是否严格串行仍待确认；无损观测必须覆盖相关负载窗口。', ['T00', 'T01', 'T02', 'T03', 'T04', 'T05', 'T06']],
  ['0.1 是所有步骤共用的修复与复验入口。历史通过结论保留，版本变化后重新判断能否消费；结果不明时先核对回执与实际状态。', ['R01', 'H06', 'T06', 'N08']],
  ['5.1～5.8 展开通信组预检、测试、报告、溯源与评审。5.3 包含机内、跨机和全目标三个子步骤。失败后整组创建新尝试；最终评审只解锁退出流程。', ['N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08']],
];
diagramDescriptions.push(['0.2 对所有流程产物及原始观测逐条建索引。各来源独立同步，源表保持权威；清理已核验事件才触发归档与维护态。', ['H07', 'H02', 'C01', 'R01']]);
function renderDiagram() {
  const viewport = document.querySelector('.diagram-viewport');
  viewport.scrollTop = 0;
  viewport.scrollLeft = 0;
  document.querySelectorAll('[data-diagram]').forEach(b => {
    const active = Number(b.dataset.diagram) === diagram;
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
  $('diagram-image').src = `diagrams/page-${diagram + 1}.svg?v=${READING_VERSION}`;
  $('diagram-image').alt = model.diagrams[diagram];
  $('diagram-image').style.width = 100 * zoom + '%';
  $('diagram-caption').textContent = `${model.diagrams[diagram]} · ${Math.round(zoom * 100)}%`;
  const [text, ids] = diagramDescriptions[diagram];
  $('diagram-explanation').innerHTML = `<p>${esc(text)}</p><div>${ids.map(flowButton).join('')}</div>`;
  $('diagram-error').hidden = true;
}
function renderLayer(id = 'T01') {
  const f = flow(id);
  document.querySelectorAll('[data-layer]').forEach(b => {
    const active = b.dataset.layer === id;
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
  $('layer-detail').innerHTML = `<span class="flow-id">第 4 步 · 网络测试</span><h3>${esc(label(f))}</h3><p>${esc(f.purpose)}</p><div class="layer-fields">${[['输入与资源', f.resources], ['执行内容', f.actions], ['通过与产物', f.post], ['失败与证明不足', f.failure]].map(([k, v]) => `<div><h4>${k}</h4><p>${esc(v)}</p></div>`).join('')}</div><div class="decision-links">${decisionLinks(f.decisions)}</div>${flowButton(f.id)}`;
}
function renderDemo() {
  const flags = Object.fromEntries(['path', 'version', 'stale', 'unknown', 'waiver', 'auth'].map(k => [k, $('demo-' + k).checked]));
  const reasons = [];
  if (flags.path) reasons.push('路径缺口：既有 A:1 → B:1 证明不覆盖新增 A:1 → C:1。');
  if (flags.version) reasons.push('版本不匹配：证明绑定配置 c1，本次相关配置已经变为 c2。');
  if (flags.stale) reasons.push('就绪证明过期：31 秒超过默认 30 秒有效期，需要刷新。');
  if (flags.unknown && !flags.waiver) reasons.push('必需观测不足：PFC 不可采集为 unknown，不能填 0 或判正常。');
  if (flags.auth) reasons.push('项目执行权限缺失：即使有有效豁免也不能派发。');
  const reject = reasons.length > 0, waived = flags.waiver;
  $('demo-verdict').innerHTML = `<div class="verdict-box ${reject ? 'blocked' : waived ? 'waived' : ''}"><div class="eyebrow">本次消费判定 · 模拟</div><h3>${reject ? '拒绝消费' : waived ? '按有效豁免允许消费' : '允许消费'}</h3><p>保存的验收结论：<strong>${waived ? 'WAIVED' : 'PASS'}</strong> · ${reject ? '历史结论保留，但不满足当前任务条件。' : waived ? '本项缺口有明确范围和期限的审批，保持豁免结论。' : '本次目标、路径、档位、版本和时效匹配。'}</p>${reasons.length ? `<ul>${reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}</div>`;
}
function renderVerification() {
  const s = report.summary;
  $('verification-stats').innerHTML = [[s.passed_cases + '/' + s.cases, '固定用例通过', '准入、接线、无损与通信组'], [s.structural_checks, '结构检查', '输入摘要、引用、依赖与图文件'], [s.killed_mutations + '/' + s.mutations, '注入错误被发现', '检查成功与失败边界'], [model.decisions.length, '业务待确认', '模型通过不会自动解决缺口']].map(([n, t, d]) => `<div class="stat"><b>${n}</b><span>${t}</span><small>${d}</small></div>`).join('');
  document.querySelector('.action-verification')?.remove();
  if (report.walkthrough) $('verification-stats').insertAdjacentHTML('afterend', `<details class="action-verification"><summary>动作数据与 CMDB：${report.walkthrough.checks.filter(c => c.passed).length}/${report.walkthrough.checks.length} 项有限检查 · ${report.walkthrough.cards} 张卡片</summary><p>${esc(report.walkthrough.scope)}</p><ul>${report.walkthrough.checks.map(c => `<li>${c.passed ? '✓' : '✕'} ${esc(c.name)}</li>`).join('')}</ul></details>`);
  $('race-detail').textContent = `在 ${report.version_race.states} 个可达状态、${report.version_race.transitions} 条转移的有限模型中，保留版本复核时未发现旧版本被错误放行；移除后得到上面的反例。`;
  $('cases-count').textContent = `${report.cases.length} 个用例`;
  $('case-table').innerHTML = report.cases.map((c, i) => `<tr><td>${String(i + 1).padStart(2, '0')}</td><td>${esc(model.case_names[c.id])}</td><td><span class="${c.status === 'pass' ? 'pass' : 'failed'}">${c.status === 'pass' ? '✓ 通过' : '✕ 未通过'}</span></td><td>${c.invariants.map(id => esc(model.invariants[id])).join('<br>')}</td></tr>`).join('');
  $('decisions').innerHTML = model.decisions.map(d => `<article id="decision-${esc(d.id)}" class="decision" tabindex="-1"><span class="tag q">待确认</span><div><h3>${esc(d.topic)}</h3><p>${esc(d.recommendation)}</p><p><strong>未决边界：</strong>${esc(d.boundary)}</p><div>${d.flows.map(flowButton).join('')}</div></div><aside>建议责任人<b>${esc(d.owner)}</b></aside></article>`).join('');
}
function restoreHash() {
  const [requested, code] = location.hash.slice(1).split('/');
  if (requested === 'contracts' && code) {
    const stage = [...model.stages, model.common].find(s => 'stage-' + s.id === code);
    if (stage) {
      $('group-filter').value = stage.id; $('search').value = ''; selected = stage.flows[0];
      renderFlows(); showView('contracts', false); return;
    }
    const f = model.flows.find(x => x.code === code);
    if (f) { focusFlow(f.id, false); return; }
  }
  showView(requested || 'contracts', false);
  if (requested === 'wiring' && code) {
    const target = $('wiring-' + code);
    if (target?.matches('h3')) { target.scrollIntoView({ block: 'start' }); target.focus({ preventScroll: true }); }
  }
}
async function init() {
  $('load-error').hidden = true;
  model = undefined; report = undefined;
  try {
    [model, report] = await Promise.all(['reading-model.json', 'verification-report.json'].map(p => fetch(`${p}?v=${READING_VERSION}`).then(r => {
      if (!r.ok) throw new Error(`无法读取 ${p}（${r.status}）`);
      return r.json();
    })));
    if (model.version !== READING_VERSION || report.reading_version !== READING_VERSION) throw new Error('页面与讲解数据的版本不一致，请刷新后重试。');
    $('group-filter').innerHTML = '<option value="">全部步骤与公共流程</option>' + [...model.stages, model.common].map(s => `<option value="${s.id}">${s.id === '0' ? '' : `${s.id} · `}${esc(s.name)}</option>`).join('');
    $('flow-total').textContent = model.flows.length;
    $('spine').innerHTML = model.stages.map(s => `<button class="spine-item" data-group="${s.id}" aria-pressed="false"><span class="spine-num">第 ${s.id} 步 · ${s.flows.length} 个流程</span><b>${esc(s.name)}</b><small>${esc(s.summary)}</small></button>`).join('');
    $('artifact-select').innerHTML = model.artifacts.map(a => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');
    $('artifact-select').value = 'g5';
    $('diagram-tabs').innerHTML = model.diagrams.map((name, i) => `<button class="tab" data-diagram="${i}">${esc(name)}</button>`).join('');
    $('layer-tabs').innerHTML = ['T01', 'T02', 'T03', 'T04', 'T05'].map(id => `<button class="tab" data-layer="${id}">${esc(label(flow(id)))}</button>`).join('');
    $('ll-rules').innerHTML = model.rules.map(r => `<article class="ll-rule"><div><h4>${esc(r.name)}</h4><p>${esc(r.description)}</p></div></article>`).join('');
    $('glossary').innerHTML = model.glossary.map(g => `<div><dt>${esc(g.name)}</dt><dd>${esc(g.description)}</dd></div>`).join('');
    renderFlows(); renderArtifact(); renderDiagram(); renderLayer(); renderDemo(); renderVerification(); renderWiringSample(); restoreHash();
  } catch (error) {
    model = undefined; report = undefined;
    $('load-error').hidden = false;
    $('load-error-text').textContent = error.message;
    $('flow-list').innerHTML = '<div class="empty">讲解资料暂不可用，请重试加载。</div>';
    $('flow-detail').innerHTML = '';
    $('stage-overview').innerHTML = '';
    $('wiring-overview').innerHTML = '';
    $('wiring-content').innerHTML = '<p class="empty">样板资料尚未加载，请重试。</p>';
    $('verification-stats').innerHTML = '<p class="empty">校验结果尚未加载。</p>';
  }
}

document.addEventListener('click', e => {
  const b = e.target.closest('button,a');
  if (!b || !model) return;
  if (b.matches('a[href^="#wiring/"]')) {
    e.preventDefault(); writeHash(b.getAttribute('href').slice(1)); restoreHash(); return;
  }
  if (b.dataset.view) showView(b.dataset.view);
  if (b.dataset.go) showView(b.dataset.go);
  if (b.dataset.select) { selected = b.dataset.select; renderFlows(); writeHash('contracts/' + flow(selected).code); }
  if (b.dataset.flow) focusFlow(b.dataset.flow);
  if (b.dataset.detailMode) setDetailMode(b.dataset.detailMode);
  if (b.dataset.outputFormat) { dataSide = 'outputs'; dataArtifact = b.dataset.outputFormat; renderDataContracts(); setDetailMode('data'); $('data-artifact').focus({ preventScroll: true }); }
  if (b.dataset.dataSide) { dataSide = b.dataset.dataSide; dataArtifact = null; renderDataContracts(); document.querySelector(`[data-data-side="${dataSide}"]`)?.focus({ preventScroll: true }); }
  if (b.dataset.group) {
    $('group-filter').value = b.dataset.group; $('search').value = '';
    selected = model.flows.find(f => f.stage === b.dataset.group)?.id ?? null;
    renderFlows(); showView('contracts', false); writeHash('contracts/stage-' + b.dataset.group);
  }
  if (b.dataset.jump) document.querySelector('.' + b.dataset.jump)?.scrollIntoView({ block: 'start' });
  if (b.dataset.scenario) renderWiringScenario(b.dataset.scenario);
  if (b.dataset.openDiagram !== undefined) { diagram = Number(b.dataset.openDiagram); zoom = 1; renderDiagram(); showView('diagrams'); }
  if (b.dataset.diagram !== undefined) { diagram = Number(b.dataset.diagram); zoom = 1; renderDiagram(); }
  if (b.dataset.layer) renderLayer(b.dataset.layer);
  if (b.dataset.decision) {
    e.preventDefault(); showView('verification');
    const target = $('decision-' + b.dataset.decision);
    target?.scrollIntoView({ block: 'center' }); target?.focus({ preventScroll: true });
  }
});
document.addEventListener('change', e => {
  if (e.target.id === 'data-artifact' && model) { dataArtifact = e.target.value; renderDataContracts(); $('data-artifact').focus({ preventScroll: true }); }
});
$('search').addEventListener('input', () => { if (model) renderFlows(); });
$('group-filter').addEventListener('change', () => { if (model) renderFlows(); });
$('artifact-select').addEventListener('change', () => { if (model) renderArtifact(); });
['path', 'version', 'stale', 'unknown', 'waiver', 'auth'].forEach(k => $('demo-' + k).addEventListener('change', renderDemo));
$('demo-reset').addEventListener('click', () => { document.querySelectorAll('.demo-controls input').forEach(i => i.checked = false); renderDemo(); });
$('zoom-out').onclick = () => { zoom = Math.max(.6, zoom - .2); if (model) renderDiagram(); };
$('zoom-in').onclick = () => { zoom = Math.min(2.5, zoom + .2); if (model) renderDiagram(); };
$('zoom-fit').onclick = () => { zoom = 1; if (model) renderDiagram(); };
$('diagram-image').onerror = () => { $('diagram-error').hidden = false; };
$('reload-data').onclick = init;
window.addEventListener('popstate', () => { if (model) restoreHash(); });
window.addEventListener('hashchange', () => { if (model) restoreHash(); });
document.addEventListener('keydown', e => {
  if (model && e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    e.preventDefault(); showView('contracts'); $('search').focus();
  }
});
init();
