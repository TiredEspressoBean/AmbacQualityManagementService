// Work Order Traveler template (landscape US-letter).
//
// Context: Tracker/reports/adapters/work_order_traveler.py → WorkOrderTravelerContext
//
// The traveler is the #1 printed shop-floor document — the paper packet that
// rides a work order through every operation. A scannable Code 128 barcode of
// the WO ERP id sits in the header so an operator/inspector can scan the paper
// to pull the job up on screen.
//
// First adopter of the shared component kit (_common/components.typ): the
// common helpers (kv, badge, divider, info-box, table-header/row, footer-note,
// svg-img, opt) come from there; only the landscape-specific wet-ink sign-off
// cells (signoff / capture) and the barcode title block are defined locally.
//
// Layout:
//   1. Header — title + tenant (left), WO barcode + S/N (right)
//   2. Work-order info block — part, process, rev, drawing, qty, dates
//   3. Order / customer reference
//   4. Routing table — Seq | Operation | Type | Controls & Specs |
//      Operator/Date | Inspector/Date | Acc/Rej | Remarks
//      (sign-off / acc-rej / remarks cells are blank wet-ink, or as-built)
//   5. Final-release footer — qty acc/rej/scrap, final sign-off, QA stamp

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Local helpers — landscape wet-ink cells (no house equivalent)
// ----------------------------------------------------------------------------

// A sign-off cell — blank for wet-ink capture (fixed writing height), or
// pre-filled (as-built): the box grows to fit its content so text never
// overflows or overlaps the row below.
#let signoff(value: none, h: 16pt) = if value == none or value == "" {
  box(width: 100%, height: h, stroke: 0.5pt + rule, radius: 2pt)[]
} else {
  block(
    width: 100%, stroke: 0.5pt + rule, radius: 2pt,
    inset: (x: 4pt, y: 3pt),
  )[
    #set par(leading: 0.4em)
    #text(size: 8pt, font: sans-font)[#value]
  ]
}

// A labelled capture box (label above a blank or pre-filled sign-off box).
#let capture(label, value: none, h: 22pt) = [
  #text(size: 8pt, fill: muted, font: sans-font)[#label]
  #v(2pt)
  #signoff(value: value, h: h)
]

// ----------------------------------------------------------------------------
// Document — landscape, no hyphenation (keeps IDs like ORD-SHOWCASE intact)
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Work Order Traveler",
  doc-id: data.wo_number,
  classification: "Internal — Shop Floor",
)
#set page(flipped: true)
#set text(hyphenate: false)
#set par(justify: false)

// ── Header: title (left) + barcode (right) ──────────────────────────────────

#grid(
  columns: (1fr, auto),
  column-gutter: 24pt,
  align: (left + horizon, right + horizon),
  [
    #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
      WORK ORDER TRAVELER
    ]
    #v(2pt)
    #text(size: 22pt, weight: "bold", font: sans-font)[#data.part_name]
    #v(-4pt)
    #text(size: 10pt, fill: muted)[#data.tenant_name]
  ],
  grid(
    columns: (auto, auto),
    column-gutter: 12pt,
    align: (right + horizon, center + horizon),
    [
      #svg-img(data.barcode_svg, 2.3in)
      #v(-2pt)
      #text(size: 12pt, weight: "bold", font: mono-font)[#data.wo_number]
      #if data.serial != none [
        #v(1pt)
        #text(size: 9pt, fill: muted, font: mono-font)[S/N: #data.serial]
      ]
    ],
    [
      #svg-img(data.qr_svg, 0.85in)
      #v(1pt)
      #text(size: 6.5pt, fill: muted, font: sans-font)[Scan to open]
    ],
  ),
)

#v(10pt)

// ── Work-order info block (4 columns, wide values) ──────────────────────────

#info-box[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    column-gutter: 20pt,
    row-gutter: 7pt,

    kv("Work Order:", data.wo_number, label-width: auto),
    kv("Part Number:", data.part_number, label-width: auto),
    kv("Process:", data.process_name, label-width: auto),
    kv("Part Rev:", data.revision, label-width: auto),

    kv("Drawing #:", data.drawing_number, label-width: auto),
    kv("Drawing Rev:", data.drawing_revision, label-width: auto),
    kv("Qty:", str(data.quantity), label-width: auto),
    kv("Priority:", priority-badge(data.priority), label-width: auto),

    kv("Status:", status-badge(data.status), label-width: auto),
    kv("Start:", data.start_date, label-width: auto),
    kv("Due:", data.due_date, label-width: auto),
    kv("Generated:", data.generated_date, label-width: auto),
  )
  #v(8pt)
  #line(length: 100%, stroke: 0.6pt + rule)
  #v(8pt)
  #grid(
    columns: (1fr, 1fr, 2fr),
    column-gutter: 20pt,
    kv("Order:", data.order_number, label-width: auto),
    kv("Customer:", data.customer_name, label-width: auto),
    kv("Order Name:", data.order_name, label-width: auto),
  )
]

#v(12pt)

// ── Routing table ───────────────────────────────────────────────────────────

= Routing — #str(data.total_operations) operations

#if data.operations.len() == 0 [
  #text(fill: muted, style: "italic")[
    No routing found for this work order. Confirm a process is assigned before
    releasing the job to the floor.
  ]
] else [
  #set text(size: 8.5pt)

  #let cols = (0.5fr, 2fr, 0.9fr, 2.3fr, 1.15fr, 1.15fr, 1fr, 2.3fr)

  #table-header[
    #grid(
      columns: cols,
      column-gutter: 6pt,
      text(weight: "semibold", font: sans-font)[Op],
      text(weight: "semibold", font: sans-font)[Operation],
      text(weight: "semibold", font: sans-font)[Type],
      text(weight: "semibold", font: sans-font)[Controls & Specs],
      align(center)[#text(weight: "semibold", font: sans-font)[Operator / Date]],
      align(center)[#text(weight: "semibold", font: sans-font)[Inspector / Date]],
      align(center)[#text(weight: "semibold", font: sans-font)[Qty Acc / Rej]],
      align(center)[#text(weight: "semibold", font: sans-font)[Remarks]],
    )
  ]

  #for (idx, op) in data.operations.enumerate() [
    #table-row(idx)[
      #grid(
        columns: cols,
        column-gutter: 6pt,
        align: horizon + left,
        text(fill: ink, font: mono-font, weight: "semibold")[#if op.op_number != none [#op.op_number] else [#op.seq]],
        [
          #text(weight: "semibold", font: sans-font)[#op.step_name]
          #if op.is_outside_process [ #h(4pt) #badge("OSP", warn, rgb("#fef3c7")) ]
          #if op.description != none [
            #v(1pt)
            #text(size: 7.5pt, fill: muted, font: sans-font)[#op.description]
          ]
        ],
        [
          #text(fill: muted, font: sans-font)[#op.step_type]
          #if op.std_time != none [
            #v(1pt)
            #text(size: 7.5pt, fill: muted, font: sans-font)[⏱ #op.std_time]
          ]
        ],
        [
          #if op.controls.len() == 0 and op.specs.len() == 0 [
            #text(fill: muted)[—]
          ] else [
            #if op.controls.len() > 0 [
              #text(size: 8pt, fill: muted, font: sans-font)[#op.controls.join(" · ")]
            ]
            #for spec in op.specs [
              #v(1pt)
              #text(size: 7.5pt, font: mono-font)[• #spec]
            ]
          ]
        ],
        signoff(value: op.operator, h: 26pt),
        signoff(value: op.inspector, h: 26pt),
        // Quantity accepted / rejected — blank number boxes for wet-ink counts.
        [
          #stack(spacing: 4pt,
            grid(columns: (auto, 1fr), column-gutter: 4pt, align: horizon,
              text(size: 7pt, fill: muted, font: sans-font)[Acc], signoff(h: 13pt)),
            grid(columns: (auto, 1fr), column-gutter: 4pt, align: horizon,
              text(size: 7pt, fill: muted, font: sans-font)[Rej], signoff(h: 13pt)))
        ],
        signoff(value: op.remarks, h: 34pt),
      )
    ]
  ]
]

#v(14pt)

// ── Final-release footer ────────────────────────────────────────────────────

= Final Release

#info-box[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    column-gutter: 20pt,
    row-gutter: 12pt,
    capture("Qty accepted", value: data.qty_accepted),
    capture("Qty rejected", value: data.qty_rejected),
    capture("Qty scrapped", value: data.qty_scrapped),
    capture("Date completed", value: data.date_completed),
    capture("Final inspection — sign-off / date", value: data.final_signoff),
    grid.cell(colspan: 2, capture("QA release — “released for shipment” stamp / signature", value: data.qa_release)),
    capture("Date released", value: data.date_released),
  )
]

#v(12pt)

// ── Footer note ─────────────────────────────────────────────────────────────

#footer-note([
  This packet must accompany the work order through every operation. Operators
  and inspectors sign off each step as it completes; QA sign-off operations
  require a qualified inspector. Scan the header barcode (#data.wo_number) to
  open this job on screen. Do not advance the job past a failed or unsigned
  control step, and do not release for shipment with any open control step or
  nonconformance.
])
