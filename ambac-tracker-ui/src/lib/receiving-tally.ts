// A lot's sample, counted the way the server counts it (services/qms/receiving_inspection
// .evaluate_lot_acceptance): a recorded defect makes it at least one defective, even
// with every reading in spec — a unit carrying a nonconformity is a defective unit.

/** The defectives to judge by: what the readings / tally say, at least one if a defect is recorded. */
export const withRecordedDefects = (counted: number, recordedDefects: readonly string[] | undefined) =>
    Math.max(counted, (recordedDefects?.length ?? 0) > 0 ? 1 : 0);

/** Why the count is what it is, when a recorded defect is what made it one. */
export const recordedDefectReason = (counted: number, recordedDefects: readonly string[] | undefined) =>
    counted < 1 && (recordedDefects?.length ?? 0) > 0
        ? ` (a recorded defect: ${recordedDefects!.join(", ")})`
        : "";
