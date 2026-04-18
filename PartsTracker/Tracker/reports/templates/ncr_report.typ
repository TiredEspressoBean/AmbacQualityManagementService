// Non-Conformance Report (NCR) template.
//
// Context: Tracker/reports/adapters/ncr.py → NcrContext
//
// Layout:
//   1. Title block with doc metadata
//   2. Status + severity badges, disposition type
//   3. Identification grid (part, work order, step)
//   4. Non-conformance description
//   5. Per-QualityReport defect tables
//   6. Containment block
//   7. Disposition / resolution block
//   8. Customer approval block (conditional)
//   9. Scrap verification block (conditional)
//  10. Closure signature block

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8.5pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

#let state-badge(state) = {
  if state == "OPEN" { badge("OPEN", warn, rgb("#fef3c7")) }
  else if state == "IN_PROGRESS" { badge("IN PROGRESS", accent, rgb("#dbeafe")) }
  else if state == "CLOSED" { badge("CLOSED", ok, rgb("#dcfce7")) }
  else { badge(state, muted, rgb("#e2e8f0")) }
}

#let severity-badge(sev) = {
  if sev == "CRITICAL" { badge("CRITICAL", bad, rgb("#fee2e2")) }
  else if sev == "MAJOR" { badge("MAJOR", warn, rgb("#fef3c7")) }
  else if sev == "MINOR" { badge("MINOR", muted, rgb("#e2e8f0")) }
  else { badge(sev, muted, rgb("#e2e8f0")) }
}

// Field/value row — label muted, value in ink. Accepts `none` for missing data.
#let field(label, value) = grid(
  columns: (auto, 1fr),
  column-gutter: 10pt,
  text(fill: muted, font: sans-font, size: 9pt)[*#label*],
  if value == none or value == "" [
    #text(fill: muted, style: "italic")[—]
  ] else [
    #value
  ],
)

// Format an ISO datetime string → "2026-04-13 14:22 UTC" (light touch).
#let fmt-dt(iso) = {
  if iso == none { return none }
  // Typst doesn't parse ISO dates natively; show the string with T replaced.
  let s = str(iso)
  s.replace("T", " ").slice(0, calc.min(s.len(), 16))
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Non-Conformance Report",
  doc-id: data.disposition_number,
  classification: "Controlled Document",
)

// Title block
#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    NON-CONFORMANCE REPORT
  ]
  #v(2pt)
  #text(size: 22pt, weight: "bold", font: sans-font)[#data.disposition_number]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[Tenant: #data.tenant_name]
  #v(4pt)
  #state-badge(data.current_state) #h(6pt)
  #severity-badge(data.severity)
  #if data.disposition_type != none {
    h(6pt)
    badge(
      data.disposition_type.replace("_", " "),
      ink,
      rgb("#f1f5f9"),
    )
  }
]

#v(10pt)

// Identification grid
#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  field("Part", data.part_erp_id),
  field("Part Type", data.part_type_name),

  field("Work Order", data.work_order_erp_id),
  field("Step", data.step_name),

  field("Rework Attempt", str(data.rework_attempt_at_step)),
  field("Opened", fmt-dt(data.created_at)),

  field("Assigned To", data.assigned_to),
  field("", none),
)

= Non-Conformance Description

#if data.description == "" [
  #text(fill: muted, style: "italic")[No description recorded.]
] else [
  #data.description
]

#if data.quality_reports.len() > 0 [
  #v(6pt)
  == Associated Quality Reports

  #for qr in data.quality_reports [
    #v(4pt)
    *#qr.report_number* #h(6pt)
    #if qr.status == "FAIL" {
      badge("FAIL", bad, rgb("#fee2e2"))
    } else if qr.status == "PASS" {
      badge("PASS", ok, rgb("#dcfce7"))
    } else {
      badge(qr.status, muted, rgb("#e2e8f0"))
    }
    #h(6pt)
    #if qr.detected_by != none [
      #text(size: 9pt, fill: muted)[detected by #qr.detected_by]
    ]
    #if qr.detected_at != none [
      #text(size: 9pt, fill: muted)[ · #fmt-dt(qr.detected_at)]
    ]

    #v(2pt)
    #if qr.description != "" [
      #text(size: 10pt)[#qr.description]
      #v(4pt)
    ]

    #if qr.defects.len() > 0 [
      #table(
        columns: (2fr, auto, 1fr, auto, 2fr),
        align: (left, center, left, center, left),
        stroke: (x, y) => (
          bottom: if y == 0 { 0.8pt + ink } else { 0.3pt + rule },
          top: if y == 0 { 0.8pt + ink } else { none },
        ),
        inset: (x: 6pt, y: 4pt),
        fill: (_, row) => if calc.rem(row, 2) == 0 and row > 0 { rgb("#f8fafc") },

        [*Defect*], [*Count*], [*Location*], [*Severity*], [*Notes*],
        ..qr.defects.map(d => (
          [#d.error_name],
          [#d.count],
          if d.location == "" [#text(fill: muted)[—]] else [#d.location],
          if d.severity == "CRITICAL" { text(fill: bad)[#d.severity] }
          else if d.severity == "MAJOR" { text(fill: warn)[#d.severity] }
          else if d.severity == "MINOR" { text(fill: muted)[#d.severity] }
          else [#d.severity],
          if d.notes == "" [#text(fill: muted)[—]] else [#d.notes],
        )).flatten()
      )
    ] else [
      #text(size: 9pt, fill: muted, style: "italic")[No defects recorded on this report.]
    ]
  ]
]

= Containment

#if data.containment_action == "" [
  #text(fill: muted, style: "italic")[No containment action recorded.]
] else [
  #data.containment_action

  #v(4pt)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 4pt,
    field("Completed By", data.containment_completed_by),
    field("Completed At", fmt-dt(data.containment_completed_at)),
  )
]

= Disposition & Resolution

#if data.resolution_notes == "" [
  #text(fill: muted, style: "italic")[No resolution notes recorded.]
] else [
  #data.resolution_notes
]

#if data.requires_customer_approval [
  == Customer Approval

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    field(
      "Approval Received",
      if data.customer_approval_received {
        text(fill: ok, weight: "semibold")[Yes]
      } else {
        text(fill: warn, weight: "semibold")[Pending]
      },
    ),
    field("Approval Reference", data.customer_approval_reference),
    field("Approval Date", fmt-dt(data.customer_approval_date)),
    field("", none),
  )
]

#if data.disposition_type == "SCRAP" [
  == Scrap Verification

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    field(
      "Verified",
      if data.scrap_verified {
        text(fill: ok, weight: "semibold")[Yes]
      } else {
        text(fill: warn, weight: "semibold")[No]
      },
    ),
    field("Method", data.scrap_verification_method),
    field("Verified By", data.scrap_verified_by),
    field("Verified At", fmt-dt(data.scrap_verified_at)),
  )
]

#pagebreak(weak: true)

= Closure

#if data.resolution_completed [
  This NCR has been formally closed.

  #v(6pt)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,
    field("Resolution Completed By", data.resolution_completed_by),
    field("Resolution Completed At", fmt-dt(data.resolution_completed_at)),
  )
] else [
  #text(fill: warn, style: "italic")[
    Resolution pending. This NCR is in #data.current_state status and has
    not been formally closed.
  ]
]

#v(28pt)

= Signatures

#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 20pt,

  [
    *Originator* \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date]
  ],
  [
    *Quality Manager* \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date]
  ],
  [
    *Customer* \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date]
  ],
)
