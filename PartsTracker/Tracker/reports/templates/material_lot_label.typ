// Material Lot Label — 4"×2" labels for received lots.
//
// Context: Tracker/reports/adapters/material_lot_label.py
//            → MaterialLotLabelBatchContext { layout, labels: list[MaterialLotLabelContext] }
//
// layout "thermal": one label per 4"×2" page (Zebra-style roll, same stock as the
//                   Part ID label).
// layout "sheet":   ten labels per US Letter page, 2 × 5 — Avery 5163 / 8163
//                   geometry (0.5" top margin, 0.156" sides, 0.188" column gap).

#import "_common/page-setup.typ": ink, muted, sans-font, mono-font
#import "_common/components.typ": svg-img, opt

#let data = json.decode(sys.inputs.at("data"))

#set text(font: sans-font, size: 9pt, fill: ink)
#set par(justify: false, leading: 0.45em)

#let render-label(label) = block(width: 4in - 0.2in, height: 2in - 0.2in, breakable: false)[
  #grid(
    columns: (1fr, 0.6in),
    column-gutter: 4pt,
    [
      #text(size: 12pt, weight: "bold")[#label.item_name]
      #if label.part_number != none [
        #h(4pt) #text(size: 8pt, fill: muted, font: mono-font)[#label.part_number]
      ]
      #v(1pt)
      #text(size: 9pt, font: mono-font, weight: "bold")[
        #text(fill: muted, weight: "regular")[LOT] #h(2pt) #label.lot_number
      ] \
      #text(size: 7pt)[
        #text(fill: muted)[Supplier:] #opt(label.supplier_name)
        #if label.supplier_lot_number != none [ · #text(fill: muted)[Lot] #label.supplier_lot_number ]
      ] \
      #text(size: 7pt)[
        #text(fill: muted)[Qty:] #label.quantity
        #if label.received_as != none [ (#label.received_as)]
        #if label.heat_number != none [ · #text(fill: muted)[Heat] #label.heat_number ]
      ]
    ],
    align(right + top)[#svg-img(label.qr_svg, 0.6in)],
  )
  #v(1pt)
  #align(center)[#svg-img(label.barcode_svg, 3.5in)]
  #text(size: 6.5pt, fill: muted)[
    Recv #opt(if label.received_date != none { str(label.received_date) } else { none })
    #if label.expiration_date != none [ · #text(fill: ink, weight: "bold")[Use by #str(label.expiration_date)]]
    #h(1fr)
    #label.tenant_name · #str(label.print_date)
  ]
]

#if data.layout == "sheet" {
  set page(paper: "us-letter", margin: (top: 0.5in, bottom: 0.5in, left: 0.156in, right: 0.156in))
  // Each cell is a full 4"×2" label; the 0.1" inset matches the thermal page margin.
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
