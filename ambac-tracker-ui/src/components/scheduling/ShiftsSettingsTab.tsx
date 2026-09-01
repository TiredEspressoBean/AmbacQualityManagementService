// Work-hours (Shift calendar) editor — the tab in the scheduling settings dialog.
// The solver's working windows are derived from these shifts, including their
// standing daily breaks (break_windows): the 09:00 facility break and lunch are
// shift properties subtracted every day, not calendar events.
import { useEffect, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useShifts, useSaveShift, useDeleteShift } from "@/hooks/useScheduling";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]; // index = day number 0..6

type BreakWindow = { start: string; end: string }; // "HH:MM"

type Row = {
  key: string;        // stable local key (id or draft-n)
  id?: string;        // undefined for a not-yet-saved draft
  name: string;
  code: string;
  start_time: string; // "HH:MM"
  end_time: string;   // "HH:MM"
  days: number[];
  breaks: BreakWindow[];
  is_active: boolean;
};

const hhmm = (t: string | undefined) => (t ? t.slice(0, 5) : "");
const parseDays = (s: string | undefined) =>
  (s ?? "").split(",").map((x) => x.trim()).filter(Boolean).map(Number).filter((n) => n >= 0 && n <= 6);
const parseBreaks = (v: unknown): BreakWindow[] =>
  Array.isArray(v)
    ? v
        .map((b) => ({ start: hhmm((b as BreakWindow)?.start), end: hhmm((b as BreakWindow)?.end) }))
        .filter((b) => b.start && b.end)
    : [];

let draftSeq = 0;

export function ShiftsSettingsTab() {
  const { data, isLoading } = useShifts();
  const save = useSaveShift();
  const del = useDeleteShift();
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    const list = ((data as any)?.results ?? data ?? []) as any[];
    if (!Array.isArray(list)) return;
    setRows(
      list.map((s) => ({
        key: s.id,
        id: s.id,
        name: s.name ?? "",
        code: s.code ?? "",
        start_time: hhmm(s.start_time),
        end_time: hhmm(s.end_time),
        days: parseDays(s.days_of_week),
        breaks: parseBreaks(s.break_windows),
        is_active: s.is_active ?? true,
      }))
    );
  }, [data]);

  const patch = (key: string, upd: Partial<Row>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...upd } : r)));

  const toggleDay = (key: string, day: number) =>
    setRows((rs) =>
      rs.map((r) =>
        r.key === key
          ? { ...r, days: r.days.includes(day) ? r.days.filter((d) => d !== day) : [...r.days, day].sort() }
          : r
      )
    );

  const patchBreak = (key: string, i: number, upd: Partial<BreakWindow>) =>
    setRows((rs) =>
      rs.map((r) =>
        r.key === key
          ? { ...r, breaks: r.breaks.map((b, bi) => (bi === i ? { ...b, ...upd } : b)) }
          : r
      )
    );

  const addBreak = (key: string) =>
    setRows((rs) =>
      rs.map((r) =>
        r.key === key ? { ...r, breaks: [...r.breaks, { start: "09:00", end: "09:15" }] } : r
      )
    );

  const removeBreak = (key: string, i: number) =>
    setRows((rs) =>
      rs.map((r) => (r.key === key ? { ...r, breaks: r.breaks.filter((_, bi) => bi !== i) } : r))
    );

  const addRow = () =>
    setRows((rs) => [
      ...rs,
      {
        key: `draft-${draftSeq++}`,
        name: "",
        code: "",
        start_time: "06:00",
        end_time: "18:00",
        days: [0, 1, 2, 3, 4],
        breaks: [
          { start: "09:00", end: "09:15" },
          { start: "12:00", end: "12:30" },
        ],
        is_active: true,
      },
    ]);

  const saveRow = (r: Row) => {
    if (!r.name.trim() || !r.code.trim() || !r.start_time || !r.end_time) return;
    save.mutate({
      id: r.id,
      name: r.name.trim(),
      code: r.code.trim(),
      start_time: r.start_time,
      end_time: r.end_time,
      days_of_week: r.days.join(","),
      break_windows: r.breaks.filter((b) => b.start && b.end),
      is_active: r.is_active,
    });
  };

  const removeRow = (r: Row) => {
    if (r.id) del.mutate(r.id);
    else setRows((rs) => rs.filter((x) => x.key !== r.key)); // discard unsaved draft
  };

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="grid gap-3">
      <p className="text-xs text-muted-foreground">
        The solver only schedules attended work inside active shift windows. Times are
        local; overnight shifts (end ≤ start) roll into the next day. Breaks are the
        shift's standing daily pauses (morning break, lunch) — subtracted from every
        working day.
      </p>

      {rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No shifts yet — add one below.</p>
      )}

      {rows.map((r) => (
        <div key={r.key} className="grid gap-2 rounded-md border p-3">
          <div className="flex flex-wrap items-end gap-2">
            <div className="grid gap-1">
              <Label className="text-[11px]">Name</Label>
              <Input
                className="h-8 w-40"
                value={r.name}
                placeholder="Day Shift"
                onChange={(e) => patch(r.key, { name: e.target.value })}
              />
            </div>
            <div className="grid gap-1">
              <Label className="text-[11px]">Code</Label>
              <Input
                className="h-8 w-20"
                value={r.code}
                placeholder="DAY"
                onChange={(e) => patch(r.key, { code: e.target.value })}
              />
            </div>
            <div className="grid gap-1">
              <Label className="text-[11px]">Start</Label>
              <Input
                type="time"
                className="h-8 w-28"
                value={r.start_time}
                onChange={(e) => patch(r.key, { start_time: e.target.value })}
              />
            </div>
            <div className="grid gap-1">
              <Label className="text-[11px]">End</Label>
              <Input
                type="time"
                className="h-8 w-28"
                value={r.end_time}
                onChange={(e) => patch(r.key, { end_time: e.target.value })}
              />
            </div>
            <div className="flex items-center gap-1.5 pb-1.5">
              <Switch
                checked={r.is_active}
                onCheckedChange={(v) => patch(r.key, { is_active: v })}
              />
              <Label className="text-[11px]">Active</Label>
            </div>
          </div>

          {/* Standing daily breaks (facility break, lunch, ...) */}
          <div className="flex flex-wrap items-center gap-2">
            <Label className="text-[11px] text-muted-foreground">Breaks</Label>
            {r.breaks.map((b, i) => (
              <span key={i} className="flex items-center gap-1 rounded border px-1.5 py-0.5">
                <Input
                  type="time"
                  className="h-6 w-24 border-0 p-0 text-[11px] shadow-none"
                  value={b.start}
                  onChange={(e) => patchBreak(r.key, i, { start: e.target.value })}
                />
                <span className="text-[11px] text-muted-foreground">–</span>
                <Input
                  type="time"
                  className="h-6 w-24 border-0 p-0 text-[11px] shadow-none"
                  value={b.end}
                  onChange={(e) => patchBreak(r.key, i, { end: e.target.value })}
                />
                <button
                  type="button"
                  title="Remove break"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => removeBreak(r.key, i)}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-1.5 text-[11px]"
              onClick={() => addBreak(r.key)}
            >
              <Plus className="mr-0.5 h-3 w-3" /> Add break
            </Button>
          </div>

          <div className="flex items-center gap-1">
            {DAYS.map((d, i) => (
              <button
                key={d}
                type="button"
                onClick={() => toggleDay(r.key, i)}
                className={`rounded px-2 py-0.5 text-[11px] border ${
                  r.days.includes(i)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground"
                }`}
              >
                {d}
              </button>
            ))}
            <div className="ml-auto flex gap-1">
              <Button size="sm" className="h-7" onClick={() => saveRow(r)} disabled={save.isPending}>
                Save
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 text-destructive"
                title={r.id ? "Remove shift" : "Discard"}
                onClick={() => removeRow(r)}
                disabled={del.isPending}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      ))}

      <Button variant="outline" size="sm" className="w-fit" onClick={addRow}>
        <Plus className="mr-1 h-4 w-4" /> Add shift
      </Button>
    </div>
  );
}
