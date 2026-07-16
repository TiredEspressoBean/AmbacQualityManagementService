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

// Local fills — kept light so the document reads as a clean table rather than a
// stack of outlined forms. `band` shades the read-only reference row; `chip`
// marks a captured (as-built) value. Both are airy enough to sit under text
// without competing with the dark ink/rule colors (tuned for photocopying).
#let band = rgb("#f6f8fb")
#let chip = rgb("#eef2f7")

// ----------------------------------------------------------------------------
// Local helpers — landscape wet-ink cells (no house equivalent)
// ----------------------------------------------------------------------------

// A sign-off cell — blank for wet-ink capture (fixed writing height), or
// pre-filled (as-built): the box grows to fit its content so text never
// overflows or overlaps the row below.
#let signoff(value: none, h: 16pt) = if value == none or value == "" {
  // Blank write-in field — a light bordered box gives four walls to write in.
  box(width: 100%, height: h, stroke: 0.5pt + rule, radius: 2pt)[]
} else {
  // Pre-filled (as-built) value — a soft fill chip (no border) shows captured
  // data without adding another outline to the row. Grows to fit its content.
  block(
    width: 100%, fill: chip, radius: 2pt,
    inset: (x: 5pt, y: 3pt),
  )[
    #set par(leading: 0.4em)
    #text(size: 8pt, font: sans-font)[#value]
  ]
}

// A labelled capture box (label above a blank or pre-filled sign-off box).
// Default height suits the job-level Final Release boxes; per-op capture
// cells pass an explicit taller height.
#let capture(label, value: none, h: 18pt) = [
  #text(size: 8pt, fill: muted, font: sans-font)[#label]
  #v(3.5pt)
  #signoff(value: value, h: h)
]

// An empty tick box + label (for the packet-contents checklist).
#let chk(label) = box(baseline: 1.5pt)[
  #box(width: 9pt, height: 9pt, stroke: 0.75pt + rule, radius: 1pt)
  #h(3pt)
  #text(size: 8.5pt, font: sans-font)[#label]
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

// ── Packet contents (what should physically travel with this job) ───────────

#box(
  fill: band, stroke: 0.5pt + rule, radius: 4pt,
  inset: (x: 10pt, y: 7pt), width: 100%,
)[
  #text(size: 8pt, fill: muted, font: sans-font, weight: "semibold")[Packet includes:]
  #h(10pt)
  #chk[Engineering drawing (Rev #if data.drawing_revision != none [#data.drawing_revision.replace("Rev ", "")] else [\_\_])]
  #h(14pt) #chk[Material cert]
  #h(14pt) #chk[First-article (FAIR)]
  #h(14pt) #chk[Inspection sheet]
  #h(14pt) #chk[Other: #box(width: 90pt, height: 9pt, stroke: (bottom: 0.6pt + rule))]
]

#v(12pt)

// ── Routing table ───────────────────────────────────────────────────────────

= Routing — #str(data.total_operations) operations

#text(size: 8pt, fill: muted, font: sans-font)[
  Left columns describe each operation; the sign-off, quantity, and remarks
  columns mirror the digital record. Operations are signed off on the digital
  work order as they complete. The write-in columns are a fallback — if a
  device isn't at hand or something needs a note, write it here to keep the job
  moving.
]
#v(6pt)

#if data.operations.len() == 0 [
  #text(fill: muted, style: "italic")[
    No routing found for this work order. Confirm a process is assigned before
    releasing the job to the floor.
  ]
] else [
  #set text(size: 8.5pt)

  // One row per operation: reference columns (Op / Operation / Type / Controls
  // & Specs) on the left, fill-in columns (Operator / Inspector / Acc / Rej /
  // Remarks) on the right. A native table() reprints the column header at the
  // top of every page the routing spans (table.header repeat). Blank fields are
  // bordered boxes to write in; captured as-built values are soft chips.
  #let cols = (0.45fr, 1.9fr, 0.75fr, 2.2fr, 1.3fr, 1.3fr, 0.42fr, 0.42fr, 1.9fr)
  #let hdr(body, ..a) = text(weight: "semibold", font: sans-font, ..a)[#body]
  // Guard: each cell is unbreakable, so an operation's row relocates whole to
  // the next page rather than splitting its boxes across the page boundary.
  #let c = table.cell.with(breakable: false)

  #table(
    columns: cols,
    inset: (x: 6pt, y: 5pt),
    align: top + left,
    // Horizontal rules only (no verticals); a heavier rule under the header.
    stroke: (x, y) => (bottom: if y == 0 { 0.75pt + rule } else { 0.5pt + rule }),
    fill: (x, y) => if y == 0 { band },

    table.header(
      repeat: true,
      hdr[Op], hdr[Operation], hdr[Type], hdr[Controls & Specs],
      hdr[Operator / Date], hdr[Inspector / Date],
      hdr(size: 7.5pt)[Acc], hdr(size: 7.5pt)[Rej], hdr[Remarks],
    ),

    ..data.operations.map(op => (
      c(text(fill: ink, font: mono-font, weight: "medium", size: 10pt)[#if op.op_number != none [#op.op_number] else [#op.seq]]),
      c[
        #text(weight: "semibold", font: sans-font)[#op.step_name]
        #if op.is_outside_process [ #h(4pt) #badge("OSP", warn, rgb("#fef3c7")) ]
        #if op.description != none [
          #v(1pt)
          #text(size: 7.5pt, fill: muted, font: sans-font)[#op.description]
        ]
      ],
      c[
        #text(fill: muted, font: sans-font)[#op.step_type]
        #if op.std_time != none [
          #v(1pt)
          #text(size: 7.5pt, fill: muted, font: sans-font)[⏱ #op.std_time]
        ]
      ],
      c[
        #if op.controls.len() == 0 and op.specs.len() == 0 [
          #text(fill: muted)[—]
        ] else [
          #if op.controls.len() > 0 [
            #text(size: 8pt, fill: muted, font: sans-font)[#op.controls.join(" · ")]
          ]
          #for spec in op.specs [
            #v(1pt)
            #text(size: 7.5pt, fill: muted, font: sans-font)[• #spec]
          ]
        ]
      ],
      // Fill-in fields — tall bordered boxes for handwriting; as-built = chip.
      c(signoff(value: op.operator, h: 32pt)),
      c(signoff(value: op.inspector, h: 32pt)),
      c(signoff(h: 32pt)),
      c(signoff(h: 32pt)),
      c(signoff(value: op.remarks, h: 32pt)),
    )).flatten(),
  )
]

#v(6pt)

// ── Closeout — the sign-off key has one row per operation and flows after the
// routing (a long routing's key may span pages); Final Release + footer are
// glued together below so the footer never orphans. ─────────────────────────
= Sign-off Key

#text(size: 8pt, fill: muted, font: sans-font)[
  Print each signer once below. If you sign a routing row on paper, use these
  initials — paper sign-offs are a fallback; the authoritative sign-off is
  captured on the digital work order.
]
#v(5pt)

#let keyhead(n) = text(size: 7.5pt, fill: muted, font: sans-font, weight: "semibold")[#n]
#let keycell() = box(width: 100%, height: 22pt, stroke: (bottom: 0.5pt + rule))

// One row per operation, sized directly from the routing so the number of
// sign-off rows matches the step count (floor of 3 for very short routings).
#let keyrows = calc.max(3, data.operations.len())

#grid(
  columns: (2.6fr, 1fr, 1fr),
  column-gutter: 14pt,
  row-gutter: 6pt,
  keyhead("Name"), keyhead("Badge / ID"), keyhead("Initials"),
  ..range(keyrows).map(_ => (
    keycell(), keycell(), keycell(),
  )).flatten(),
)

#v(6pt)

// Final Release + footer stay together (non-breakable) so the footer never
// orphans onto a near-empty trailing page.
#block(breakable: false, width: 100%)[

= Final Release

#info-box[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    column-gutter: 20pt,
    row-gutter: 9pt,
    capture("Qty accepted", value: data.qty_accepted),
    capture("Qty rejected", value: data.qty_rejected),
    capture("Qty scrapped", value: data.qty_scrapped),
    capture("Date completed", value: data.date_completed),
    grid.cell(colspan: 4, capture("NCR # / Disposition — record any nonconformance raised and how it was dispositioned", h: 15pt)),
    capture("Final inspection — sign-off / date", value: data.final_signoff),
    grid.cell(colspan: 2, capture("QA release — “released for shipment” stamp / signature", value: data.qa_release)),
    capture("Date released", value: data.date_released),
  )
]

#v(5pt)

// ── Footer note ─────────────────────────────────────────────────────────────

#footer-note([
  The digital work order is the system of record — scan the header barcode
  (#data.wo_number) to open the live job; capturing each operation there is the
  authoritative sign-off. QA sign-off operations require a qualified inspector.
  Do not advance the job past a failed or unsigned control step, and do not
  release for shipment with any open control step or nonconformance.
])

#v(6pt)

// Document-control line — a printed copy is a snapshot, not the controlled master.
#align(center, text(size: 7pt, fill: muted, font: sans-font)[
  Uncontrolled printed snapshot as of #data.generated_date — verify the current revision before use.
])

]  // end final-release + footer block
