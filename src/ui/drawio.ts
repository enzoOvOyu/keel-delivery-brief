import { enableDrawioEditor } from './drawio-editor'
import viewerUrl from '../vendor/drawio/viewer-static.min.js?url'
import licenseUrl from '../vendor/drawio/LICENSE?url'
// The upstream viewer exposes browser globals, not a TypeScript module.
type ViewerWindow = Window & typeof globalThis & {
  GraphViewer: new (container: HTMLElement, xml: Element, options: object) => any
  mxConstants: { DEFAULT_FONTFAMILY: string }
  onDrawioViewerLoad: () => void
  keelViewer?: any
}

export function enableDrawio() {
  const viewport = document.querySelector<HTMLElement>('.diagram-viewport')!
  const image = document.getElementById('diagram-image') as HTMLImageElement
  const frame = document.createElement('iframe')
  frame.id = 'drawio-viewer'; frame.title = 'draw.io 流程图查看器'
  frame.dataset.license = new URL(licenseUrl, document.baseURI).href
  frame.hidden = true
  viewport.append(frame)
  let loading: Promise<void> | undefined
  let viewer: any
  let currentPage = -1
  let requested = { diagram: 0, zoom: 1, fit: false }
  let baseScale = 1
  enableDrawioEditor(viewport, sync)

  function fit() {
    if (!viewer?.graph || viewport.classList.contains('editing') || document.body.dataset.view !== 'diagrams') return
    const graph = viewer.graph
    graph.maxFitScale = null
    graph.view.scaleAndTranslate(1, 0, 0)
    graph.fit(16, false, 10, true, false, true)
    baseScale = graph.view.scale
    graph.view.setScale(baseScale * requested.zoom)
    graph.center(true, false)
    graph.container.scrollTop = 0
  }
  function sync() {
    if (!viewer?.graph || viewport.classList.contains('editing') || document.body.dataset.view !== 'diagrams') return
    if (currentPage !== requested.diagram) {
      currentPage = requested.diagram
      viewer.selectPage(currentPage)
      const graph = viewer.graph
      const family = getComputedStyle(document.documentElement).getPropertyValue('--app-font').trim()
      const cells = Object.values(graph.getModel().cells).filter((cell: any) => cell.vertex || cell.edge)
      graph.setCellStyles('fontFamily', family, cells)
      fit()
    } else if (requested.fit) fit()
    else zoomAt(requested.zoom)
  }
  function zoomAt(ratio: number, x?: number, y?: number) {
    if (!viewer?.graph) return
    const graph = viewer.graph
    const scale = graph.view.scale
    const next = baseScale * ratio
    x ??= graph.container.clientWidth / 2
    y ??= graph.container.clientHeight / 2
    const t = graph.view.translate
    graph.view.scaleAndTranslate(next, t.x + x / next - x / scale, t.y + y / next - y / scale)
  }
  async function load() {
    const response = await fetch('downloads/keel-delivery.drawio')
    if (!response.ok) throw new Error('draw.io source unavailable')
    const xml = await response.text()
    frame.srcdoc = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>html,body{height:100%;margin:0;background:white}#graph{position:absolute;inset:0;overflow:hidden!important;cursor:grab;touch-action:none}#graph:active{cursor:grabbing}</style></head><body><div id="graph" style="width:100%;height:100%" tabindex="0" role="region" aria-label="可拖动流程图"></div></body></html>'
    await new Promise<void>(resolve => frame.addEventListener('load', () => resolve(), { once: true }))
    const win = frame.contentWindow as ViewerWindow
    const doc = frame.contentDocument!
    win.onDrawioViewerLoad = () => {}
    await new Promise<void>((resolve, reject) => {
      const script = doc.createElement('script')
      script.src = new URL(viewerUrl, document.baseURI).href
      script.onload = () => resolve(); script.onerror = () => reject(new Error('draw.io viewer unavailable'))
      doc.head.append(script)
    })
    const family = getComputedStyle(document.documentElement).getPropertyValue('--app-font').trim()
    doc.documentElement.style.fontFamily = family
    doc.body.style.fontFamily = family
    win.mxConstants.DEFAULT_FONTFAMILY = family
    const source = new win.DOMParser().parseFromString(xml, 'application/xml')
    if (source.querySelector('parsererror')) throw new Error('Invalid draw.io XML')
    image.hidden = true; frame.hidden = false; viewport.classList.add('drawio-ready')
    viewer = new win.GraphViewer(doc.getElementById('graph')!, source.documentElement, {
      nav: true, lightbox: false, toolbar: '', resize: false, responsive: false,
      'check-visible-state': false,
      'auto-fit': false, 'auto-crop': false, 'allow-zoom-in': true, border: 16,
    })
    win.keelViewer = viewer
    // Pan the graph transform directly, including when the fitted canvas has no scroll range.
    const graph = viewer.graph
    graph.setPanning(false)
    const canvas = graph.container as HTMLElement
    let drag: { id: number; x: number; y: number; tx: number; ty: number } | undefined
    canvas.addEventListener('pointerdown', (event: PointerEvent) => {
      if (event.button !== 0) return
      event.preventDefault(); event.stopImmediatePropagation()
      canvas.focus({ preventScroll: true })
      canvas.setPointerCapture(event.pointerId)
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, tx: graph.view.translate.x, ty: graph.view.translate.y }
      canvas.style.cursor = 'grabbing'
    }, true)
    canvas.addEventListener('pointermove', (event: PointerEvent) => {
      if (!drag || drag.id !== event.pointerId) return
      event.preventDefault(); event.stopImmediatePropagation()
      graph.view.setTranslate(drag.tx + (event.clientX - drag.x) / graph.view.scale, drag.ty + (event.clientY - drag.y) / graph.view.scale)
    }, true)
    const release = () => { drag = undefined; canvas.style.cursor = 'grab' }
    canvas.addEventListener('pointerup', release)
    canvas.addEventListener('pointercancel', release)
    canvas.addEventListener('lostpointercapture', release)
    canvas.addEventListener('wheel', (event: WheelEvent) => {
      event.preventDefault(); event.stopImmediatePropagation()
      const bounds = canvas.getBoundingClientRect()
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? canvas.clientHeight : 1)
      const zoom = Math.max(.2, Math.min(4, requested.zoom * Math.exp(-delta * .002)))
      zoomAt(zoom, event.clientX - bounds.left, event.clientY - bounds.top)
      requested = { ...requested, zoom, fit: false }
      document.dispatchEvent(new CustomEvent('ui:diagram-zoom', { detail: { zoom } }))
    }, { passive: false, capture: true })
    sync()
  }
  function activate() {
    if (document.body.dataset.view !== 'diagrams') return
    if (!loading) loading = load().catch(() => {
      viewer = undefined; currentPage = -1
      frame.hidden = true; image.hidden = false; viewport.classList.remove('drawio-ready')
      document.getElementById('diagram-error')!.hidden = false
      loading = undefined
    })
    else if (viewer) sync()
  }
  document.addEventListener('ui:diagram', ((event: CustomEvent<typeof requested>) => {
    requested = event.detail; activate()
  }) as EventListener)
  new MutationObserver(activate).observe(document.body, { attributes: true, attributeFilter: ['data-view'] })
  let resize = 0
  new ResizeObserver(() => {
    cancelAnimationFrame(resize); resize = requestAnimationFrame(fit)
  }).observe(viewport)
  activate()
}
