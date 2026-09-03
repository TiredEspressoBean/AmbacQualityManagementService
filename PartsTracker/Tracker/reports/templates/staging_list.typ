// Staging List — the materials handler's walk sheet.
// Context: Tracker/reports/adapters/staging_list.py → StagingListContext
//
// Read on the floor with a cart, so: one block per station, jobs in the order they
// arrive, a tick box per job, and shortages called out where the picker will see them
// BEFORE walking to an empty bin.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#let station-header(name, jobs, short) = {
  v(8pt)
  block(
    fill: rgb("#1e40af"), inset: (x: 8pt, y: 5pt),
    radius: (top-left: 4pt, top-right: 4pt), width: 100%,
  )[
    #grid(columns: (1fr, auto),
      text(weight: "semibold", fill: white, font: sans-font, size: 10pt)[#name],
      text(fill: rgb("#bfdbfe"), font: sans-font, size: 9pt)[
        #jobs job#if jobs != 1 [s]#if short > 0 [ · #short short]
      ])
  ]
}

// An empty box the handler ticks. Pre-ticked when the system already knows the job
// was staged, so a reprint mid-shift doesn't lose what's already done.
#let tick(done) = box(
  width: 12pt, height: 12pt, stroke: 0.6pt + rule, radius: 2pt,
)[#if done [#align(center + horizon)[#text(size: 9pt, weight: "bold")[✓]]]]

#show: page-setup.with(
  title: "Staging List",
  classification: "Internal — Shop Floor",
)

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[STAGING LIST]
  #v(2pt)
  #text(size: 20pt, weight: "bold", font: sans-font)[
    #if data.station_filter != "" [#data.station_filter] else [All stations]
  ]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font)[
    #data.window_from — #data.window_to (next #data.window_hours h) · printed #data.generated_date
  ]
]

#v(10pt)

#if data.is_stale [
  #block(fill: rgb("#fffbeb"), stroke: 0.5pt + rgb("#f59e0b"), inset: 7pt,
         radius: 3pt, width: 100%)[
    #text(size: 9pt)[
      *Schedule is stale* — these times may have moved. Confirm before staging to them.
    ]
  ]
  #v(6pt)
]

#if data.note != "" [
  #block(fill: rgb("#f1f5f9"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 10pt)[#data.note]
  ]
] else if data.stations.len() == 0 [
  #block(fill: rgb("#f1f5f9"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 10pt)[Nothing scheduled in this window.]
  ]
] else [
  #for station in data.stations [
    #station-header(station.name, station.job_count, station.short_count)

    #for job in station.jobs [
      #block(stroke: (x: 0.5pt + rule, bottom: 0.5pt + rule), inset: (x: 8pt, y: 6pt),
             width: 100%, breakable: false)[
        #grid(columns: (auto, 1fr, auto), column-gutter: 8pt,
          align(horizon)[#tick(job.staged)],
          [
            #text(weight: "semibold", font: mono-font, size: 10pt)[#job.erp_id]
            #h(6pt)
            #text(size: 9pt, fill: muted, font: sans-font)[#job.step_name]
            #if job.part_type != "" [
              #text(size: 9pt, fill: muted)[ · #job.part_type]
            ]
          ],
          align(right)[
            #text(size: 9pt, weight: "semibold")[#job.units unit#if job.units != 1 [s]]
            #linebreak()
            #text(size: 8.5pt, fill: muted, font: sans-font)[#job.starts_at]
          ],
        )

        #if job.materials.len() > 0 [
          #v(4pt)
          #for m in job.materials [
            #grid(columns: (1.6fr, 0.4fr, 1.6fr), column-gutter: 8pt,
              text(size: 9pt)[#m.material],
              align(right)[#text(size: 9pt, weight: "semibold")[#m.qty]],
              // Shortage wins the cell: better to read it here than at the bin.
              if m.is_short {
                text(size: 8.5pt, fill: bad, weight: "semibold")[SHORT #m.short_qty]
              } else if m.lots != "" {
                text(size: 8.5pt, fill: muted, font: mono-font)[
                  #m.lots#if m.storage_location != "" [ · #m.storage_location]
                ]
              } else {
                text(size: 8.5pt, fill: muted)[—]
              },
            )
          ]
        ] else [
          #v(2pt)
          #text(size: 8.5pt, fill: muted, style: "italic")[
            No material consumed at this step.
          ]
        ]

        #if job.fixtures != "" [
          #v(3pt)
          #text(size: 8.5pt, fill: muted, font: sans-font)[Tooling: #job.fixtures]
        ]
      ]
    ]
  ]
]

#if data.unmapped.len() > 0 [
  #v(12pt)
  #block(fill: rgb("#eff6ff"), stroke: 0.5pt + rgb("#3b82f6"), inset: 8pt,
         radius: 3pt, width: 100%)[
    #text(size: 9pt, weight: "semibold")[Components not mapped to a step]
    #v(2pt)
    #text(size: 8.5pt, fill: muted)[
      Needed, but the BOM doesn't say at which operation — so they can't be put on a
      bench list. Set "consumed at step" on the BOM line.
    ]
    #v(3pt)
    #for u in data.unmapped [
      #text(size: 8.5pt, font: mono-font)[#u]
      #linebreak()
    ]
  ]
]

#v(14pt)
#divider()
#v(6pt)
#grid(columns: (1fr, 1fr), column-gutter: 24pt,
  text(size: 9pt, fill: muted)[
    Staged by: #box(width: 120pt, stroke: (bottom: 0.5pt + rule))[]
  ],
  text(size: 9pt, fill: muted)[
    Time: #box(width: 100pt, stroke: (bottom: 0.5pt + rule))[]
  ],
)
#v(4pt)
#text(size: 8.5pt, fill: muted, style: "italic")[
  #data.total_jobs job#if data.total_jobs != 1 [s] on this sheet#if data.total_short > 0 [, #data.total_short short].
  Lots listed are the ones the system will record as consumed — pull those.
]
