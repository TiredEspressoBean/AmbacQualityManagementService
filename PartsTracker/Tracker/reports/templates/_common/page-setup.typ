// Shared page setup and typography for all QMS reports.
//
// Import from a template with:
//   #import "_common/page-setup.typ": *
//
// Then call:
//   #show: page-setup.with(title: "My Report")
//
// Or use the palette / typography helpers directly.

// ----------------------------------------------------------------------------
// Palette — tuned for SHOP-FLOOR print survivability: high contrast, dark
// borders, all colors readable in grayscale and on a smudged photocopy.
// (Screen-light slate-on-white did not survive the floor.)
// ----------------------------------------------------------------------------
#let ink        = rgb("#0f172a")   // body text (near-black)
#let muted      = rgb("#334155")   // labels, captions — darkened for legibility
#let rule       = rgb("#64748b")   // table borders, separators — dark enough to copy
#let accent     = rgb("#1e3a8a")   // links, emphasis (deeper blue)
#let ok         = rgb("#14532d")   // pass / approved (deep green)
#let warn       = rgb("#854d0e")   // draft / marginal (deep amber)
#let bad        = rgb("#7f1d1d")   // fail / rejected (deep red)

// Fill tints — bold enough to survive the shop floor / a photocopier (see the
// palette note above). Shared so every template pulls the same shades.
#let panel      = rgb("#f1f5f9")   // boxed info panels (info-box)
#let band       = rgb("#d8e1ec")   // table header / section band
#let stripe     = rgb("#eaeef4")   // zebra alternate row
#let chip       = rgb("#dbe6f2")   // captured-value highlight (as-built)

// ----------------------------------------------------------------------------
// Typography
// ----------------------------------------------------------------------------
#let body-font = ("Noto Serif", "Liberation Serif", "Libertinus Serif")
#let sans-font = ("Noto Sans", "Liberation Sans", "DejaVu Sans")
#let mono-font = ("Noto Sans Mono", "DejaVu Sans Mono")

// ----------------------------------------------------------------------------
// Page setup helper
// Wraps the document with standard page margins, font, header, footer.
// ----------------------------------------------------------------------------
// NOTE: `title` must be a named parameter (not positional) because
// Typst's .with() partial application has a known issue (#916, #3329)
// where mixing positional args with .with(name: value) causes
// "missing argument: body" errors in #show: rules.
#let page-setup(
  title: "",
  doc-id: none,
  classification: "Controlled Document",
  body,
) = {
  set document(title: title)
  set page(
    "us-letter",
    margin: (top: 0.85in, bottom: 0.85in, left: 0.9in, right: 0.9in),
    header: context {
      if counter(page).get().first() > 1 [
        #set text(size: 8pt, fill: muted, font: sans-font)
        #grid(columns: (1fr, 1fr),
          [#title],
          align(right)[#if doc-id != none [#doc-id] else []])
        #v(-8pt)
        #line(length: 100%, stroke: 0.6pt + rule)
      ]
    },
    footer: context {
      set text(size: 8pt, fill: muted, font: sans-font)
      line(length: 100%, stroke: 0.6pt + rule)
      v(2pt)
      grid(columns: (1fr, 1fr, 1fr),
        [#classification],
        align(center)[#if doc-id != none [#doc-id] else []],
        align(right)[
          Page #counter(page).display("1") of #counter(page).final().first()
        ])
    },
  )
  set text(font: body-font, size: 10.5pt, fill: ink)
  set par(justify: true, leading: 0.65em)
  show heading: set text(font: sans-font, weight: "semibold", fill: ink)
  show heading.where(level: 1): it => {
    v(4pt); it; v(-2pt); line(length: 100%, stroke: 0.9pt + rule); v(4pt)
  }
  body
}
