// BOM Report template.
//
// Context: Tracker/reports/adapters/bom_report.py → BOMReportContext
//
// Layout:
//   1. Title block — report title, BOM status badge, tenant name
//   2. Header info grid — parent part, revision, type, effective date
//   3. Component table — Find # | Part Number | Description | Qty | UoM | Optional | Notes
//   4. Footer note (shop reference document, not a quality record)

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Status badge — DRAFT=amber, RELEASED=green, OBSOLETE=red
#let status-badge(status) = {
  if status == "RELEASED"  { badge("RELEASED",  ok,   rgb("#dcfce7")) }
  else if status == "DRAFT" { badge("DRAFT",    warn,  rgb("#fef3c7")) }
  else if status == "OBSOLETE" { badge("OBSOLETE", bad, rgb("#fee2e2")) }
  else                     { badge(status,      muted, rgb("#e2e8f0")) }
}

// Optional indicator badge
#let optional-badge(is_optional) = {
  if is_optional {
    badge("OPT", warn, rgb("#fef3c7"))
  } else {
    text(size: 8pt, fill: muted, font: sans-font)[—]
  }
}

// Key-value row helper for the header info block
#let kv(key, value) = grid(
  columns: (90pt, 1fr),
  column-gutter: 6pt,
  text(size: 9pt, fill: muted, font: sans-font)[#key],
  text(size: 9pt)[#value],
)

// Section divider rule
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.4pt + rule)
  v(6pt)
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Bill of Materials",
  classification: "Internal — Shop Reference",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    BILL OF MATERIALS
  ]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[#data.parent_part_name]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(6pt)
  #status-badge(data.status)
]

#v(14pt)

// ── Header info ──────────────────────────────────────────────────────────────

#block(
  fill: rgb("#f8fafc"),
  stroke: 0.5pt + rule,
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 6pt,

    kv("Part Number:", data.parent_part_number),
    kv("Revision:", data.revision),
    kv("Part Name:", data.parent_part_name),
    kv("BOM Type:", data.bom_type),
    kv("Status:", data.status),
    kv("Effective Date:", if data.effective_date != none { data.effective_date } else { "—" }),
  )
]

#v(14pt)

// ── Component table ──────────────────────────────────────────────────────────

= Components — #data.total_line_count lines

#if data.lines.len() == 0 [
  #text(fill: muted, style: "italic")[
    No component lines defined for this bill of materials.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  // Table header
  #block(
    fill: rgb("#f1f5f9"),
    stroke: 0.5pt + rule,
    inset: (x: 6pt, y: 5pt),
    width: 100%,
    radius: (top-left: 3pt, top-right: 3pt),
  )[
    #grid(
      columns: (0.7fr, 1.5fr, 2.5fr, 0.6fr, 0.6fr, 0.65fr, 2fr),
      column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Find \#],
      text(weight: "semibold", font: sans-font)[Part Number],
      text(weight: "semibold", font: sans-font)[Description],
      align(right)[#text(weight: "semibold", font: sans-font)[Qty]],
      text(weight: "semibold", font: sans-font)[UoM],
      align(center)[#text(weight: "semibold", font: sans-font)[Opt?]],
      text(weight: "semibold", font: sans-font)[Notes],
    )
  ]

  // Table rows
  #for (idx, line) in data.lines.enumerate() [
    #let row-fill = if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") }
    #block(
      fill: row-fill,
      stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
      inset: (x: 6pt, y: 5pt),
      width: 100%,
    )[
      #grid(
        columns: (0.7fr, 1.5fr, 2.5fr, 0.6fr, 0.6fr, 0.65fr, 2fr),
        column-gutter: 6pt,
        align(horizon)[
          #text(fill: muted, font: mono-font)[#line.find_number]
        ],
        align(horizon)[
          #text(font: mono-font)[#line.component_part_number]
        ],
        align(horizon)[
          #text(font: sans-font)[#line.component_name]
        ],
        align(horizon + right)[
          #text(weight: "semibold")[#line.quantity]
        ],
        align(horizon)[
          #text(fill: muted)[#line.unit_of_measure]
        ],
        align(horizon + center)[
          #optional-badge(line.is_optional)
        ],
        align(horizon)[
          #text(fill: muted, size: 8.5pt)[#line.notes]
        ],
      )
    ]
  ]
]

#v(16pt)
#divider()

// ── Footer note ───────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* This is a shop reference document. It is not a controlled quality
  record. The released engineering BOM is maintained in the PLM/ERP system.
  Total lines: #data.total_line_count.
  Status: #data.status. Revision: #data.revision.
]
