// Part ID Label Batch — N × 4"×2" thermal labels, one per page.
//
// Context: Tracker/reports/adapters/part_id_label_batch.py
//            → PartIdLabelBatchContext { labels: list[PartIdLabelContext] }
//
// Each label is identical in layout to part_id_label.typ; this template
// just iterates and emits a pagebreak between entries. Kept in its own
// file so the single-part template stays zero-branching and easy to
// proof against a physical printer.

// House palette and helpers, imported rather than copied — see the note in
// part_id_label.typ. Label stock skips page-setup's `#show` rule, not its colours.
#import "_common/page-setup.typ": ink, muted, sans-font, mono-font
#import "_common/components.typ": svg-img, opt

#let data = json.decode(sys.inputs.at("data"))

#set page(width: 4in, height: 2in, margin: 0.1in)
#set text(font: sans-font, size: 9pt, fill: ink)
#set par(justify: false, leading: 0.45em)

#let render-label(label) = [
  #grid(
    columns: (1fr, 0.55in),
    column-gutter: 4pt,
    [
      #text(size: 13pt, weight: "bold", font: sans-font)[#label.part_number]
      #if label.revision != none [
        #h(4pt)
        #text(size: 9pt, fill: muted, weight: "regular")[· #label.revision]
      ]

      #v(1pt)
      #text(size: 8pt, font: mono-font)[
        #text(fill: muted)[S/N:] #h(2pt) #label.serial
      ] \
      #text(size: 7.5pt, font: sans-font)[
        #text(fill: muted)[WO:] #h(2pt) #opt(label.work_order_number)
      ]
    ],
    align(right + top)[
      #svg-img(label.qr_svg, 0.55in)
    ],
  )

  #v(2pt)

  #align(center)[
    #svg-img(label.barcode_svg, 3.5in)
  ]

  #v(1pt)

  #text(size: 6.5pt, fill: muted, font: sans-font)[
    #label.tenant_name
    #h(1fr)
    #str(label.print_date)
  ]
]

#for (idx, label) in data.labels.enumerate() {
  if idx > 0 { pagebreak() }
  render-label(label)
}
