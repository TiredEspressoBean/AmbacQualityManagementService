// Non-Conformance Report (NCR) template.
//
// Context: Tracker/reports/adapters/ncr.py → NcrContext
//
// Layout:
//   1. Title block with doc metadata (NCR number, state, severity)
//   2. Where it was found (work order, step, load)
//   3. Non-conformance description
//   4. Per-inspection-record defect tables
//   5. Containment block
//   6. What it covers: one row per part / lot with its decision
//   7. Each decision: authority, notes, customer approval, scrap verification
//   8. Closure signature block

#import "_common/frame.typ": *

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

#let dash(v) = if v == none or v == "" [#text(fill: muted)[—]] else [#v]
#let decision-name(t) = if t == none [#text(fill: warn)[Awaiting decision]] else [#humanize(t)]

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: doc-frame.with(
  doc-type: "Non-Conformance Report",
  title: data.ncr_number,
  doc-id: data.ncr_number,
  kind: "record",
  org: data.tenant_name,
  status: [
    #state-badge(data.state) #h(6pt)
    #severity-badge(data.severity)
  ],
)

// Where it was found
#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  field("Work Order", data.work_order_erp_id),
  field("Found At", data.step_name),

  field("Part Type", data.part_type_name),
  field("Covers", str(data.decisions.len()) + if data.decisions.len() == 1 { " item" } else { " items" }),

  // A failed batch cycle's NCR names its load.
  ..if data.batch_load != none {
    (field("Batch Load", data.batch_load), field("", none))
  },

  field("Opened", fmt-dt(data.created_at)),
  field("Raised By", data.raised_by),
)

= Non-Conformance Description

#if data.description == "" [
  #text(fill: muted, style: "italic")[No description recorded.]
] else [
  #data.description
]

#if data.quality_reports.len() > 0 [
  #v(6pt)
  == Inspection Records

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
          dash(d.location),
          if d.severity == "CRITICAL" { text(fill: bad)[#d.severity] }
          else if d.severity == "MAJOR" { text(fill: warn)[#d.severity] }
          else if d.severity == "MINOR" { text(fill: muted)[#d.severity] }
          else [#d.severity],
          dash(d.notes),
        )),
        column-gutter: 12pt,
        inset-y: 4pt,
        aligns: (left, center, left, center, left),
      )
    ] else [
      #text(size: 9pt, fill: muted, style: "italic")[No defects recorded on this record.]
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

= Disposition

#if data.decisions.len() == 0 [
  #text(fill: muted, style: "italic")[Nothing has been put up for a decision yet.]
] else [
  #report-table(
    (2fr, 1fr, 1.4fr, 1.4fr, 1fr),
    ([Part / Lot], [Part Status], [Disposition], [Decision], [State]),
    data.decisions.map(d => (
      [*#d.subject*],
      dash(if d.part_status == none { none } else { humanize(d.part_status) }),
      dash(d.disposition_number),
      decision-name(d.disposition_type),
      if d.current_state == none [#text(fill: muted)[—]] else { state-badge(d.current_state) },
    )),
    column-gutter: 10pt,
    inset-y: 4pt,
    aligns: (left, left, left, left, center),
  )

  // The detail of each decision made; the table says which still wait.
  #for d in data.decisions.filter(d => d.disposition_type != none) [
    #v(8pt)
    == #d.subject #h(4pt) #text(size: 9pt, fill: muted, weight: "regular")[#dash(d.disposition_number)]

    // Who decided it, and when — the authority behind it.
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 16pt,
      row-gutter: 6pt,
      field("Decision", decision-name(d.disposition_type)),
      field("Rework Attempt", str(d.rework_attempt_at_step)),
      field("Authorized By", d.decision_authorized_by),
      field("Authorized At", fmt-dt(d.decision_authorized_at)),
      field("Assigned To", d.assigned_to),
      field("", none),
    )

    #if d.resolution_notes != "" [
      #v(4pt)
      #d.resolution_notes
    ]

    #if d.requires_customer_approval [
      #v(4pt)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 16pt,
        row-gutter: 6pt,
        field(
          "Customer Approval",
          if d.customer_approval_received {
            text(fill: ok, weight: "semibold")[Received]
          } else {
            text(fill: warn, weight: "semibold")[Pending]
          },
        ),
        field("Approval Reference", d.customer_approval_reference),
        field("Approval Date", fmt-dt(d.customer_approval_date)),
        field("", none),
      )
    ]

    #if d.disposition_type == "SCRAP" [
      #v(4pt)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 16pt,
        row-gutter: 6pt,
        field(
          "Scrap Verified",
          if d.scrap_verified {
            text(fill: ok, weight: "semibold")[Yes]
          } else {
            text(fill: warn, weight: "semibold")[No]
          },
        ),
        field("Method", d.scrap_verification_method),
        field("Verified By", d.scrap_verified_by),
        field("Verified At", fmt-dt(d.scrap_verified_at)),
      )
    ]

    #if d.resolution_completed [
      #v(4pt)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 16pt,
        row-gutter: 6pt,
        field("Completed By", d.resolution_completed_by),
        field("Completed At", fmt-dt(d.resolution_completed_at)),
      )
    ]
  ]
]

#pagebreak(weak: true)

= Closure

#if data.state == "CLOSED" [
  This NCR is closed: every decision under it has been carried out.

  #v(6pt)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,
    field("Closed At", fmt-dt(data.closed_at)),
    field("", none),
  )
] else [
  #text(fill: warn, style: "italic")[
    This NCR is open: a decision under it is still to be made or carried out.
  ]
]

#v(20pt)

#signature-block(("Originator", "Quality Manager", "Customer"))

#end-marker([End of Report — #data.ncr_number])
