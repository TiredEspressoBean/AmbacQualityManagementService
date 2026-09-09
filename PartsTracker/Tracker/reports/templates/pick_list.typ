// Material Requisition template — the per-work-order document that authorises
// issue against a job and records who handed the material over.
//
// NOT the shelf walk: that is `pick_sheet` (one row per material across jobs,
// ordered by location), and the per-bench kit is `staging_list`. This one is
// per work order, which is why it carries the signature block.
//
// Context: Tracker/reports/adapters/pick_list.py → PickListContext
//
// Layout:
//   1. Title block — report title, part, tenant, generated date
//   2. Work-order header — WO / part / qty / due, plus a Code 128 of the WO so the
//      sheet scans back to the job (same encoding as the traveler)
//   3. Shortage banner — how many lines are short, before the walk rather than
//      discovered at line 31
//   4. Component table — Find # | Part Number | Description | Qty/Ea | Qty Req'd |
//      Pull from | Lot pulled | Opt | ✓
//      "Pull from" names the lots FEFO consumption will draw; "Lot pulled" is the
//      write-in for what was actually taken, which is what traceability records.
//   5. Issue record — Picked by / Checked by / Issued to, the conventional
//      two-step verification that makes this a record of material issue
//   6. Footer note

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — kv / optional-badge / report-table / footer-note all come from
// _common/components.typ; this template adds none of its own.
// ----------------------------------------------------------------------------

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Material Requisition",
  classification: "Internal — Shop Floor",
)

// ── Title block ──────────────────────────────────────────────────────────────

#report-title(
  [PICK LIST / MATERIAL REQUISITION],
  data.part_name,
  data.tenant_name,
  generated: data.generated_date,
  title-size: 17pt,
)

#v(9pt)

// ── Work order header ─────────────────────────────────────────────────────────

#info-box[
  // Barcode sits with the work-order facts so the sheet scans back to the job —
  // the same Code 128 the traveler carries, so both papers scan alike.
  #grid(
    columns: (1fr, auto),
    column-gutter: 16pt,
    align: (top, top + right),
    grid(
      columns: (1fr, 1fr),
      column-gutter: 16pt,
      row-gutter: 6pt,

      kv("Work Order:", data.wo_number, label-width: 74pt),
      kv("Part Number:", data.part_number, label-width: 74pt),
      kv("Part Name:", data.part_name, label-width: 74pt),
      kv("Qty to Produce:", str(data.qty_to_produce), label-width: 74pt),
      kv("Due Date:", if data.due_date != none { data.due_date } else { "—" },
         label-width: 74pt),
      [],
    ),
    if data.barcode_svg != "" [
      #svg-img(data.barcode_svg, 1.25in)
      #v(-3pt)
      #align(center)[#text(size: 7.5pt, font: mono-font, fill: muted)[#data.wo_number]]
    ],
  )
]

#v(9pt)

// ── Component pick table ──────────────────────────────────────────────────────

= Components — #data.total_line_count lines

// Shortages are called out per row, but a picker shouldn't have to read forty of
// them to learn three bins are light. Say it before the walk.
#if data.short_line_count > 0 [
  #v(-2pt)
  #block(fill: warn-tint, stroke: 0.5pt + warn, inset: 5pt, radius: 3pt, width: 100%)[
    #text(size: 9pt)[
      *#data.short_line_count of #data.total_line_count lines are short.*
      Marked SHORT below with whatever stock does exist — check those before you walk.
    ]
  ]
  #v(6pt)
]

#if data.items.len() == 0 [
  #text(fill: muted, style: "italic")[
    No released BOM found for this part type. Contact engineering before picking materials.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  #report-table(
    (0.5fr, 1.65fr, 1.9fr, 0.5fr, 0.85fr, 1.8fr, 1.15fr, 0.45fr, 0.5fr),
    ([Find \#], [Part Number], [Description], [Qty/Ea], [Qty Req'd],
     [Pull from], [Lot pulled], [Opt], [✓]),
    data.items.map(item => (
      text(fill: muted, font: mono-font)[#item.find_number],
      text(font: mono-font)[#item.component_part_number],
      text(font: sans-font)[#item.component_name],
      text(fill: muted)[#item.qty_per_assembly],
      // UoM rides with the number — "50 EA" reads as one fact and frees a column
      // for the lot the picker actually took.
      [#text(weight: "semibold")[#item.qty_required]#text(size: 8pt, fill: muted)[ #item.unit_of_measure]],
      // Lot + location: pull THESE lots. Consumption records oldest-expiry first,
      // so picking a different lot desynchronises the traceability record from
      // what physically went into the unit. A shortage is called out here rather
      // than discovered at an empty bin.
      {
        if item.not_picked_reason != "" [
          // Never in the crib — built here, or bought but not kitted through staging.
          // Without saying so this cell reads identically to an out-of-stock part.
          #text(size: 8pt, fill: muted, style: "italic")[#item.not_picked_reason]
        ] else if item.qty_short != "" [
          #text(size: 8pt, fill: warn, weight: "semibold")[SHORT #item.qty_short]
          #if item.lots != "" [
            #linebreak()
            #text(size: 7.5pt, fill: muted, font: mono-font)[#item.lots]
          ]
        ] else if item.lots != "" [
          #text(size: 8pt, font: mono-font)[#item.lots]
          #if item.storage_location != "" [
            #linebreak()
            #text(size: 7.5pt, fill: muted, font: sans-font)[#item.storage_location]
          ]
        ] else [
          #text(size: 8pt, fill: muted)[—]
        ]
        if item.consumed_at_step != "" [
          #linebreak()
          #text(size: 7pt, fill: muted, font: sans-font)[at #item.consumed_at_step]
        ]
      },
      // What was ACTUALLY taken. AS9100 asks which lots went into the unit, not
      // which ones the plan reserved — and the named lot is regularly empty,
      // short, or already taken. Blank for MAKE lines: nothing to pull.
      if item.not_picked_reason != "" { [] } else {
        box(width: 100%, height: 13pt, stroke: (bottom: 0.5pt + rule))[]
      },
      optional-badge(item.is_optional),
      if item.not_picked_reason != "" { [] } else {
        box(width: 13pt, height: 13pt, stroke: 0.5pt + rule, radius: 2pt)[]
      },
    )),
    aligns: (left, left, left, right, right, left, left, center, center),
    inset-y: 4pt,
  )
]

#v(8pt)

// ── Issue record ──────────────────────────────────────────────────────────────
//
// Two signatures, not one: picking and checking are the conventional two-step
// verification, and an unsigned sheet isn't a record of material issue — which is
// the thing an audit asks this document to be.

// No divider here: the table's own bottom rule already closes it, and
// `footer-note` draws one below. Three rules in four inches is noise.
#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 18pt,
  ..("Picked by", "Checked by", "Issued to / Cell").map(role => [
      #text(size: 8.5pt, fill: muted, font: sans-font)[#role]
      #v(9pt)
      #box(width: 100%, stroke: (bottom: 0.5pt + rule))[]
      #v(2pt)
      #text(size: 8pt, fill: muted, font: sans-font)[Date: #box(width: 1fr, stroke: (bottom: 0.5pt + rule))]
    ])
)

#v(8pt)

// ── Footer note ────────────────────────────────────────────────────────────────
//
// Deliberately short. The work order and generated date used to be repeated here;
// both now appear twice already (header block and barcode), and a footer nobody
// finishes reading is a footer that hides the one line that matters.

#footer-note[
  Record the lot you actually pulled — that is the lot the traceability record will
  claim went into the unit. Return this sheet to production after picking.
]
