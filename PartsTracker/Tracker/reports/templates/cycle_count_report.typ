// Count differences — what a cycle count found that didn't match.
//
// Context: Tracker/reports/adapters/cycle_count.py → CycleCountContext
//
// For keying into the stock register. Quantities only; no values.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let qty(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: page-setup.with(
  title: "Count Differences",
  doc-id: data.count_number,
  classification: "Cycle Count",
)

#report-title(
  [COUNT DIFFERENCES],
  data.count_number,
  data.our_org,
  generated: data.issued_date,
)

#v(10pt)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Location", text(weight: "semibold")[#data.location]),
  field("Status", data.status),
  field("Counted by", opt(data.submitted_by)),
  field("Date", str(data.issued_date)),
)

#divider()

#if data.lines.len() == 0 [
  #info-box[Everything counted matched what was expected.]
] else [
  #report-table(
    (auto, 1fr, auto, auto, auto, auto),
    ("Lot / serial", "Item", "Expected", "Counted", "Difference", "What"),
    data.lines.map(l => (
      text(font: mono-font)[#l.label],
      [#opt(l.item) #if l.elsewhere != none [ \ #text(size: 8pt, fill: muted)[UQMES had it at #l.elsewhere]]],
      [#qty(l.expected) #l.unit],
      [#qty(l.counted) #l.unit],
      qty(l.difference),
      l.what,
    )),
    aligns: (left, left, right, right, right, left),
  )
]
