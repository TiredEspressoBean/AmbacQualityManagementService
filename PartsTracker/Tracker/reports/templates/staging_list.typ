// Kit Sheet — one kit per (work order, operation), grouped by the bench it goes to.
// Context: Tracker/reports/adapters/staging_list.py → StagingListContext
//
// The second half of the round. The Pick Sheet (pick_sheet.typ) pulls everything from
// the shelves in one walk; this is how that pile gets split and delivered.
//
// A kit holds only what ITS operation consumes, so it is delivered, consumed at the
// bench, and its container comes back — it never travels with the product. What
// travels is the unit and its traveler.
//
// The lot write-in lives HERE, not on the Pick Sheet. Batch-picking commingles by
// construction: 200 seals pulled from three lots, split across twelve kits. The only
// place the record can honestly say which lot went into which unit is at the split.
//
// Grouped by station because that is the delivery walk; the KIT is still the unit,
// and two work orders at one bench are two kits with two labels.

#import "_common/kitting.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Kit Sheet",
  title: if data.station_filter != "" [#data.station_filter] else [All stations],
  kind: "shop",
  subtitle: window-line(data),
  org: data.tenant_name,
)

#stale-notice(data, "staging")
#round-empty(data, data.stations.len() > 0, [Nothing scheduled in this window.])

#if data.note == "" and data.stations.len() > 0 [
  #for station in data.stations [
    // A job that consumes nothing and needs no tooling has no kit. Printing a block
    // per such job pads the sheet with entries the handler can only skip — and worse,
    // "no material consumed at this step" reads the same whether that is genuinely
    // true or the BOM simply never said where the parts go (see the unmapped box).
    // Count them instead; the bench still learns the work is coming from the board.
    #let kits = station.jobs.filter(j => j.materials.len() > 0 or j.fixtures != "")
    #let nothing = station.jobs.len() - kits.len()

    // A bench with no kits gets no block at all — a delivery sheet listing stations
    // you aren't delivering to is just more paper to page past.
    #if kits.len() > 0 [
    #group-band(station.name,
      count: [#kits.len() job#if kits.len() != 1 [s]#if station.short_count > 0 [ · #station.short_count short]])

    #for job in kits [
      #block(stroke: 0.5pt + rule, inset: (x: 8pt, y: 6pt), width: 100%,
             breakable: false, above: 0pt, below: 0pt)[
        #grid(columns: (auto, 1fr, auto), column-gutter: 8pt,
          align(horizon)[#tick(done: job.staged)],
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
          #grid(columns: (1.5fr, 0.35fr, 1.35fr, 1.1fr), column-gutter: 8pt,
            text(size: 7.5pt, fill: muted, font: sans-font, tracking: 0.4pt)[MATERIAL],
            [],
            text(size: 7.5pt, fill: muted, font: sans-font, tracking: 0.4pt)[PULL FROM],
            text(size: 7.5pt, fill: muted, font: sans-font, tracking: 0.4pt)[LOT PUT IN KIT],
          )
          #v(2pt)
          #for m in job.materials [
            #grid(columns: (1.5fr, 0.35fr, 1.35fr, 1.1fr), column-gutter: 8pt,
              text(size: 9pt)[#m.material],
              align(right)[#text(size: 9pt, weight: "semibold")[#m.qty]],
              // Shortage wins the cell: better to read it here than at the bin.
              if m.is_short {
                // Short, but partial stock may still exist — say where, or the
                // picker can't fetch the part they could have had.
                [
                  #text(size: 8.5pt, fill: bad, weight: "semibold")[SHORT #m.short_qty]
                  #if m.lots != "" [
                    #linebreak()
                    #text(size: 8pt, fill: muted, font: mono-font)[
                      #m.lots#if m.storage_location != "" [ · #m.storage_location]
                    ]
                  ]
                ]
              } else if m.lots != "" {
                text(size: 8.5pt, fill: muted, font: mono-font)[
                  #m.lots#if m.storage_location != "" [ · #m.storage_location]
                ]
              } else {
                text(size: 8.5pt, fill: muted)[—]
              },
              // What actually went in. The Pick Sheet named the lots the combined
              // draw would take; only here, at the split, can anyone say which lot
              // reached which unit — and that is the claim the traceability record
              // makes. Blank so the handler writes what they really put in the tote.
              align(horizon)[
                #box(width: 100%, height: 11pt, stroke: (bottom: 0.5pt + rule))[]
              ],
            )
          ]
        ] else [
          // Reached only when the kit is tooling-only — a material-less, tooling-less
          // job never gets a block at all.
          #v(2pt)
          #text(size: 8.5pt, fill: muted, style: "italic")[Tooling only.]
        ]

        #if job.fixtures != "" [
          #v(3pt)
          #text(size: 8.5pt, fill: muted, font: sans-font)[Tooling: #job.fixtures]
        ]
      ]
    ]

    // Said, not silently dropped: a handler who knows six more jobs land here can
    // tell "nothing to stage" apart from "this sheet missed them".
    #if nothing > 0 [
      #block(inset: (x: 8pt, y: 5pt), width: 100%)[
        #text(size: 8.5pt, fill: muted, style: "italic")[
          #nothing further job#if nothing != 1 [s] scheduled here
          need#if nothing == 1 [s] nothing staged.
        ]
      ]
    ]
    ]
  ]
]

#unmapped-box(data.unmapped)

#v(10pt)
#signature-block(
  ((role: "Staged by", caption: "Name · Time"), none, none),
  heading: none, gap: 18pt,
)
#v(8pt)
#footer-note[
  // Kits printed, not jobs scheduled: a job with nothing to stage has no block, and is
  // counted under its station instead.
  #let kits = data.stations.map(st => st.jobs.filter(j => j.materials.len() > 0 or j.fixtures != "").len()).sum(default: 0)
  #kits kit#if kits != 1 [s] on this sheet#if data.total_short > 0 [, #data.total_short short].
  Lots listed are the ones the system will record as consumed — pull those.
]
