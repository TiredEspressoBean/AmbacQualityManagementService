// Smoke test template for the Typst pipeline.
// Exercises: context injection, import resolution, fonts, basic markup,
// and a vendored Universe package (cetz) to prove package resolution works.
//
// Context shape:
//   { "name": str, "number": int }

#import "_common/page-setup.typ": *
#import "@preview/cetz:0.3.2": canvas, draw

#let data = json.decode(sys.inputs.at("data"))

#show: page-setup.with(
  title: "Typst Pipeline Smoke Test",
  doc-id: "SMOKE-TEST-001",
)

= Hello, #data.name

This is a smoke test of the Typst PDF pipeline.

#v(6pt)

== Verification checks

- *Context injected via sys.inputs:* name = "#data.name", number = #data.number
- *`_common/page-setup.typ` imported:* page has header and footer on subsequent pages
- *Body font loaded:* this paragraph renders in a serif face (Noto Serif or fallback)
- *Sans font loaded:* this heading renders in #text(font: sans-font)[sans]
- *Monospace font loaded:* #text(font: mono-font)[inline monospace]
- *Palette loaded:* #text(fill: ok)[ok], #text(fill: warn)[warn], #text(fill: bad)[bad]

#v(8pt)

== Fonts in use

This paragraph is in the body font: a serif face intended for compliance
document body text. Quick brown fox jumps over the lazy dog.

#text(font: sans-font)[
  This paragraph is in the sans font: used for headings, labels, and
  UI-adjacent elements. Quick brown fox jumps over the lazy dog.
]

#text(font: mono-font)[
  INJ-2500-0847  \
  0123456789  \
  this is monospace
]

#v(8pt)

== CeTZ package test

Proves `@preview/cetz` resolves from the vendored package cache:

#align(center)[
  #canvas(length: 1cm, {
    import draw: *
    rect((0, 0), (7, 1.2), fill: rgb("#dbeafe"), stroke: 0.5pt + ink, radius: 3pt)
    // Circles on the left, text to the right so they don't overlap
    circle((0.5, 0.6), radius: 0.25, fill: ok, stroke: none)
    circle((1.3, 0.6), radius: 0.25, fill: warn, stroke: none)
    circle((2.1, 0.6), radius: 0.25, fill: bad, stroke: none)
    content((4.55, 0.6), text(font: sans-font, size: 10pt)[
      cetz rendered this rectangle
    ])
  })
]

#v(8pt)

== Pagination test

The following text spans multiple pages (with headers/footers) to verify
the page-setup helper works correctly.

#for i in range(1, 8) [
  This is paragraph #i of the pagination test. Lorem ipsum dolor sit
  amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
  labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
  exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
  Duis aute irure dolor in reprehenderit in voluptate velit esse cillum
  dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
  proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

  #v(4pt)
]
