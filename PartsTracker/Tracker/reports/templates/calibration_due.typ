// Calibration Due Report template.
//
// Context: Tracker/reports/adapters/calibration_due.py → CalibrationDueContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Summary bar — total / overdue / due-soon counts
//   3. Equipment table — sorted by due_date ascending (overdue first)
//   4. Footer note (planning document, not a quality record)

#import "_common/page-setup.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Status badge — OVERDUE=red, DUE_SOON=amber, CURRENT=green
#let status-badge(status) = {
  if status == "OVERDUE"  { badge("OVERDUE",  bad,  rgb("#fee2e2")) }
  else if status == "DUE_SOON" { badge("DUE SOON", warn, rgb("#fef3c7")) }
  else                    { badge("CURRENT",  ok,   rgb("#dcfce7")) }
}

// Result badge — PASS=green, FAIL=red, LIMITED=amber
#let result-badge(result) = {
  if result == "PASS"    { badge("PASS",    ok,   rgb("#dcfce7")) }
  else if result == "FAIL" { badge("FAIL",  bad,  rgb("#fee2e2")) }
  else if result == "LIMITED" { badge("LIMITED", warn, rgb("#fef3c7")) }
  else                   { badge(result,   muted, rgb("#e2e8f0")) }
}

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
  title: "Calibration Due Report",
  classification: "Internal — Quality Planning",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    CALIBRATION DUE REPORT
  ]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[Calibration Status]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font)[
    Generated: #data.generated_date
  ]
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
    columns: (1fr, 1fr, 1fr),
    column-gutter: 12pt,

    // Total
    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_equipment]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total Equipment Tracked]
    ],

    // Overdue
    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.overdue_count > 0 { bad } else { ok },
      )[#data.overdue_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Overdue]
    ],

    // Due Soon
    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.due_soon_count > 0 { warn } else { ok },
      )[#data.due_soon_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Due Within 30 Days]
    ],
  )
]

#v(14pt)

// ── Equipment table ──────────────────────────────────────────────────────────

= Equipment Calibration Status

#if data.items.len() == 0 [
  #text(fill: muted, style: "italic")[
    No equipment with calibration records found for this tenant.
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
      columns: (2.5fr, 1.8fr, 1.4fr, 1.1fr, 1.1fr, 0.7fr, 1fr),
      column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Equipment],
      text(weight: "semibold", font: sans-font)[Serial],
      text(weight: "semibold", font: sans-font)[Location],
      text(weight: "semibold", font: sans-font)[Last Cal],
      text(weight: "semibold", font: sans-font)[Due Date],
      align(right)[#text(weight: "semibold", font: sans-font)[Days]],
      align(center)[#text(weight: "semibold", font: sans-font)[Status]],
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
        columns: (2.5fr, 1.8fr, 1.4fr, 1.1fr, 1.1fr, 0.7fr, 1fr),
        column-gutter: 6pt,
        align(horizon)[
          #text(font: sans-font)[#item.equipment_name]
        ],
        align(horizon)[
          #text(fill: muted, font: mono-font)[#item.equipment_serial]
        ],
        align(horizon)[
          #text(fill: muted)[#item.location]
        ],
        align(horizon)[
          #text(fill: muted)[#item.last_cal_date]
        ],
        align(horizon)[
          #text(
            fill: if item.status == "OVERDUE" { bad }
                  else if item.status == "DUE_SOON" { warn }
                  else { ink },
            weight: if item.status == "OVERDUE" { "semibold" } else { "regular" },
          )[#item.due_date]
        ],
        align(horizon + right)[
          #let days = item.days_until_due
          #text(
            fill: if days < 0 { bad } else if days <= 30 { warn } else { muted },
            weight: if days < 0 { "semibold" } else { "regular" },
          )[#if days < 0 [#str(days)] else [+#str(days)]]
        ],
        align(horizon + center)[
          #status-badge(item.status)
        ],
      )
    ]
  ]
]

#v(16pt)
#divider()

// ── Footer note ───────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* This is a planning document generated from calibration record data as
  of #data.generated_date. It is not a calibration certificate or quality record.
  Status thresholds: OVERDUE = past due date; DUE SOON = due within 30 days;
  CURRENT = more than 30 days remaining.
]
