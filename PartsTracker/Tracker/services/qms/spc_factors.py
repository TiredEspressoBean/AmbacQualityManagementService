"""SPC control-chart constants shared by the capability endpoint and the SPC report.

d2 — the mean of the relative range for a subgroup of n, used to estimate within-
subgroup sigma as R̄ / d2. Values for n = 2..25 from the standard control-chart
constants table (AIAG SPC manual, Appendix; ASTM E2587). The table stopped at n=10
and a larger subgroup fell back to n=5's 2.326, understating Cp/Cpk (round-3 #15).
"""

D2_FACTORS = {
    2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970,
    10: 3.078, 11: 3.173, 12: 3.258, 13: 3.336, 14: 3.407, 15: 3.472, 16: 3.532,
    17: 3.588, 18: 3.640, 19: 3.689, 20: 3.735, 21: 3.778, 22: 3.819, 23: 3.858,
    24: 3.895, 25: 3.931,
}

MIN_SUBGROUP, MAX_SUBGROUP = 2, 25
