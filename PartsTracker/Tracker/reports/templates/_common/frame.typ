// The document frame — every letter-format report opens with it.
//
//   #import "_common/frame.typ": *
//   #show: doc-frame.with(
//     doc-type: "Non-Conformance Report",   // the kind of document (eyebrow)
//     title: data.disposition_number,       // what this one is about
//     doc-id: data.disposition_number,      // number for the header/footer
//     kind: "record",
//   )
//
// It owns everything that is the same on every sheet: page geometry (portrait or
// `landscape: true`), the brand row (organisation name and logo), the title block,
// the running header, and the footer — classification, document number, page count,
// print date, and the uncontrolled-copy notice. A template supplies only its body.
// Labels on label stock don't use it; they import the palette and parts they need.
//
// Branding arrives in the context as `_meta` (injected for every report by
// PdfGenerator), so templates don't pass it: `org_name`, `logo` (PNG bytes as an
// int array, or none) and `printed_at`. The palette stays fixed — it was darkened
// for shop-floor print survival, and a tenant colour would undo that.

#import "page-setup.typ": *
#import "components.typ": *

#let _meta = json.decode(sys.inputs.at("data", default: "{}")).at("_meta", default: (:))

// What the document is, for whoever holds the paper. Three kinds, one wording each.
//   record   — a quality record (NCR, CAPA, certificate, inspection record)
//   shop     — a working sheet for the floor (traveler, pick list, dispatch list)
//   customer — leaves the building to a customer (packing list, CoC)
//   supplier — leaves the building to a supplier (SCAR, return to vendor)
#let CLASSIFICATION = (
  record: "Controlled Document",
  shop: "Shop Floor",
  customer: "Customer Copy",
  supplier: "Supplier Copy",
)

// `uncontrolled: auto` stamps shop sheets: they reproduce live data (routing, specs,
// a schedule, stock) whose master is the system, and go stale the moment they print.
// Records and outbound documents are not stamped — a signed record IS the record,
// and a customer copy is a copy by definition.
#let doc-frame(
  doc-type: "",
  title: "",
  doc-id: none,
  kind: "record",
  uncontrolled: auto,
  landscape: false,
  subtitle: none,     // muted line under the title (a part name, a date window)
  status: none,       // content under the title — usually a row of badges
  aside: none,        // right of the title block — barcode / QR; replaces the number
  org: none,          // fallback organisation name when no `_meta` (tests)
  id-in-title: true,  // false when the body already prints the number prominently
  body,
) = {
  let org-name = _meta.at("org_name", default: none)
  if org-name == none { org-name = org }
  let logo = _meta.at("logo", default: none)
  let printed = _meta.at("printed_at", default: none)
  let stamp = if uncontrolled == auto { kind == "shop" } else { uncontrolled }

  let lead = {
    set text(size: 7.5pt, fill: muted, font: sans-font)
    grid(
      columns: (1fr, auto),
      if stamp [
        #text(weight: "bold", fill: warn, tracking: 0.6pt)[UNCONTROLLED WHEN PRINTED]
        — check the system before relying on this copy.
      ] else [],
      if printed != none [Printed #printed] else [],
    )
  }

  show: page-setup.with(
    title: doc-type,
    doc-id: doc-id,
    classification: CLASSIFICATION.at(kind),
    flipped: landscape,
    footer-lead: if stamp or printed != none { lead } else { none },
  )

  // Shop sheets are read on the floor, through scratched safety glasses: sans body,
  // no justification. Records keep the house serif.
  set text(font: sans-font) if kind == "shop"
  set par(justify: false) if kind == "shop"

  // ── Brand row ──────────────────────────────────────────────────────────────
  grid(
    columns: (1fr, auto),
    align: (left + horizon, right + horizon),
    {
      if logo != none {
        box(baseline: 30%, image(bytes(logo), height: 0.42in))
        h(8pt)
      }
      text(size: 10pt, weight: "semibold", font: sans-font, fill: ink)[#if org-name != none [#org-name]]
    },
    text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[#upper(doc-type)],
  )
  v(-4pt)
  line(length: 100%, stroke: 0.9pt + ink)
  v(6pt)

  // ── Title block ────────────────────────────────────────────────────────────
  grid(
    columns: (1fr, auto),
    column-gutter: 18pt,
    align: (left + horizon, right + horizon),
    {
      text(size: 20pt, weight: "bold", font: sans-font)[#title]
      if subtitle != none {
        v(-6pt)
        text(size: 10pt, fill: muted, font: sans-font)[#subtitle]
      }
      if status != none {
        v(0pt)
        status
      }
    },
    if aside != none { aside }
    else if id-in-title and doc-id != none and doc-id != title {
      text(size: 12pt, weight: "bold", font: mono-font)[#doc-id]
    },
  )
  // The one gap between title block and content — templates add none of their own.
  v(12pt)
  body
}

// ── Shared closing parts ─────────────────────────────────────────────────────

// Wet-ink signature block. `roles` is an array of strings, or of dictionaries
// (role:, hint:, name:, caption:) — `hint` says what the signature attests, `name`
// pre-prints who is expected to sign, `caption` replaces "Name · Signature · Date"
// under the line (a receiver also notes the condition on arrival). One style for
// every sheet: role, space to sign, a rule, and the caption.
#let signature-block(roles, heading: "Signatures", intro: none, gap: 26pt) = block(breakable: false)[
  #if heading != none [= #heading]
  #if intro != none { text(size: 9.5pt)[#intro]; v(6pt) }
  #let rs = roles.map(r => if r == none or type(r) != str { r } else { (role: r) })
  // Two rows — labels, then lines — so every signing line sits at the same height
  // even when one role pre-prints a name and its neighbour doesn't. `none` holds a
  // column open, so a lone signature keeps the width it has in a row of three.
  #grid(
    columns: (1fr,) * rs.len(),
    column-gutter: 20pt,
    ..rs.map(r => if r == none { [] } else {
      text(size: 9.5pt, weight: "semibold", font: sans-font)[#r.role]
      if r.at("hint", default: none) != none {
        linebreak()
        text(size: 8.5pt, fill: muted, font: sans-font)[#r.hint]
      }
      if r.at("name", default: none) != none {
        linebreak()
        text(size: 9pt, fill: muted)[#r.name]
      }
    }),
    ..rs.map(r => if r == none { [] } else {
      v(gap)
      line(length: 100%, stroke: 0.5pt + ink)
      v(-6pt)
      text(size: 8pt, fill: muted, font: sans-font)[#r.at("caption", default: "Name · Signature · Date")]
    }),
  )
]

// End-of-document marker, with an optional closing statement under it.
#let end-marker(label, note: none) = block(breakable: false, width: 100%)[
  #v(10pt)
  #align(center)[
    #line(length: 60%, stroke: 0.5pt + rule)
    #v(2pt)
    #text(size: 9pt, fill: muted, font: sans-font, tracking: 1pt)[#upper(label)]
    #if note != none {
      v(0pt)
      text(size: 8pt, fill: muted)[#note]
    }
  ]
]

// A banner for a condition the reader must see before using the sheet — a stale
// plan, a shortage. `tone` is a palette tone ("warn" | "bad" | "accent").
#let notice(body, tone: "warn") = {
  let pair = (warn: (warn, warn-tint), bad: (bad, bad-tint), accent: (accent, accent-tint)).at(tone)
  block(fill: pair.last(), stroke: 0.75pt + pair.first(), radius: 3pt, inset: (x: 8pt, y: 5pt), width: 100%)[
    #text(size: 9pt, fill: pair.first(), font: sans-font)[#body]
  ]
}

// Nothing to list — said plainly, in the space the table would have taken.
#let empty-state(body) = block(stroke: (paint: rule, thickness: 0.6pt, dash: "dashed"),
                                radius: 3pt, inset: 14pt, width: 100%)[
  #align(center, text(size: 9.5pt, fill: muted, font: sans-font)[#body])
]

// A heading over one group of rows (a work centre, a requirements section): the
// group name, and a count on the right. Sits directly on the report-table below it.
#let group-band(title, count: none) = block(
  fill: accent, inset: (x: 8pt, y: 5pt), radius: (top-left: 3pt, top-right: 3pt),
  width: 100%, below: 0pt, above: 12pt, breakable: false,
)[
  #grid(columns: (1fr, auto),
    text(weight: "semibold", fill: white, font: sans-font, size: 10pt)[#title],
    if count != none { text(fill: accent-tint, font: sans-font, size: 9pt)[#count] })
]

// Headline numbers across the top of a summary sheet. `stats` is an array of
// (value:, label:, tone:) — tone is optional and colours the value.
#let stat-panel(stats) = info-box[
  #grid(
    columns: (1fr,) * stats.len(),
    column-gutter: 12pt,
    ..stats.map(s => align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font,
            fill: (ok: ok, warn: warn, bad: bad, accent: accent, plain: ink).at(s.at("tone", default: "plain")))[#s.value]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[#s.label]
    ]),
  )
]
