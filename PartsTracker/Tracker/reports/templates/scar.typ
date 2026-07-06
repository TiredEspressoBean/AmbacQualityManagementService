// Supplier Corrective Action Request (SCAR) template.
//
// Context: Tracker/reports/adapters/scar.py → ScarContext
//
// Supplier-facing: states the nonconformance we found + requests a structured
// 8D corrective-action response by a due date. Layout:
//   1. Title block — SCAR number, severity/status badges
//   2. Issued To (supplier) / Issued By (us) + key dates + response-due callout
//   3. Nonconformance description (+ our immediate containment)
//   4. Required supplier response — 8D blocks (blank, for the supplier to complete)
//   5. Supplier sign-off + return instructions

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ── Helpers ─────────────────────────────────────────────────────────────────

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8.5pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

#let severity-badge(s) = {
  if s == "CRITICAL" { badge("CRITICAL", bad, rgb("#fee2e2")) }
  else if s == "MAJOR" { badge("MAJOR", warn, rgb("#fef3c7")) }
  else if s == "MINOR" { badge("MINOR", ok, rgb("#dcfce7")) }
  else { badge(s, muted, rgb("#e2e8f0")) }
}

#let status-badge(s) = {
  if s == "OPEN" { badge("OPEN", accent, rgb("#dbeafe")) }
  else if s == "IN_PROGRESS" { badge("IN PROGRESS", warn, rgb("#fef3c7")) }
  else if s == "PENDING_VERIFICATION" { badge("AWAITING RESPONSE", warn, rgb("#fef3c7")) }
  else if s == "CLOSED" { badge("CLOSED", ok, rgb("#dcfce7")) }
  else { badge(s, muted, rgb("#e2e8f0")) }
}

#let kv(label, value) = grid(
  columns: (auto, 1fr), column-gutter: 10pt,
  text(fill: muted, font: sans-font, size: 9pt)[*#label*],
  if value == none or value == "" [ #text(fill: muted, style: "italic")[—] ] else [ #value ],
)

#let divider() = { v(6pt); line(length: 100%, stroke: 0.4pt + rule); v(6pt) }

#let fmt-date(d) = if d == none or d == "" [ #text(fill: muted, style: "italic")[—] ] else [ #d ]

// A labeled, empty box for the supplier to complete (the "request" half of a SCAR).
#let response-box(code, label, hint, lines: 3) = {
  v(6pt)
  block(width: 100%, breakable: false)[
    #text(size: 9.5pt, weight: "semibold", font: sans-font)[
      #text(fill: accent)[#code] · #label
    ]
    #if hint != none [ #h(6pt) #text(size: 8pt, fill: muted, style: "italic")[#hint] ]
    #v(3pt)
    #block(
      width: 100%, height: lines * 16pt,
      stroke: 0.5pt + rule, radius: 3pt, inset: 6pt,
    )[]
  ]
}

// ── Document ──────────────────────────────────────────────────────────────────

#show: page-setup.with(
  title: "Supplier Corrective Action Request",
  doc-id: data.scar_number,
  classification: "Confidential — Supplier Corrective Action Request",
)

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    SUPPLIER CORRECTIVE ACTION REQUEST (SCAR)
  ]
  #v(2pt)
  #text(size: 22pt, weight: "bold", font: sans-font)[#data.scar_number]
  #v(6pt)
  #severity-badge(data.severity)
  #h(6pt)
  #status-badge(data.status)
]

#v(12pt)

= Request Details

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  kv("Issued To (Supplier)", text(weight: "semibold")[#data.supplier_name]),
  kv("Issued By", data.issued_by_org),
  kv("Originator", data.issued_by_person),
  kv("Severity", severity-badge(data.severity)),
  kv("Date Issued", fmt-date(data.issued_date)),
  kv("Response Due", fmt-date(data.response_due_date)),
)

#v(8pt)
#block(
  width: 100%, fill: rgb("#fef3c7"), stroke: 0.5pt + warn,
  inset: (x: 10pt, y: 8pt), radius: 4pt,
)[
  #text(weight: "semibold", fill: warn, font: sans-font)[Response required] —
  please complete sections D3–D7 below and return this form by
  #if data.response_due_date == none [ the agreed date ] else [ *#data.response_due_date* ].
]

#divider()

= D2 · Nonconformance (reported by #data.issued_by_org)

#if data.problem_statement == "" [
  #text(fill: muted, style: "italic")[No description provided.]
] else [ #data.problem_statement ]

#if data.immediate_action != "" and data.immediate_action != none [
  #v(8pt)
  #text(fill: muted, font: sans-font, size: 9pt)[*Our immediate containment*]
  #v(2pt)
  #data.immediate_action
]

#divider()

= Required Supplier Response (8D)

#text(size: 9pt, fill: muted)[
  Complete each section below. Attach objective evidence (data, photos, updated
  control plans / FMEA) where applicable.
]

#response-box("D3", "Containment Action", "Immediate action to protect against further escape", lines: 3)
#response-box("D4", "Root Cause", "Why it occurred (5-Why / Fishbone) and why it escaped detection", lines: 4)
#response-box("D5", "Corrective Action", "Permanent action that eliminates the root cause", lines: 3)
#response-box("D6", "Implementation & Verification", "Date implemented + how effectiveness was verified", lines: 3)
#response-box("D7", "Prevent Recurrence", "Systemic / read-across changes (FMEA, control plan, work instructions)", lines: 3)

#v(14pt)

= Supplier Sign-off

#grid(
  columns: (1fr, 1fr), column-gutter: 20pt,
  [
    *Prepared by (Supplier)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Title · Date]
  ],
  [
    *Accepted by (#data.issued_by_org)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Quality · Signature · Date]
  ],
)

#v(16pt)
#align(center)[
  #line(length: 60%, stroke: 0.5pt + rule)
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font, tracking: 1pt)[
    END OF SCAR — #data.scar_number
  ]
  #v(2pt)
  #text(size: 8pt, fill: muted)[
    Return the completed form to #data.issued_by_org Quality by the response-due date.
  ]
]
