/** "A solve is running" — for everyone looking at the board, not just whoever started it.
 *
 *  Three states worth distinguishing, because they call for different reactions:
 *
 *  - **running** — a worker has it. Shows time remaining, which is honest here because
 *    CP-SAT runs to a wall-clock cap: the finish is bounded, not guessed. Phrased as
 *    "up to", since proving optimality ends it early.
 *  - **queued** — nobody has picked it up yet. Brief is normal; sustained means no
 *    worker is running, which is a thing to go fix rather than wait out.
 *  - **stale** — past its cap plus grace with no result. The worker almost certainly
 *    died. Said out loud instead of spinning forever, because an indicator that never
 *    resolves teaches people to ignore indicators.
 */
import { Loader2, AlertTriangle } from "lucide-react";
import { useActiveRun } from "@/hooks/useScheduling";

const LABEL: Record<string, string> = {
  solve: "Solving the schedule",
  draft: "Running a what-if",
  dispatch: "Assigning operators",
};

/** "1m 40s" / "12s" — a bare seconds count reads as noise past a minute. */
function humanSeconds(total: number): string {
  const s = Math.max(0, Math.round(total));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

export function ActiveRunBanner() {
  const { data } = useActiveRun();
  if (!data) return null;

  if (data.stale) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <span>
          A {LABEL[data.kind ?? "solve"]?.toLowerCase() ?? "run"} was queued{" "}
          {humanSeconds(data.seconds_elapsed ?? 0)} ago and hasn&rsquo;t finished. The
          background worker may not be running &mdash; the board below is the last good
          result, not a stuck one.
        </span>
      </div>
    );
  }

  if (!data.running) return null;

  // PENDING here means queued, not running: Celery reports STARTED once a worker picks
  // it up, so the two are genuinely distinguishable rather than guessed at.
  const queued = data.state === "PENDING";
  return (
    <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm">
      <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
      <span>
        <strong>{LABEL[data.kind ?? "solve"] ?? "Working"}</strong>
        {queued ? (
          <span className="text-muted-foreground">
            {" "}&mdash; queued {humanSeconds(data.seconds_elapsed ?? 0)} ago, waiting for
            a worker.
          </span>
        ) : (
          <span className="text-muted-foreground">
            {" "}&mdash; up to {humanSeconds(data.seconds_remaining ?? 0)} left. The board
            below is the previous result until it lands.
          </span>
        )}
      </span>
    </div>
  );
}
