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

#import "_common/kitting.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Pick Sheet",
  title: if data.station_filter != "" [#data.station_filter] else [All stations],
  kind: "shop",
  subtitle: window-line(data),
  org: data.tenant_name,
)

#stale-notice(data, "pulling")
#round-empty(data, data.rows.len() > 0, [Nothing to pull in this window.])

#if data.note == "" and data.rows.len() > 0 [
  = #data.total_lines material#if data.total_lines != 1 [s] → #data.total_kits kit#if data.total_kits != 1 [s]

  #if data.total_short > 0 [
    #v(-2pt)
    #notice[
      *#data.total_short of #data.total_lines lines are short.* Pull what exists and
      flag the rest — the kits below will be incomplete.
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

#unmapped-box(data.unmapped)

#v(10pt)

#signature-block(
  ((role: "Pulled by", caption: "Name · Date"), (role: "Sorted to kits by", caption: "Name · Date"), none),
  heading: none, gap: 18pt,
)

#v(8pt)

#footer-note[
  Quantities are the combined need for every kit in this window. Split each row to its
  kits as listed before delivering — the lot that went into each unit is recorded on
  that kit's sheet, not here.
]
