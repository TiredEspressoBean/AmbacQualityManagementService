// Checking Aids template — PPAP Element 16.
//
// Context: Tracker/reports/adapters/checking_aids.py → CheckingAidsContext
//
// Point-in-time snapshot of measurement equipment used to verify product
// conformance for a PPAP submission. Shows calibration TRACEABILITY
// (cert number + standards + cal date), not live status.
//
// Layout:
//   1. Title block — PPAP Element 16 label
//   2. Header — part number (optional) + submission date + tenant
//   3. Gage table: Gage ID | Description | Mfr / Model | Cal Interval | Cal Cert # | Cal Date
//   4. Quality Manager signature block

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

// Key-value row helper — muted label, value in ink
#let kv(label, value) = grid(
  columns: (auto, 1fr),
  column-gutter: 10pt,
  text(fill: muted, font: sans-font, size: 9pt)[*#label*],
  if value == none or value == "" {
    text(fill: muted, style: "italic")[—]
  } else {
    value
  },
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
  title: "Checking Aids",
  classification: "PPAP — Element 16",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    PPAP ELEMENT 16
  ]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[Checking Aids]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[Measurement Equipment List]
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
    kv("Organization:", data.tenant_name),
    kv("Submission Date:", str(data.submission_date)),
    kv(
      "Part Number:",
      if data.part_number == none { none } else { data.part_number },
    ),
    kv("Total Gages:", str(data.total_count)),
  )
]

#v(14pt)

// ── Gage table ────────────────────────────────────────────────────────────────

= Measurement Equipment

#if data.items.len() == 0 [
  #text(fill: muted, style: "italic")[
    No measurement equipment found for this tenant.
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
      columns: (1.5fr, 2.2fr, 1.6fr, 1.5fr, 1.1fr),
      column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Gage ID],
      text(weight: "semibold", font: sans-font)[Description],
      text(weight: "semibold", font: sans-font)[Mfr / Model],
      text(weight: "semibold", font: sans-font)[Cal Cert \#],
      text(weight: "semibold", font: sans-font)[Cal Date],
    )
  ]

  // Table rows
  #for (idx, item) in data.items.enumerate() [
    #let row-fill = if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") }
    #block(
      fill: row-fill,
      stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
      inset: (x: 6pt, y: 5pt),
      width: 100%,
    )[
      #grid(
        columns: (1.5fr, 2.2fr, 1.6fr, 1.5fr, 1.1fr),
        column-gutter: 6pt,
        align(horizon)[
          #text(fill: muted, font: mono-font, size: 8.5pt)[#item.gage_id]
        ],
        align(horizon)[
          #text(font: sans-font, weight: "semibold")[#item.name]
          #if item.equipment_type != none [
            #linebreak()
            #text(size: 8pt, fill: muted)[#item.equipment_type]
          ]
        ],
        align(horizon)[
          #if item.manufacturer != none [
            #text[#item.manufacturer]
          ]
          #if item.model != none [
            #linebreak()
            #text(size: 8pt, fill: muted, font: mono-font)[#item.model]
          ]
        ],
        align(horizon)[
          #if item.cal_cert_number != none {
            text(font: mono-font, size: 8.5pt)[#item.cal_cert_number]
          } else {
            text(fill: muted, style: "italic", size: 8.5pt)[not available]
          }
        ],
        align(horizon)[
          #if item.cal_date != none {
            text(font: mono-font, size: 8.5pt)[#str(item.cal_date)]
          } else {
            text(fill: muted, style: "italic", size: 8.5pt)[—]
          }
        ],
      )
    ]
  ]
]

#v(20pt)

// ── Signature block ──────────────────────────────────────────────────────────

= Attestation

#text(size: 9.5pt)[
  I certify that the measurement equipment listed above was used to verify
  product conformance for the PPAP submission referenced herein, and that
  each listed gage was in calibration at the time the measurements were taken.
  Calibration traceability is maintained through the certificate numbers
  listed; individual calibration certificates are available on request.
]

#v(24pt)

#grid(
  columns: (1fr,),
  [
    *Quality Manager* \
    #v(28pt)
    #line(length: 80%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
)

#v(16pt)
#divider()

// ── Footer note ───────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* This is a PPAP Element 16 submission artifact. It records the
  measurement equipment used to verify conformance at the time of PPAP
  submission, not live calibration status. For current calibration status
  see the Calibration Due Report.
]
