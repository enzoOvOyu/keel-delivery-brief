import * as React from "react"
import { createPortal } from "react-dom"
import { createRoot } from "react-dom/client"
import { LayoutList, Cable, Database, Workflow, BookOpen, Network, FlaskConical, ClipboardCheck, Search, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { prepareDenseDetails } from "./density"
import { prepareWiring, selectWiringPanel, wiringGroups } from "./wiring"
// @ts-expect-error The existing read-only guide controller is JavaScript.
import { presentation } from "@/legacy/app.js"

type Item = { value: string; label: React.ReactNode; attrs: Record<string, string>; active: boolean; small?: boolean }
type Placement = { id: number; target: HTMLElement; kind: string; items: Item[]; value: string; origin?: HTMLInputElement | HTMLSelectElement }
let nextId = 0
const metadata = new WeakMap<HTMLElement, Placement>()
let refresh: () => void = () => {}

// Reuse the rendered labels verbatim; the adapter never authors business text.
function label(node: Node, key = 0): React.ReactNode {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent
  if (!(node instanceof HTMLElement)) return null
  const attrs: Record<string, string> = {}
  for (const name of ["id", "class", "aria-hidden"]) {
    if (node.hasAttribute(name)) attrs[name === "class" ? "className" : name] = node.getAttribute(name)!
  }
  return React.createElement(node.tagName.toLowerCase(), { ...attrs, key }, ...Array.from(node.childNodes).map((n, i) => label(n, i)))
}
function children(node: HTMLElement) { return Array.from(node.childNodes).map((n, i) => label(n, i)) }
function act(kind: string, value: string) { presentation.act(kind, value); refresh() }
const icons = [LayoutList, Cable, Database, BookOpen, Workflow, Network, FlaskConical, ClipboardCheck]

function Navigation({ placement: p }: { placement: Placement }) {
  const details = p.items.map((item, index) => ({ item, index })).filter(({ item }) => ["wiring", "network"].includes(item.attrs["data-view"]))
  const activeDetail = details.find(({ item }) => item.active)?.item.value
  const [expanded, setExpanded] = React.useState(Boolean(activeDetail))
  React.useEffect(() => { if (activeDetail) setExpanded(true) }, [activeDetail])
  const navItem = (item: Item, i: number, nested = false) => {
    const Icon = icons[i]
    return <Button key={item.value} variant="ghost" className={`nav ${nested ? "nav-child" : ""} ${item.active ? "active" : ""}`}
      {...item.attrs} hidden={item.attrs["data-flow"] === "C01"} aria-current={item.active ? "page" : undefined}
      onClick={() => act(item.attrs["data-flow"] ? "flow" : "view", item.value)}>
      <Icon aria-hidden="true" /><span className="nav-label">{item.label}</span>
    </Button>
  }
  return <>{p.items.map((item, i) => {
    if (item.attrs["data-view"] === "network") return null
    if (item.attrs["data-view"] !== "wiring") return navItem(item, i)
    return <div className="nav-group" key="flow-details">
      <Button variant="ghost" className={`nav nav-group-toggle ${activeDetail ? "group-active" : ""}`}
        aria-expanded={expanded} aria-controls="flow-detail-navigation" onClick={() => setExpanded(open => !open)}>
        <BookOpen aria-hidden="true" /><span className="nav-label">流程详解</span><ChevronDown className="nav-chevron" aria-hidden="true" />
      </Button>
      <div id="flow-detail-navigation" className="nav-children" hidden={!expanded}>
        {details.map(({ item: child, index }) => navItem(child, index, true))}
      </div>
    </div>
  })}</>
}

function TabGroup({ placement: p }: { placement: Placement }) {
  const wide = React.useSyncExternalStore(
    cb => { const q = matchMedia("(min-width: 1024px)"); q.addEventListener("change", cb); return () => q.removeEventListener("change", cb) },
    () => matchMedia("(min-width: 1024px)").matches,
  )
  const kind = p.kind === "detail" ? "detail" : p.kind === "layers" ? "layer" : p.kind === "diagrams" ? "diagram" : "scenario"
  return <Tabs value={p.value} orientation={p.kind === "layers" && wide ? "vertical" : "horizontal"}
    activationMode={p.kind === "wiring" ? "manual" : "automatic"}
    onValueChange={value => { if (p.kind === "wiring") { selectWiringPanel(p.target.id, value, true); refresh() } else act(kind, value) }} className={`inspection-tabs tabs-${p.kind}`}>
    <TabsList aria-label={p.target.getAttribute("aria-label") || p.target.id || "详细信息类别"}>
      {p.items.map(item => <TabsTrigger key={item.value} value={item.value} {...item.attrs}
        id={p.kind === "wiring" ? `${p.target.id}-${item.value}-trigger` : `ui-${p.kind}-${item.value}`} aria-controls={p.kind === "detail" ? `${item.value === "action" ? "action" : item.value === "data" ? "data" : "contract"}-information` : p.kind === "layers" ? "layer-detail" : p.kind === "diagrams" ? "diagram-panel" : "wiring-scenario"}
        {...(p.kind === "wiring" ? { "aria-controls": wiringGroups().get(p.target.id)?.panels.get(item.value)?.id } : {})}
        aria-pressed={p.value === item.value} className={p.value === item.value ? "active" : ""}>{item.label}</TabsTrigger>)}
    </TabsList>
  </Tabs>
}

function SelectControl({ placement: p }: { placement: Placement }) {
  const native = p.origin as HTMLSelectElement
  const EMPTY = "__all_steps__"
  return <Select value={p.value || EMPTY} onValueChange={value => {
    native.value = value === EMPTY ? "" : value
    native.dispatchEvent(new Event("change", { bubbles: true })); refresh()
  }}>
    <SelectTrigger id={`ui-${native.id}`} aria-label={native.getAttribute("aria-label") || native.dataset.uiLabel || native.id} className="inspection-select"><SelectValue /></SelectTrigger>
    <SelectContent position="popper" className="inspection-options">{p.items.map(item => <SelectItem key={item.value || EMPTY} value={item.value || EMPTY}>{item.label}</SelectItem>)}</SelectContent>
  </Select>
}

function SearchControl({ placement: p }: { placement: Placement }) {
  const original = p.origin as HTMLInputElement
  return <><Search aria-hidden="true" /><Input id="search" type="search" defaultValue={original.value}
    placeholder={original.placeholder} aria-label={original.getAttribute("aria-label") || undefined}
    onInput={() => { original.dispatchEvent(new Event("input")); refresh() }} /><kbd>/</kbd></>
}

function ActionPath({ placement: p }: { placement: Placement }) {
  return <>{p.items.map((item, i) => <React.Fragment key={item.value}>{i > 0 && <span aria-hidden="true"> → </span>}<Button variant="ghost" onClick={() => {
    p.target.parentElement?.querySelectorAll(":scope > .action-chain > section")[i]?.scrollIntoView({ behavior: "smooth", block: "start" })
  }}>{item.label}</Button></React.Fragment>)}</>
}

function Control({ placement: p }: { placement: Placement }) {
  if (p.kind === "navigation") return <Navigation placement={p} />
  if (["detail", "layers", "diagrams", "scenarios", "wiring"].includes(p.kind)) return <TabGroup placement={p} />
  if (p.kind === "select") return <SelectControl placement={p} />
  if (p.kind === "search") return <SearchControl placement={p} />
  if (p.kind === "path") return <ActionPath placement={p} />
  if (p.kind === "sides") return <>{p.items.map((item, i) => <React.Fragment key={item.value}>{i > 0 && <span aria-hidden="true">→</span>}<Button variant={item.active ? "secondary" : "ghost"} {...item.attrs} aria-pressed={item.active} onClick={() => act("side", item.value)}>{item.label}</Button></React.Fragment>)}</>
  return <><Badge variant="secondary">{p.items[0].label}</Badge><Button asChild><a href="downloads/keel-development-handoff.zip" download>{p.items[1].label}</a></Button></>
}

function capture(target: HTMLElement, kind: string, key?: string): Placement {
  let p = metadata.get(target)
  if (!p) {
    const nodes = kind === "header" ? Array.from(target.children) : kind === "search" ? [] : Array.from(target.querySelectorAll("button"))
    const items = nodes.map((node, i) => {
      const e = node as HTMLElement
      return { value: e.getAttribute(`data-${key}`) || String(i), label: children(e), attrs: Object.fromEntries(Array.from(e.attributes).filter(a => a.name.startsWith("data-")).map(a => [a.name, a.value])), active: e.getAttribute("aria-pressed") === "true" || e.classList.contains("active") }
    })
    p = { id: ++nextId, target, kind, items, value: items.find(i => i.active)?.value || items[0]?.value || "" }
    if (kind === "search") p.origin = target.querySelector("input")!
    if (kind === "path") p.items = target.textContent!.split(" → ").map((text, i) => ({ value: String(i), label: text, attrs: {}, active: false }))
    metadata.set(target, p)
    target.replaceChildren()
    target.dataset.uiOwned = "true"
    target.removeAttribute("role")
  }
  return p
}

function nativeSelect(native: HTMLSelectElement): Placement {
  let target = native.nextElementSibling as HTMLElement | null
  if (!target?.classList.contains("ui-select-host")) {
    target = document.createElement("span"); target.className = "ui-select-host"; target.dataset.uiOwned = "true"
    native.after(target); native.hidden = true; native.tabIndex = -1; native.setAttribute("aria-hidden", "true")
    native.dataset.uiLabel = native.labels?.[0]?.textContent || native.id
    for (const l of Array.from(native.labels || [])) l.htmlFor = `ui-${native.id}`
  }
  let p = metadata.get(target)
  if (!p) { p = { id: ++nextId, target, kind: "select", items: [], value: native.value, origin: native }; metadata.set(target, p) }
  p.items = Array.from(native.options).map(o => ({ value: o.value, label: o.text, attrs: {}, active: o.selected }))
  p.value = native.value
  return { ...p }
}

export function mountPresentation() {
  const mount = document.createElement("div"); mount.id = "ui-presentation"; document.body.append(mount)
  let signature = ""
  let queue = 0
  let update: (p: Placement[]) => void = () => {}
  function collect() {
    const state = presentation.state()
    if (!state.loaded) return
    const placements: Placement[] = []
    const add = (selector: string, kind: string, key?: string) => {
      const target = document.querySelector<HTMLElement>(selector)
      if (!target || !target.childNodes.length && !metadata.has(target)) return
      const p = capture(target, kind, key)
      if (kind === "navigation") {
        for (const item of p.items) item.active = item.attrs["data-flow"] ? state.view === "contracts" && item.value === state.selected : item.value === state.view
      } else if (kind === "detail") p.value = state.detailMode
      else if (kind === "diagrams") p.value = String(state.diagram)
      else if (kind === "wiring") p.value = wiringGroups().get(target.id)!.value
      else if (kind === "sides") p.items.forEach(item => { item.active = item.value === state.dataSide })
      else if (["layers", "scenarios"].includes(kind)) {
        const chosen = target.querySelector<HTMLElement>("button[aria-pressed=true]")
        if (chosen) p.value = chosen.getAttribute(`data-${key}`) || p.value
      }
      placements.push({ ...p, items: p.items.map(i => ({ ...i })) })
    }
    add(".sidebar nav", "navigation", "view")
    // A public flow uses a different data attribute from top-level views.
    const nav = placements.find(p => p.kind === "navigation")
    nav?.items.forEach(item => { if (item.attrs["data-flow"]) { item.value = item.attrs["data-flow"]; item.active = state.view === "contracts" && state.selected === item.value } })
    add("#header-actions", "header")
    add(".search-wrap", "search")
    if (state.loaded) {
      prepareWiring()
      prepareDenseDetails()
      for (const id of wiringGroups().keys()) {
        if (document.getElementById(id)) add(`#${id}`, "wiring", "wiring-value")
        else wiringGroups().delete(id)
      }
      add(".detail-switch", "detail", "detail-mode")
      add("#layer-tabs", "layers", "layer")
      add("#diagram-tabs", "diagrams", "diagram")
      add(".scenario-tabs", "scenarios", "scenario")
      add(".data-direction", "sides", "data-side")
      document.querySelectorAll<HTMLSelectElement>("#group-filter, #artifact-select, #data-artifact").forEach(native => placements.push(nativeSelect(native)))
      for (const mode of ["action", "data", "contract"]) {
        const panel = document.getElementById(`${mode}-information`)
        panel?.setAttribute("role", "tabpanel"); panel?.setAttribute("aria-labelledby", `ui-detail-${mode}`)
      }
    }
    const next = placements.map(p => [p.id, p.value, p.items.map(i => [i.value, i.active, typeof i.label === "string" ? i.label : ""])].flat()).map(v => JSON.stringify(v)).join("|")
    if (next !== signature) { signature = next; update(placements) }
  }
  refresh = () => { if (!queue) queue = requestAnimationFrame(() => { queue = 0; collect() }) }
  function Presentation() {
    const [placements, setPlacements] = React.useState<Placement[]>([])
    React.useLayoutEffect(() => { update = setPlacements; refresh() }, [])
    return <>{placements.map(p => createPortal(<Control placement={p} />, p.target, String(p.id)))}</>
  }
  createRoot(mount).render(<Presentation />)
  new MutationObserver(refresh).observe(document.querySelector(".app")!, { subtree: true, childList: true, attributes: true, attributeFilter: ["aria-pressed", "hidden"] })
  for (const name of ["change", "input", "click"]) document.addEventListener(name, refresh)
  window.addEventListener("hashchange", refresh)
  window.addEventListener("popstate", refresh)
}
