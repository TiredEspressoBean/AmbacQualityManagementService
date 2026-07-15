// Shared report component kit.
//
// The house base is `page-setup.typ` (page geometry, palette, typography,
// header/footer). This file adds the reusable *content* components that were,
// historically, copy-pasted into every template (kv, badge, divider, info
// box, table header/row, footer note). New reports should:
//
//   #import "_common/page-setup.typ": *
//   #import "_common/components.typ": *
//
// (import page-setup first — the components depend on its palette + fonts).
//
// Existing templates keep their inline copies until migrated; this kit is the
// forward convention, adopted first by work_order_traveler.typ.

#import "page-setup.typ": *

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

// Render an SVG source string as an image (barcodes / QR codes).
#let svg-img(svg-str, w) = image(bytes(svg-str), width: w)

// Optional value — render the value, or a muted em dash when empty.
#let opt(v) = if v == none or v == "" { text(fill: muted)[—] } else { v }

// Section divider rule (matches the house `divider()` verbatim).
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.6pt + rule)
  v(6pt)
}

// ---------------------------------------------------------------------------
// Key / value
// ---------------------------------------------------------------------------

// Boxed-grid style (pick_list / bom lineage): fixed label column, plain 9pt
// label (caller includes the trailing colon), muted em-dash fallback.
#let kv(key, value, label-width: 90pt) = grid(
  columns: (label-width, 1fr),
  column-gutter: 6pt,
  text(size: 9pt, fill: muted, font: sans-font)[#key],
  if value == none or value == "" {
    text(size: 9pt, fill: muted, style: "italic")[—]
  } else {
    text(size: 9pt, font: sans-font)[#value]
  },
)

// Field style (ncr / calibration / capa lineage): auto label width, bold muted
// label (no colon), italic em-dash fallback.
#let field(label, value) = grid(
  columns: (auto, 1fr),
  column-gutter: 10pt,
  text(size: 9pt, fill: muted, font: sans-font)[*#label*],
  if value == none or value == "" {
    text(fill: muted, style: "italic")[—]
  } else { value },
)

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------

// Canonical badge (house-identical): coloured pill with semibold label.
#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8pt, weight: "semibold", fill: fg, font: sans-font)[#label],
)

// Status → palette badge, using the shared colour mapping:
//   pass/approved/released/complete → ok      (green)
//   fail/rejected                   → bad      (red)
//   pending/draft/in-progress       → accent   (blue)
//   otherwise                       → muted    (grey)
#let status-badge(status) = {
  let s = upper(status)
  if s in ("PASS", "APPROVED", "RELEASED", "COMPLETE", "COMPLETED", "ACC") {
    badge(status, ok, rgb("#dcfce7"))
  } else if s in ("FAIL", "REJECTED", "REJ") {
    badge(status, bad, rgb("#fee2e2"))
  } else if s in ("PENDING", "DRAFT", "IN PROGRESS", "UNDER REVIEW") {
    badge(status, accent, rgb("#dbeafe"))
  } else {
    badge(status, muted, rgb("#e2e8f0"))
  }
}

// Priority → palette badge: high/urgent/critical red, low grey, else amber.
#let priority-badge(priority) = {
  let p = upper(priority)
  if p in ("HIGH", "URGENT", "CRITICAL") {
    badge(priority, bad, rgb("#fee2e2"))
  } else if p in ("LOW",) {
    badge(priority, muted, rgb("#e2e8f0"))
  } else {
    badge(priority, warn, rgb("#fef3c7"))
  }
}

// ---------------------------------------------------------------------------
// Panels & tables
// ---------------------------------------------------------------------------

// Boxed key-value panel (the shared `#f8fafc` info block).
#let info-box(body) = block(
  fill: rgb("#f1f5f9"),
  stroke: 0.75pt + rule,
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[#body]

// Table header band (caller supplies the grid of header cells).
#let table-header(body) = block(
  fill: rgb("#dbe2ea"),
  stroke: 0.9pt + rule,
  inset: (x: 6pt, y: 5pt),
  width: 100%,
  radius: (top-left: 3pt, top-right: 3pt),
)[#body]

// Striped table row (caller supplies the grid of row cells).
#let table-row(idx, body, inset-y: 5pt) = block(
  fill: if calc.rem(idx, 2) == 0 { white } else { rgb("#eef2f7") },
  stroke: (bottom: 0.5pt + rule, left: 0.75pt + rule, right: 0.75pt + rule),
  inset: (x: 6pt, y: inset-y),
  width: 100%,
)[#body]

// ---------------------------------------------------------------------------
// Title & footer
// ---------------------------------------------------------------------------

// Centred report title block: letter-spaced eyebrow, bold title, tenant, and
// an optional "Generated: <date>" line or a trailing badge (pass via `trailing`).
#let report-title(eyebrow, title, tenant, generated: none, trailing: none, title-size: 20pt) = align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[#upper(eyebrow)]
  #v(2pt)
  #text(size: title-size, weight: "bold", font: sans-font)[#title]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#tenant]
  #if generated != none {
    v(4pt)
    text(size: 9pt, fill: muted, font: sans-font)[Generated: #generated]
  }
  #if trailing != none {
    v(6pt)
    trailing
  }
]

// Small muted footer note preceded by a divider, with a bolded lead word.
#let footer-note(body, lead: "Note") = {
  divider()
  text(size: 8.5pt, fill: muted)[*#lead:* #body]
}
