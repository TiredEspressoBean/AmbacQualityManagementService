"""
Acceptance-sampling calculator (pure, stateless — no DB, no tenant scope).

Given a lot size + plan parameters, returns the sample size (n) and accept/reject
numbers (Ac/Re). Three strategies:
  - ``C0``  — zero-acceptance-number (Squeglia). Ac is ALWAYS 0, Re ALWAYS 1
              (any defective rejects the lot). Default for aero/auto.
  - ``Z14`` — ANSI/ASQ Z1.4 single sampling, **Normal / Tightened / Reduced**
              severity (Tables II-A / II-B / II-C). **Attribute** (count defectives).
              Normal & Tightened: Re = Ac + 1. Reduced: Re may exceed Ac + 1 — the
              accept/reject gap (Ac < d < Re → accept the lot, revert to normal).
  - ``Z19`` — ANSI/ASQ Z1.9 (ex MIL-STD-414) **variables**, standard-deviation
              method, normal severity. Returns n + the acceptability constant ``k``;
              the lot is accepted when the quality index (USL−x̄)/s (and/or
              (x̄−LSL)/s) is ≥ k. Operates on ONE measured characteristic.

⚠ TABLE VERIFICATION: the sample-size code letters, sample sizes, Ac values, and
the Z1.9 ``k`` constants below are transcribed for the common AQL columns and MUST
be verified against a controlled copy of ANSI/ASQ Z1.4 (Table I + Table II-A),
Squeglia's "Zero Acceptance Number Sampling Plans", and ANSI/ASQ Z1.9 (Table A-2 +
the std-deviation-method master table) before use in production acceptance
decisions. The *mechanism* — count defectives vs Ac/Re for attribute; x̄/s vs k for
variables — is correct regardless; the table cells are data to confirm. Golden
tests cover the anchors we're confident in.
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
_LAST_TAB_IDX = _LETTERS.index("N")  # last code letter tabulated in _Z14_NORMAL_AC
_Z14_SAMPLE_SIZE = {
    "A": 2, "B": 3, "C": 5, "D": 8, "E": 13, "F": 20, "G": 32, "H": 50,
    "J": 80, "K": 125, "L": 200, "M": 315, "N": 500, "P": 800, "Q": 1250, "R": 2000,
}

# Z1.4 Table II-A single sampling, NORMAL — acceptance number Ac per (code letter, AQL).
# Re = Ac + 1. Transcribed cell-for-cell from the MIL-STD-105E Table II-A scan
# (Z1.4 attribute tables are identical to 105E); verified 2026-07-06.
#
# ARROWS ARE PRESERVED, not flattened to numbers: an arrow means "use the first
# numeric plan in this AQL column in the arrow's direction — AND its sample size."
#   _DOWN (↓) → search toward larger code letters (bigger n).
#   _UP   (↑) → search toward smaller code letters (smaller n).
# Flattening arrows into the nearest Ac (the prior bug) silently changed n and
# let lots be accepted that the standard rejects — e.g. M@6.5 / N@4.0 / N@6.5 were
# a bogus Ac=21 but are really up-arrows.
_UP = "UP"
_DOWN = "DOWN"
_Z14_NORMAL_AC = {
    # letter: {aql: Ac | _UP | _DOWN}
    "C": {0.65: _DOWN, 1.0: _DOWN, 1.5: _DOWN, 2.5: 0,     4.0: _UP,   6.5: _DOWN},
    "D": {0.65: _DOWN, 1.0: _DOWN, 1.5: 0,     2.5: _UP,   4.0: _DOWN, 6.5: 1},
    "E": {0.65: _DOWN, 1.0: 0,     1.5: _UP,   2.5: _UP,   4.0: 1,     6.5: 2},
    "F": {0.65: 0,     1.0: _UP,   1.5: _DOWN, 2.5: 1,     4.0: 2,     6.5: 3},
    "G": {0.65: _UP,   1.0: _DOWN, 1.5: 1,     2.5: 2,     4.0: 3,     6.5: 5},
    "H": {0.65: _DOWN, 1.0: 1,     1.5: 2,     2.5: 3,     4.0: 5,     6.5: 7},   # H@2.5 anchor (3,4)
    "J": {0.65: 1,     1.0: 2,     1.5: 3,     2.5: 5,     4.0: 7,     6.5: 10},  # J@1.0 anchor (2,3)
    "K": {0.65: 2,     1.0: 3,     1.5: 5,     2.5: 7,     4.0: 10,    6.5: 14},
    "L": {0.65: 3,     1.0: 5,     1.5: 7,     2.5: 10,    4.0: 14,    6.5: 21},
    "M": {0.65: 5,     1.0: 7,     1.5: 10,    2.5: 14,    4.0: 21,    6.5: _UP},
    "N": {0.65: 7,     1.0: 10,    1.5: 14,    2.5: 21,    4.0: _UP,   6.5: _UP},
}

# Z1.4 Table II-B single sampling, TIGHTENED — Ac per (code letter, AQL). Re = Ac + 1.
# Same sample sizes as normal (_Z14_SAMPLE_SIZE). Arrows follow the same rule as II-A.
# Cross-verified 2026-07-07 against the MIL-STD-105E primary scan (gridded image reads
# of rows H/K/N) with the decoder validated on the known-good Normal table. The
# tightened Ac ladder is 0,1,2,3,5,8,12,18,27,41.
_Z14_TIGHTENED_AC = {
    "C": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN, 1.5: _DOWN, 2.5: _DOWN, 4.0: 0,    6.5: 1},
    "D": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN, 1.5: _DOWN, 2.5: 0,    4.0: 1,    6.5: 2},
    "E": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN, 1.5: 0,    2.5: 1,    4.0: 2,    6.5: 3},
    "F": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: 0,    1.5: 1,    2.5: 2,    4.0: 3,    6.5: 5},
    "G": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: 0,    1.0: 1,    1.5: 2,    2.5: 3,    4.0: 5,    6.5: 8},
    "H": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: 0,    0.65: 1,    1.0: 2,    1.5: 3,    2.5: 5,    4.0: 8,    6.5: 12},
    "J": {0.10: _DOWN, 0.15: _DOWN, 0.25: 0,    0.40: 1,    0.65: 2,    1.0: 3,    1.5: 5,    2.5: 8,    4.0: 12,   6.5: 18},
    "K": {0.10: _DOWN, 0.15: 0,    0.25: 1,    0.40: 2,    0.65: 3,    1.0: 5,    1.5: 8,    2.5: 12,   4.0: 18,   6.5: 27},
    "L": {0.10: 0,    0.15: 1,    0.25: 2,    0.40: 3,    0.65: 5,    1.0: 8,    1.5: 12,   2.5: 18,   4.0: 27,   6.5: 41},
    "M": {0.10: 1,    0.15: 2,    0.25: 3,    0.40: 5,    0.65: 8,    1.0: 12,   1.5: 18,   2.5: 27,   4.0: 41,   6.5: _UP},
    "N": {0.10: 2,    0.15: 3,    0.25: 5,    0.40: 8,    0.65: 12,   1.0: 18,   1.5: 27,   2.5: 41,   4.0: _UP,  6.5: _UP},
}

# Z1.4 Table II-C single sampling, REDUCED — (Ac, Re) per (code letter, AQL).
# REDUCED uses SMALLER sample sizes AND has the accept/reject gap (Re is often
# NOT Ac+1): when observed defectives d satisfy Ac < d < Re, the lot is ACCEPTED
# but reduced inspection is discontinued (revert to normal — §4.7.4.b / §4.10.1.4).
# Cross-verified 2026-07-07 (rows D–N confirmed via gridded image reads). Row C
# (degenerate n=2) had an ambiguous top-corner cell at AQL 4.0/6.5 → left as arrows
# (fail-closed: resolves down to row D, a slightly larger conservative sample) rather
# than ship an unverified value.
_Z14_REDUCED_SAMPLE_SIZE = {
    "A": 2, "B": 2, "C": 2, "D": 3, "E": 5, "F": 8, "G": 13, "H": 20,
    "J": 32, "K": 50, "L": 80, "M": 125, "N": 200, "P": 315, "Q": 500, "R": 800,
}
_Z14_REDUCED_ACRE = {
    "C": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN,  1.5: _DOWN,  2.5: _DOWN,  4.0: _DOWN,    6.5: _DOWN},   # 4.0/6.5 uncertain → fail-closed to D
    "D": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN,  1.5: _DOWN,  2.5: _DOWN,  4.0: (0, 1),    6.5: (0, 2)},
    "E": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN,  1.5: _DOWN,  2.5: (0, 1),  4.0: (0, 2),    6.5: (1, 3)},
    "F": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: _DOWN,  1.5: (0, 1),  2.5: (0, 2),  4.0: (1, 3),    6.5: (1, 4)},
    "G": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: _DOWN, 1.0: (0, 1),  1.5: (0, 2),  2.5: (1, 3),  4.0: (1, 4),    6.5: (2, 5)},
    "H": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: _DOWN, 0.65: (0, 1),  1.0: (0, 2),  1.5: (1, 3),  2.5: (1, 4),  4.0: (2, 5),    6.5: (3, 6)},
    "J": {0.10: _DOWN, 0.15: _DOWN, 0.25: _DOWN, 0.40: (0, 1),  0.65: (0, 2),  1.0: (1, 3),  1.5: (1, 4),  2.5: (2, 5),  4.0: (3, 6),    6.5: (5, 8)},
    "K": {0.10: _DOWN, 0.15: _DOWN, 0.25: (0, 1),  0.40: (0, 2),  0.65: (1, 3),  1.0: (1, 4),  1.5: (2, 5),  2.5: (3, 6),  4.0: (5, 8),    6.5: (7, 10)},
    "L": {0.10: _DOWN, 0.15: (0, 1),  0.25: (0, 2),  0.40: (1, 3),  0.65: (1, 4),  1.0: (2, 5),  1.5: (3, 6),  2.5: (5, 8),  4.0: (7, 10),   6.5: (10, 13)},
    "M": {0.10: (0, 1),  0.15: (0, 2),  0.25: (1, 3),  0.40: (1, 4),  0.65: (2, 5),  1.0: (3, 6),  1.5: (5, 8),  2.5: (7, 10), 4.0: (10, 13),  6.5: (14, 17)},
    "N": {0.10: (0, 2),  0.15: (1, 3),  0.25: (1, 4),  0.40: (2, 5),  0.65: (3, 6),  1.0: (5, 8),  1.5: (7, 10), 2.5: (10, 13),4.0: (14, 17),  6.5: (21, 24)},
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

# ── ANSI/ASQ Z1.9 (variables, standard-deviation method, normal) ─────────────
# Table A-2 — sample-size code letters by lot size + general inspection level.
# (Z1.9 bands differ from Z1.4; do NOT reuse _CODE_LETTERS.) ⚠ verify.
_Z19_CODE_LETTERS = [
    (8,            {"I": "B", "II": "B", "III": "C"}),
    (15,           {"I": "B", "II": "B", "III": "D"}),
    (25,           {"I": "B", "II": "C", "III": "E"}),
    (50,           {"I": "C", "II": "D", "III": "F"}),
    (90,           {"I": "D", "II": "E", "III": "G"}),
    (150,          {"I": "E", "II": "F", "III": "H"}),
    (280,          {"I": "F", "II": "G", "III": "I"}),
    (400,          {"I": "G", "II": "H", "III": "I"}),
    (500,          {"I": "G", "II": "H", "III": "J"}),
    (1200,         {"I": "H", "II": "J", "III": "K"}),
    (3200,         {"I": "I", "II": "K", "III": "L"}),
    (10000,        {"I": "J", "II": "L", "III": "M"}),
    (35000,        {"I": "K", "II": "M", "III": "N"}),
    (150000,       {"I": "L", "II": "N", "III": "P"}),
    (float("inf"), {"I": "M", "II": "P", "III": "P"}),
]

# Sample size n by code letter (std-deviation method). ⚠ verify.
_Z19_SAMPLE_SIZE = {
    "B": 3, "C": 4, "D": 5, "E": 7, "F": 10, "G": 15, "H": 20,
    "I": 25, "J": 30, "K": 40, "L": 60, "M": 85, "N": 115, "P": 150,
}

# Acceptability constant k per (code letter, AQL) — std-deviation method, NORMAL,
# k-method. Accept the lot when (USL−x̄)/s ≥ k (and/or (x̄−LSL)/s ≥ k).
#
# Letters B–J: VERIFIED 2026-07-06 against the MIL-STD-414 Table B-1 scan (n is
# identical between MIL-STD-414 and ANSI/ASQ Z1.9-2003 for B–J, so k matches).
# Un-tabulated low-AQL cells (arrows) are omitted → _z19_plan raises, which is
# correct (no plan at that intersection; use a different level/AQL).
#
# Letters K–P (large lots): DELIBERATELY NOT TABULATED — fail closed. Z1.9-2003
# re-sized these vs MIL-STD-414 (n = 40/60/85/115/150), and the current Z1.9-2003
# master table is paywalled, so we can't verify them from a free primary source.
# Rather than ship borrowed/approximate constants (a wrong k = a wrong accept/reject),
# `_z19_plan` raises for these letters — the operator drops to a lower inspection
# level or attribute/C=0 sampling. Add verified K–P here only from a purchased
# ANSI/ASQ Z1.9-2003 copy. (Variables sampling on lots this large is uncommon at
# the target facility size; C=0 covers the attribute path at any lot size.)
_Z19_K = {
    # letter: {aql: k}   — B–J VERIFIED 2026-07-06 against MIL-STD-414 Table B-1
    # (n is identical between MIL-STD-414 and Z1.9-2003 for B–J, so k matches).
    "B": {2.5: 1.12, 4.0: 0.958, 6.5: 0.765, 10.0: 0.566},
    "C": {1.0: 1.45, 1.5: 1.34, 2.5: 1.17, 4.0: 1.01, 6.5: 0.814, 10.0: 0.617},
    "D": {0.65: 1.65, 1.0: 1.53, 1.5: 1.40, 2.5: 1.24, 4.0: 1.07, 6.5: 0.874, 10.0: 0.675},
    "E": {0.65: 1.75, 1.0: 1.62, 1.5: 1.50, 2.5: 1.33, 4.0: 1.15, 6.5: 0.955, 10.0: 0.755},
    "F": {0.65: 1.84, 1.0: 1.72, 1.5: 1.58, 2.5: 1.41, 4.0: 1.23, 6.5: 1.03, 10.0: 0.828},
    "G": {0.65: 1.91, 1.0: 1.79, 1.5: 1.65, 2.5: 1.47, 4.0: 1.30, 6.5: 1.09, 10.0: 0.886},
    "H": {0.65: 1.96, 1.0: 1.82, 1.5: 1.69, 2.5: 1.51, 4.0: 1.33, 6.5: 1.12, 10.0: 0.917},
    "I": {0.65: 1.98, 1.0: 1.85, 1.5: 1.72, 2.5: 1.53, 4.0: 1.35, 6.5: 1.14, 10.0: 0.936},
    "J": {0.65: 2.00, 1.0: 1.86, 1.5: 1.73, 2.5: 1.55, 4.0: 1.36, 6.5: 1.15, 10.0: 0.946},
    # K–P intentionally absent → fail closed (see header note).
}


@dataclass(frozen=True)
class SamplePlan:
    sample_size: int        # n
    accept_number: int      # Ac (attribute; sentinel 0 for variables)
    reject_number: int      # Re (attribute; sentinel 1 for variables)
    strategy: str           # 'C0' | 'Z14' | 'Z19'
    inspection_level: str   # 'I' | 'II' | 'III'
    severity: str           # 'NORMAL' | 'TIGHTENED' | 'REDUCED'
    # Variables (Z1.9) only — blank/None for attribute plans:
    method: str = ""        # '' | 'K_SINGLE'  (M_DOUBLE reserved)
    k: float | None = None  # acceptability constant (std-dev method)

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


def _z14_resolve(letter: str, aql: float, table: dict, sizes: dict):
    """Resolve (sample_size, cell) for a Z1.4 single plan, FOLLOWING arrows to the
    adjacent plan (↓ = larger sample below; ↑ = smaller sample above), per
    MIL-STD-105E. Following an arrow changes BOTH n and the plan to the resolved
    letter's. ``cell`` is an int Ac (normal/tightened) or an (Ac, Re) tuple (reduced).

    Code letters A/B (tiny lots) aren't tabulated; a missing cell searches toward
    the tabulated C–N band (↓ from below it, ↑ from above), then is clamped by lot
    size upstream. A wholly-untabulated column trips the cycle guard → raise.
    """
    idx = _LETTERS.index(letter)
    seen: set[str] = set()
    while 0 <= idx < len(_LETTERS):
        lt = _LETTERS[idx]
        if lt in seen:  # cycle guard (shouldn't happen in a valid table)
            break
        seen.add(lt)
        cell = table.get(lt, {}).get(aql)
        if isinstance(cell, (int, tuple)):
            return sizes[lt], cell
        if cell == _UP:
            idx -= 1
        elif cell == _DOWN:
            idx += 1
        else:
            idx += -1 if idx > _LAST_TAB_IDX else 1
    raise ValueError(f"No Z1.4 plan for code letter {letter} at AQL {aql}")


def _z14_plan(letter: str, aql: float, severity: str) -> tuple[int, int, int]:
    """(sample_size, Ac, Re) for a Z1.4 single plan at the given severity.
    Normal/Tightened: Re = Ac + 1. Reduced: (Ac, Re) from the table — Re may exceed
    Ac + 1 (the accept/reject gap; a lot with Ac < d < Re is accepted but reverts
    inspection to normal)."""
    if severity == "TIGHTENED":
        n, ac = _z14_resolve(letter, aql, _Z14_TIGHTENED_AC, _Z14_SAMPLE_SIZE)
        return n, ac, ac + 1
    if severity == "REDUCED":
        n, (ac, re) = _z14_resolve(letter, aql, _Z14_REDUCED_ACRE, _Z14_REDUCED_SAMPLE_SIZE)
        return n, ac, re
    n, ac = _z14_resolve(letter, aql, _Z14_NORMAL_AC, _Z14_SAMPLE_SIZE)
    return n, ac, ac + 1


def _c0_sample_size(lot_size: int, aql: float) -> int:
    table = _C0_SAMPLE_SIZE.get(aql)
    if table is None:
        raise ValueError(f"No C=0 table column for AQL {aql}")
    for lot_max, n in table:
        if lot_size <= lot_max:
            return min(n, lot_size)
    return min(table[-1][1], lot_size)


def _z19_code_letter(lot_size: int, level: str) -> str:
    level = level if level in ("I", "II", "III") else "II"
    for lot_max, letters in _Z19_CODE_LETTERS:
        if lot_size <= lot_max:
            return letters[level]
    return _Z19_CODE_LETTERS[-1][1][level]


def _z19_plan(letter: str, aql: float) -> tuple[int, float]:
    """(sample_size, k) for a Z1.9 std-deviation-method normal plan."""
    k = _Z19_K.get(letter, {}).get(aql)
    if k is None:
        # Fail closed rather than return an unverified constant. High code letters
        # (K–P, large lots) are intentionally not tabulated pending verified
        # Z1.9-2003 values; low-AQL cells for small letters are arrows (no plan).
        raise ValueError(
            f"No tabulated Z1.9 variables plan for code letter {letter} at AQL {aql}. "
            f"Use a lower inspection level, a different AQL, or attribute (C=0) "
            f"sampling for this lot."
        )
    return _Z19_SAMPLE_SIZE[letter], k


def evaluate_variables(
    *,
    values: list[float],
    usl: float | None = None,
    lsl: float | None = None,
    k: float,
) -> dict:
    """Z1.9 std-deviation-method acceptance decision (k-method, single or double
    limit) over the measured ``values`` of one characteristic. Stateless.

    Accept when the relevant quality index ≥ k:
      QU = (USL − x̄) / s   (upper limit)   QL = (x̄ − LSL) / s   (lower limit)
    With both limits present, BOTH indices must clear k. Returns the computed
    statistics + verdict; callers persist/snapshot as needed.
    """
    n = len(values)
    if n < 2:
        raise ValueError("variables sampling needs at least 2 readings")
    if usl is None and lsl is None:
        raise ValueError("variables sampling needs at least one spec limit")
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    s = var ** 0.5

    if s == 0:
        # No spread: accept iff the mean is within the spec limit(s).
        accept = (usl is None or mean <= usl) and (lsl is None or mean >= lsl)
        return {"mean": mean, "s": 0.0, "q_u": None, "q_l": None, "k": k, "accept": accept}

    q_u = (usl - mean) / s if usl is not None else None
    q_l = (mean - lsl) / s if lsl is not None else None
    indices = [q for q in (q_u, q_l) if q is not None]
    accept = all(q >= k for q in indices)
    return {"mean": mean, "s": s, "q_u": q_u, "q_l": q_l, "k": k, "accept": accept}


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
    level, n + Ac from the normal single-sampling table (arrows followed), Re = Ac + 1.

    ``severity`` selects the Z1.4 master table: NORMAL (Table II-A), TIGHTENED
    (II-B — same n, stricter Ac), or REDUCED (II-C — smaller n, and Re may exceed
    Ac + 1, the accept/reject gap). The effective severity is chosen by the
    switching engine (``services.qms.severity_switching``); this function just
    applies whatever severity it's handed. C=0 and Z1.9 ignore severity.
    """
    if lot_size < 0:
        raise ValueError("lot_size must be non-negative")
    aql_s = _snap_aql(aql)
    level = inspection_level if inspection_level in ("I", "II", "III") else "II"
    sev = severity if severity in ("NORMAL", "TIGHTENED", "REDUCED") else "NORMAL"

    if strategy == "Z14":
        letter = _code_letter(lot_size, level)
        n, ac, re = _z14_plan(letter, aql_s, sev)
        n = min(n, lot_size) if lot_size > 0 else 0
        return SamplePlan(n, ac, re, "Z14", level, sev)

    if strategy == "Z19":
        letter = _z19_code_letter(lot_size, level)
        n, k = _z19_plan(letter, aql_s)
        n = min(n, lot_size) if lot_size > 0 else 0
        # Ac/Re sentinels (0/1) keep attribute consumers happy; the verdict uses k.
        return SamplePlan(n, 0, 1, "Z19", level, severity, method="K_SINGLE", k=k)

    # Default C=0
    n = _c0_sample_size(lot_size, aql_s) if lot_size > 0 else 0
    return SamplePlan(n, 0, 1, "C0", level, severity)
