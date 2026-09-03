// Sourcing & Production Requirements template.
// Context: Tracker/reports/adapters/requirements.py → RequirementsContext

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: page-setup.with(
  title: "Sourcing & Production Requirements",
  classification: "Internal — Purchasing / Production",
)

// A date cell that turns red when it's on/before today (past due to act).
#let date-cell(d) = {
  if d == none { text(fill: muted)[—] }
  else if d <= data.generated_date { text(fill: bad, weight: "semibold")[#d] }
  else { text[#d] }
}
#let plain-date(d) = if d == none { text(fill: muted)[—] } else [#d]

#let section-header(title, count) = {
  v(8pt)
  block(
    fill: rgb("#1e40af"), inset: (x: 8pt, y: 5pt),
    radius: (top-left: 4pt, top-right: 4pt), width: 100%,
  )[
    #grid(columns: (1fr, auto),
      text(weight: "semibold", fill: white, font: sans-font, size: 10pt)[#title],
      text(fill: rgb("#bfdbfe"), font: sans-font, size: 9pt)[#count item#if count != 1 [s]])
  ]
}

#let hcell(body, a: left) = align(a)[#text(weight: "semibold", font: sans-font, size: 9pt)[#body]]
#let hrow(cols, cells) = block(
  fill: rgb("#f1f5f9"), stroke: (bottom: 0.5pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
  inset: (x: 6pt, y: 5pt), width: 100%,
)[#grid(columns: cols, column-gutter: 6pt, ..cells)]
#let drow(idx, cols, cells) = block(
  fill: if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") },
  stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
  inset: (x: 6pt, y: 5pt), width: 100%,
)[#set text(size: 9pt); #grid(columns: cols, column-gutter: 6pt, ..cells)]

#report-title(
  [SOURCING & PRODUCTION REQUIREMENTS],
  [What To Buy, Build & Procure],
  data.tenant_name,
  trailing-gap: 4pt,
  trailing: [
    #text(size: 9pt, fill: muted, font: sans-font)[Generated: #data.generated_date · red = order by now]
  ],
)

#v(10pt)

// ── SOURCE (buy) ──────────────────────────────────────────────────────────────
#let src-cols = (2.4fr, 0.7fr, 0.8fr, 1fr, 1fr, 1.1fr)
#section-header("Source — purchased materials to buy", data.source.len())
#hrow(src-cols, (hcell[Material], hcell(a: right)[Short], hcell[Lead], hcell[Need by], hcell[Order by], hcell[Incoming]))
#if data.source.len() == 0 [ #drow(0, (1fr,), (text(fill: muted, style: "italic")[Nothing to buy.],)) ] else [
  #for (idx, r) in data.source.enumerate() [
    #drow(idx, src-cols, (
      align(horizon)[#text(font: sans-font)[#r.material]],
      align(horizon + right)[#text(font: mono-font)[#r.qty_short]],
      align(horizon)[#if r.lead_time_days == none [#text(fill: muted)[—]] else [#r.lead_time_days d]],
      align(horizon)[#plain-date(r.need_by)],
      align(horizon)[#date-cell(r.order_by)],
      align(horizon)[#text(fill: muted)[#plain-date(r.incoming_date)]],
    ))
  ]
]

// ── PRODUCE (build) ────────────────────────────────────────────────────────────
#let prod-cols = (1.5fr, 1.8fr, 0.6fr, 1fr, 1.1fr)
#section-header("Produce — in-house components to build", data.produce.len())
#hrow(prod-cols, (hcell[Work order], hcell[Component], hcell(a: right)[Qty], hcell[Need by], hcell[Status]))
#if data.produce.len() == 0 [ #drow(0, (1fr,), (text(fill: muted, style: "italic")[Nothing to build.],)) ] else [
  #for (idx, r) in data.produce.enumerate() [
    #drow(idx, prod-cols, (
      align(horizon)[#text(font: mono-font)[#r.work_order]],
      align(horizon)[#text(font: sans-font)[#r.component]],
      align(horizon + right)[#text(font: mono-font)[#r.qty]],
      align(horizon)[#plain-date(r.need_by)],
      align(horizon)[#text(fill: muted, font: sans-font)[#r.status]],
    ))
  ]
]

// ── TOOLING ────────────────────────────────────────────────────────────────────
#let tool-cols = (2.4fr, 1fr, 0.8fr, 1.1fr)
#section-header("Tooling — resources not on hand", data.tooling.len())
#hrow(tool-cols, (hcell[Resource], hcell[Kind], hcell[Lead], hcell[Order by]))
#if data.tooling.len() == 0 [ #drow(0, (1fr,), (text(fill: muted, style: "italic")[Nothing outstanding.],)) ] else [
  #for (idx, r) in data.tooling.enumerate() [
    #drow(idx, tool-cols, (
      align(horizon)[#text(font: sans-font)[#r.fixture]],
      align(horizon)[#text(fill: muted)[#r.kind]],
      align(horizon)[#if r.lead_time_days == none [#text(fill: muted)[—]] else [#r.lead_time_days d]],
      align(horizon)[#date-cell(r.order_by)],
    ))
  ]
]

#footer-note(
  lead: "Note",
  [Order-by = need-by − purchase lead time, from the live schedule. Coverage is a flag (net of on-hand + promised), not a reservation — stock and POs live in the ERP.],
)
