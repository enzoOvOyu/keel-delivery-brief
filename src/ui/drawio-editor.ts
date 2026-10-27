const EDITOR_ORIGIN = 'https://embed.diagrams.net'
const MAX_XML_SIZE = 10 * 1024 * 1024

function validXml(xml: unknown): xml is string {
  if (typeof xml !== 'string' || xml.length > MAX_XML_SIZE || /<!DOCTYPE/i.test(xml)) return false
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  return !doc.querySelector('parsererror') && ['mxfile', 'mxGraphModel'].includes(doc.documentElement.nodeName)
}

export function enableDrawioEditor(viewport: HTMLElement, onClose: () => void) {
  const edit = document.getElementById('diagram-edit') as HTMLButtonElement
  const toolbar = document.createElement('div')
  toolbar.className = 'diagram-editor-tools'
  toolbar.hidden = true
  const status = document.createElement('span')
  status.setAttribute('role', 'status')
  const button = (label: string, action: () => void) => {
    const node = document.createElement('button')
    node.type = 'button'; node.className = 'button small'; node.textContent = label
    node.addEventListener('click', action)
    toolbar.append(node)
    return node
  }
  toolbar.append(status)
  const editor = document.createElement('iframe')
  editor.id = 'drawio-editor'; editor.title = 'draw.io 流程图编辑器'
  editor.referrerPolicy = 'no-referrer'
  editor.hidden = true
  viewport.before(toolbar)
  viewport.append(editor)
  let active = false
  let ready = false
  let opening = false
  let xml = ''
  let key = ''
  let publishedSource = ''
  let timer: ReturnType<typeof setTimeout> | undefined
  let sourceRequest: AbortController | undefined
  let session = 0
  const send = (message: object) => editor.contentWindow?.postMessage(JSON.stringify(message), EDITOR_ORIGIN)
  const close = () => {
    session++; sourceRequest?.abort(); clearTimeout(timer)
    active = false; ready = false
    toolbar.hidden = true; editor.hidden = true; editor.removeAttribute('src')
    viewport.classList.remove('editing')
    document.getElementById('diagram-tabs')!.hidden = false
    document.getElementById('diagram-explanation')!.hidden = false
    edit.disabled = false
    for (const id of ['zoom-in', 'zoom-out', 'zoom-fit']) (document.getElementById(id) as HTMLButtonElement).disabled = false
    if (document.fullscreenElement === viewport) void document.exitFullscreen()
    onClose()
    edit.focus()
  }
  const persist = (next: string) => {
    xml = next
    try {
      localStorage.setItem(key, JSON.stringify({ source: publishedSource, xml }))
      status.textContent = '草稿已保存在此浏览器；未同步页面数据。点击编辑器“保存”下载图纸。'
    } catch {
      status.textContent = '浏览器无法保存草稿，请点击编辑器“保存”下载图纸。'
    }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([xml], { type: 'application/xml' }))
    const link = document.createElement('a')
    link.href = url; link.download = 'keel-delivery-edited.drawio'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const retry = button('重新加载编辑器', () => {
    clearTimeout(timer); ready = false
    status.textContent = '正在加载官方编辑器，需要连接 embed.diagrams.net…'
    const params = new URLSearchParams({ embed: '1', proto: 'json', spin: '1', libraries: '1', lang: 'zh', ui: 'kennedy', configure: '1', saveAndExit: '1' })
    editor.removeAttribute('src')
    const page = Number(document.querySelector('[data-diagram][aria-pressed=true]')?.getAttribute('data-diagram') || 0)
    const pageId = new DOMParser().parseFromString(xml, 'application/xml').querySelectorAll('diagram')[page]?.id
    if (pageId) params.set('page-id', pageId)
    editor.src = `${EDITOR_ORIGIN}/?${params}`
    timer = setTimeout(() => {
      if (!ready && active) status.textContent = '官方编辑器暂未连接，请检查网络后重试，或返回查看并下载原图。'
    }, 20000)
  })
  button('全屏编辑', () => {
    if (document.fullscreenElement === viewport) void document.exitFullscreen()
    else void viewport.requestFullscreen().catch(() => { status.textContent = '浏览器不支持全屏，可继续在当前页面编辑。' })
  })
  button('返回查看', close)

  window.addEventListener('message', event => {
    if (!active || event.origin !== EDITOR_ORIGIN || event.source !== editor.contentWindow) return
    let message: { event?: string; xml?: unknown; exit?: boolean }
    try { message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data } catch { return }
    if (!message || typeof message !== 'object') return
    if (message.event === 'configure') send({ action: 'configure', config: { defaultFonts: ['PingFang SC', 'Microsoft YaHei', 'Noto Sans SC'], zoomWheel: true } })
    else if (message.event === 'init') {
      ready = true; clearTimeout(timer)
      send({ action: 'load', xml, autosave: 1, title: 'keel-delivery.drawio', saveAndExit: 1 })
      status.textContent = '可编辑节点、文字与连线；滚轮缩放，右键拖动画布。保存将下载图纸，不改写流程数据。'
    } else if (message.event === 'autosave' || message.event === 'save') {
      if (!validXml(message.xml)) { status.textContent = '编辑器返回的图纸格式无效，未保存。'; return }
      persist(message.xml)
      if (message.event === 'save') {
        download()
        send({ action: 'status', message: '已下载 .drawio，草稿保留在当前浏览器', modified: false })
        if (message.exit) close()
      }
    } else if (message.event === 'exit') close()
  })

  edit.addEventListener('click', async () => {
    if (opening || active) return
    opening = true; edit.disabled = true; retry.disabled = false
    const currentSession = ++session
    try {
      sourceRequest = new AbortController()
      const response = await fetch('downloads/keel-delivery.drawio', { signal: sourceRequest.signal })
      if (!response.ok) throw new Error('source unavailable')
      xml = await response.text()
      if (!validXml(xml)) throw new Error('invalid source')
      // Verify the full source as well as the key, including on HTTP LAN deployments.
      publishedSource = xml
      let hash = 2166136261
      for (let i = 0; i < xml.length; i++) hash = Math.imul(hash ^ xml.charCodeAt(i), 16777619)
      key = `keel:drawio:draft:${xml.length}:${hash >>> 0}`
      try {
        const draft = JSON.parse(localStorage.getItem(key) || 'null')
        if (draft?.source === publishedSource && validXml(draft.xml)) xml = draft.xml
      } catch { /* Download still works with storage disabled. */ }
      if (currentSession !== session || document.body.dataset.view !== 'diagrams') return
      active = true; toolbar.hidden = false; editor.hidden = false
      viewport.classList.add('editing')
      document.getElementById('diagram-tabs')!.hidden = true
      document.getElementById('diagram-explanation')!.hidden = true
      for (const id of ['zoom-in', 'zoom-out', 'zoom-fit']) (document.getElementById(id) as HTMLButtonElement).disabled = true
      retry.click()
    } catch {
      if (currentSession !== session) return
      toolbar.hidden = false; status.textContent = '原始图纸加载失败，请返回查看后重试。'
      retry.disabled = true
    } finally { opening = false; if (!active) edit.disabled = false }
  })
  new MutationObserver(() => { if (active && document.body.dataset.view !== 'diagrams') close() })
    .observe(document.body, { attributes: true, attributeFilter: ['data-view'] })
}
