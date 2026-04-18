// CAPA Report template.
//
// Context: Tracker/reports/adapters/capa_report.py → CapaReportContext
//
// Layout:
//   1. Title block — CAPA number prominent, status + severity badges
//   2. Problem Description section
//   3. Immediate Action section (if present)
//   4. Root Cause Analysis section
//      - Method + summary
//      - 5-Why Q&A pairs (if method == FIVE_WHYS)
//      - Fishbone 6M categories (if method == FISHBONE)
//   5. Action Items table grouped by type
//      Columns: Description | Owner | Due | Completed | Status
//   6. Effectiveness Verification section (if present)
//   7. Approval section
//   8. Signature block — Initiator | Quality Manager | Approver

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8.5pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Status badge
#let status-badge(s) = {
  if s == "OPEN"                  { badge("OPEN",                 accent, rgb("#dbeafe")) }
  else if s == "IN_PROGRESS"      { badge("IN PROGRESS",          warn,   rgb("#fef3c7")) }
  else if s == "PENDING_VERIFICATION" { badge("PENDING VERIFICATION", warn, rgb("#fef3c7")) }
  else if s == "CLOSED"           { badge("CLOSED",               ok,     rgb("#dcfce7")) }
  else if s == "CANCELLED"        { badge("CANCELLED",            muted,  rgb("#e2e8f0")) }
  else                            { badge(s,                      muted,  rgb("#e2e8f0")) }
}

// Severity badge
#let severity-badge(s) = {
  if s == "CRITICAL" { badge("CRITICAL", bad,  rgb("#fee2e2")) }
  else if s == "MAJOR"   { badge("MAJOR",    warn, rgb("#fef3c7")) }
  else if s == "MINOR"   { badge("MINOR",    ok,   rgb("#dcfce7")) }
  else                   { badge(s,          muted, rgb("#e2e8f0")) }
}

// Task status badge
#let task-badge(s) = {
  if s == "COMPLETED"     { badge("COMPLETED",   ok,   rgb("#dcfce7")) }
  else if s == "IN_PROGRESS" { badge("IN PROGRESS", warn, rgb("#fef3c7")) }
  else if s == "NOT_STARTED" { badge("NOT STARTED", muted, rgb("#e2e8f0")) }
  else if s == "CANCELLED" { badge("CANCELLED",  muted, rgb("#e2e8f0")) }
  else                    { badge(s,             muted, rgb("#e2e8f0")) }
}

// Effectiveness result badge
#let effectiveness-badge(r) = {
  if r == "CONFIRMED"       { badge("CONFIRMED EFFECTIVE", ok,   rgb("#dcfce7")) }
  else if r == "NOT_EFFECTIVE" { badge("NOT EFFECTIVE",    bad,  rgb("#fee2e2")) }
  else if r == "INCONCLUSIVE" { badge("INCONCLUSIVE",     warn,  rgb("#fef3c7")) }
  else                      { badge(r,                    muted, rgb("#e2e8f0")) }
}

// Approval status badge
#let approval-badge(s) = {
  if s == "APPROVED"      { badge("APPROVED",     ok,   rgb("#dcfce7")) }
  else if s == "REJECTED" { badge("REJECTED",     bad,  rgb("#fee2e2")) }
  else if s == "PENDING"  { badge("PENDING",      warn, rgb("#fef3c7")) }
  else                    { badge("NOT REQUIRED",  muted, rgb("#e2e8f0")) }
}

// Field/value row — muted label, value body text; handles none/empty gracefully.
// Named `kv` to avoid shadowing the Typst built-in `field`.
#let kv(label, value) = grid(
  columns: (auto, 1fr),
  column-gutter: 10pt,
  text(fill: muted, font: sans-font, size: 9pt)[*#label*],
  if value == none or value == "" [
    #text(fill: muted, style: "italic")[—]
  ] else [
    #value
  ],
)

// Section divider rule
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.4pt + rule)
  v(6pt)
}

// Format a date string or none → em-dash
#let fmt-date(d) = if d == none or d == "" [ #text(fill: muted, style: "italic")[—] ] else [ #d ]

// Render human label for task type
#let task-type-label(t) = {
  if t == "CONTAINMENT"  [ Containment ]
  else if t == "CORRECTIVE"  [ Corrective ]
  else if t == "PREVENTIVE"  [ Preventive ]
  else [ #t ]
}

// Render human label for CAPA type
#let capa-type-label(t) = {
  if t == "CORRECTIVE"          [ Corrective Action ]
  else if t == "PREVENTIVE"     [ Preventive Action ]
  else if t == "CUSTOMER_COMPLAINT" [ Customer Complaint ]
  else if t == "AUDIT_FINDING"  [ Audit Finding ]
  else if t == "INTERNAL_AUDIT" [ Internal Audit ]
  else [ #t ]
}

// Render human label for RCA method
#let rca-method-label(m) = {
  if m == "FIVE_WHYS"   [ 5 Whys ]
  else if m == "FISHBONE"   [ Fishbone (Ishikawa) ]
  else if m == "FAULT_TREE" [ Fault Tree Analysis ]
  else if m == "PARETO"     [ Pareto Analysis ]
  else [ #m ]
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "CAPA Report",
  doc-id: data.capa_number,
  classification: "Controlled Document — Quality Management System",
)

// ── Title block ───────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    CORRECTIVE & PREVENTIVE ACTION REPORT
  ]
  #v(2pt)
  #text(size: 22pt, weight: "bold", font: sans-font)[#data.capa_number]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(6pt)
  #status-badge(data.status)
  #h(6pt)
  #severity-badge(data.severity)
]

#v(12pt)

// ── CAPA header ──────────────────────────────────────────────────────────────

= CAPA Header

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  kv("CAPA Type",      capa-type-label(data.capa_type)),
  kv("Severity",       severity-badge(data.severity)),

  kv("Initiated By",   data.initiated_by),
  kv("Assigned To",    data.assigned_to),

  kv("Date Opened",    fmt-date(data.initiated_date)),
  kv("Due Date",       fmt-date(data.due_date)),

  kv("Completed Date", fmt-date(data.completed_date)),
  kv("Status",         status-badge(data.status)),
)

#divider()

// ── Problem Description ───────────────────────────────────────────────────────

= Problem Description

#data.problem_statement

// ── Immediate Action ─────────────────────────────────────────────────────────

#if data.immediate_action != "" and data.immediate_action != none [
  #divider()

  = Immediate / Containment Action

  #data.immediate_action
]

#divider()

// ── Root Cause Analysis ───────────────────────────────────────────────────────

= Root Cause Analysis

#if data.rca == none [
  #text(fill: muted, style: "italic")[No root cause analysis recorded.]
] else [
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    kv("Method",       rca-method-label(data.rca.method)),
    kv("Conducted By", data.rca.conducted_by),

    kv("Date",         fmt-date(data.rca.conducted_date)),
    kv("",             none),
  )

  #v(6pt)
  #text(fill: muted, font: sans-font, size: 9pt)[*Root Cause Summary*]
  #v(2pt)
  #if data.rca.root_cause_summary == "" or data.rca.root_cause_summary == none [
    #text(fill: muted, style: "italic")[Not yet documented.]
  ] else [
    #data.rca.root_cause_summary
  ]

  // 5-Why sub-section
  #if data.rca.five_whys != none and data.rca.five_whys.whys.len() > 0 [
    #v(10pt)
    #text(weight: "semibold", font: sans-font, size: 10pt)[5-Why Analysis]
    #v(4pt)

    #set par(justify: false)
    #for (idx, pair) in data.rca.five_whys.whys.enumerate() [
      #block(
        fill: if calc.rem(idx, 2) == 0 { rgb("#f8fafc") } else { white },
        stroke: 0.4pt + rule,
        inset: (x: 8pt, y: 6pt),
        width: 100%,
        radius: 3pt,
      )[
        #grid(
          columns: (auto, 1fr),
          column-gutter: 8pt,
          row-gutter: 4pt,
          text(size: 9pt, weight: "semibold", fill: accent, font: sans-font)[Why #str(idx + 1)],
          text(size: 9pt, fill: muted, font: sans-font)[#pair.question],
          [],
          text(size: 9.5pt)[#pair.answer],
        )
      ]
      #v(3pt)
    ]

    #if data.rca.five_whys.identified_root_cause != "" [
      #v(4pt)
      #block(
        fill: rgb("#f0fdf4"),
        stroke: 0.5pt + ok,
        inset: (x: 8pt, y: 6pt),
        width: 100%,
        radius: 3pt,
      )[
        #text(size: 9pt, weight: "semibold", fill: ok, font: sans-font)[Identified Root Cause] \
        #v(2pt)
        #data.rca.five_whys.identified_root_cause
      ]
    ]
  ]

  // Fishbone sub-section
  #if data.rca.fishbone != none [
    #v(10pt)
    #text(weight: "semibold", font: sans-font, size: 10pt)[Fishbone / Ishikawa — 6M Categories]
    #v(4pt)

    #let fishbone = data.rca.fishbone
    #let categories = (
      ("Man (People)",   fishbone.man_causes),
      ("Machine",        fishbone.machine_causes),
      ("Material",       fishbone.material_causes),
      ("Method",         fishbone.method_causes),
      ("Measurement",    fishbone.measurement_causes),
      ("Environment",    fishbone.environment_causes),
    )

    #set par(justify: false)
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 10pt,
      row-gutter: 8pt,
      ..for (label, causes) in categories {
        (
          block(
            fill: rgb("#f8fafc"),
            stroke: 0.4pt + rule,
            inset: (x: 8pt, y: 6pt),
            width: 100%,
            radius: 3pt,
          )[
            #text(size: 9pt, weight: "semibold", fill: muted, font: sans-font)[#label]
            #if causes.len() == 0 [
              #v(2pt)
              #text(size: 9pt, fill: muted, style: "italic")[—]
            ] else [
              #for c in causes [
                #v(2pt)
                #text(size: 9pt)[• #c]
              ]
            ]
          ],
        )
      }
    )

    #if fishbone.identified_root_cause != "" [
      #v(4pt)
      #block(
        fill: rgb("#f0fdf4"),
        stroke: 0.5pt + ok,
        inset: (x: 8pt, y: 6pt),
        width: 100%,
        radius: 3pt,
      )[
        #text(size: 9pt, weight: "semibold", fill: ok, font: sans-font)[Identified Root Cause] \
        #v(2pt)
        #fishbone.identified_root_cause
      ]
    ]
  ]
]

#divider()

// ── Action Items table ────────────────────────────────────────────────────────

= Action Items

#if data.tasks.len() == 0 [
  #text(fill: muted, style: "italic")[No action items recorded.]
] else [
  #let task-types = ("CONTAINMENT", "CORRECTIVE", "PREVENTIVE")

  #for task-type in task-types {
    let group = data.tasks.filter(t => t.task_type == task-type)
    if group.len() > 0 {
      v(6pt)
      block[
        #text(size: 10pt, weight: "semibold", font: sans-font)[
          #task-type-label(task-type) Actions
        ]
      ]
      v(4pt)

      set text(size: 9pt)
      set par(justify: false)

      // Header row
      block(
        fill: rgb("#f1f5f9"),
        stroke: 0.5pt + rule,
        inset: (x: 6pt, y: 5pt),
        width: 100%,
        radius: (top-left: 3pt, top-right: 3pt),
      )[
        #grid(
          columns: (3fr, 1.5fr, 1fr, 1fr, 1.2fr),
          column-gutter: 6pt,
          text(weight: "semibold", font: sans-font)[Description],
          text(weight: "semibold", font: sans-font)[Owner],
          text(weight: "semibold", font: sans-font)[Due],
          text(weight: "semibold", font: sans-font)[Completed],
          align(center)[#text(weight: "semibold", font: sans-font)[Status]],
        )
      ]

      // Data rows
      for (idx, task) in group.enumerate() {
        let row-fill = if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") }
        block(
          fill: row-fill,
          stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
          inset: (x: 6pt, y: 5pt),
          width: 100%,
        )[
          #grid(
            columns: (3fr, 1.5fr, 1fr, 1fr, 1.2fr),
            column-gutter: 6pt,
            align(horizon)[
              #text(font: sans-font, size: 8pt, fill: muted)[#task.task_number] \
              #v(1pt)
              #task.description
            ],
            align(horizon)[
              #if task.owner == none or task.owner == "" [
                #text(fill: muted, style: "italic")[—]
              ] else [
                #task.owner
              ]
            ],
            align(horizon)[#fmt-date(task.due_date)],
            align(horizon)[#fmt-date(task.completed_date)],
            align(horizon + center)[#task-badge(task.status)],
          )
        ]
      }

      v(10pt)
    }
  }
]

#divider()

// ── Effectiveness Verification ────────────────────────────────────────────────

= Effectiveness Verification

#if data.verification == none [
  #text(fill: muted, style: "italic")[
    No effectiveness verification recorded. CAPA cannot be closed until
    verification is documented with evidence showing the problem has not
    recurred over the defined monitoring period.
  ]
] else [
  #let v-data = data.verification

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    kv("Verified By",     v-data.verified_by),
    kv("Verification Date", fmt-date(v-data.verification_date)),

    kv("Result",          effectiveness-badge(v-data.effectiveness_result)),
    kv("",                none),
  )

  #v(8pt)
  #text(fill: muted, font: sans-font, size: 9pt)[*Verification Method*]
  #v(2pt)
  #if v-data.verification_method == "" [
    #text(fill: muted, style: "italic")[—]
  ] else [
    #v-data.verification_method
  ]

  #v(6pt)
  #text(fill: muted, font: sans-font, size: 9pt)[*Success Criteria*]
  #v(2pt)
  #if v-data.verification_criteria == "" [
    #text(fill: muted, style: "italic")[—]
  ] else [
    #v-data.verification_criteria
  ]

  #if v-data.verification_notes != "" and v-data.verification_notes != none [
    #v(6pt)
    #text(fill: muted, font: sans-font, size: 9pt)[*Verification Notes*]
    #v(2pt)
    #v-data.verification_notes
  ]
]

#divider()

// ── Approval section ──────────────────────────────────────────────────────────

= Approval

#if not data.approval.approval_required [
  #text(fill: muted, style: "italic")[
    Management approval is not required for this CAPA.
  ]
] else [
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    kv("Approval Status", approval-badge(data.approval.approval_status)),
    kv("Approved By",     data.approval.approved_by),

    kv("Approved Date",   fmt-date(data.approval.approved_at)),
    kv("",                none),
  )
]

#v(20pt)

// ── Signature block ───────────────────────────────────────────────────────────

= Signatures

#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 20pt,

  [
    *Initiator* \
    #text(size: 9pt, fill: muted)[#if data.initiated_by != none [#data.initiated_by] else []] \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
  [
    *Quality Manager* \
    #v(34pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
  [
    *Approver / QRB* \
    #v(34pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
)

#v(16pt)
#align(center)[
  #line(length: 60%, stroke: 0.5pt + rule)
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font, tracking: 1pt)[
    END OF REPORT — #data.capa_number
  ]
  #v(2pt)
  #text(size: 8pt, fill: muted)[
    This CAPA may not be closed until effectiveness verification is documented
    with evidence that the problem has not recurred over the monitoring period.
  ]
]
