// Work Order Traveler template (landscape US-letter).
//
// Context: Tracker/reports/adapters/work_order_traveler.py → WorkOrderTravelerContext
//
// The traveler is the #1 printed shop-floor document — the paper packet that
// rides a work order through every operation. A scannable Code 128 barcode of
// the WO ERP id sits in the header so an operator/inspector can scan the paper
// to pull the job up on screen.
//
// Common helpers (kv, badge, divider, info-box, footer-note, svg-img, opt,
// wo-priority-badge) come from the shared kit (_common/components.typ); the
// landscape-specific wet-ink sign-off cells (signoff / capture), the barcode
// title block, and the WorkOrderStatus badge are defined locally.
//
// Layout:
//   1. Header — title + tenant (left), WO barcode + S/N (right)
//   2. Work-order info block — part, process, rev, drawing, qty, dates
//   3. Order / customer reference
//   4. Routing table — Seq | Operation | Type | Controls & Specs |
//      Operator/Date | Inspector/Date | Acc/Rej | Remarks
//      (sign-off / acc-rej / remarks cells are blank wet-ink, or as-built)
//   5. Final-release footer — qty acc/rej/scrap, final sign-off, QA stamp

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

// Local fills — kept light so the document reads as a clean table rather than a
// stack of outlined forms. `band` shades the read-only reference row; `chip`
// marks a captured (as-built) value. Both are airy enough to sit under text
// without competing with the dark ink/rule colors (tuned for photocopying).
// band / chip / stripe fill tints come from the shared palette (page-setup).

// ----------------------------------------------------------------------------
// Local helpers — landscape wet-ink cells (no house equivalent)
// ----------------------------------------------------------------------------

// Work-order status, keyed to WorkOrderStatus's display labels (see
// Tracker/models/mes_lite.py). Local because this vocabulary is the traveler's
// alone — priority is shared with the dispatch list, status isn't.
#let status-badge(status) = {
  let s = upper(status)
  if s == "COMPLETED" { tone-badge(status, "ok") }
  else if s in ("PENDING", "IN PROGRESS") { tone-badge(status, "accent") }
  else if s in ("ON HOLD", "WAITING FOR OPERATOR") { tone-badge(status, "warn") }
  else { tone-badge(status, "muted") }
}

// A sign-off cell — blank for wet-ink capture (fixed writing height), or
// pre-filled (as-built): the box grows to fit its content so text never
// overflows or overlaps the row below.
#let signoff(value: none, h: 16pt) = if value == none or value == "" {
  // Blank write-in field — a light bordered box gives four walls to write in.
  box(width: 100%, height: h, stroke: 0.75pt + rule, radius: 2pt)[]
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

#show: doc-frame.with(
  doc-type: "Work Order Traveler",
  title: data.part_name,
  doc-id: data.wo_number,
  kind: "shop",
  landscape: true,
  org: data.tenant_name,
  aside: grid(
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
// No hyphenation: keeps IDs like ORD-SHOWCASE intact. (Sans body and ragged
// paragraphs come from the frame, as on every shop sheet.)
#set text(hyphenate: false)

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
    kv("Priority:", wo-priority-badge(data.priority), label-width: auto),

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
  fill: band, stroke: 0.75pt + rule, radius: 4pt,
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

// Sticky: the heading and its key travel with the table, rather than stranding at
// the foot of page 1 while the whole table starts overleaf.
#block(sticky: true)[
= Routing — #str(data.total_operations) operations

#text(size: 8pt, fill: muted, font: sans-font)[
  Left columns describe each operation; the sign-off, quantity, and remarks
  columns mirror the digital record. Operations are signed off on the digital
  work order as they complete. The write-in columns are a fallback — if a
  device isn't at hand or something needs a note, write it here to keep the job
  moving.
]
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
  // The routing table's conventions — repeating header, unbreakable cells,
  // horizontal rules, banded zebra — are now the shared `report-table` defaults,
  // generalised from this document. `column-gutter: 12pt` + `edge-inset: 6pt`
  // reproduces the uniform 6pt-per-side cell inset this table has always used;
  // `valign: top` keeps the operator writing from the top of a 32pt wet-ink box.
  #report-table(
    (0.45fr, 1.9fr, 0.75fr, 2.2fr, 1.3fr, 1.3fr, 0.42fr, 0.42fr, 1.9fr),
    ([Op], [Operation], [Type], [Controls & Specs],
     [Operator / Date], [Inspector / Date],
     text(size: 7.5pt)[Acc], text(size: 7.5pt)[Rej], [Remarks]),
    data.operations.map(op => (
      text(fill: ink, font: sans-font, weight: "semibold", size: 10pt)[#if op.op_number != none [#op.op_number] else [#op.seq]],
      {
        text(weight: "semibold", font: sans-font)[#op.step_name]
        if op.is_outside_process [ #h(4pt) #tone-badge("OSP", "warn") ]
        if op.description != none [
          #v(1pt)
          #text(size: 7.5pt, fill: muted, font: sans-font)[#op.description]
        ]
      },
      {
        text(fill: muted, font: sans-font)[#op.step_type]
        if op.std_time != none [
          #v(1pt)
          #text(size: 7.5pt, fill: muted, font: sans-font)[⏱ #op.std_time]
        ]
      },
      {
        if op.controls.len() == 0 and op.specs.len() == 0 [
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
        // As-built for the printed serial — the actual next to the spec.
        if op.at("visits", default: 0) > 1 [
          #v(2pt)
          #tone-badge(str(op.visits) + " visits — reworked", "warn")
        ]
        for r in op.at("recorded", default: ()) [
          #v(1pt)
          #text(size: 7.5pt, font: sans-font)[▸ #r]
        ]
        for m in op.at("materials", default: ()) [
          #v(1pt)
          #text(size: 7.5pt, font: sans-font)[◦ #m]
        ]
        for o in op.at("overrides", default: ()) [
          #v(1pt)
          #text(size: 7.5pt, font: sans-font, fill: warn)[Override: #o]
        ]
      },
      // Fill-in fields — tall bordered boxes for handwriting; as-built = chip.
      signoff(value: op.operator, h: 32pt),
      signoff(value: op.inspector, h: 32pt),
      signoff(value: if op.acc_rej == "ACC" { "✓" } else { none }, h: 32pt),
      // Needs repair is not an accept: it goes in the Rej column, said as RPR.
      signoff(value: if op.acc_rej == "REJ" { "✗" } else if op.acc_rej == "RPR" { "RPR" } else { none }, h: 32pt),
      signoff(value: op.remarks, h: 32pt),
    )),
    column-gutter: 12pt,
    edge-inset: 6pt,
    valign: top,
  )
]

#v(6pt)

// ── Serials on this work order — where each unit is (2026-10-08) ─────────────
#if data.at("serials", default: ()).len() > 0 [
  = Serials — #str(data.serials.len() + data.at("serials_truncated", default: 0))

  #text(size: 8pt, fill: muted, font: sans-font)[
    Where each unit stands as of #data.generated_date. Print a single serial's
    as-built record from its part page.
  ]
  #v(4pt)
  #set text(size: 8pt)
  #report-table(
    (1.4fr, 2fr, 1.2fr, 0.9fr),
    ([Serial], [Current step], [Status], [Open NCRs]),
    data.serials.map(s => (
      text(font: mono-font)[#s.serial],
      if s.step != none [#s.step] else [#text(fill: muted)[—]],
      [#s.status],
      if s.open_ncrs > 0 { tone-badge(str(s.open_ncrs), "warn") } else { text(fill: muted)[—] },
    )),
    column-gutter: 12pt,
    edge-inset: 6pt,
  )
  #if data.at("serials_truncated", default: 0) > 0 [
    #text(size: 7.5pt, fill: muted, font: sans-font)[…and #str(data.serials_truncated) more serials on the live work order.]
  ]
  #v(6pt)
]

// ── Closeout — the sign-off key has one row per operation and flows after the
// routing (a long routing's key may span pages); Final Release + footer are
// glued together below so the footer never orphans. ─────────────────────────
// Sticky, so the heading and its key never strand at a page foot apart from the table.
#block(sticky: true)[
= Sign-off Key

#text(size: 8pt, fill: muted, font: sans-font)[
  Print each signer once below. If you sign a routing row on paper, use these
  initials — paper sign-offs are a fallback; the authoritative sign-off is
  captured on the digital work order.
]
]

// One row per operation, sized directly from the routing so the number of
// sign-off rows matches the step count (floor of 3 for very short routings).
#let keyrows = calc.max(3, data.operations.len())

// A table, so the column labels reprint wherever the key breaks across pages. Sized
// like the routing table above it.
#{
  set text(size: 8pt)
  report-table(
    (2.6fr, 1fr, 1fr),
    ("Name", "Badge / ID", "Initials"),
    range(keyrows).map(_ => ([], [], [])),
    inset-y: 7pt,
  )
}

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
    grid.cell(colspan: 4, capture(
      "NCR # / Disposition — record any nonconformance raised and how it was dispositioned",
      value: if data.at("nonconformances", default: ()).len() > 0 { data.nonconformances.join(linebreak()) } else { none },
      h: 15pt)),
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


]  // end final-release + footer block
