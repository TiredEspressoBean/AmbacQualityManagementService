// Dispatch List template.
//
// Context: Tracker/reports/adapters/dispatch_list.py → DispatchListContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Summary bar — total open WOs, overdue count
//   3. Per work-center section:
//        Section heading: step name + WO count
//        Table: WO # | Part | Qty | Due Date | Days | Priority | Status
//        Overdue rows shown in red/bold
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

// Priority badge colouring
#let priority-badge(p) = {
  if p == "Urgent"  { badge("URGENT", bad,  rgb("#fee2e2")) }
  else if p == "High"   { badge("HIGH",   warn, rgb("#fef3c7")) }
  else if p == "Normal" { badge("NORMAL", ok,   rgb("#dcfce7")) }
  else                  { badge("LOW",    muted, rgb("#e2e8f0")) }
}

// Status text colouring (WorkOrderStatus values)
#let status-color(s) = {
  if s == "IN_PROGRESS"         { ok   }
  else if s == "ON_HOLD"        { warn }
  else if s == "WAITING_FOR_OPERATOR" { warn }
  else                          { muted }
}

// Human-friendly status label
#let status-label(s) = {
  if s == "IN_PROGRESS"               { "In Progress" }
  else if s == "PENDING"              { "Pending" }
  else if s == "ON_HOLD"              { "On Hold" }
  else if s == "WAITING_FOR_OPERATOR" { "Waiting" }
  else                                { s }
}

// Days cell — red/bold when negative (overdue), amber when <= 3, otherwise muted
#let days-cell(d) = {
  if d == none [
    #text(fill: muted)[—]
  ] else {
    let dval = int(d)
    let col = if dval < 0 { bad } else if dval <= 3 { warn } else { muted }
    let wt  = if dval < 0 { "semibold" } else { "regular" }
    if dval < 0 {
      text(fill: col, weight: wt)[#str(dval)]
    } else {
      text(fill: col, weight: wt)[+#str(dval)]
    }
  }
}

// Section divider rule
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.4pt + rule)
  v(6pt)
}

// Column widths shared between header and data rows
#let col-widths = (1.4fr, 2.2fr, 0.7fr, 1.1fr, 0.65fr, 1fr, 1.1fr)

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Dispatch List",
  classification: "Internal — Production Planning",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    DISPATCH LIST
  ]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[What's Running Today]
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
    columns: (1fr, 1fr),
    column-gutter: 12pt,

    // Total open WOs
    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_open_wos]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total Open Work Orders]
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
  )
]

#v(14pt)

// ── Work center groups ────────────────────────────────────────────────────────

#if data.groups.len() == 0 [
  #text(fill: muted, style: "italic")[
    No open work orders found for this tenant.
  ]
] else [
  #for group in data.groups [
    // ── Section heading ─────────────────────────────────────────────────────
    #v(8pt)
    #block(
      fill: rgb("#1e40af"),
      inset: (x: 8pt, y: 5pt),
      radius: (top-left: 4pt, top-right: 4pt),
      width: 100%,
    )[
      #grid(
        columns: (1fr, auto),
        text(weight: "semibold", fill: white, font: sans-font, size: 10pt)[
          #group.step_name
        ],
        text(fill: rgb("#bfdbfe"), font: sans-font, size: 9pt)[
          #group.wo_count WO#if group.wo_count != 1 [s]
        ],
      )
    ]

    // ── Table header ─────────────────────────────────────────────────────────
    #set par(justify: false)
    #block(
      fill: rgb("#f1f5f9"),
      stroke: (bottom: 0.5pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
      inset: (x: 6pt, y: 5pt),
      width: 100%,
    )[
      #set text(size: 9pt)
      #grid(
        columns: col-widths,
        column-gutter: 6pt,
        text(weight: "semibold", font: sans-font)[WO \#],
        text(weight: "semibold", font: sans-font)[Part],
        align(right)[#text(weight: "semibold", font: sans-font)[Qty]],
        text(weight: "semibold", font: sans-font)[Due Date],
        align(right)[#text(weight: "semibold", font: sans-font)[Days]],
        align(center)[#text(weight: "semibold", font: sans-font)[Priority]],
        text(weight: "semibold", font: sans-font)[Status],
      )
    ]

    // ── Table rows ───────────────────────────────────────────────────────────
    #for (idx, item) in group.items.enumerate() [
      #let is-overdue = item.days_until_due != none and int(item.days_until_due) < 0
      #let row-fill = if is-overdue {
        rgb("#fff5f5")
      } else if calc.rem(idx, 2) == 0 {
        white
      } else {
        rgb("#f8fafc")
      }
      #set par(justify: false)
      #block(
        fill: row-fill,
        stroke: (bottom: 0.3pt + rule, left: 0.5pt + rule, right: 0.5pt + rule),
        inset: (x: 6pt, y: 5pt),
        width: 100%,
      )[
        #set text(size: 9pt)
        #grid(
          columns: col-widths,
          column-gutter: 6pt,
          // WO number — bold + red when overdue
          align(horizon)[
            #text(
              font: mono-font,
              fill: if is-overdue { bad } else { ink },
              weight: if is-overdue { "semibold" } else { "regular" },
            )[#item.wo_number]
          ],
          // Part name
          align(horizon)[
            #text(font: sans-font)[#item.part_name]
          ],
          // Qty remaining
          align(horizon + right)[
            #text(fill: muted)[#item.qty_remaining]
          ],
          // Due date — red when overdue
          align(horizon)[
            #text(
              fill: if is-overdue { bad } else { muted },
              weight: if is-overdue { "semibold" } else { "regular" },
            )[#if item.due_date == none [—] else [#item.due_date]]
          ],
          // Days until due
          align(horizon + right)[
            #days-cell(item.days_until_due)
          ],
          // Priority badge
          align(horizon + center)[
            #priority-badge(item.priority)
          ],
          // Status
          align(horizon)[
            #text(fill: status-color(item.status), font: sans-font)[
              #status-label(item.status)
            ]
          ],
        )
      ]
    ]

    #v(16pt)
  ]
]

#divider()

// ── Footer note ───────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* This Dispatch List is a planning document generated from live production
  data as of #data.generated_date. It is not a quality record or traveler. Work
  centers are approximated by the current manufacturing step assigned to each part.
  Sort order: most urgent (earliest due date) first within each work center.
  Days column: negative values indicate the work order is past its due date.
]
