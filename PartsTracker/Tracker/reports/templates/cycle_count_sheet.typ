// Count sheet — walk one location and write down what's there.
//
// Context: Tracker/reports/adapters/cycle_count.py → CycleCountContext
//
// A blind count leaves "Expected" blank, so the counter counts rather than confirms.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let qty(v) = if v == none { "" } else { str(v) }

#show: page-setup.with(
  title: "Count Sheet",
  doc-id: data.count_number,
  classification: "Cycle Count",
)

#report-title(
  [COUNT SHEET],
  data.count_number,
  data.our_org,
  generated: data.issued_date,
)

#v(10pt)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Location", text(weight: "semibold", size: 13pt)[#data.location]),
  field("Count", if data.blind [Blind — expected quantities hidden] else [Sighted]),
  field("Started by", opt(data.started_by)),
  field("Date", str(data.issued_date)),
)

#divider()

#report-table(
  (auto, 1fr, auto, auto, 1fr),
  ("Lot / serial", "Item", "Expected", "Counted", "Note"),
  data.lines.map(l => (
    text(font: mono-font)[#l.label],
    opt(l.item),
    [#qty(l.expected) #l.unit],
    [],
    [],
  )),
  aligns: (left, left, right, right, left),
)

#v(8pt)
#text(size: 9pt, fill: muted)[Anything here that isn't on this sheet: write its lot or serial below.]
#v(70pt)

#grid(
  columns: (1fr, 1fr), column-gutter: 20pt,
  [
    *Counted by* \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date]
  ],
  [],
)
