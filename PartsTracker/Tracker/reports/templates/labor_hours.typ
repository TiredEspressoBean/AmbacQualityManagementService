// Operator Hours template.
// Context: Tracker/reports/adapters/labor_hours.py → LaborHoursContext

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#let col-widths = (3fr, 1.2fr, 1.2fr)

#show: page-setup.with(
  title: "Operator Hours",
  classification: "Internal — Payroll",
)

#report-title(
  [OPERATOR HOURS],
  [Shop Hours by Operator],
  data.tenant_name,
  trailing-gap: 4pt,
  trailing: [
    #text(size: 9pt, fill: muted, font: sans-font)[
        Period: #data.start_date — #data.end_date · Generated: #data.generated_date
      ]
  ],
)

#v(14pt)

#info-box[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 12pt,
    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_on_shift]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total On-Shift Hours]
    ],
    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_direct]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total Direct (Job) Hours]
    ],
  )
]

#v(14pt)

#if data.rows.len() == 0 [
  #text(fill: muted, style: "italic")[No hours logged in this period.]
] else [
  // Header
  #block(
    fill: rgb("#f1f5f9"),
    stroke: (bottom: 0.5pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
    inset: (x: 6pt, y: 5pt),
    width: 100%,
  )[
    #set text(size: 9pt)
    #grid(
      columns: col-widths, column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Operator],
      align(right)[#text(weight: "semibold", font: sans-font)[On-Shift hrs]],
      align(right)[#text(weight: "semibold", font: sans-font)[Direct hrs]],
    )
  ]
  // Rows
  #for (idx, r) in data.rows.enumerate() [
    #block(
      fill: if calc.rem(idx, 2) == 0 { white } else { rgb("#f8fafc") },
      stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
      inset: (x: 6pt, y: 5pt),
      width: 100%,
    )[
      #set text(size: 9pt)
      #grid(
        columns: col-widths, column-gutter: 6pt,
        align(horizon)[#text(font: sans-font)[#r.name]],
        align(horizon + right)[#text(font: mono-font)[#r.on_shift_hours]],
        align(horizon + right)[#text(font: mono-font, fill: muted)[#r.direct_hours]],
      )
    ]
  ]
  // Total
  #block(
    fill: rgb("#eef2ff"),
    stroke: (bottom: 0.5pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
    inset: (x: 6pt, y: 5pt),
    width: 100%,
  )[
    #set text(size: 9pt, weight: "semibold")
    #grid(
      columns: col-widths, column-gutter: 6pt,
      text(font: sans-font)[Total],
      align(right)[#text(font: mono-font)[#data.total_on_shift]],
      align(right)[#text(font: mono-font)[#data.total_direct]],
    )
  ]
]

#footer-note(
  lead: "Note",
  [On-shift = clock-in→out attendance (breaks excluded); direct = time clocked onto jobs. Shop-floor operators only. Hours data for payroll — not a payroll calculation.],
)
