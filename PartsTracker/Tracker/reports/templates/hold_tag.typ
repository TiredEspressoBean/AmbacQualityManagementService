// Hold / quarantine tag — the removable tag that goes ON nonconforming material.
//
// Context: Tracker/reports/adapters/hold_tag.py → HoldTagContext
//
// ISO 9001 §8.7.1: identify nonconforming output so it isn't used by mistake. The
// permanent part / lot labels carry no status; this tag does, and comes off when the
// item is released.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#let tone = if data.heading == "REJECTED" { bad } else if data.heading == "QUARANTINE" { bad } else { warn }
#let tint = if data.heading == "HOLD" { warn-tint } else { bad-tint }

#show: doc-frame.with(
  doc-type: "Hold Tag",
  title: data.identifier,
  doc-id: data.identifier,
  kind: "shop",
  // A tag marks the item's state now; it is reissued, not revised.
  uncontrolled: false,
  subtitle: [#data.kind · #data.item_name],
  org: data.tenant_name,
)

// The heading a person reads from across the floor.
#block(
  width: 100%, fill: tint, stroke: 2pt + tone, radius: 4pt,
  inset: (x: 14pt, y: 16pt),
)[
  #align(center)[
    #text(size: 44pt, weight: "bold", fill: tone, font: sans-font, tracking: 2pt)[#data.heading]
    #v(2pt)
    #text(size: 14pt, weight: "semibold", fill: tone, font: sans-font)[
      DO NOT USE UNTIL RELEASED
    ]
  ]
]

#v(10pt)

= Item

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Item", [#text(weight: "semibold")[#data.item_name] #if data.part_number != none [ · #data.part_number ]]),
  field(data.identifier_label, text(weight: "semibold", font: mono-font)[#data.identifier]),
  field("Quantity", text(weight: "semibold")[#data.quantity]),
  field("Location", opt(data.at("location", default: none))),
  ..if data.at("work_order", default: none) != none {
    (field("Work order", data.work_order), field("Step", opt(data.at("step", default: none))))
  } else { () },
)

#divider()

= Why it is held

#if data.reasons.len() > 0 [
  #for r in data.reasons [- #r]
]
#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("NCR / VDMR", text(font: mono-font)[#opt(data.at("record_number", default: none))]),
  field("Quality reports", if data.report_numbers.len() == 0 { text(fill: muted)[—] }
                           else { text(font: mono-font)[#data.report_numbers.join(", ")] }),
)
#if data.record_note != "" [
  #v(4pt)
  #data.record_note
]

#divider()

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Placed by", opt(data.at("placed_by", default: none))),
  field("Placed", opt(data.at("placed_at", default: none))),
)

#v(16pt)

#signature-block((
  (role: "Released by", caption: "Name · Date · Disposition / reason released"),
), heading: "Release")
