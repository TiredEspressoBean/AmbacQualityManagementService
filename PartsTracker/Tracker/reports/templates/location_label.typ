// Location Label — 4"×2" label for a shelf, cage, rack or bin.
//
// Context: Tracker/reports/adapters/location_label.py
//            → LocationLabelBatchContext { layout, labels: list[LocationLabelContext] }
//
// The barcode carries "LOC:<name>" so a scanner can tell a location from a lot or a
// serial. Layouts as material_lot_label.typ: "thermal" one per page, "sheet" ten per
// Letter page (Avery 5163 geometry).

#import "_common/page-setup.typ": ink, muted, sans-font, mono-font
#import "_common/components.typ": svg-img

#let data = json.decode(sys.inputs.at("data"))

#set text(font: sans-font, size: 9pt, fill: ink)
#set par(justify: false, leading: 0.45em)

#let render-label(label) = block(width: 4in - 0.2in, height: 2in - 0.2in, breakable: false)[
  #grid(
    columns: (1fr, 0.6in),
    column-gutter: 4pt,
    [
      #text(size: 7pt, fill: muted, tracking: 1pt)[LOCATION] \
      #text(size: 20pt, weight: "bold")[#label.name]
      #if label.description != none [ \ #text(size: 7.5pt, fill: muted)[#label.description] ]
    ],
    align(right + top)[#svg-img(label.qr_svg, 0.6in)],
  )
  #v(1fr)
  #align(center)[#svg-img(label.barcode_svg, 3.5in)]
  #text(size: 6.5pt, fill: muted)[#h(1fr) #label.tenant_name · #str(label.print_date)]
]

#if data.layout == "sheet" {
  set page(paper: "us-letter", margin: (top: 0.5in, bottom: 0.5in, left: 0.156in, right: 0.156in))
  let cells = data.labels.map(l => box(width: 4in, height: 2in, inset: 0.1in, render-label(l)))
  for (i, chunk) in cells.chunks(10).enumerate() {
    if i > 0 { pagebreak() }
    grid(columns: (4in, 4in), column-gutter: 0.188in, row-gutter: 0in, ..chunk)
  }
} else {
  set page(width: 4in, height: 2in, margin: 0.1in)
  for (idx, label) in data.labels.enumerate() {
    if idx > 0 { pagebreak() }
    render-label(label)
  }
}
