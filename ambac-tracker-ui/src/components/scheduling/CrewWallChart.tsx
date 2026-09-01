/**
 * Crew wall chart — the industry-standard "who's out, when" artifact:
 * people as rows, days as columns, absence bars colored by kind. Names live
 * once in the row header (never truncated into day cells); a horizontal scan
 * answers "when is X out", a vertical scan answers "who's out Thursday".
 * Plant-wide events (closures, overtime) render as full-height column bands
 * behind the rows. Replaces the month grid at crew/station scope — a month
 * cell can't carry named absences (every absence tool leads with this form).
 */
export type WallBar = {
  key: string;
  startDay: number; // 1-based day-of-month, clipped to the viewed month
  endDay: number;
  color: string;
  title: string;    // tooltip: "PTO · Sep 3–4 · Vacation day"
  label: string;    // short text shown when the bar is wide enough (kind)
};

export type WallRow = {
  id: string;
  name: string;
  bars: WallBar[];
};

export type WallBand = {
  day: number;
  kind: "closure" | "overtime";
  title: string;
};

const BAND_STYLE: Record<WallBand["kind"], string> = {
  closure: "bg-red-500/15",
  overtime: "bg-green-500/15",
};

export function CrewWallChart({
  rows, daysInMonth, weekendDays, bands, today, selectedDays, onDayClick,
}: {
  rows: WallRow[];
  daysInMonth: number;
  /** 1-based days that fall on Sat/Sun (tinted). */
  weekendDays: Set<number>;
  bands: WallBand[];
  /** 1-based day-of-month for today, when the viewed month is the current one. */
  today: number | null;
  selectedDays: Set<number>;
  onDayClick?: (day: number) => void;
}) {
  const cols = `minmax(10rem, 12rem) repeat(${daysInMonth}, minmax(1.375rem, 1fr))`;
  const bandsByDay = new Map<number, WallBand[]>();
  for (const b of bands) {
    const list = bandsByDay.get(b.day) ?? [];
    list.push(b);
    bandsByDay.set(b.day, list);
  }

  const dayBg = (d: number) => {
    const dayBands = bandsByDay.get(d) ?? [];
    if (dayBands.some((b) => b.kind === "closure")) return BAND_STYLE.closure;
    if (dayBands.some((b) => b.kind === "overtime")) return BAND_STYLE.overtime;
    return weekendDays.has(d) ? "bg-muted/40" : "";
  };
  const dayTitle = (d: number) =>
    (bandsByDay.get(d) ?? []).map((b) => b.title).join(" · ") || undefined;

  return (
    <div className="overflow-x-auto p-2">
      {/* Header: day numbers (clickable → reuses the page's day-selection/add flow) */}
      <div className="grid" style={{ gridTemplateColumns: cols }}>
        <div />
        {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((d) => (
          <button
            key={d}
            type="button"
            onClick={onDayClick ? () => onDayClick(d) : undefined}
            title={dayTitle(d)}
            className={[
              "border-b py-1 text-center text-[11px] tabular-nums",
              dayBg(d),
              onDayClick ? "cursor-pointer hover:bg-accent/50" : "",
              selectedDays.has(d) ? "bg-primary/15 font-semibold ring-1 ring-inset ring-primary" : "",
              today === d ? "text-primary font-bold" : "text-muted-foreground",
            ].join(" ")}
          >
            {d}
          </button>
        ))}
      </div>

      {rows.length === 0 && (
        <p className="p-4 text-sm text-muted-foreground">No people in this scope.</p>
      )}

      {rows.map((r) => (
        // One grid per row: day cells and absence bars share the same explicit
        // grid row, so bars overlay cells without positioning hacks.
        <div key={r.id} className="grid items-center" style={{ gridTemplateColumns: cols, gridTemplateRows: "1.75rem" }}>
          <div className="h-full truncate border-b py-1 pr-2 text-sm" style={{ gridRow: 1, gridColumn: 1 }} title={r.name}>
            {r.name}
          </div>
          {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((d) => (
            <div
              key={d}
              title={dayTitle(d)}
              style={{ gridRow: 1, gridColumn: d + 1 }}
              className={[
                "h-full border-b border-l",
                dayBg(d),
                selectedDays.has(d) ? "bg-primary/10" : "",
                today === d ? "border-l-primary/60" : "",
              ].join(" ")}
            />
          ))}
          {r.bars.map((b) => (
            <div
              key={b.key}
              className="z-10 mx-px flex h-5 items-center overflow-hidden rounded px-1"
              style={{
                gridRow: 1,
                gridColumn: `${b.startDay + 1} / ${b.endDay + 2}`,
                backgroundColor: b.color,
              }}
              title={b.title}
            >
              {b.endDay - b.startDay >= 1 && (
                <span className="truncate text-[10px] font-medium text-white/95">{b.label}</span>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default CrewWallChart;
