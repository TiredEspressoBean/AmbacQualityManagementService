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
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared field / divider come from _common/components.typ
// ----------------------------------------------------------------------------

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

#info-box[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 6pt,
    field("Organization:", data.tenant_name),
    field("Submission Date:", str(data.submission_date)),
    field(
      "Part Number:",
      if data.part_number == none { none } else { data.part_number },
    ),
    field("Total Gages:", str(data.total_count)),
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
  #table-header[
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
    #table-row(idx)[
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

// ── Footer note ───────────────────────────────────────────────────────────────

#footer-note([
  This is a PPAP Element 16 submission artifact. It records the
  measurement equipment used to verify conformance at the time of PPAP
  submission, not live calibration status. For current calibration status
  see the Calibration Due Report.
])
