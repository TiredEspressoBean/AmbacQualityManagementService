// Pick List / Material Requisition template.
//
// Context: Tracker/reports/adapters/pick_list.py → PickListContext
//
// Layout:
//   1. Title block — report title, WO number, part, qty to produce, due date
//   2. Component table — Find # | Part Number | Description | Qty/Ea | Qty Required | UoM | Opt | Picked
//   3. Footer note — "Return this list to production after picking."

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared kv / badge / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Optional indicator badge (uses the shared badge)
#let optional-badge(is_optional) = {
  if is_optional {
    badge("OPT", warn, rgb("#fef3c7"))
  } else {
    text(size: 8pt, fill: muted, font: sans-font)[—]
  }
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Pick List / Material Requisition",
  classification: "Internal — Shop Floor",
)

// ── Title block ──────────────────────────────────────────────────────────────

#report-title(
  [PICK LIST / MATERIAL REQUISITION],
  data.part_name,
  data.tenant_name,
  generated: data.generated_date,
)

#v(14pt)

// ── Work order header ─────────────────────────────────────────────────────────

#info-box[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 6pt,

    kv("Work Order:", data.wo_number),
    kv("Part Number:", data.part_number),
    kv("Part Name:", data.part_name),
    kv("Qty to Produce:", str(data.qty_to_produce)),
    kv("Due Date:", if data.due_date != none { data.due_date } else { "—" }),
    [],
  )
]

#v(14pt)

// ── Component pick table ──────────────────────────────────────────────────────

= Components — #data.total_line_count lines

#if data.items.len() == 0 [
  #text(fill: muted, style: "italic")[
    No released BOM found for this part type. Contact engineering before picking materials.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  // Table header
  #table-header[
    #grid(
      columns: (0.5fr, 1.7fr, 2.0fr, 0.55fr, 0.75fr, 0.45fr, 1.9fr, 0.45fr, 0.85fr),
      column-gutter: 9pt,
      text(weight: "semibold", font: sans-font)[Find \#],
      text(weight: "semibold", font: sans-font)[Part Number],
      text(weight: "semibold", font: sans-font)[Description],
      align(right)[#text(weight: "semibold", font: sans-font)[Qty/Ea]],
      align(right)[#text(weight: "semibold", font: sans-font)[Qty Req'd]],
      text(weight: "semibold", font: sans-font)[UoM],
      text(weight: "semibold", font: sans-font)[Pull from],
      align(center)[#text(weight: "semibold", font: sans-font)[Opt]],
      align(center)[#text(weight: "semibold", font: sans-font)[Picked]],
    )
  ]

  // Table rows
  #for (idx, item) in data.items.enumerate() [
    #table-row(idx)[
      #grid(
        columns: (0.5fr, 1.7fr, 2.0fr, 0.55fr, 0.75fr, 0.45fr, 1.9fr, 0.45fr, 0.85fr),
        column-gutter: 9pt,
        align(horizon)[
          #text(fill: muted, font: mono-font)[#item.find_number]
        ],
        align(horizon)[
          #text(font: mono-font)[#item.component_part_number]
        ],
        align(horizon)[
          #text(font: sans-font)[#item.component_name]
        ],
        align(horizon + right)[
          #text(fill: muted)[#item.qty_per_assembly]
        ],
        align(horizon + right)[
          #text(weight: "semibold")[#item.qty_required]
        ],
        align(horizon)[
          #text(fill: muted)[#item.unit_of_measure]
        ],
        // Lot + location: pull THESE lots. Consumption records oldest-expiry first,
        // so picking a different lot desynchronises the traceability record from
        // what physically went into the unit. A shortage is called out here rather
        // than discovered at an empty bin.
        align(horizon)[
          #if item.qty_short != "" [
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
          #if item.consumed_at_step != "" [
            #linebreak()
            #text(size: 7pt, fill: muted, font: sans-font)[at #item.consumed_at_step]
          ]
        ],
        align(horizon + center)[
          #optional-badge(item.is_optional)
        ],
        align(horizon + center)[
          #box(width: 48pt, height: 14pt, stroke: 0.5pt + rule, radius: 2pt)[]
        ],
      )
    ]
  ]
]

#v(16pt)
#divider()

// ── Footer note ────────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* Return this list to production after picking.
  Qty Required = Qty/Ea × WO qty (#str(data.qty_to_produce) units).
  Verify lot/serial numbers against traveler before issuing materials.
  Work Order: #data.wo_number. Generated: #data.generated_date.
]
