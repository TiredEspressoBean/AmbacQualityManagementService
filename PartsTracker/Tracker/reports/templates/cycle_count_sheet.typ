// Count sheet — walk one location and write down what's there.
//
// Context: Tracker/reports/adapters/cycle_count.py → CycleCountContext
//
// A blind count leaves "Expected" blank, so the counter counts rather than confirms.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let qty(v) = if v == none { "" } else { str(v) }

#show: doc-frame.with(
  doc-type: "Count Sheet",
  title: data.count_number,
  doc-id: data.count_number,
  kind: "shop",
  uncontrolled: false,
  org: data.our_org,
)

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
    // Blind: the expected quantity is withheld, so the unit moves to the count it
    // qualifies rather than sitting alone under "Expected".
    if l.expected == none [] else [#qty(l.expected) #l.unit],
    align(right, text(fill: muted)[#l.unit]),
    [],
  )),
  aligns: (left, left, right, right, left),
  inset-y: 10pt,   // tall enough to write a count by hand
)

#v(10pt)
#text(size: 9pt, fill: muted)[Anything here that isn't on this sheet: write its lot or serial below.]
#v(4pt)
#report-table(
  (1fr, 2fr, 0.8fr, 1fr),
  ("Lot / serial", "Item", "Counted", "Note"),
  range(4).map(_ => ([], [], [], [])),
  inset-y: 10pt,
)
#v(16pt)

#signature-block(((role: "Counted by", caption: "Name · Date"), none, none), heading: none)
