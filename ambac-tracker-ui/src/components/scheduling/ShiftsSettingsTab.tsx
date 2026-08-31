// Work-hours (Shift calendar) editor — the tab in the scheduling settings dialog.
// The solver's working windows are derived from these shifts.
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useShifts, useSaveShift, useDeleteShift } from "@/hooks/useScheduling";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]; // index = day number 0..6

type Row = {
  key: string;        // stable local key (id or draft-n)
  id?: string;        // undefined for a not-yet-saved draft
  name: string;
  code: string;
  start_time: string; // "HH:MM"
  end_time: string;   // "HH:MM"
  days: number[];
  is_active: boolean;
};

const hhmm = (t: string | undefined) => (t ? t.slice(0, 5) : "");
const parseDays = (s: string | undefined) =>
  (s ?? "").split(",").map((x) => x.trim()).filter(Boolean).map(Number).filter((n) => n >= 0 && n <= 6);

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
        local; overnight shifts (end ≤ start) roll into the next day.
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
