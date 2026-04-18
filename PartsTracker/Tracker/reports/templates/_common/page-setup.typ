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
// Palette — deliberately muted for print, all colors readable in grayscale.
// ----------------------------------------------------------------------------
#let ink        = rgb("#0f172a")   // body text
#let muted      = rgb("#475569")   // labels, captions
#let rule       = rgb("#cbd5e1")   // table borders, separators
#let accent     = rgb("#1e40af")   // links, emphasis
#let ok         = rgb("#166534")   // pass / approved
#let warn       = rgb("#92400e")   // draft / marginal
#let bad        = rgb("#991b1b")   // fail / rejected

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
        #line(length: 100%, stroke: 0.3pt + rule)
      ]
    },
    footer: context {
      set text(size: 8pt, fill: muted, font: sans-font)
      line(length: 100%, stroke: 0.3pt + rule)
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
    v(4pt); it; v(-2pt); line(length: 100%, stroke: 0.5pt + rule); v(4pt)
  }
  body
}
