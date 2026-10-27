import { createInspectionTabs } from './wiring'

export function prepareDenseDetails() {
  const info = document.getElementById('action-information')
  if (info && !info.dataset.compact && info.querySelector('.action-chain')) {
    info.dataset.compact = 'true'
    const context = info.querySelector<HTMLElement>(':scope > .action-context')
    if (context) {
      const details = document.createElement('details'), summary = document.createElement('summary')
      details.className = 'action-context compact-hardware'
      summary.append(context.querySelector(':scope > .tag')!, context.querySelector(':scope > h4')!)
      details.append(summary, ...Array.from(context.childNodes)); context.replaceWith(details)
    }
    info.querySelectorAll<HTMLElement>('.action-chain').forEach((chain, i) => {
      const sections = Array.from(chain.querySelectorAll<HTMLElement>(':scope > section'))
      const nav = createInspectionTabs(`flow-action-tabs-${i}`, sections.map((panel, j) => ({
        value: String(j), label: panel.querySelector('h4,h5')!.textContent!, panel,
      })), info.getAttribute('aria-label')!)
      nav.classList.add('compact-action-tabs')
      if (i === 0) { nav.classList.add('action-path'); info.querySelector(':scope > .action-path')?.replaceWith(nav) }
      else chain.before(nav)
    })
  }
  for (const article of document.querySelectorAll<HTMLElement>('#decisions > .decision:not([data-compact])')) {
    article.dataset.compact = 'true'
    const details = document.createElement('details')
    const summary = document.createElement('summary')
    const body = article.querySelector<HTMLElement>(':scope > div')!
    summary.append(article.querySelector(':scope > .tag')!, body.querySelector('h3')!, article.querySelector(':scope > aside')!)
    details.append(summary, body); article.append(details)
  }
}
export function compactPageContext() {
  const intro = document.querySelector<HTMLElement>('main > .intro')!
  const legend = document.querySelector<HTMLElement>('main > .legend')!
  const details = document.createElement('details'), summary = document.createElement('summary')
  details.className = 'site-context'; summary.textContent = '阅读指南'
  intro.before(details); details.append(summary, intro, legend)
}
