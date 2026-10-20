// Parts shared by the two sheets of a kitting round: the Pick Sheet (one walk of the
// shelves, pick_sheet.typ) and the Kit Sheet (the split into kits, staging_list.typ).
// Both cover the same window of the same schedule, so the window line, the stale
// warning, the empty state and the unmapped-components box are one thing said once.

#import "frame.typ": *

// "Apr 15 06:00 — Apr 15 14:00 (next 8 h)" — the frame's subtitle on both sheets.
#let window-line(data) = [#data.window_from — #data.window_to (next #data.window_hours h)]

// A schedule that has moved since it was solved. `act` is what the reader is about
// to do to it: "pulling", "staging".
#let stale-notice(data, act) = if data.is_stale {
  notice[*Schedule is stale* — these times may have moved. Confirm before #act to them.]
  v(6pt)
}

// The adapter's explanation when there is nothing to show (no active schedule, say),
// or `empty` when there simply is nothing in the window. None when there is content.
#let round-empty(data, has-content, empty) = {
  if data.note != "" { empty-state[#data.note] }
  else if not has-content { empty-state[#empty] }
}

// BOM lines these jobs need that name no operation, so they can't be assigned to a
// kit. Listed rather than dropped: a silent gap is how a kit goes out light.
#let unmapped-box(items) = if items.len() > 0 {
  v(10pt)
  block(fill: accent-tint, stroke: 0.5pt + accent, inset: 8pt, radius: 3pt, width: 100%,
        breakable: false)[
    #text(size: 9pt, weight: "semibold", font: sans-font)[Not on this sheet — components with no operation]
    #v(2pt)
    #text(size: 8.5pt, fill: muted)[
      These jobs need them, but the BOM doesn't say at which operation, so they can't be
      assigned to a kit. Set "consumed at step" on the BOM line.
    ]
    #v(3pt)
    #for u in items [
      #text(size: 8.5pt, font: mono-font)[#u]
      #linebreak()
    ]
  ]
}

// An empty box the handler ticks; pre-ticked when the system already knows it's done,
// so a reprint mid-shift doesn't lose what's finished.
#let tick(done: false) = box(width: 12pt, height: 12pt, stroke: 0.6pt + rule, radius: 2pt)[
  #if done [#align(center + horizon)[#text(size: 9pt, weight: "bold")[✓]]]
]
