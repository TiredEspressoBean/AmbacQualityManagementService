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
  field(data.scope_label, text(weight: "semibold", size: 13pt)[#data.location]),
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
    // An item count spans locations, so each line says where to look.
    [#opt(l.item) #if l.where != none [ \ #text(size: 8pt, fill: muted)[At #l.where]]],
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
// A location count asks what else is here; an item count asks where else it turned up.
#let item-count = data.scope_label != "Location"
#text(size: 9pt, fill: muted)[#if item-count [Any of it found somewhere not on this sheet: write its lot or serial and where.] else [Anything here that isn't on this sheet: write its lot or serial below.]]
#v(4pt)
#report-table(
  (1fr, 2fr, 0.8fr, 1fr),
  ("Lot / serial", if item-count [Found at] else [Item], "Counted", "Note"),
  range(4).map(_ => ([], [], [], [])),
  inset-y: 10pt,
)
#v(16pt)

#signature-block(((role: "Counted by", caption: "Name · Date"), none, none), heading: none)
