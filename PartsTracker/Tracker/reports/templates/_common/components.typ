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
// Every letter-format template uses this kit. The two label templates
// (part_id_label*.typ) deliberately don't: they print on label stock and skip
// page-setup's page geometry entirely, so they import only the palette.
//
// Note that Typst shadows silently — a template that defines its own `#let
// status-badge` after importing this file gets the local one with no warning.
// That is fine where the local version encodes a domain vocabulary; it is a
// bug where someone meant to use the shared helper.

#import "page-setup.typ": *

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

// Render an SVG source string as an image (barcodes / QR codes).
#let svg-img(svg-str, w) = image(bytes(svg-str), width: w)

// Optional value — render the value, or a muted em dash when empty.
#let opt(v) = if v == none or v == "" { text(fill: muted)[—] } else { v }

// Section divider rule.
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

// Low-level badge: coloured pill with semibold label. Prefer `tone-badge` —
// this stays for the handful of one-off pairings that aren't a palette tone.
#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8pt, weight: "semibold", fill: fg, font: sans-font)[#label],
)

// Badge by palette tone — "ok" | "warn" | "bad" | "accent" | "muted".
//
// Deliberately NOT a status→colour mapper. Each report speaks its own status
// vocabulary (a BOM is RELEASED/DRAFT/OBSOLETE, a CAPA is OPEN/PENDING_
// VERIFICATION/CLOSED, a gauge is CURRENT/DUE_SOON/OVERDUE) and the same word
// can mean different urgency in different documents. A generic matcher has to
// guess, and anything it doesn't recognise silently renders grey — so the
// *vocabulary* stays with the template that owns it and only the *palette
// pairing* is shared. That's the part that was actually being copied.
#let tone-badge(label, tone) = {
  let fill-for = (
    ok: (ok, ok-tint),
    warn: (warn, warn-tint),
    bad: (bad, bad-tint),
    accent: (accent, accent-tint),
    muted: (muted, muted-tint),
  )
  let pair = fill-for.at(tone)
  badge(label, pair.first(), pair.last())
}

// Work-order priority badge, keyed to WorkOrderPriority's display labels
// ("Urgent" / "High" / "Normal" / "Low" — see Tracker/models/mes_lite.py).
//
// This one IS shared, unlike status: priority is a single enum that both the
// traveler and the dispatch list render, and they used to disagree — the same
// High work order printed red on one sheet and amber on the other. Amber is the
// gradient that leaves red meaning Urgent alone.
#let wo-priority-badge(priority) = {
  let p = upper(priority)
  if p == "URGENT" { tone-badge(upper(priority), "bad") }
  else if p == "HIGH" { tone-badge(upper(priority), "warn") }
  else if p == "NORMAL" { tone-badge(upper(priority), "ok") }
  else { tone-badge(upper(priority), "muted") }
}

// Optional-component indicator (BOM lineage): an OPT chip, or a muted dash.
#let optional-badge(is_optional) = {
  if is_optional {
    tone-badge("OPT", "warn")
  } else {
    text(size: 8pt, fill: muted, font: sans-font)[—]
  }
}

// ---------------------------------------------------------------------------
// Panels & tables
// ---------------------------------------------------------------------------

// Boxed key-value panel (shared info block).
#let info-box(body) = block(
  fill: panel,
  stroke: 0.75pt + rule,
  radius: 4pt,
  inset: 12pt,
  width: 100%,
)[#body]

// Paginated report table — the one to reach for.
//
// The house table, generalised from work_order_traveler.typ, which was the only
// template already building a real Typst table and so the only one that never
// had the page-break bug the stacked-block `table-header`/`table-row` below
// carry. Its conventions are the defaults here:
//
//   * `table.header(repeat: true)` — column headings reprint on every page.
//     A block cannot repeat, so the stacked-block form drops them: page 2 of a
//     long list is bare columns of part numbers and lot codes.
//   * `breakable: false` cells — a row relocates whole to the next page rather
//     than splitting. Matters wherever a cell stacks several lines (lot numbers
//     over a location, a spec list, a wet-ink box); half a row's lot codes
//     stranded at a page break is worse than a short page.
//   * Horizontal rules only — banded and zebra-striped, no verticals. A real
//     Typst table rules every column by default, which no house sheet did.
//
//   columns  — Typst column spec, e.g. (0.5fr, 2fr, 1fr)
//   header   — array of header cell bodies (styled semibold sans by this helper;
//              a caller may wrap one in `text(size: …)` to override)
//   rows     — array of arrays of cell bodies, one inner array per row
//   aligns   — optional per-column horizontal alignment, e.g. (left, right, center)
//   valign   — vertical cell alignment; `top` for tall wet-ink forms so an
//              operator writes from the top of the cell
//
// `column-gutter` is split across the shared cell edge, so it means the same
// thing it did in the inner grid of the stacked-block version.
#let report-table(
  columns,
  header,
  rows,
  column-gutter: 9pt,
  inset-y: 5pt,
  edge-inset: 6pt,
  aligns: none,
  valign: horizon,
) = {
  let ncols = columns.len()
  let halign = if aligns == none { (left,) * ncols } else { aligns }
  let c = table.cell.with(breakable: false)
  table(
    columns: columns,
    inset: (x, y) => (
      left: if x == 0 { edge-inset } else { column-gutter / 2 },
      right: if x == ncols - 1 { edge-inset } else { column-gutter / 2 },
      top: inset-y,
      bottom: inset-y,
    ),
    align: (x, y) => halign.at(x) + valign,
    // y == 0 is the header; body rows zebra from the first data row.
    fill: (x, y) => if y == 0 { band }
      else if calc.rem(y - 1, 2) == 0 { white }
      else { stripe },
    // Heavier rule under the header, hairline between rows, nothing vertical.
    stroke: (x, y) => (
      bottom: if y == 0 { 1pt + rule } else { 0.75pt + rule },
    ),
    table.header(
      repeat: true,
      ..header.map(h => text(weight: "semibold", font: sans-font)[#h]),
    ),
    ..rows.map(r => r.map(cell => c(cell))).flatten(),
  )
}

// Table header band (caller supplies the grid of header cells).
// `spacing: 0pt` so the header + rows abut with no gap — the rows are
// intentionally top-less and share the border above them (a gap would leave
// each row open-topped / "U-shaped").
//
// Does NOT repeat across pages — prefer `report-table` for anything that can run
// long. Kept for short fixed-height tables where the block form is simpler.
#let table-header(body) = block(
  fill: band,
  stroke: 0.9pt + rule,
  inset: (x: 6pt, y: 5pt),
  width: 100%,
  spacing: 0pt,
  radius: (top-left: 3pt, top-right: 3pt),
)[#body]

// Striped table row (caller supplies the grid of row cells). Top-less by
// design; `spacing: 0pt` makes it abut the header/previous row so its top edge
// is the line above it (see table-header note).
#let table-row(idx, body, inset-y: 5pt) = block(
  fill: if calc.rem(idx, 2) == 0 { white } else { stripe },
  stroke: (bottom: 0.5pt + rule, left: 0.75pt + rule, right: 0.75pt + rule),
  inset: (x: 6pt, y: inset-y),
  width: 100%,
  spacing: 0pt,
)[#body]

// ---------------------------------------------------------------------------
// Title & footer
// ---------------------------------------------------------------------------

// Centred report title block: letter-spaced eyebrow, bold title, tenant, and
// an optional "Generated: <date>" line or a trailing badge (pass via `trailing`).
// `trailing-gap` exists because templates historically used 4pt or 6pt before their
// badge/date line; parameterising it let all of them adopt this helper without a
// single pixel moving.
#let report-title(eyebrow, title, tenant, generated: none, trailing: none,
                  title-size: 20pt, trailing-gap: 6pt) = align(center)[
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
    v(trailing-gap)
    trailing
  }
]

// Small muted footer note preceded by a divider, with a bolded lead word.
//
// Unbreakable: the rule and the note are one object. Left breakable, Typst will
// happily fit the divider at the foot of a page and push the note to the next,
// which reads as a stray rule under the content and an orphaned sentence
// overleaf. (Same guard the traveler applies to its final-release block.)
// `below: 0pt` — the note is the last thing on the sheet, so trailing block
// spacing only eats the margin. Leading spacing is kept: the flow already had it,
// and zeroing both moved the footer further than the wrapper ever did.
#let footer-note(body, lead: "Note") = block(breakable: false, below: 0pt)[
  #divider()
  #text(size: 8.5pt, fill: muted)[*#lead:* #body]
]
