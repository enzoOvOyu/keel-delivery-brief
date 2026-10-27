import "./styles.css"
import "./ui/layout.css"
import "./ui/wiring.css"
import "./ui/density.css"
import "./ui/decisions.css"
import { mountDecisions } from "./ui/decisions"
import { compactPageContext } from "./ui/density"
import { enableDrawio } from "./ui/drawio"
import { mountPresentation } from "./ui/presentation"

const layerTabs = document.getElementById("layer-tabs")!
const layerDetail = document.getElementById("layer-detail")!
const inspection = document.createElement("div")
inspection.className = "inspection-layout network-inspection"
layerTabs.before(inspection)
inspection.append(layerTabs, layerDetail)
layerDetail.setAttribute("role", "tabpanel")
layerDetail.setAttribute("aria-label", "网络测试详解")
document.querySelector(".diagram-viewport")!.id = "diagram-panel"

// Move existing explanatory material into an expandable reading aid.
const note = document.querySelector("#view-contracts > .reading-note")!
const bridge = document.querySelector(".bridge-note")!
const details = document.createElement("details")
details.className = "reading-context"
const summary = document.createElement("summary")
summary.append(note.querySelector("strong")!)
note.before(details)
details.append(summary, note, bridge)

compactPageContext()
mountPresentation()
mountDecisions()

enableDrawio()
