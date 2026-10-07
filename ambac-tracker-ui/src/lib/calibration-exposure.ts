/** Whether a calibration found its gauge unfit for use — a FAIL, or found out of tolerance
 *  before adjustment — so what the gauge measured since its last good calibration is in
 *  question (ISO 9001 7.1.5.2; /quality/calibrations/records/$id/exposure). */
export const foundUnfit = (r: { result?: string | null; as_found_in_tolerance?: boolean | null }) =>
    r.result === "FAIL" || r.as_found_in_tolerance === false;
