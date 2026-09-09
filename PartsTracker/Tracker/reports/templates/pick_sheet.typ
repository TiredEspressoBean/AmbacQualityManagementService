// Pick Sheet — the shelf sweep.
//
// Context: Tracker/reports/adapters/pick_sheet.py → PickSheetContext
//
// One row per MATERIAL across every job in the window, ordered by where it lives, so
// the picker visits each bin once. Under each row sit its drops — which kit every
// portion belongs to — because a batched pull is worthless without the split.
//
// Layout:
//   1. Title block — window, station filter, counts
//   2. Shortage banner — how many lines are light, before the walk
//   3. Material rows — qty, lots, location, tick box, then the drop breakdown
//   4. Unmapped components — BOM lines with no operation, so they can't be kitted
//   5. Picked-by block

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// An empty box the picker ticks once the whole quantity is on the cart.
#let tick() = box(width: 12pt, height: 12pt, stroke: 0.6pt + rule, radius: 2pt)[]

#show: page-setup.with(
  title: "Pick Sheet",
  classification: "Internal — Shop Floor",
)

#report-title(
  [PICK SHEET],
  if data.station_filter != "" [#data.station_filter] else [All stations],
  data.tenant_name,
  title-size: 17pt,
  trailing-gap: 4pt,
  trailing: [
    #text(size: 9pt, fill: muted, font: sans-font)[
      #data.window_from — #data.window_to (next #data.window_hours h) · printed #data.generated_date
    ]
  ],
)

#v(9pt)

#if data.is_stale [
  #block(fill: warn-tint, stroke: 0.5pt + warn, inset: 5pt, radius: 3pt, width: 100%)[
    #text(size: 9pt)[
      *Schedule is stale* — these times may have moved. Confirm before pulling to them.
    ]
  ]
  #v(6pt)
]

#if data.note != "" [
  #block(fill: panel, inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 10pt)[#data.note]
  ]
] else if data.rows.len() == 0 [
  #block(fill: panel, inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 10pt)[Nothing to pull in this window.]
  ]
] else [
  = #data.total_lines material#if data.total_lines != 1 [s] → #data.total_kits kit#if data.total_kits != 1 [s]

  #if data.total_short > 0 [
    #v(-2pt)
    #block(fill: warn-tint, stroke: 0.5pt + warn, inset: 5pt, radius: 3pt, width: 100%)[
      #text(size: 9pt)[
        *#data.total_short of #data.total_lines lines are short.* Pull what exists and
        flag the rest — the kits below will be incomplete.
      ]
    ]
    #v(6pt)
  ]

  #set text(size: 9pt)
  #set par(justify: false)

  #for (idx, row) in data.rows.enumerate() [
    #block(
      breakable: false,
      fill: if calc.rem(idx, 2) == 0 { white } else { stripe },
      stroke: (bottom: 0.75pt + rule),
      inset: (x: 6pt, y: 6pt),
      width: 100%,
      spacing: 0pt,
    )[
      #grid(columns: (auto, 1fr, auto), column-gutter: 9pt,
        align(horizon)[#tick()],
        [
          #text(weight: "semibold", font: sans-font, size: 10pt)[#row.material]
          #if row.storage_location != "" [
            #h(6pt)
            #text(size: 8.5pt, fill: muted, font: sans-font)[#row.storage_location]
          ]
          #if row.lots != "" [
            #linebreak()
            #text(size: 8pt, fill: muted, font: mono-font)[#row.lots]
          ]
        ],
        align(right + horizon)[
          #text(size: 12pt, weight: "bold")[#row.qty]
          #if row.is_short [
            #linebreak()
            #text(size: 8.5pt, fill: bad, weight: "semibold")[SHORT #row.short_qty]
          ]
        ],
      )

      // The sortation instruction. This is the half that makes a batched pull
      // usable: 200 seals with no split is a slower way to fail.
      #v(4pt)
      #pad(left: 21pt)[
        #for d in row.drops [
          #grid(columns: (auto, 1fr), column-gutter: 8pt,
            text(size: 8.5pt, weight: "semibold", font: mono-font)[#d.qty],
            text(size: 8.5pt, fill: muted, font: sans-font)[
              → #d.erp_id · #d.step_name · #d.station#if d.staged [ #h(4pt) #tone-badge("STAGED", "ok")]
            ],
          )
        ]
      ]
    ]
  ]
]

#if data.unmapped.len() > 0 [
  #v(10pt)
  #block(fill: accent-tint, stroke: 0.5pt + accent, inset: 7pt, radius: 3pt, width: 100%)[
    #text(size: 9pt, weight: "semibold")[Not on this sheet — components with no operation]
    #v(2pt)
    #text(size: 8.5pt, fill: muted)[
      These jobs need them, but the BOM doesn't say at which operation, so they can't be
      assigned to a kit. Set "consumed at step" on the BOM line.
    ]
    #v(3pt)
    #for u in data.unmapped [
      #text(size: 8.5pt, font: mono-font)[#u]
      #linebreak()
    ]
  ]
]

#v(10pt)

#grid(
  columns: (1fr, 1fr),
  column-gutter: 18pt,
  ..("Pulled by", "Sorted to kits by").map(role => [
      #text(size: 8.5pt, fill: muted, font: sans-font)[#role]
      #v(9pt)
      #box(width: 100%, stroke: (bottom: 0.5pt + rule))[]
      #v(2pt)
      #text(size: 8pt, fill: muted, font: sans-font)[Date: #box(width: 1fr, stroke: (bottom: 0.5pt + rule))]
    ])
)

#v(8pt)

#footer-note[
  Quantities are the combined need for every kit in this window. Split each row to its
  kits as listed before delivering — the lot that went into each unit is recorded on
  that kit's sheet, not here.
]
