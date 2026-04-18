// Deviation Request / Use-As-Is template.
//
// Context: Tracker/reports/adapters/deviation_request.py → DeviationRequestContext
//
// Layout:
//   1. Title block — disposition number, disposition type badge, severity badge
//   2. Part Identification section
//   3. Nonconformance Description section
//   4. Engineering Justification section (resolution_notes)
//   5. Customer Approval section (conditional — only if requires_customer_approval)
//   6. Signature block — Engineering + Quality (+ Customer if customer approval required)

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8.5pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Disposition type badge — USE_AS_IS=blue, REPAIR=amber
#let disposition-badge(dtype) = {
  if dtype == "USE_AS_IS" {
    badge("USE AS IS", accent, rgb("#dbeafe"))
  } else if dtype == "REPAIR" {
    badge("REPAIR", warn, rgb("#fef3c7"))
  } else {
    badge(dtype, muted, rgb("#e2e8f0"))
  }
}

// Severity badge
#let severity-badge(sev) = {
  if sev == "CRITICAL" { badge("CRITICAL", bad, rgb("#fee2e2")) }
  else if sev == "MAJOR" { badge("MAJOR", warn, rgb("#fef3c7")) }
  else if sev == "MINOR" { badge("MINOR", ok, rgb("#dcfce7")) }
  else { badge(sev, muted, rgb("#e2e8f0")) }
}

// State badge
#let state-badge(state) = {
  if state == "CLOSED" { badge("CLOSED", ok, rgb("#dcfce7")) }
  else if state == "IN_PROGRESS" { badge("IN PROGRESS", warn, rgb("#fef3c7")) }
  else { badge("OPEN", muted, rgb("#e2e8f0")) }
}

// Field/value row — muted label, value in ink; handles none/empty gracefully
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

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Deviation Request",
  doc-id: data.disposition_number,
  classification: "Controlled Document — AS9100D / IATF 16949",
)

// ── Title block ───────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    DEVIATION REQUEST / USE-AS-IS AUTHORIZATION
  ]
  #v(2pt)
  #text(size: 22pt, weight: "bold", font: sans-font)[#data.disposition_number]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(6pt)
  #disposition-badge(data.disposition_type)
  #h(8pt)
  #severity-badge(data.severity)
  #h(8pt)
  #state-badge(data.current_state)
  #v(2pt)
  #text(size: 9pt, fill: muted)[
    Date Opened: #str(data.created_at).slice(0, 10)
  ]
]

#v(14pt)

// ── Part Identification ───────────────────────────────────────────────────────

= Part Identification

#set par(justify: false)
#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  kv("Part / Serial Number", data.part_erp_id),
  kv("Part Type", data.part_type_name),

  kv("Work Order", data.work_order_erp_id),
  kv("Detected at Step", data.step_name),

  kv("MRB Reviewer", data.assigned_to),
  kv("", none),
)

#divider()

// ── Nonconformance Description ────────────────────────────────────────────────

= Nonconformance Description

#text(size: 9pt, fill: muted)[
  Specify the requirement vs. actual condition and the quantity affected.
]
#v(4pt)

#if data.description == "" [
  #text(fill: muted, style: "italic")[No description recorded.]
] else [
  #data.description
]

#divider()

// ── Engineering Justification ─────────────────────────────────────────────────

= Engineering Justification

#text(size: 9pt, fill: muted)[
  Engineering must affirm that the deviation does not adversely affect
  form, fit, or function, and that the product is safe to use as-is
  or in its repaired condition.
]
#v(4pt)

#if data.resolution_notes == "" [
  #text(fill: muted, style: "italic")[No engineering justification recorded.]
] else [
  #data.resolution_notes
]

// ── Customer Approval (conditional) ──────────────────────────────────────────

#if data.requires_customer_approval [
  #divider()

  = Customer Approval

  #set par(justify: false)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    row-gutter: 6pt,

    [
      #text(fill: muted, font: sans-font, size: 9pt)[*Approval Received*] \
      #v(2pt)
      #if data.customer_approval_received [
        #badge("APPROVED", ok, rgb("#dcfce7"))
      ] else [
        #badge("PENDING", warn, rgb("#fef3c7"))
      ]
    ],
    kv("Approval Reference", data.customer_approval_reference),

    kv(
      "Approval Date",
      if data.customer_approval_date == none { "" } else { str(data.customer_approval_date) },
    ),
    kv("", none),
  )
]

#v(20pt)

// ── Signature block ──────────────────────────────────────────────────────────

= Signatures

#text(size: 9pt, fill: muted)[
  Engineering sign-off is mandatory for all use-as-is and repair
  dispositions. Quality cannot approve alone.
]
#v(8pt)

#if data.requires_customer_approval [
  // 3-column: Engineering, Quality, Customer
  #set par(justify: false)
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 20pt,

    [
      *Engineering* \
      #text(size: 8.5pt, fill: muted)[Technical acceptability] \
      #v(28pt)
      #line(length: 100%, stroke: 0.5pt + ink) \
      #text(size: 9pt, fill: muted)[Name · Signature · Date]
    ],
    [
      *Quality* \
      #text(size: 8.5pt, fill: muted)[QMS compliance] \
      #v(28pt)
      #line(length: 100%, stroke: 0.5pt + ink) \
      #text(size: 9pt, fill: muted)[Name · Signature · Date]
    ],
    [
      *Customer* \
      #text(size: 8.5pt, fill: muted)[Contractual approval] \
      #v(28pt)
      #line(length: 100%, stroke: 0.5pt + ink) \
      #text(size: 9pt, fill: muted)[Name · Signature · Date]
    ],
  )
] else [
  // 2-column: Engineering, Quality
  #set par(justify: false)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,

    [
      *Engineering* \
      #text(size: 8.5pt, fill: muted)[Technical acceptability] \
      #v(28pt)
      #line(length: 100%, stroke: 0.5pt + ink) \
      #text(size: 9pt, fill: muted)[Name · Signature · Date]
    ],
    [
      *Quality* \
      #text(size: 8.5pt, fill: muted)[QMS compliance] \
      #v(28pt)
      #line(length: 100%, stroke: 0.5pt + ink) \
      #text(size: 9pt, fill: muted)[Name · Signature · Date]
    ],
  )
]
