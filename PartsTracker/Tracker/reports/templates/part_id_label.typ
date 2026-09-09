// Part ID Label / WIP Tag — 4"×2" thermal label.
//
// Context: Tracker/reports/adapters/part_id_label.py → PartIdLabelContext
//
// Compliance: ISO 9001 §8.5.2 — product identification.
//
// This is a PERMANENT label. It stays with the part for its whole life.
// Inspection status and current step are NOT included — they change over
// time, and a stale label is worse than none. Status is conveyed by
// stickers/stamps/containers on the shop floor.
//
// Layout (printable area ≈ 288pt × 144pt after 0.1in margins):
//
//   ┌──────────────────────────────────┬───────┐
//   │ PART NUMBER       · Rev N        │  QR   │
//   │ S/N: serial                      │  0.6" │
//   │ WO: xxxx                         │       │
//   ├──────────────────────────────────┴───────┤
//   │ ████ Code 128 barcode ████████████████   │
//   │ tenant · date (muted 7pt)                │
//   └──────────────────────────────────────────┘
//
// DO NOT import page-setup.typ — labels use custom page sizes.

// ----------------------------------------------------------------------------
// Palette & typography
//
// Imported, not copied. A label prints on label stock, so it deliberately skips
// page-setup's `#show` rule (page geometry, header/footer) — but it should still
// use the house colours. The previous local copy had drifted: it kept the
// original screen-light muted/rule, missing the later darkening of the shared
// palette for shop-floor legibility. Labels go on parts, which is exactly where
// that fix matters most.
// ----------------------------------------------------------------------------

#import "_common/page-setup.typ": ink, muted, rule, sans-font, mono-font

// ----------------------------------------------------------------------------
// Data
// ----------------------------------------------------------------------------

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Page — custom label size
// ----------------------------------------------------------------------------

#set page(width: 4in, height: 2in, margin: 0.1in)
#set text(font: sans-font, size: 9pt, fill: ink)
#set par(justify: false, leading: 0.45em)

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

// svg-img (barcode/QR) and opt (value-or-em-dash) come from the shared kit.
#import "_common/components.typ": svg-img, opt

// ----------------------------------------------------------------------------
// Label body — everything in one flow to avoid overflow to second page
// ----------------------------------------------------------------------------

// Top section: two columns (part info | QR code)
#grid(
  columns: (1fr, 0.55in),
  column-gutter: 4pt,

  // Left cell: part number + revision + serial + WO
  [
    #text(size: 13pt, weight: "bold", font: sans-font)[#data.part_number]
    #if data.revision != none [
      #h(4pt)
      #text(size: 9pt, fill: muted, weight: "regular")[· #data.revision]
    ]

    #v(1pt)
    #text(size: 8pt, font: mono-font)[
      #text(fill: muted)[S/N:] #h(2pt) #data.serial
    ] \
    #text(size: 7.5pt, font: sans-font)[
      #text(fill: muted)[WO:] #h(2pt) #opt(data.work_order_number)
    ]
  ],

  // Right cell: QR code
  align(right + top)[
    #svg-img(data.qr_svg, 0.55in)
  ],
)

#v(2pt)

// Middle section: barcode (centered, wide)
#align(center)[
  #svg-img(data.barcode_svg, 3.5in)
]

#v(1pt)

// Footer: tenant + date (muted, tiny)
#text(size: 6.5pt, fill: muted, font: sans-font)[
  #data.tenant_name
  #h(1fr)
  #str(data.print_date)
]
