"""Planning layer — aggregate capacity/demand planning above the CP-SAT scheduler.

Where the scheduler answers "exactly how do we run the next few weeks", this layer
answers the coarse, long-range question "roughly, can we take this on, and when" —
rough-cut capacity planning (RCCP) and capable-to-promise (CTP). No solver: it's
capacity-vs-load arithmetic over time buckets, so it scales to years cheaply.
"""
