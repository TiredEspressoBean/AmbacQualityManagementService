// Sourcing & Production Requirements template.
// Context: Tracker/reports/adapters/requirements.py → RequirementsContext

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Sourcing & Production Requirements",
  title: [What To Buy, Build & Procure],
  kind: "shop",
  subtitle: [As of #data.generated_date · red = order by now],
  org: data.tenant_name,
)

// A date cell that turns red when it's on/before today (past due to act).
#let date-cell(d) = {
  if d == none { text(fill: muted)[—] }
  else if d <= data.generated_date { text(fill: bad, weight: "semibold")[#d] }
  else { text[#d] }
}
#let plain-date(d) = if d == none { text(fill: muted)[—] } else [#d]

// One requirements section: its band, then its table — or one muted line when empty.
#let section(title, rows, cols, header, aligns, empty) = {
  group-band(title, count: [#rows.len() item#if rows.len() != 1 [s]])
  if rows.len() == 0 {
    block(stroke: (bottom: 0.75pt + rule), inset: (x: 6pt, y: 6pt), width: 100%, above: 0pt)[
      #text(size: 9pt, fill: muted, style: "italic")[#empty]]
  } else {
    report-table(cols, header, rows, aligns: aligns)
  }
}

#set text(size: 9pt)

// ── SOURCE (buy) ──────────────────────────────────────────────────────────────
#let src-cols = (2fr, 0.6fr, 1.1fr, 0.6fr, 1fr, 1fr, 1fr)
// "Recoverable" is what the core bank could yield — a forecast, shown BESIDE the short
// figure and never subtracted from it. Buying to the short column is always safe; the
// recoverable column is what a planner may choose to wait on.
#section("Source — purchased materials to buy",
  data.source.map(r => (
    r.material,
    [#text(font: mono-font)[#r.qty_short]
      #if r.forecast_short > 0 [#linebreak()#text(size: 7pt, fill: muted)[+#r.forecast_short forecast]]],
    if r.recoverable <= 0 { text(fill: muted)[—] } else [
      #text(font: mono-font)[#r.recoverable]
      #text(size: 7pt, fill: muted)[ (#r.recoverable_cores cores)]
    ],
    if r.lead_time_days == none { text(fill: muted)[—] } else [#r.lead_time_days d],
    plain-date(r.need_by),
    date-cell(r.order_by),
    text(fill: muted)[#plain-date(r.incoming_date)],
  )),
  src-cols,
  ("Material", "Short", "Recoverable", "Lead", "Need by", "Order by", "Incoming"),
  (left, right, right, left, left, left, left),
  [Nothing to buy.],
)

// ── RECOVER (tear down) ────────────────────────────────────────────────────────
// One row per CORE TYPE: one core yields several components, so a per-component list
// would ask for the same unit repeatedly. Covers replacement slots on exchange rebuilds
// — the only demand recovered stock may fill — after what is on the shelf and what
// teardowns already committed will yield. A PROPOSAL — nothing here commits a core.
#let rec-cols = (1.4fr, 0.8fr, 0.9fr, 2.6fr, 1fr)
#section("Recover — teardown proposed to refill recovered stock",
  data.recover.map(r => (
    [#r.core_type #linebreak()#text(size: 7pt, fill: muted)[#r.cores_available in bank]],
    text(font: mono-font)[#r.cores_to_tear_down],
    text(font: mono-font)[#r.cores_in_flight],
    [#for c in r.components [
      #c.component: #c.covered_by_teardown
      #if c.still_short > 0 [#text(size: 7pt, fill: muted)[ (#c.still_short still short)]]
      #linebreak()
    ]],
    if r.start_by == none { text(fill: muted)[—] } else { date-cell(r.start_by) },
  )),
  rec-cols,
  ("Core type", "Tear down", "Committed", "Covers", "Start by"),
  (left, right, right, left, left),
  [Nothing to recover.],
)

// ── PRODUCE (build) ────────────────────────────────────────────────────────────
#let prod-cols = (1.5fr, 1.8fr, 0.6fr, 1fr, 1.1fr)
#section("Produce — in-house components to build",
  data.produce.map(r => (
    text(font: mono-font)[#r.work_order],
    r.component,
    text(font: mono-font)[#r.qty],
    plain-date(r.need_by),
    text(fill: muted)[#humanize(r.status)],
  )),
  prod-cols,
  ("Work order", "Component", "Qty", "Need by", "Status"),
  (left, left, right, left, left),
  [Nothing to build.],
)

// ── TOOLING ────────────────────────────────────────────────────────────────────
#let tool-cols = (2.4fr, 1fr, 0.8fr, 1.1fr)
#section("Tooling — resources not on hand",
  data.tooling.map(r => (
    r.fixture,
    text(fill: muted)[#humanize(r.kind)],
    if r.lead_time_days == none { text(fill: muted)[—] } else [#r.lead_time_days d],
    date-cell(r.order_by),
  )),
  tool-cols,
  ("Resource", "Kind", "Lead", "Order by"),
  (left, left, left, left),
  [Nothing outstanding.],
)

#footer-note(
  lead: "Note",
  [Order-by = need-by − purchase lead time, from the live schedule. Coverage is a flag (net of on-hand + promised), not a reservation — stock and POs live in the ERP.],
)
