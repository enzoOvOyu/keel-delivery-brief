// Presentation only: move existing nodes into shared panels without rewriting text.
type Group = { value: string; panels: Map<string, HTMLElement> }
const groups = new Map<string, Group>()
let preparedSection: HTMLElement | null = null
let navigation: { value: string; label: string }[] | undefined
export const wiringGroups = () => groups

export function createInspectionTabs(id: string, entries: { value: string; label: string; panel: HTMLElement }[], label: string) {
  const nav = document.createElement('div')
  nav.id = id; nav.className = 'wiring-panel-tabs'; nav.setAttribute('aria-label', label)
  const group: Group = { value: entries[0].value, panels: new Map() }
  for (const entry of entries) {
    const button = document.createElement('button')
    button.type = 'button'; button.textContent = entry.label
    button.dataset.wiringValue = entry.value
    button.setAttribute('aria-pressed', String(entry.value === group.value))
    entry.panel.id ||= `${id}-${entry.value}`
    button.setAttribute('aria-controls', entry.panel.id)
    entry.panel.setAttribute('role', 'tabpanel')
    entry.panel.setAttribute('aria-label', entry.label)
    entry.panel.setAttribute('aria-labelledby', `${id}-${entry.value}-trigger`)
    entry.panel.hidden = entry.value !== group.value
    group.panels.set(entry.value, entry.panel); nav.append(button)
  }
  groups.set(id, group)
  return nav
}
export function selectWiringPanel(id: string, value: string, navigate = false) {
  const group = groups.get(id)
  if (!group?.panels.has(value)) return
  const changed = group.value !== value
  group.value = value
  for (const [key, panel] of group.panels) panel.hidden = key !== value
  if (changed && navigate && id === 'wiring-navigation') {
    history.pushState(null, '', `#wiring/${value}`)
  }
}
function divide(section: HTMLElement, id: string) {
  const heading = section.querySelector<HTMLElement>(':scope > .sample-subheading')!
  const table = section.querySelector<HTMLElement>(':scope > .sample-table')!
  const before = document.createElement('div'), after = document.createElement('div')
  before.className = after.className = 'wiring-inner-panel'
  const firstLabel = table.querySelector('th')!.textContent!
  const secondLabel = heading.textContent!
  let node: ChildNode | null = heading
  while (node) { const next: ChildNode | null = node.nextSibling; after.append(node); node = next }
  table.before(before); before.append(table)
  const nav = createInspectionTabs(id, [{ value: 'first', label: firstLabel, panel: before }, { value: 'second', label: secondLabel, panel: after }], section.querySelector('h3')!.textContent!)
  before.before(nav); section.append(after)
}
export function prepareWiring() {
  const content = document.getElementById('wiring-content')!
  const firstSection = content.querySelector<HTMLElement>('.sample-section')
  if (!firstSection || firstSection === preparedSection) return
  preparedSection = firstSection
  content.dataset.uiWiringReady = 'true'
  groups.clear()
  const oldNav = document.querySelector<HTMLElement>('.sample-nav')!
  const sections = Array.from(content.querySelectorAll<HTMLElement>(':scope > .sample-section'))
  const links = Array.from(oldNav.querySelectorAll('a'))
  navigation ||= links.map(link => ({ value: link.hash.split('/')[1], label: link.textContent! }))
  const entries = sections.map((panel, i) => ({ ...navigation![i], panel }))
  const nav = createInspectionTabs('wiring-navigation', entries, oldNav.getAttribute('aria-label')!)
  nav.classList.add('sample-nav')
  oldNav.replaceWith(nav)
  let bench = document.querySelector('.wiring-workbench')
  if (!bench) { bench = document.createElement('div'); bench.className = 'wiring-workbench'; nav.before(bench) }
  bench.append(nav, content)
  divide(sections[0], 'wiring-roles-tabs')
  divide(sections[2], 'wiring-evidence-tabs')
  const timeline = content.querySelector<HTMLElement>('.wiring-timeline')!
  const steps = Array.from(timeline.querySelectorAll<HTMLElement>(':scope > .wiring-step'))
  timeline.before(createInspectionTabs('wiring-step-tabs', steps.map((panel, i) => ({ value: String(i), label: panel.querySelector('.wiring-step-title')!.textContent!, panel })), sections[1].querySelector('h3')!.textContent!))
  for (const [i, step] of steps.entries()) {
    const dl = step.querySelector<HTMLElement>(':scope > dl')!
    const example = step.querySelector<HTMLDetailsElement>('.wiring-action-example')!
    const summary = example.querySelector('summary')!
    example.open = true; summary.hidden = true
    const mode = createInspectionTabs(`wiring-step-mode-${i}`, [{ value: 'summary', label: dl.querySelectorAll('dt')[1].textContent!, panel: dl }, { value: 'example', label: summary.textContent!, panel: example }], step.querySelector('h4')!.textContent!)
    dl.before(mode)
    const chain = example.querySelector<HTMLElement>('.action-chain')!
    const parts = Array.from(chain.querySelectorAll<HTMLElement>(':scope > section'))
    chain.before(createInspectionTabs(`wiring-action-tabs-${i}`, parts.map((panel, j) => ({ value: String(j), label: panel.querySelector('h4,h5')!.textContent!, panel })), summary.textContent!))
  }
  const [view, section] = location.hash.slice(1).split('/')
  if (view === 'wiring' && section) selectWiringPanel('wiring-navigation', section)
}
// Reveal deep-linked panels before the existing controller scrolls/focuses headings.
document.addEventListener('ui:wiring-section', ((event: CustomEvent<string>) => {
  prepareWiring(); selectWiringPanel('wiring-navigation', event.detail)
}) as EventListener)
