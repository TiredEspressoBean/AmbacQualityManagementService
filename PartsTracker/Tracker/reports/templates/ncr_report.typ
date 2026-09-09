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
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared badge / field come from _common/components.typ
// ----------------------------------------------------------------------------

#let state-badge(state) = {
  if state == "OPEN" { tone-badge("OPEN", "warn") }
  else if state == "IN_PROGRESS" { tone-badge("IN PROGRESS", "accent") }
  else if state == "CLOSED" { tone-badge("CLOSED", "ok") }
  else { tone-badge(state, "muted") }
}

#let severity-badge(sev) = {
  if sev == "CRITICAL" { tone-badge("CRITICAL", "bad") }
  else if sev == "MAJOR" { tone-badge("MAJOR", "warn") }
  else if sev == "MINOR" { tone-badge("MINOR", "muted") }
  else { tone-badge(sev, "muted") }
}

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
#report-title(
  [NON-CONFORMANCE REPORT],
  data.disposition_number,
  [Tenant: #data.tenant_name],
  title-size: 22pt,
  trailing-gap: 4pt,
  trailing: [
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
  ],
)

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
      tone-badge("FAIL", "bad")
    } else if qr.status == "PASS" {
      tone-badge("PASS", "ok")
    } else {
      tone-badge(qr.status, "muted")
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
      #report-table(
        (2fr, auto, 1fr, auto, 2fr),
        ([Defect], [Count], [Location], [Severity], [Notes]),
        qr.defects.map(d => (
          [#d.error_name],
          [#d.count],
          if d.location == "" [#text(fill: muted)[—]] else [#d.location],
          if d.severity == "CRITICAL" { text(fill: bad)[#d.severity] }
          else if d.severity == "MAJOR" { text(fill: warn)[#d.severity] }
          else if d.severity == "MINOR" { text(fill: muted)[#d.severity] }
          else [#d.severity],
          if d.notes == "" [#text(fill: muted)[—]] else [#d.notes],
        )),
        column-gutter: 12pt,
        inset-y: 4pt,
        aligns: (left, center, left, center, left),
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
