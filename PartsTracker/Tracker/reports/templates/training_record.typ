// Training Record template.
//
// Context: Tracker/reports/adapters/training_record.py → TrainingRecordContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Employee info header — name, email/ID
//   3. Summary bar — total / current / expired / no-expiry counts
//   4. Training table — topic, completed, expires, trainer, status badge
//   5. ISO 9001 7.2 note (competence evidence, not just attendance)
//   6. Signature block — Employee, Trainer, Supervisor (3-column)

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Status badge — CURRENT=green, EXPIRED=red, EXPIRING_SOON=amber, no expiry=muted
#let status-badge(status) = {
  if status == "CURRENT"        { badge("CURRENT",        ok,   rgb("#dcfce7")) }
  else if status == "EXPIRED"   { badge("EXPIRED",        bad,  rgb("#fee2e2")) }
  else if status == "EXPIRING_SOON" { badge("EXPIRING SOON", warn, rgb("#fef3c7")) }
  else                          { badge(status,           muted, rgb("#e2e8f0")) }
}

// Key-value helper for the employee info block
#let kv(key, value) = grid(
  columns: (90pt, 1fr),
  text(size: 9pt, fill: muted, font: sans-font)[#key],
  text(size: 9pt, font: sans-font)[#value],
)

// Section divider rule
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.4pt + rule)
  v(6pt)
}

// Signature line
#let sig-line(role) = {
  v(28pt)
  line(length: 100%, stroke: 0.5pt + ink)
  v(2pt)
  text(size: 8.5pt, fill: muted, font: sans-font)[#role]
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Training Record",
  classification: "Controlled Document — ISO 9001 §7.2",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    TRAINING RECORD
  ]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[Training History]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font)[
    Generated: #data.generated_date
  ]
]

#v(14pt)

// ── Employee info ─────────────────────────────────────────────────────────────

#block(
  fill: rgb("#f8fafc"),
  stroke: 0.5pt + rule,
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[
  #text(size: 9pt, weight: "semibold", fill: muted, font: sans-font)[EMPLOYEE]
  #v(6pt)
  #kv("Name:", data.employee_name)
  #v(2pt)
  #kv("Email / ID:", data.employee_email)
  #v(2pt)
  #kv("Record ID:", data.employee_id)
]

#v(14pt)

// ── Summary bar ──────────────────────────────────────────────────────────────

#block(
  fill: rgb("#f8fafc"),
  stroke: 0.5pt + rule,
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    column-gutter: 12pt,

    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total]
    ],

    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.current_count > 0 { ok } else { muted },
      )[#data.current_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Current]
    ],

    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.expired_count > 0 { bad } else { muted },
      )[#data.expired_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Expired]
    ],

    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font, fill: muted)[#data.no_expiry_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[No Expiry]
    ],
  )
]

#v(14pt)

// ── Training table ────────────────────────────────────────────────────────────

= Training History

#if data.records.len() == 0 [
  #text(fill: muted, style: "italic")[
    No training records found for this employee.
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
      columns: (2.8fr, 1.2fr, 1.2fr, 1.6fr, 1.1fr),
      column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Training Topic],
      text(weight: "semibold", font: sans-font)[Completed],
      text(weight: "semibold", font: sans-font)[Expires],
      text(weight: "semibold", font: sans-font)[Trainer / Provider],
      align(center)[#text(weight: "semibold", font: sans-font)[Status]],
    )
  ]

  // Table rows
  #for (idx, rec) in data.records.enumerate() [
    #let row-fill = if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") }
    #block(
      fill: row-fill,
      stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
      inset: (x: 6pt, y: 5pt),
      width: 100%,
    )[
      #grid(
        columns: (2.8fr, 1.2fr, 1.2fr, 1.6fr, 1.1fr),
        column-gutter: 6pt,
        align(horizon)[
          #text(font: sans-font, weight: "semibold")[#rec.topic]
          #if rec.notes != "" [
            #v(1pt)
            #text(size: 8pt, fill: muted)[#rec.notes]
          ]
        ],
        align(horizon)[
          #text(fill: muted)[#rec.completed_date]
        ],
        align(horizon)[
          #if rec.expires_date != none [
            #text(
              fill: if rec.status == "EXPIRED" { bad }
                    else if rec.status == "EXPIRING_SOON" { warn }
                    else { muted },
            )[#rec.expires_date]
          ] else [
            #text(fill: muted, style: "italic")[—]
          ]
        ],
        align(horizon)[
          #if rec.trainer != "" [
            #text(fill: muted)[#rec.trainer]
          ] else [
            #text(fill: muted, style: "italic")[—]
          ]
        ],
        align(horizon + center)[
          #status-badge(rec.status)
        ],
      )
    ]
  ]
]

#v(16pt)
#divider()

// ── ISO 9001 §7.2 note ────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *ISO 9001:2015 §7.2 — Competence:* This record demonstrates the effectiveness
  of training as required by the standard. Assessment results and competency
  evaluations must be retained as documented information. Status: CURRENT =
  valid and within expiry date; EXPIRING SOON = expires within 30 days;
  EXPIRED = past expiry date; NO EXPIRY = no expiry date defined (evergreen).
]

#v(20pt)

// ── Signature block ───────────────────────────────────────────────────────────

= Signatures

#text(size: 9pt, fill: muted)[
  Signatures below confirm attendance (Employee), training delivery (Trainer),
  and verification of competency (Supervisor/Manager).
]

#v(8pt)

#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 20pt,

  [
    #sig-line("Employee — Acknowledging Attendance")
    #v(4pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Name: #data.employee_name]
    #v(2pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Date: ________________]
  ],

  [
    #sig-line("Trainer — Confirming Delivery")
    #v(4pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Name: ________________]
    #v(2pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Date: ________________]
  ],

  [
    #sig-line("Supervisor — Confirming Competency")
    #v(4pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Name: ________________]
    #v(2pt)
    #text(size: 8pt, fill: muted, font: sans-font)[Date: ________________]
  ],
)
