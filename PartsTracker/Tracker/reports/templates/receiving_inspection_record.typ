// Receiving Inspection Record — evidence a received lot was verified before release.
//
// Context: Tracker/reports/adapters/receiving_inspection_record.py
//            → ReceivingInspectionRecordContext
//
// ISO 9001 §8.6: evidence of conformity with the acceptance criteria, and
// traceability to whoever authorized the release. Layout:
//   1. Title block — lot number, verdict badge
//   2. The lot as received (item, supplier, heat, quantity, CoC on file)
//   3. Plan and sampling (RIP, strategy, n / Ac / Re or k)
//   4. Results — measurements, then checklist answers
//   5. Decision — accepted / rejected / holds released, by whom and when

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#let verdict-badge(v) = {
  if v == "PASS" { tone-badge("PASS", "ok") }
  else if v == "FAIL" { tone-badge("FAIL", "bad") }
  else if v == "PENDING" { tone-badge("PENDING", "warn") }
  else { tone-badge("NO INSPECTION", "muted") }
}

// `opt` for numbers: a count is shown as text, a missing one as a muted dash.
#let optn(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#let dt(v) = if v == none or v == "" { text(fill: muted)[—] } else { str(v).slice(0, calc.min(16, str(v).len())).replace("T", " ") }

#show: page-setup.with(
  title: "Receiving Inspection Record",
  doc-id: data.lot_number,
  classification: "Internal — Quality Record",
)

#report-title(
  [RECEIVING INSPECTION RECORD],
  data.lot_number,
  data.tenant_name,
  generated: data.generated_date,
  trailing: verdict-badge(data.verdict),
)

#v(10pt)

= Lot as received

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Item", [#text(weight: "semibold")[#data.item_name] #if data.part_number != none [ · #data.part_number ]]),
  field("Status", data.status),
  field("Supplier", opt(data.supplier_name)),
  field("Supplier lot", opt(data.supplier_lot_number)),
  field("Heat number", opt(data.heat_number)),
  field("Bought from", opt(data.source_type)),
  field("Quantity", [#data.quantity #if data.received_as != none [ (counted as #data.received_as)]]),
  field("ERP PO / line", opt(data.erp_po)),
  field("Received", [#opt(data.received_date) #if data.received_by != none [ · #data.received_by ]]),
  field("CoC on file", if data.coc_on_file { "Yes" } else { text(fill: muted)[No] }),
)

#divider()

= Plan and sampling

#if data.report_number == none [
  #text(fill: muted, style: "italic")[
    No receiving inspection was performed — this item has no receiving inspection plan,
    so the lot went to stock on receipt (dock-to-stock).
  ]
] else [
  #grid(
    columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
    field("Receiving plan", opt(data.plan_name)),
    field("Inspection report", data.report_number),
    field("Sampling", opt(data.strategy)),
    field("Sample size (n)", optn(data.sample_size)),
    if data.k != none { field("Acceptability constant (k)", str(data.k)) }
      else { field("Accept / reject", [Ac #optn(data.accept_number) · Re #optn(data.reject_number)]) },
    field("Defectives found", optn(data.defectives_found)),
    field("Inspected by", opt(data.inspected_by)),
    field("Verdict", verdict-badge(data.verdict)),
  )
]

#if data.measurements.len() > 0 [
  #divider()
  = Measurements
  #report-table(
    (auto, 1fr, auto, auto, auto, auto),
    ("#", "Characteristic", "Balloon", "Spec", "Value", "Result"),
    data.measurements.map(m => (
      if m.sample == none { "—" } else { str(m.sample) },
      m.characteristic,
      opt(m.balloon),
      opt(m.spec),
      m.value,
      if m.result == "OK" { tone-badge("OK", "ok") } else { tone-badge("OUT", "bad") },
    )),
    aligns: (right, left, left, left, right, center),
  )
]

#if data.checklist.len() > 0 [
  #divider()
  = Checks
  #report-table(
    (1fr, 1fr, auto),
    ("Check", "Answer", "By"),
    data.checklist.map(c => (c.question, c.answer, opt(c.by))),
  )
]

#divider()

= Release

#if data.events.len() == 0 [
  #text(fill: muted, style: "italic")[No release decision recorded yet.]
] else [
  #report-table(
    (auto, 1fr, auto, auto),
    ("Decision", "Reason", "By", "When"),
    data.events.map(e => (
      text(weight: "semibold")[#e.what],
      opt(e.note),
      opt(e.by),
      dt(e.at),
    )),
  )
]

#v(14pt)
#align(center)[
  #line(length: 60%, stroke: 0.5pt + rule)
  #v(4pt)
  #text(size: 8pt, fill: muted)[
    Generated from live records on #data.generated_date — the lot, its inspection report and
    its audit log are the record of source.
  ]
]
