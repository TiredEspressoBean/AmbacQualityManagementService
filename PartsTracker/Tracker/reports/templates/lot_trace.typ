// Lot trace — where one material lot came from and where it went.
//
// Context: Tracker/reports/adapters/lot_trace.py → LotTraceContext
//
// For an auditor or a recall. The forward trace is only as complete as consumption
// recording, and says so.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Lot Trace",
  title: data.lot_number,
  doc-id: data.lot_number,
  kind: "record",
  org: data.our_org,
)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Item", text(weight: "semibold")[#data.item_name]),
  field("Status", data.status),
  field("Quantity received", data.quantity),
  field("Received", if data.received_date == none { text(fill: muted)[—] } else { str(data.received_date) }),
)

#divider()

= Came from

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Supplier", opt(data.supplier)),
  field("Their lot", opt(data.supplier_lot_number)),
  field("Heat number", opt(data.heat_number)),
  field("Source", opt(data.source_type)),
  field("ERP PO / line", opt(data.erp_po)),
  field("Split from", opt(data.parent_lot_number)),
)
#if data.split_lots.len() > 0 [
  #v(4pt)
  #text(size: 9pt, fill: muted)[Split into: #data.split_lots.join(", ")]
]

#divider()

= Where it went

#if data.uses.len() == 0 [
  #info-box[Nothing has been drawn from this lot (or from lots split off it).]
] else [
  #report-table(
    // Every text column takes a share: with one `1fr` among five `auto`s, the autos
    // claimed the width and the part column collapsed to a word per line.
    (auto, auto, 1.2fr, 1.1fr, 0.9fr, 1.3fr),
    ("Lot", "Used", "Part · built into", "Work order · order", "Customer", "Shipped"),
    data.uses.map(u => (
      text(font: mono-font, size: 8.5pt)[#u.lot_number],
      [#u.used #if u.step != none [ \ #text(size: 8pt, fill: muted)[#u.step]]],
      [#opt(u.part) #if u.built_into != none [ \ #text(size: 8pt, fill: muted)[→ #u.built_into]]],
      [#opt(u.work_order) #if u.order != none [ \ #text(size: 8pt, fill: muted)[#u.order]]],
      opt(u.customer),
      opt(u.shipped),
    )),
    aligns: (left, right, left, left, left, left),
  )
]

#v(6pt)
#text(size: 9pt, fill: muted)[
  Customers reached: #if data.customers.len() == 0 [none yet] else [#data.customers.join(", ")].
  This trace shows what steps recorded drawing from the lot; material used without a
  recorded draw leaves no trail here.
]

#v(14pt)
#text(size: 9pt, fill: muted)[Issued by #opt(data.issued_by) · #str(data.issued_date)]
