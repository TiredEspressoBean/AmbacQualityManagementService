// Why a reading can't be taken with a gauge, mirroring the server's refusal at capture
// (services/mes/equipment.py gauge_refusal): out of service, failed calibration, or
// past its calibration due date (refused since 2026-11-11). Pickers grey the gauge out
// with this reason instead of offering it and refusing on submit.
export type GaugeState = {
    status?: string | null;
    calibration_status?: string | null;
    next_calibration_due?: string | null;
};

const fmtDate = (iso: string) =>
    new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export function gaugeUnusableReason(g: GaugeState): string | null {
    // Failed first: a failed calibration also sets out of service, and is the reason.
    if (g.calibration_status === "FAILED") return "calibration failed";
    if (g.status === "OUT_OF_SERVICE") return "out of service";
    if (g.calibration_status === "OVERDUE") {
        return g.next_calibration_due
            ? `calibration overdue since ${fmtDate(g.next_calibration_due)}`
            : "never calibrated";
    }
    return null;
}
