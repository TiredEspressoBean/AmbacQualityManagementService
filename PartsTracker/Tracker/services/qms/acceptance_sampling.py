"""
Acceptance-sampling calculator (pure, stateless — no DB, no tenant scope).

Given a lot size + plan parameters, returns the sample size (n) and accept/reject
numbers (Ac/Re). Two strategies:
  - ``C0``  — zero-acceptance-number (Squeglia). Ac is ALWAYS 0, Re ALWAYS 1
              (any defective rejects the lot). Default for aero/auto.
  - ``Z14`` — ANSI/ASQ Z1.4 single sampling, normal severity. Re = Ac + 1
              (single sampling has no gap).

⚠ TABLE VERIFICATION: the sample-size code letters, sample sizes, and Ac values
below are transcribed for the common AQL columns and MUST be verified against a
controlled copy of ANSI/ASQ Z1.4 (Table I + Table II-A) and Squeglia's
"Zero Acceptance Number Sampling Plans" before use in production acceptance
decisions. The *mechanism* (count defectives across n units, accept if ≤ Ac,
reject if ≥ Re) is correct regardless; the table cells are data to confirm.
Golden tests cover the anchors we're confident in.
"""
from __future__ import annotations

from dataclasses import dataclass

# Standard AQL series (percent) we support. Callers must use a standard AQL;
# a non-standard value snaps up to the next standard AQL (Z1.4 convention).
STANDARD_AQLS = [0.10, 0.15, 0.25, 0.40, 0.65, 1.0, 1.5, 2.5, 4.0, 6.5, 10.0]

# Z1.4 Table I — sample-size code letters by lot-size range and inspection level.
# (lot_max, {level: letter}); general levels I/II/III.
_CODE_LETTERS = [
    (8,       {"I": "A", "II": "A", "III": "B"}),
    (15,      {"I": "A", "II": "B", "III": "C"}),
    (25,      {"I": "B", "II": "C", "III": "D"}),
    (50,      {"I": "C", "II": "D", "III": "E"}),
    (90,      {"I": "C", "II": "E", "III": "F"}),
    (150,     {"I": "D", "II": "F", "III": "G"}),
    (280,     {"I": "E", "II": "G", "III": "H"}),
    (500,     {"I": "F", "II": "H", "III": "J"}),
    (1200,    {"I": "G", "II": "J", "III": "K"}),
    (3200,    {"I": "H", "II": "K", "III": "L"}),
    (10000,   {"I": "J", "II": "L", "III": "M"}),
    (35000,   {"I": "K", "II": "M", "III": "N"}),
    (150000,  {"I": "L", "II": "N", "III": "P"}),
    (500000,  {"I": "M", "II": "P", "III": "Q"}),
    (float("inf"), {"I": "N", "II": "Q", "III": "R"}),
]

_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R"]
_Z14_SAMPLE_SIZE = {
    "A": 2, "B": 3, "C": 5, "D": 8, "E": 13, "F": 20, "G": 32, "H": 50,
    "J": 80, "K": 125, "L": 200, "M": 315, "N": 500, "P": 800, "Q": 1250, "R": 2000,
}

# Z1.4 Table II-A single sampling, NORMAL — acceptance number Ac per (code letter, AQL).
# Re = Ac + 1. "D" = down-arrow (use the first plan below — i.e. the next code
# letter that has a numeric Ac). Only the common AQL columns are populated.
_D = "DOWN"
_Z14_NORMAL_AC = {
    # letter: {aql: Ac or DOWN}
    "C": {0.65: _D, 1.0: _D, 1.5: _D, 2.5: 0, 4.0: 0, 6.5: 1},
    "D": {0.65: _D, 1.0: _D, 1.5: 0, 2.5: 0, 4.0: 1, 6.5: 2},
    "E": {0.65: _D, 1.0: 0, 1.5: 0, 2.5: 1, 4.0: 2, 6.5: 3},
    "F": {0.65: 0, 1.0: 0, 1.5: 1, 2.5: 2, 4.0: 3, 6.5: 5},
    "G": {0.65: 0, 1.0: 1, 1.5: 2, 2.5: 3, 4.0: 5, 6.5: 7},
    "H": {0.65: 1, 1.0: 1, 1.5: 2, 2.5: 3, 4.0: 5, 6.5: 8},   # H@2.5 anchor (3,4)
    "J": {0.65: 1, 1.0: 2, 1.5: 3, 2.5: 5, 4.0: 7, 6.5: 10},  # J@1.0 anchor (2,3)
    "K": {0.65: 2, 1.0: 3, 1.5: 5, 2.5: 7, 4.0: 10, 6.5: 14},
    "L": {0.65: 3, 1.0: 5, 1.5: 7, 2.5: 10, 4.0: 14, 6.5: 21},
    "M": {0.65: 5, 1.0: 7, 1.5: 10, 2.5: 14, 4.0: 21, 6.5: 21},
    "N": {0.65: 7, 1.0: 10, 1.5: 14, 2.5: 21, 4.0: 21, 6.5: 21},
}

# C=0 (Squeglia) sample sizes by AQL → [(lot_max, n)]. Ac=0, Re=1 always.
# Common AQL columns; verify against Squeglia's published tables.
_C0_SAMPLE_SIZE = {
    0.65: [(50, 13), (90, 13), (150, 20), (280, 29), (500, 34), (1200, 42), (3200, 50), (10000, 60), (float("inf"), 74)],
    1.0:  [(50, 8),  (90, 12), (150, 13), (280, 20), (500, 29), (1200, 34), (3200, 42), (10000, 50), (float("inf"), 60)],
    1.5:  [(50, 5),  (90, 8),  (150, 12), (280, 13), (500, 20), (1200, 29), (3200, 34), (10000, 42), (float("inf"), 50)],
    2.5:  [(50, 5),  (90, 5),  (150, 8),  (280, 12), (500, 13), (1200, 20), (3200, 29), (10000, 34), (float("inf"), 42)],
    4.0:  [(50, 3),  (90, 5),  (150, 5),  (280, 8),  (500, 12), (1200, 13), (3200, 20), (10000, 29), (float("inf"), 34)],
    6.5:  [(50, 2),  (90, 3),  (150, 5),  (280, 5),  (500, 8),  (1200, 12), (3200, 13), (10000, 20), (float("inf"), 29)],
}


@dataclass(frozen=True)
class SamplePlan:
    sample_size: int        # n
    accept_number: int      # Ac
    reject_number: int      # Re
    strategy: str           # 'C0' | 'Z14'
    inspection_level: str   # 'I' | 'II' | 'III'
    severity: str           # 'NORMAL' | 'TIGHTENED' | 'REDUCED'

    @classmethod
    def sample(cls) -> "SamplePlan":
        return cls(5, 0, 1, "C0", "II", "NORMAL")


def _snap_aql(aql: float) -> float:
    for a in STANDARD_AQLS:
        if aql <= a + 1e-9:
            return a
    return STANDARD_AQLS[-1]


def _code_letter(lot_size: int, level: str) -> str:
    level = level if level in ("I", "II", "III") else "II"
    for lot_max, letters in _CODE_LETTERS:
        if lot_size <= lot_max:
            return letters[level]
    return _CODE_LETTERS[-1][1][level]


def _z14_ac(letter: str, aql: float) -> tuple[int, int]:
    """Resolve (sample_size, Ac) for a Z1.4 normal single plan, following the
    down-arrow rule (use the first code letter at or below that has a numeric Ac)."""
    start = _LETTERS.index(letter)
    for i in range(start, len(_LETTERS)):
        lt = _LETTERS[i]
        ac = _Z14_NORMAL_AC.get(lt, {}).get(aql)
        if isinstance(ac, int):
            return _Z14_SAMPLE_SIZE[lt], ac
    # Fell off the bottom — use the largest defined plan for this AQL.
    for lt in reversed(_LETTERS):
        ac = _Z14_NORMAL_AC.get(lt, {}).get(aql)
        if isinstance(ac, int):
            return _Z14_SAMPLE_SIZE[lt], ac
    raise ValueError(f"No Z1.4 plan for AQL {aql}")


def _c0_sample_size(lot_size: int, aql: float) -> int:
    table = _C0_SAMPLE_SIZE.get(aql)
    if table is None:
        raise ValueError(f"No C=0 table column for AQL {aql}")
    for lot_max, n in table:
        if lot_size <= lot_max:
            return min(n, lot_size)
    return min(table[-1][1], lot_size)


def compute_sample_plan(
    *,
    lot_size: int,
    aql: float,
    inspection_level: str = "II",
    severity: str = "NORMAL",
    strategy: str = "C0",
) -> SamplePlan:
    """Return the acceptance-sampling plan for a lot.

    C0: Ac=0, Re=1, n from the Squeglia table. Z14: code letter from lot size +
    level, n + Ac from the normal single-sampling table, Re = Ac + 1.
    """
    if lot_size < 0:
        raise ValueError("lot_size must be non-negative")
    aql_s = _snap_aql(aql)
    level = inspection_level if inspection_level in ("I", "II", "III") else "II"

    if strategy == "Z14":
        letter = _code_letter(lot_size, level)
        n, ac = _z14_ac(letter, aql_s)
        n = min(n, lot_size) if lot_size > 0 else 0
        return SamplePlan(n, ac, ac + 1, "Z14", level, severity)

    # Default C=0
    n = _c0_sample_size(lot_size, aql_s) if lot_size > 0 else 0
    return SamplePlan(n, 0, 1, "C0", level, severity)
