"""
CP-SAT Scheduling Playground -- Layered Manufacturing Scheduler

Table of Contents:
  1. DOMAIN MODELS          - Dataclasses matching Django models
  2. SAMPLE DATA            - Simulated shop floor data
  3. SHOP ECONOMICS         - Cost rates and penalty configuration
  4. UTILITIES              - Helpers, lookups, formatting
  5. LAYER 1: MACHINE SCHEDULE  - CP-SAT solver (operations x machines x time)
  6. LAYER 2: OPERATOR DISPATCH - Shift-level assignment + dispatch lists
  7. REPORTING              - Output formatting for both layers
  8. MAIN                   - Entry point and configuration display

Architecture:
  Layer 1 (CP-SAT) decides WHAT runs WHERE and WHEN.
    - Deterministic durations from timing model (no operator dependency)
    - Transfer batches: next op starts when first piece is done
    - Fixtures as cumulative resource constraints
    - Preferred machine: dialed-in equipment gets reduced setup time
    - Cost-based objective: late penalties + overtime premium + makespan

  Layer 2 (heuristic) decides WHO runs each station.
    - Assigns operators to work centers per shift (the whiteboard)
    - Generates per-station dispatch lists (what to run next)
    - Multi-machine tending: operators free during machine cycle time

Time Elements (SAP/ERP standard):
  Queue Time  -> Solver output (minimized), not an input
  Setup Time  -> Sequence-dependent changeover, operator-attended
  Run Time    -> cycle_time x num_cycles (machine) + load/unload x qty (operator)
  Wait Time   -> Post-process dwell (cure, cool, dry) -- fixed per step pair
  Move Time   -> Transport between bays -- fixed per location pair

Run: python Documents/cpsat_playground.py
"""

from ortools.sat.python import cp_model
from dataclasses import dataclass, field
from datetime import time
import math
from collections import defaultdict


# =====================================================================
# 1. DOMAIN MODELS
# =====================================================================

@dataclass
class OperationTiming:
    """Time breakdown for a single manufacturing operation.

    cycle_time:             Machine time per cycle (one cycle processes pieces_per_cycle items)
    load_unload_per_piece:  Operator touch time per individual piece
    setup_minutes:          Internal setup (machine stopped, operator present)
    external_setup_minutes: Setup that overlaps with prior job's run time (SMED)
    attention_type:         'full' = operator present entire time
                            'load_unload' = operator only needed for load/unload, free during cycle
    """
    setup_minutes: int
    external_setup_minutes: int = 0
    cycle_time: float = 0
    load_unload_per_piece: float = 0
    attention_type: str = "full"
    pieces_per_cycle: int = 1

    def machine_wall_time(self, quantity: int) -> int:
        """Total time machine is occupied. Layer 1 uses this."""
        num_cycles = math.ceil(quantity / self.pieces_per_cycle)
        effective_setup = max(0, self.setup_minutes - self.external_setup_minutes)
        run = math.ceil(self.cycle_time * num_cycles)
        load = math.ceil(self.load_unload_per_piece * quantity)
        return effective_setup + run + load

    def first_piece_done(self, quantity: int) -> int:
        """Minutes until first piece completes. Used for transfer batch overlap."""
        if quantity <= 1:
            return self.machine_wall_time(quantity)
        effective_setup = max(0, self.setup_minutes - self.external_setup_minutes)
        return effective_setup + math.ceil(self.cycle_time) + math.ceil(self.load_unload_per_piece)

    def operator_attended_time(self, quantity: int) -> int:
        """How long the operator must be present. Layer 2 uses this."""
        if self.attention_type == "full":
            return self.machine_wall_time(quantity)
        effective_setup = max(0, self.setup_minutes - self.external_setup_minutes)
        return effective_setup + math.ceil(self.load_unload_per_piece * quantity)

    def operator_free_time(self, quantity: int) -> int:
        """Time operator can tend other machines during this operation."""
        return self.machine_wall_time(quantity) - self.operator_attended_time(quantity)


@dataclass
class Shift:
    id: int
    name: str
    start_time: time
    end_time: time


@dataclass
class ContinuousMachine:
    """A machine that runs 24/7 producing parts from fed stock (e.g., bar-fed lathe).

    Not scheduled task-by-task. Instead, acts as a capacity source:
    the solver knows parts become available at a computed rate.

    changeover_minutes: time to switch to a different part number (full stop)
    bar_change_minutes: time to reload bar stock (brief pause, operator touch)
    parts_per_bar: how many parts one bar produces before needing reload
    bars_per_magazine: how many bars the feeder holds
    """
    id: int
    name: str
    parts_per_hour: float
    changeover_minutes: int = 45        # full changeover to different part number
    bar_change_minutes: int = 5         # brief operator touch to reload magazine
    parts_per_bar: int = 50
    bars_per_magazine: int = 6
    status: str = "IN_SERVICE"

    @property
    def parts_per_magazine(self) -> int:
        return self.parts_per_bar * self.bars_per_magazine

    @property
    def hours_per_magazine(self) -> float:
        """Hours of unattended run time before needing bar reload."""
        return self.parts_per_magazine / self.parts_per_hour

    def time_to_produce(self, quantity: int) -> int:
        """Total minutes to produce quantity, including bar changes."""
        magazines_needed = math.ceil(quantity / self.parts_per_magazine)
        production_minutes = math.ceil(quantity / self.parts_per_hour * 60)
        bar_changes = max(0, magazines_needed - 1) * self.bar_change_minutes
        return production_minutes + bar_changes

    def first_piece_available(self) -> int:
        """Minutes until first piece is done after changeover."""
        return self.changeover_minutes + math.ceil(60 / self.parts_per_hour)

    def operator_touch_per_day(self) -> int:
        """Minutes of operator time needed per 24hr day."""
        magazines_per_day = 24 / max(self.hours_per_magazine, 0.1)
        return math.ceil(magazines_per_day * self.bar_change_minutes)


@dataclass
class Equipment:
    id: int
    name: str
    equipment_type: str
    status: str                 # IN_SERVICE | OUT_OF_SERVICE | IN_CALIBRATION | IN_MAINTENANCE
    location: str               # physical bay -- drives transport time
    days_until_cal_due: int = None
    dialed_in_steps: list = field(default_factory=list)  # steps this machine is set up for


@dataclass
class Fixture:
    id: int
    name: str
    compatible_steps: list      # which step IDs need this fixture
    quantity: int               # how many exist in the shop
    mount_time: int = 0


@dataclass
class WorkCenter:
    id: int
    name: str
    code: str
    default_efficiency: float   # 100.0 = no loss, 92.0 = 8% efficiency loss
    equipment_ids: list
    step_ids: list              # which steps happen here
    changeover_time: dict = None  # {(from_step, to_step): minutes}
    batch_capacity: int = 1     # >1 = parallel processing (e.g., cleaning tank)


@dataclass
class Step:
    id: int
    name: str
    step_type: str              # TASK | REWORK
    timing: OperationTiming
    workcenter_id: int
    requires_qa_signoff: bool = False
    requires_first_piece_inspection: bool = False
    fpi_scope: str = ""         # PER_WORKORDER | PER_SHIFT | PER_EQUIPMENT
    max_visits: int = None      # rework limit
    required_fixture_id: int = None


@dataclass
class Operator:
    id: int
    name: str
    certified_steps: list
    is_qa_inspector: bool = False
    available_from: int = 0         # minutes into horizon (0 = start of Day 1)
    preferred_steps: list = field(default_factory=list)
    speed_factor: float = 1.0       # >1.0 = faster, <1.0 = slower (for dispatch scoring)


@dataclass
class Part:
    id: int
    remaining_steps: list
    quantity: int = 1
    part_status: str = "IN_PROGRESS"
    total_rework_count: int = 0
    is_fpi_candidate: bool = False


@dataclass
class WorkOrder:
    id: int
    name: str
    priority: int               # 1=Urgent, 2=High, 3=Normal
    due_date_minutes: int       # minutes from horizon start
    customer: str
    workorder_status: str = "IN_PROGRESS"
    parts: list = field(default_factory=list)


@dataclass
class SolverWeights:
    """Objective weights in cents. The solver minimizes total cost in cents."""
    name: str = "Balanced"
    lateness_urgent: int = 0    # set from LATE_PENALTY_CPM after economics config
    lateness_high: int = 0
    lateness_normal: int = 0
    overtime_cost: int = 0
    makespan_weight: int = 0
    batching_weight: int = 5
    machine_affinity_weight: int = 0


# =====================================================================
# 2. SAMPLE DATA
# =====================================================================

MINUTES_PER_DAY = 10 * 60      # 4x10 schedule: 10-hour days
WORK_DAYS = 4                   # Mon-Thu
WORK_DAYS = 4                     # 4-day work week (for display/reporting)

# MAX_HORIZON is computed dynamically in the solver from total workload.
# It's not a planning decision — it's just the upper bound on variable domains
# so the solver has room to place everything. Due dates handle urgency.

SHIFT = Shift(1, "Day Shift", time(6, 0), time(16, 30))
LUNCH_START_OFFSET = 5 * 60    # 5 hours into shift = 11:00 AM
LUNCH_DURATION = 30

# -- Equipment --
# Status: IN_SERVICE = available, IN_MAINTENANCE = down, etc.
EQUIPMENT = {
    1: Equipment(1, "Disassembly Station 1", "disassembly", "IN_SERVICE", "Bay A"),
    2: Equipment(2, "Cleaning Tank 1", "cleaning", "IN_SERVICE", "Bay A"),
    3: Equipment(3, "Inspection Bench 1", "inspection", "IN_SERVICE", "Bay B"),
    4: Equipment(4, "Flow Bench A", "flow_test", "IN_SERVICE", "Bay C",
                 dialed_in_steps=[4]),
    5: Equipment(5, "Flow Bench B", "flow_test", "IN_SERVICE", "Bay C",
                 days_until_cal_due=3),
    6: Equipment(6, "Assembly Bench 1", "assembly", "IN_SERVICE", "Bay D",
                 dialed_in_steps=[5]),
    7: Equipment(7, "Assembly Bench 2", "assembly", "IN_MAINTENANCE", "Bay D"),
    8: Equipment(8, "Test Stand 1", "test", "IN_SERVICE", "Bay E"),
}

# Transport times between bays (minutes). Symmetric -- lookup handles both directions.
TRANSPORT_TIMES = {
    ("Bay A", "Bay B"): 3, ("Bay B", "Bay C"): 4, ("Bay C", "Bay D"): 5,
    ("Bay D", "Bay E"): 5, ("Bay A", "Bay C"): 6, ("Bay B", "Bay D"): 7,
    ("Bay C", "Bay E"): 8, ("Bay A", "Bay D"): 8, ("Bay B", "Bay E"): 10,
    ("Bay A", "Bay E"): 12,
}

FIXTURES = {
    1: Fixture(1, "Flow Test Adapter Kit", [4], quantity=2, mount_time=5),
    2: Fixture(2, "Assembly Fixture Set", [5, 7], quantity=2, mount_time=8),
    3: Fixture(3, "Final Test Mount", [6], quantity=1, mount_time=3),
}

WORKCENTERS = {
    1: WorkCenter(1, "Disassembly Bay", "DISASM", 95.0, [1], [1]),
    2: WorkCenter(2, "Cleaning Station", "CLEAN", 90.0, [2], [2], batch_capacity=3),
    3: WorkCenter(3, "Inspection Area", "INSP", 100.0, [3], [3]),
    4: WorkCenter(4, "Flow Test Lab", "FLOW", 100.0, [4, 5], [4]),
    5: WorkCenter(5, "Assembly Area", "ASSY", 92.0, [6, 7], [5, 7],
                  changeover_time={(5, 7): 15, (7, 5): 15}),
    6: WorkCenter(6, "Final Test", "TEST", 100.0, [8], [6]),
}

# -- Steps with timing breakdown --
STEPS = {
    1: Step(1, "Disassembly", "TASK",
            OperationTiming(setup_minutes=10, load_unload_per_piece=30, attention_type="full"),
            workcenter_id=1),
    2: Step(2, "Cleaning", "TASK",
            OperationTiming(setup_minutes=5, cycle_time=15, load_unload_per_piece=2,
                            attention_type="load_unload", pieces_per_cycle=3),
            workcenter_id=2),
    3: Step(3, "Nozzle Inspection", "TASK",
            OperationTiming(setup_minutes=5, load_unload_per_piece=25, attention_type="full"),
            workcenter_id=3, requires_qa_signoff=True,
            requires_first_piece_inspection=True, fpi_scope="PER_WORKORDER"),
    4: Step(4, "Flow Testing", "TASK",
            OperationTiming(setup_minutes=8, cycle_time=18, load_unload_per_piece=3,
                            attention_type="load_unload"),
            workcenter_id=4, requires_qa_signoff=True, required_fixture_id=1),
    5: Step(5, "Assembly", "TASK",
            OperationTiming(setup_minutes=10, load_unload_per_piece=35, attention_type="full"),
            workcenter_id=5, required_fixture_id=2),
    6: Step(6, "Final Test", "TASK",
            OperationTiming(setup_minutes=5, cycle_time=12, load_unload_per_piece=3,
                            attention_type="load_unload"),
            workcenter_id=6, requires_qa_signoff=True, max_visits=2, required_fixture_id=3),
    7: Step(7, "Rework", "REWORK",
            OperationTiming(setup_minutes=10, load_unload_per_piece=40, attention_type="full"),
            workcenter_id=5, max_visits=2, required_fixture_id=2),
}

# Post-process wait times: (from_step, to_step) -> minutes of dwell (cure, dry, cool)
WAIT_TIMES = {
    (2, 3): 30,    # Cleaning -> Inspection: drying time
    (7, 5): 20,    # Rework -> Assembly: adhesive cure
}

QA_SIGNOFF_DURATION = 5  # minutes for QA inspector to review and sign off

# -- Continuous (lights-out) Machines --
# These run 24/7 and feed parts into the job shop workflow.
# Not scheduled by the solver — they produce at a known rate.
CONTINUOUS_MACHINES = {
    1: ContinuousMachine(
        id=1, name="Bar-Fed Lathe (Nuts)",
        parts_per_hour=120,         # 2 parts/min = fast screw machine
        changeover_minutes=45,      # full changeover between part numbers
        bar_change_minutes=5,       # operator loads new bar magazine
        parts_per_bar=80,           # parts per 12-ft bar
        bars_per_magazine=6,        # magazine holds 6 bars
    ),
    2: ContinuousMachine(
        id=2, name="Bar-Fed Lathe (Fittings)",
        parts_per_hour=60,          # slower, more complex parts
        changeover_minutes=60,
        bar_change_minutes=5,
        parts_per_bar=40,
        bars_per_magazine=4,
    ),
}

# Steps that are produced by continuous machines (not scheduled, just availability)
# These map a step to a continuous machine — the solver uses the machine's production
# rate to determine when parts are available for downstream operations.
CONTINUOUS_STEPS = {
    # step_id: (continuous_machine_id, changeover_needed: bool)
    # If a WO has this step, the solver computes availability from the machine's rate
    # instead of scheduling it as a task.
    8: {"machine_id": 1, "name": "Nut Production (lights-out)"},
    9: {"machine_id": 2, "name": "Fitting Production (lights-out)"},
}

# -- Operators --
OPERATORS = {
    1: Operator(1, "Sarah", [1, 2, 3, 4, 5, 6],
                preferred_steps=[4, 5], speed_factor=1.05),
    2: Operator(2, "Carlos", [1, 2, 3, 4, 6, 7],
                preferred_steps=[1, 4], speed_factor=1.0),
    3: Operator(3, "Mike", [1, 2, 4, 5],
                available_from=2 * 60, speed_factor=0.9),   # arrives 2h late Day 1
    4: Operator(4, "Priya", [3, 4, 5, 6, 7],
                is_qa_inspector=True, preferred_steps=[3, 6], speed_factor=1.1),
}

# -- Work Orders --
WORK_ORDERS = [
    WorkOrder(43, "WO-0043 (AOG URGENT)", 1, 1 * MINUTES_PER_DAY,
              "AeroJet", parts=[
                  Part(201, [4, 5, 6], quantity=5),
                  Part(202, [5, 6], quantity=4),
              ]),
    WorkOrder(42, "WO-0042 (HIGH)", 2, 2 * MINUTES_PER_DAY,
              "AeroJet", parts=[
                  Part(101, [3, 4, 5, 6], quantity=6, is_fpi_candidate=True),
                  Part(102, [4, 5, 6], quantity=5),
                  Part(103, [5, 6], quantity=4),
              ]),
    WorkOrder(41, "WO-0041 (NORMAL)", 3, 3 * MINUTES_PER_DAY,
              "IndustrialCo", parts=[
                  Part(301, [2, 3, 4, 5, 6], quantity=5),
                  Part(302, [4, 5, 6], quantity=4),
                  Part(303, [7, 5, 6], quantity=3,
                       part_status="REWORK_IN_PROGRESS", total_rework_count=1),
              ]),
    WorkOrder(40, "WO-0040 (HIGH)", 2, 2 * MINUTES_PER_DAY,
              "DefenseCorp", parts=[
                  Part(401, [3, 4, 5, 6], quantity=4),
                  Part(402, [4, 5, 6], quantity=5),
              ]),
    WorkOrder(39, "WO-0039 (HIGH RUSH)", 2, 4 * MINUTES_PER_DAY,
              "NavalSys", parts=[
                  Part(501, [4, 5, 6], quantity=6),
                  Part(502, [5, 6], quantity=4),
              ]),
    # WOs that use continuous machine output as input:
    # Step 8 (nuts) is produced by the bar-fed lathe, then goes to assembly + test
    # Note: the lathe makes these fast (120/hr), but downstream assembly is the bottleneck
    WorkOrder(38, "WO-0038 (NORMAL)", 3, 4 * MINUTES_PER_DAY,
              "IndustrialCo", parts=[
                  Part(601, [8, 5, 6], quantity=20),    # 20 nuts -> assembly -> test
                  Part(602, [8, 3, 5, 6], quantity=10),  # 10 nuts -> inspect -> assembly -> test
              ]),
    WorkOrder(37, "WO-0037 (HIGH)", 2, 3 * MINUTES_PER_DAY,
              "AeroJet", parts=[
                  Part(701, [9, 5, 6], quantity=15),    # 15 fittings -> assembly -> test
              ]),
]


# =====================================================================
# 3. SHOP ECONOMICS
# =====================================================================

SHOP_RATE_PER_HOUR = 150
OVERTIME_MULTIPLIER = 1.5
ALLOW_OVERTIME = True
MAX_OVERTIME_MINUTES = 120

LATE_PENALTY_PER_DAY = {
    1: 2000,    # Urgent/AOG: customer line down, expedite fees
    2: 500,     # High: contractual penalty, relationship damage
    3: 100,     # Normal: goodwill cost only
}

ENABLE_TRANSFER_BATCH = True
DIALED_IN_SETUP_REDUCTION = 0.5  # 50% setup reduction on preferred machine

# Derived rates in cents/minute (CP-SAT requires integers)
_SHOP_RATE_CPM = round(SHOP_RATE_PER_HOUR * 100 / 60)
_OT_PREMIUM_CPM = round(SHOP_RATE_PER_HOUR * (OVERTIME_MULTIPLIER - 1) * 100 / 60)
_LATE_PENALTY_CPM = {
    pri: round(dollars * 100 / (MINUTES_PER_DAY))
    for pri, dollars in LATE_PENALTY_PER_DAY.items()
}

# Default weights derived from economics
DEFAULT_WEIGHTS = SolverWeights(
    name="Balanced",
    lateness_urgent=_LATE_PENALTY_CPM[1],
    lateness_high=_LATE_PENALTY_CPM[2],
    lateness_normal=_LATE_PENALTY_CPM[3],
    overtime_cost=_OT_PREMIUM_CPM,
    makespan_weight=_SHOP_RATE_CPM // 10,
    batching_weight=5,
    machine_affinity_weight=_SHOP_RATE_CPM // 5,
)


# =====================================================================
# 4. UTILITIES
# =====================================================================

def fmt_time(minutes: int) -> str:
    """Format solver minutes into human-readable 'D1 06:00' format."""
    day = minutes // MINUTES_PER_DAY + 1
    t = minutes % MINUTES_PER_DAY
    hour = t // 60 + SHIFT.start_time.hour
    minute = t % 60
    return f"D{day} {hour:02d}:{minute:02d}"


def get_transport_time(loc_a: str, loc_b: str) -> int:
    """Get move time between two bays. Symmetric lookup, defaults to 5 min."""
    if loc_a == loc_b:
        return 0
    return TRANSPORT_TIMES.get((loc_a, loc_b),
           TRANSPORT_TIMES.get((loc_b, loc_a), 5))


def attend_window(task: dict) -> tuple:
    """Get (start, end) of when operator must be present for a task."""
    if task["attention_type"] == "full":
        return task["start"], task["end"]
    return task["start"], task["start"] + task["operator_attended"]


def task_overtime_minutes(task: dict) -> int:
    """Calculate how many minutes of a task fall into overtime."""
    day = task["start"] // MINUTES_PER_DAY
    day_end = day * MINUTES_PER_DAY + MINUTES_PER_DAY
    return max(0, task["end"] - day_end)


def _operational_equipment():
    """Equipment that is currently IN_SERVICE."""
    return {eid: e for eid, e in EQUIPMENT.items() if e.status == "IN_SERVICE"}


# =====================================================================
# 5. LAYER 1: MACHINE SCHEDULE (CP-SAT)
# =====================================================================

def build_machine_schedule(weights=None, quiet=False):
    """Schedule operations onto machines in time. No operator assignment.

    Returns dict with 'schedule' (list of task dicts), 'makespan', 'late_orders',
    'solve_time', 'weights', and 'lateness_vars' (for reporting).
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    global MAX_HORIZON  # set module-level so helper functions can use it

    model = cp_model.CpModel()
    constraint_counts = {}
    op_equip = _operational_equipment()

    # Compute MAX_HORIZON from total workload:
    # Sum all task durations, divide by number of operational machines,
    # multiply by 3 for safety (sequencing overhead, single-machine bottlenecks).
    # This ensures the solver always has room to place everything.
    total_work_minutes = 0
    for wo in WORK_ORDERS:
        for part in wo.parts:
            for step_id in part.remaining_steps:
                if step_id in CONTINUOUS_STEPS:
                    cm = CONTINUOUS_MACHINES[CONTINUOUS_STEPS[step_id]["machine_id"]]
                    total_work_minutes += cm.time_to_produce(part.quantity)
                elif step_id in STEPS:
                    step = STEPS[step_id]
                    total_work_minutes += step.timing.machine_wall_time(part.quantity)

    num_operational = len(op_equip)
    min_days_needed = total_work_minutes / MINUTES_PER_DAY / max(num_operational, 1)
    MAX_HORIZON = max(10 * MINUTES_PER_DAY, int(min_days_needed * 3 + 10) * MINUTES_PER_DAY)

    if not quiet:
        print(f"  Horizon: {MAX_HORIZON // MINUTES_PER_DAY} days "
              f"(computed from {total_work_minutes / 60:.0f}h work / {num_operational} machines)")

    if not quiet:
        print(f"\n  Transfer batch: {'ON' if ENABLE_TRANSFER_BATCH else 'OFF'}")
        print(f"  Shop rate: ${SHOP_RATE_PER_HOUR}/hr, OT: {OVERTIME_MULTIPLIER}x")
        print(f"  Late penalties: Urgent=${LATE_PENALTY_PER_DAY[1]}/day, "
              f"High=${LATE_PENALTY_PER_DAY[2]}/day, Normal=${LATE_PENALTY_PER_DAY[3]}/day")
        down = [e for e in EQUIPMENT.values() if e.status != "IN_SERVICE"]
        if down:
            print(f"\n  Equipment DOWN:")
            for e in down:
                print(f"    {e.name}: {e.status}")

    # -- Task variables --
    task_starts, task_ends, task_intervals = {}, {}, {}
    task_durations, task_durations_max = {}, {}
    task_first_piece = {}
    task_equip_vars, task_equip_bools = {}, {}
    all_keys = []
    task_meta = {}

    # Track continuous machine steps: these don't get solver variables,
    # they compute a fixed availability time based on production rate.
    # {(part_id, step_id): availability_minute}
    continuous_availability = {}

    for wo in WORK_ORDERS:
        if wo.workorder_status in ("ON_HOLD", "CANCELLED", "COMPLETED"):
            continue
        for part in wo.parts:
            if part.part_status in ("SCRAPPED", "CANCELLED", "COMPLETED"):
                continue
            for step_id in part.remaining_steps:
                # Check if this step is handled by a continuous machine
                if step_id in CONTINUOUS_STEPS:
                    cm_info = CONTINUOUS_STEPS[step_id]
                    cm = CONTINUOUS_MACHINES[cm_info["machine_id"]]
                    key = (part.id, step_id)

                    # Compute when all parts for this batch are ready
                    # Assumes the continuous machine is already running this part number
                    # (changeover scheduling is a separate problem)
                    production_time = cm.time_to_produce(part.quantity)
                    first_piece_time = cm.first_piece_available()

                    continuous_availability[key] = {
                        "production_time": production_time,
                        "first_piece_time": first_piece_time,
                        "all_done_minute": production_time,  # when full batch is ready
                        "machine_name": cm.name,
                        "quantity": part.quantity,
                        "parts_per_hour": cm.parts_per_hour,
                        "operator_touch": cm.operator_touch_per_day(),
                    }
                    task_meta[key] = {"part": part, "step_id": step_id, "wo": wo,
                                      "wc": None, "continuous": True}
                    continue

                step = STEPS[step_id]
                key = (part.id, step_id)
                all_keys.append(key)

                wc = WORKCENTERS[step.workcenter_id]
                eff = wc.default_efficiency / 100.0
                wc_equip = [op_equip[eid] for eid in wc.equipment_ids if eid in op_equip]

                raw_wall = step.timing.machine_wall_time(part.quantity)
                first_piece = step.timing.first_piece_done(part.quantity)
                has_dialed_in = any(step_id in e.dialed_in_steps for e in wc_equip)

                # Preferred machine: actual setup reduction -> shorter duration
                if len(wc_equip) > 1 and has_dialed_in:
                    setup_savings = int(step.timing.setup_minutes * DIALED_IN_SETUP_REDUCTION)
                    dur_preferred = max(1, int((raw_wall - setup_savings) / eff))
                    dur_normal = max(1, int(raw_wall / eff))

                    dur_var = model.new_int_var(
                        min(dur_preferred, dur_normal), max(dur_preferred, dur_normal),
                        f"d_p{part.id}_s{step_id}")
                    start = model.new_int_var(0, MAX_HORIZON, f"s_p{part.id}_s{step_id}")
                    end = model.new_int_var(0, MAX_HORIZON, f"e_p{part.id}_s{step_id}")
                    interval = model.new_interval_var(start, dur_var, end, f"iv_p{part.id}_s{step_id}")

                    task_durations[key] = dur_var
                    task_durations_max[key] = dur_normal

                    equip_var = model.new_int_var_from_domain(
                        cp_model.Domain.from_values([e.id for e in wc_equip]),
                        f"eq_p{part.id}_s{step_id}")
                    task_equip_vars[key] = equip_var

                    for equip in wc_equip:
                        assigned = model.new_bool_var(f"eq_{part.id}_{step_id}_{equip.id}")
                        model.add(equip_var == equip.id).only_enforce_if(assigned)
                        model.add(equip_var != equip.id).only_enforce_if(~assigned)
                        target_dur = dur_preferred if step_id in equip.dialed_in_steps else dur_normal
                        model.add(dur_var == target_dur).only_enforce_if(assigned)
                        task_equip_bools[(key, equip.id)] = assigned
                else:
                    dur = max(1, int(raw_wall / eff))
                    start = model.new_int_var(0, MAX_HORIZON, f"s_p{part.id}_s{step_id}")
                    end = model.new_int_var(0, MAX_HORIZON, f"e_p{part.id}_s{step_id}")
                    interval = model.new_interval_var(start, dur, end, f"iv_p{part.id}_s{step_id}")
                    task_durations[key] = dur
                    task_durations_max[key] = dur

                    if len(wc_equip) > 1:
                        equip_var = model.new_int_var_from_domain(
                            cp_model.Domain.from_values([e.id for e in wc_equip]),
                            f"eq_p{part.id}_s{step_id}")
                        task_equip_vars[key] = equip_var
                        for equip in wc_equip:
                            assigned = model.new_bool_var(f"eq_{part.id}_{step_id}_{equip.id}")
                            model.add(equip_var == equip.id).only_enforce_if(assigned)
                            model.add(equip_var != equip.id).only_enforce_if(~assigned)
                            task_equip_bools[(key, equip.id)] = assigned

                task_starts[key] = start
                task_ends[key] = end
                task_intervals[key] = interval
                task_first_piece[key] = max(1, int(first_piece / eff))
                task_meta[key] = {"part": part, "step": step, "wo": wo, "wc": wc}

    if not quiet:
        print(f"\n  Tasks: {len(task_starts)}")

    # -- Constraints --
    _add_precedence(model, all_keys, task_starts, task_ends, task_first_piece,
                    task_meta, continuous_availability, constraint_counts)
    _add_fpi_ordering(model, all_keys, task_starts, task_ends, task_meta, constraint_counts)
    max_horizon_days = MAX_HORIZON // MINUTES_PER_DAY
    overtime_vars = _add_time_windows(model, all_keys, task_starts, task_ends, task_durations_max, max_horizon_days, constraint_counts)
    _add_calibration_windows(model, all_keys, task_ends, task_equip_bools, op_equip, constraint_counts)
    _add_capacity(model, all_keys, task_starts, task_ends, task_durations, task_intervals,
                  task_equip_vars, task_equip_bools, op_equip, constraint_counts)
    _add_fixtures(model, all_keys, task_intervals, constraint_counts)
    qa_ends = _add_qa_signoff(model, all_keys, task_starts, task_ends, task_intervals, task_meta, constraint_counts)

    # -- Objective --
    objective_terms = []

    # Overtime premium
    if ALLOW_OVERTIME and overtime_vars:
        for ot_var in overtime_vars:
            objective_terms.append(ot_var * weights.overtime_cost)

    # Late delivery penalties
    lateness_vars = {}
    priority_weights = {1: weights.lateness_urgent, 2: weights.lateness_high, 3: weights.lateness_normal}
    for wo in WORK_ORDERS:
        lateness = model.new_int_var(0, MAX_HORIZON, f"late_wo{wo.id}")
        for part in wo.parts:
            last_key = (part.id, part.remaining_steps[-1])
            if last_key in qa_ends:
                model.add(lateness >= qa_ends[last_key] - wo.due_date_minutes)
            elif last_key in task_ends:
                model.add(lateness >= task_ends[last_key] - wo.due_date_minutes)
        lateness_vars[wo.id] = lateness
        objective_terms.append(lateness * priority_weights[wo.priority])

    # Makespan
    makespan = model.new_int_var(0, MAX_HORIZON, "makespan")
    for key in task_ends:
        model.add(makespan >= task_ends[key])
    objective_terms.append(makespan * weights.makespan_weight)

    # Customer batching
    batch_count = _add_batching(model, all_keys, task_starts, task_meta, objective_terms, weights, constraint_counts)

    # Machine affinity
    affinity_count = _add_machine_affinity(model, all_keys, task_equip_bools, op_equip, objective_terms, weights, constraint_counts)

    model.minimize(sum(objective_terms))

    # -- Solve --
    if not quiet:
        print(f"\n  Constraints:")
        for name, count in constraint_counts.items():
            print(f"    {name:35s} {count}")
        print(f"\n  {'=' * 60}")
        print(f"  SOLVING (Layer 1: Machine Schedule)...")
        print(f"  {'=' * 60}")

    import os
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_workers = os.cpu_count() or 8
    # Ensure 3 default_lp instances for efficient optimality proofs.
    # CP-SAT defaults to 2 below 10 workers; 2 extra guarantees 3 at any thread count.
    solver.parameters.extra_subsolvers.extend(['default_lp', 'default_lp'])
    status = solver.solve(model)

    status_names = {
        cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID",
    }
    if not quiet:
        print(f"\n  Status: {status_names.get(status, str(status))}")
        print(f"  Solve time: {solver.wall_time:.3f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if not quiet:
            print("  No feasible solution!")
        return None

    if not quiet:
        print(f"  Makespan: {solver.value(makespan)} min ({solver.value(makespan) / MINUTES_PER_DAY:.1f} days)")

    # -- Extract schedule --
    schedule = _extract_schedule(solver, all_keys, task_starts, task_ends, task_durations,
                                 task_equip_vars, task_meta, op_equip)

    if not quiet:
        print_machine_report(solver, schedule, lateness_vars)

    return {
        "schedule": schedule,
        "makespan": solver.value(makespan),
        "late_orders": {wo.id: solver.value(lateness_vars[wo.id]) for wo in WORK_ORDERS},
        "solve_time": solver.wall_time,
        "weights": weights.name,
    }


# -- Constraint builders (called by build_machine_schedule) --

def _add_precedence(model, all_keys, task_starts, task_ends, task_first_piece,
                    task_meta, continuous_availability, counts):
    """DAG ordering with transfer batch overlap, wait/move times, and continuous machine feeds."""
    prec_count, transfer_count, continuous_count = 0, 0, 0
    op_equip = _operational_equipment()

    for wo in WORK_ORDERS:
        for part in wo.parts:
            steps = part.remaining_steps
            for i in range(len(steps) - 1):
                from_key = (part.id, steps[i])
                to_key = (part.id, steps[i + 1])

                # Case 1: Continuous machine feeds into job shop step
                # The continuous machine produces parts at a known rate.
                # The downstream job shop step can start when the first piece is ready
                # (transfer batch from continuous → job shop).
                if from_key in continuous_availability:
                    if to_key not in task_starts:
                        continue
                    cm_info = continuous_availability[from_key]
                    if part.quantity > 1:
                        # First piece available after changeover + 1 cycle
                        model.add(task_starts[to_key] >= cm_info["first_piece_time"])
                    else:
                        model.add(task_starts[to_key] >= cm_info["all_done_minute"])
                    continuous_count += 1
                    continue

                # Case 2: Job shop step feeds into continuous machine step
                # (rare — usually continuous is upstream. Skip for now.)
                if to_key in continuous_availability:
                    continue

                # Case 3: Normal job shop → job shop precedence
                if from_key not in task_ends or to_key not in task_starts:
                    continue

                wait = WAIT_TIMES.get((steps[i], steps[i + 1]), 0)
                from_step = STEPS.get(steps[i])
                to_step = STEPS.get(steps[i + 1])
                if from_step and to_step:
                    wc_from = WORKCENTERS[from_step.workcenter_id]
                    wc_to = WORKCENTERS[to_step.workcenter_id]
                    eq_from = next((op_equip[eid] for eid in wc_from.equipment_ids if eid in op_equip), None)
                    eq_to = next((op_equip[eid] for eid in wc_to.equipment_ids if eid in op_equip), None)
                    move = get_transport_time(eq_from.location, eq_to.location) if eq_from and eq_to else 0
                else:
                    move = 0
                interop_gap = max(wait, move)

                if ENABLE_TRANSFER_BATCH and part.quantity > 1:
                    offset = task_first_piece[from_key] + interop_gap
                    model.add(task_starts[to_key] >= task_starts[from_key] + offset)
                    transfer_count += 1
                else:
                    model.add(task_starts[to_key] >= task_ends[from_key] + interop_gap)
                prec_count += 1

    counts["Precedence (DAG+wait+move)"] = prec_count
    counts["Transfer batch overlaps"] = transfer_count
    counts["Continuous machine feeds"] = continuous_count


def _add_fpi_ordering(model, all_keys, task_starts, task_ends, task_meta, counts):
    """First Piece Inspection: earliest FPI candidate must complete before non-FPI tasks."""
    fpi_count = 0
    for step_id, step in STEPS.items():
        if not step.requires_first_piece_inspection:
            continue
        fpi_keys = [k for k in all_keys if k[1] == step_id and k in task_starts
                     and task_meta[k]["part"].is_fpi_candidate]
        non_fpi_keys = [k for k in all_keys if k[1] == step_id and k in task_starts
                         and not task_meta[k]["part"].is_fpi_candidate]
        if not fpi_keys or not non_fpi_keys:
            continue

        if len(fpi_keys) == 1:
            for nk in non_fpi_keys:
                model.add(task_starts[nk] >= task_ends[fpi_keys[0]])
                fpi_count += 1
        else:
            fpi_min_end = model.new_int_var(0, MAX_HORIZON, f"fpi_min_{step_id}")
            model.add_min_equality(fpi_min_end, [task_ends[fk] for fk in fpi_keys])
            for nk in non_fpi_keys:
                model.add(task_starts[nk] >= fpi_min_end)
                fpi_count += 1

    counts["Precedence (FPI)"] = fpi_count


def _add_time_windows(model, all_keys, task_starts, task_ends, task_durations_max, max_horizon_days, counts):
    """Shift blocks with lunch break. Tasks must fit in a single block. Returns overtime vars."""
    num_schedule_days = max_horizon_days  # cover the full domain
    valid_blocks = []
    for day in range(num_schedule_days):
        d = day * MINUTES_PER_DAY
        valid_blocks.append((d, d + LUNCH_START_OFFSET, None))
        if ALLOW_OVERTIME:
            valid_blocks.append((d + LUNCH_START_OFFSET + LUNCH_DURATION,
                                d + MINUTES_PER_DAY + MAX_OVERTIME_MINUTES, d + MINUTES_PER_DAY))
        else:
            valid_blocks.append((d + LUNCH_START_OFFSET + LUNCH_DURATION, d + MINUTES_PER_DAY, None))

    overtime_vars = []
    tw_count = 0
    for key in all_keys:
        if key not in task_starts:
            continue
        max_dur = task_durations_max[key]
        block_bools = []
        for i, (block_start, block_end, ot_start) in enumerate(valid_blocks):
            if block_end - block_start < max_dur:
                continue
            block_bool = model.new_bool_var(f"blk_{key[0]}_{key[1]}_{i}")
            model.add(task_starts[key] >= block_start).only_enforce_if(block_bool)
            model.add(task_ends[key] <= block_end).only_enforce_if(block_bool)
            block_bools.append(block_bool)

            if ot_start is not None:
                ot_min = model.new_int_var(0, MAX_OVERTIME_MINUTES, f"ot_{key[0]}_{key[1]}_{i}")
                model.add(ot_min >= task_ends[key] - ot_start).only_enforce_if(block_bool)
                model.add(ot_min == 0).only_enforce_if(~block_bool)
                overtime_vars.append(ot_min)

        if block_bools:
            model.add_exactly_one(block_bools)
            tw_count += 1

    counts["Time windows"] = tw_count
    return overtime_vars


def _add_calibration_windows(model, all_keys, task_ends, task_equip_bools, op_equip, counts):
    """Calibration deadlines scoped to specific equipment, not entire work center."""
    cal_count = 0
    for equip in op_equip.values():
        if equip.days_until_cal_due is None or equip.days_until_cal_due > 5:
            continue
        cal_cutoff = equip.days_until_cal_due * MINUTES_PER_DAY
        wc = next((w for w in WORKCENTERS.values() if equip.id in w.equipment_ids), None)
        if not wc:
            continue
        for key in all_keys:
            if key not in task_ends or key[1] not in wc.step_ids:
                continue
            equip_bool = task_equip_bools.get((key, equip.id))
            if equip_bool is not None:
                model.add(task_ends[key] <= cal_cutoff).only_enforce_if(equip_bool)
                cal_count += 1
            elif len([eid for eid in wc.equipment_ids if eid in op_equip]) == 1:
                model.add(task_ends[key] <= cal_cutoff)
                cal_count += 1

    counts["Calibration windows"] = cal_count


def _add_capacity(model, all_keys, task_starts, task_ends, task_durations, task_intervals,
                  task_equip_vars, task_equip_bools, op_equip, counts):
    """Work center capacity: no-overlap per equipment + changeover times."""
    capacity_count, changeover_count = 0, 0

    for wc in WORKCENTERS.values():
        wc_equip = [op_equip[eid] for eid in wc.equipment_ids if eid in op_equip]
        effective_capacity = min(len(wc_equip), wc.batch_capacity)
        if effective_capacity == 0:
            continue

        wc_tasks = [k for k in all_keys if k in task_intervals and k[1] in wc.step_ids]
        if not wc_tasks:
            continue

        if len(wc_equip) > 1 and any(k in task_equip_vars for k in wc_tasks):
            for equip in wc_equip:
                equip_intervals = []
                for k in wc_tasks:
                    equip_bool = task_equip_bools.get((k, equip.id))
                    if equip_bool is not None:
                        opt = model.new_optional_interval_var(
                            task_starts[k], task_durations[k], task_ends[k],
                            equip_bool, f"opt_eq{equip.id}_p{k[0]}_s{k[1]}")
                        equip_intervals.append(opt)
                    else:
                        equip_intervals.append(task_intervals[k])
                if equip_intervals:
                    model.add_no_overlap(equip_intervals)
                    capacity_count += 1
        elif effective_capacity == 1:
            model.add_no_overlap([task_intervals[k] for k in wc_tasks])
            capacity_count += 1
            if wc.changeover_time:
                for i, ka in enumerate(wc_tasks):
                    for kb in wc_tasks[i + 1:]:
                        step_a, step_b = ka[1], kb[1]
                        co_a_to_b = wc.changeover_time.get((step_a, step_b), 0)
                        co_b_to_a = wc.changeover_time.get((step_b, step_a), 0)
                        if co_a_to_b > 0 or co_b_to_a > 0:
                            a_before_b = model.new_bool_var(f"co_{wc.id}_{ka[0]}s{step_a}_b4_{kb[0]}s{step_b}")
                            if co_a_to_b > 0:
                                model.add(task_starts[kb] >= task_ends[ka] + co_a_to_b).only_enforce_if(a_before_b)
                            if co_b_to_a > 0:
                                model.add(task_starts[ka] >= task_ends[kb] + co_b_to_a).only_enforce_if(~a_before_b)
                            changeover_count += 1
        else:
            model.add_cumulative([task_intervals[k] for k in wc_tasks], [1] * len(wc_tasks), effective_capacity)
            capacity_count += 1

    counts["Work center / equipment"] = capacity_count
    counts["Changeover pairs"] = changeover_count


def _add_fixtures(model, all_keys, task_intervals, counts):
    """Fixture availability as cumulative constraints."""
    fixture_count = 0
    for fixture in FIXTURES.values():
        fixture_tasks = [k for k in all_keys if k in task_intervals
                         and STEPS[k[1]].required_fixture_id == fixture.id]
        if len(fixture_tasks) > fixture.quantity:
            model.add_cumulative(
                [task_intervals[k] for k in fixture_tasks],
                [1] * len(fixture_tasks), fixture.quantity)
            fixture_count += 1
    counts["Fixture constraints"] = fixture_count


def _add_qa_signoff(model, all_keys, task_starts, task_ends, task_intervals, task_meta, counts):
    """QA sign-off as a serialized secondary resource. Returns qa_ends dict."""
    qa_ends_dict = {}
    qa_intervals = []
    qa_count = 0

    for key in all_keys:
        if key not in task_ends:
            continue
        step = STEPS[key[1]]
        if not step.requires_qa_signoff:
            continue

        qa_start = model.new_int_var(0, MAX_HORIZON, f"qa_s_{key[0]}_{key[1]}")
        qa_end = model.new_int_var(0, MAX_HORIZON, f"qa_e_{key[0]}_{key[1]}")
        qa_interval = model.new_interval_var(qa_start, QA_SIGNOFF_DURATION, qa_end,
                                              f"qa_iv_{key[0]}_{key[1]}")
        model.add(qa_start >= task_ends[key])

        # Block next step until QA is done
        part = task_meta[key]["part"]
        steps = part.remaining_steps
        idx = steps.index(key[1]) if key[1] in steps else -1
        if 0 <= idx < len(steps) - 1:
            next_key = (part.id, steps[idx + 1])
            if next_key in task_starts:
                model.add(task_starts[next_key] >= qa_end)

        qa_ends_dict[key] = qa_end
        qa_intervals.append(qa_interval)
        qa_count += 1

    if qa_intervals:
        model.add_no_overlap(qa_intervals)
    counts["QA sign-offs"] = qa_count
    return qa_ends_dict


def _add_batching(model, all_keys, task_starts, task_meta, objective_terms, weights, counts):
    """Customer batching: minimize time spread of same-customer jobs at same work center."""
    cust_groups = defaultdict(list)
    for key in all_keys:
        if key not in task_starts:
            continue
        wo = task_meta[key]["wo"]
        wc = task_meta[key]["wc"]
        cust_groups[(wo.customer, wc.name)].append(key)

    batch_count = 0
    for group, keys in cust_groups.items():
        if len(keys) < 2:
            continue
        group_start = model.new_int_var(0, MAX_HORIZON, f"gs_{group[0]}_{group[1]}")
        group_end = model.new_int_var(0, MAX_HORIZON, f"ge_{group[0]}_{group[1]}")
        for key in keys:
            model.add(group_start <= task_starts[key])
            model.add(group_end >= task_starts[key])
        spread = model.new_int_var(0, MAX_HORIZON, f"sp_{group[0]}_{group[1]}")
        model.add(spread == group_end - group_start)
        objective_terms.append(spread * weights.batching_weight)
        batch_count += 1

    counts["Batching preferences"] = batch_count
    return batch_count


def _add_machine_affinity(model, all_keys, task_equip_bools, op_equip, objective_terms, weights, counts):
    """Soft penalty for using non-preferred (non-dialed-in) equipment."""
    affinity_count = 0
    for key in all_keys:
        if key not in {k for k, _ in task_equip_bools}:
            continue
        step = STEPS[key[1]]
        wc = WORKCENTERS[step.workcenter_id]
        for equip in [op_equip[eid] for eid in wc.equipment_ids if eid in op_equip]:
            equip_bool = task_equip_bools.get((key, equip.id))
            if equip_bool is None:
                continue
            if step.id not in equip.dialed_in_steps:
                objective_terms.append(equip_bool * weights.machine_affinity_weight)
                affinity_count += 1

    counts["Machine affinity prefs"] = affinity_count
    return affinity_count


def _extract_schedule(solver, all_keys, task_starts, task_ends, task_durations,
                      task_equip_vars, task_meta, op_equip):
    """Pull solved values into a list of task dicts."""
    schedule = []
    for key in all_keys:
        if key not in task_starts:
            continue
        sv = solver.value(task_starts[key])
        ev = solver.value(task_ends[key])
        meta = task_meta[key]
        step, part, wo, wc = meta["step"], meta["part"], meta["wo"], meta["wc"]

        equip_id, equip_name = None, None
        if key in task_equip_vars:
            equip_id = solver.value(task_equip_vars[key])
            equip_name = EQUIPMENT[equip_id].name
        else:
            wc_eq = [op_equip[eid] for eid in wc.equipment_ids if eid in op_equip]
            if len(wc_eq) == 1:
                equip_id = wc_eq[0].id
                equip_name = wc_eq[0].name

        fixture_name = FIXTURES[step.required_fixture_id].name if step.required_fixture_id else None

        schedule.append({
            "start": sv, "end": ev, "duration": ev - sv,
            "operator_attended": step.timing.operator_attended_time(part.quantity),
            "operator_free": step.timing.operator_free_time(part.quantity),
            "part_id": part.id, "step_id": step.id,
            "step": step.name, "quantity": part.quantity,
            "attention_type": step.timing.attention_type,
            "workcenter": wc.name, "workcenter_id": wc.id,
            "equipment": equip_name, "equipment_id": equip_id,
            "work_order": wo.name, "wo_id": wo.id,
            "customer": wo.customer, "priority": wo.priority,
            "is_rework": step.step_type == "REWORK",
            "is_fpi": part.is_fpi_candidate and step.requires_first_piece_inspection,
            "qa_required": step.requires_qa_signoff,
            "fixture": fixture_name,
        })

    schedule.sort(key=lambda t: (t["start"], t["priority"]))
    return schedule


# =====================================================================
# 6. LAYER 2: OPERATOR DISPATCH
# =====================================================================

# Dispatch scoring constants
SCORE_CERT_COVERAGE = 10        # per step the operator is certified for at this WC
SCORE_QA_NEED = 30              # QA inspector assigned to QA-required work center
SCORE_STEP_PREFERENCE = 15      # operator prefers this step type
SCORE_SPEED_BONUS = 20          # per 0.1 speed_factor above 1.0
SCORE_WC_STICKINESS = 30        # bonus for staying at same work center
SCORE_TRAVEL_PENALTY_PER_MIN = 1  # penalty per minute of transport to new WC


def generate_dispatch(machine_schedule, quiet=False):
    """Assign operators to work centers per shift, then build dispatch lists."""
    schedule = machine_schedule["schedule"]

    # -- Step 1: Group tasks by (day, work_center) --
    day_wc_tasks = defaultdict(list)
    for task in schedule:
        day = task["start"] // MINUTES_PER_DAY
        day_wc_tasks[(day, task["workcenter_id"])].append(task)

    # -- Step 2: Assign operators to work centers per day --
    day_assignments = {}
    operator_day_wc = {}
    days_with_work = sorted(set(t["start"] // MINUTES_PER_DAY for t in schedule))

    for day in days_with_work:
        active_wcs = [(wc_id, tasks) for (d, wc_id), tasks in day_wc_tasks.items() if d == day]
        active_wcs.sort(key=lambda x: -sum(t["operator_attended"] for t in x[1]))
        assigned_today = set()

        for wc_id, tasks in active_wcs:
            step_ids = set(t["step_id"] for t in tasks)
            needs_qa = any(t["qa_required"] for t in tasks)
            total_attended = sum(t["operator_attended"] for t in tasks)
            ops_needed = max(1, math.ceil(total_attended / (MINUTES_PER_DAY - LUNCH_DURATION)))

            candidates = []
            for op in OPERATORS.values():
                if op.id in assigned_today:
                    continue
                if day == 0 and op.available_from > MINUTES_PER_DAY:
                    continue
                certified_overlap = step_ids & set(op.certified_steps)
                if not certified_overlap:
                    continue

                score = len(certified_overlap) * SCORE_CERT_COVERAGE
                if needs_qa and op.is_qa_inspector:
                    score += SCORE_QA_NEED
                score += len(step_ids & set(op.preferred_steps)) * SCORE_STEP_PREFERENCE
                score += (op.speed_factor - 1.0) * SCORE_SPEED_BONUS * 10
                candidates.append((op, score))

            candidates.sort(key=lambda x: -x[1])
            assigned_ops = []
            for op, _ in candidates[:ops_needed]:
                assigned_ops.append(op.id)
                assigned_today.add(op.id)
                operator_day_wc[(day, op.id)] = wc_id
            day_assignments[(day, wc_id)] = assigned_ops

    # -- Step 3: Assign tasks to stationed operators --
    assignments = []
    operator_timeline = {op_id: [] for op_id in OPERATORS}
    sorted_tasks = sorted(schedule, key=lambda t: (t["priority"], t["start"]))

    for task in sorted_tasks:
        day = task["start"] // MINUTES_PER_DAY
        stationed_ops = day_assignments.get((day, task["workcenter_id"]), [])
        best_op = _find_best_operator(task, stationed_ops, operator_timeline)

        # Fallback: try any available operator
        if best_op is None:
            best_op = _find_best_operator(task, list(OPERATORS.keys()), operator_timeline)

        if best_op is not None:
            a_start, a_end = attend_window(task)
            operator_timeline[best_op.id].append((a_start, a_end))
            assignments.append({**task, "operator": best_op.name, "operator_id": best_op.id})
        else:
            assignments.append({**task, "operator": "UNASSIGNED", "operator_id": None})

    assignments.sort(key=lambda t: (t["start"], t["priority"]))

    if not quiet:
        print_dispatch_report(assignments, day_assignments, operator_day_wc, days_with_work)

    return assignments


def _find_best_operator(task, candidate_ids, operator_timeline):
    """Score and pick the best available operator for a task."""
    best_op, best_score = None, -999
    a_start, a_end = attend_window(task)

    for op_id in candidate_ids:
        op = OPERATORS[op_id]
        if task["step_id"] not in op.certified_steps:
            continue
        if task["start"] < op.available_from:
            continue

        # Check time conflict
        conflict = any(a_start < ee and a_end > es for es, ee in operator_timeline[op.id])
        if conflict:
            continue

        score = 0
        if task["step_id"] in op.preferred_steps:
            score += SCORE_STEP_PREFERENCE
        if task["qa_required"] and op.is_qa_inspector:
            score += SCORE_QA_NEED
        score += (op.speed_factor - 1.0) * SCORE_SPEED_BONUS * 10

        if score > best_score:
            best_score = score
            best_op = op

    return best_op


# =====================================================================
# 7. REPORTING
# =====================================================================

def print_machine_report(solver, schedule, lateness_vars):
    """Print Layer 1 output: machine schedule, utilization, costs."""
    sep = "-" * 85

    # -- WO Status --
    print(f"\n  {sep}")
    print(f"  WORK ORDER STATUS")
    print(f"  {sep}")
    for wo in WORK_ORDERS:
        late = solver.value(lateness_vars[wo.id])
        status = "ON TIME" if late == 0 else f"LATE {late}m ({late/60:.1f}h)"
        print(f"    {wo.name} [{wo.customer}]: {status}")

    # -- Machine Schedule --
    print(f"\n  {sep}")
    print(f"  MACHINE SCHEDULE")
    print(f"  {sep}")
    print(f"    {'Time':12s}  {'Equipment':22s}  {'Step':16s}  "
          f"{'Part':6s}  {'Qty':3s}  {'Dur':5s}  {'Fixture':22s}  WO")

    current_wo = None
    for task in schedule:
        if task["work_order"] != current_wo:
            if current_wo is not None:
                print()  # blank line between WOs
            current_wo = task["work_order"]

        flags = ""
        if task["is_rework"]: flags += " *RW*"
        if task["is_fpi"]: flags += " *FPI*"
        if task["qa_required"]: flags += " [QA]"

        print(f"    {fmt_time(task['start']):12s}  {(task['equipment'] or task['workcenter']):22s}  "
              f"{task['step']:16s}  P{task['part_id']:<5d}  x{task['quantity']:<2d}  "
              f"{task['duration']:3d}m  {(task['fixture'] or ''):22s}  {task['work_order']}{flags}")

    # -- Equipment Utilization --
    print(f"\n  {sep}")
    print(f"  EQUIPMENT UTILIZATION")
    print(f"  {sep}")
    for equip in EQUIPMENT.values():
        equip_tasks = [t for t in schedule if t["equipment_id"] == equip.id]
        total = sum(t["duration"] for t in equip_tasks)
        status_str = "" if equip.status == "IN_SERVICE" else f" [{equip.status}]"
        dialed = f"  dialed:{','.join(STEPS[s].name for s in equip.dialed_in_steps)}" if equip.dialed_in_steps else ""
        if total > 0 or equip.status == "IN_SERVICE":
            print(f"    {equip.name:22s}: {len(equip_tasks):2d} ops  {total:4d}m  "
                  f"{total/HORIZON*100:5.1f}% util{status_str}{dialed}")

    # -- Time Elements --
    print(f"\n  {sep}")
    print(f"  TIME ELEMENTS")
    print(f"  {sep}")
    total_wall = sum(t["duration"] for t in schedule)
    total_attended = sum(t["operator_attended"] for t in schedule)
    total_free = sum(t["operator_free"] for t in schedule)
    print(f"    Machine wall time:       {total_wall:4d}m")
    print(f"    Operator attended time:   {total_attended:4d}m  ({total_attended/max(total_wall,1)*100:.0f}%)")
    print(f"    Operator free time:       {total_free:4d}m  ({total_free/max(total_wall,1)*100:.0f}% -- multi-machine tending)")

    # -- Cost Summary --
    print(f"\n  {sep}")
    print(f"  COST SUMMARY (shop rate: ${SHOP_RATE_PER_HOUR}/hr, OT: {OVERTIME_MULTIPLIER}x)")
    print(f"  {sep}")

    labor_cost = total_attended * SHOP_RATE_PER_HOUR / 60
    ot_minutes_total = sum(task_overtime_minutes(t) for t in schedule)
    ot_premium = ot_minutes_total * SHOP_RATE_PER_HOUR * (OVERTIME_MULTIPLIER - 1) / 60

    total_late_cost = 0
    for wo in WORK_ORDERS:
        late = solver.value(lateness_vars[wo.id])
        if late > 0:
            total_late_cost += (late / MINUTES_PER_DAY) * LATE_PENALTY_PER_DAY[wo.priority]

    print(f"    Labor (attended time):    ${labor_cost:,.0f}")
    print(f"    Overtime premium:         ${ot_premium:,.0f}  ({ot_minutes_total}m)")
    print(f"    Late delivery penalties:  ${total_late_cost:,.0f}")
    print(f"    {'':->50s}")
    print(f"    Total schedule cost:      ${labor_cost + ot_premium + total_late_cost:,.0f}")

    # Per-WO breakdown
    print(f"\n    Per work order:")
    for wo in WORK_ORDERS:
        wo_tasks = [t for t in schedule if t["wo_id"] == wo.id]
        wo_labor = sum(t["operator_attended"] for t in wo_tasks) * SHOP_RATE_PER_HOUR / 60
        wo_ot = sum(task_overtime_minutes(t) for t in wo_tasks)
        wo_ot_cost = wo_ot * SHOP_RATE_PER_HOUR * (OVERTIME_MULTIPLIER - 1) / 60
        late = solver.value(lateness_vars[wo.id])
        wo_late_cost = (late / MINUTES_PER_DAY) * LATE_PENALTY_PER_DAY[wo.priority] if late > 0 else 0
        wo_total = wo_labor + wo_ot_cost + wo_late_cost

        extras = ""
        if wo_ot_cost > 0: extras += f"  OT=${wo_ot_cost:,.0f}"
        if wo_late_cost > 0: extras += f"  late=${wo_late_cost:,.0f}"
        print(f"      {wo.name:30s}  labor=${wo_labor:>7,.0f}{extras}  total=${wo_total:>7,.0f}")

    # -- Fixture Usage --
    print(f"\n  {sep}")
    print(f"  FIXTURE USAGE")
    print(f"  {sep}")
    for fixture in FIXTURES.values():
        fixture_tasks = [t for t in schedule if t["fixture"] == fixture.name]
        if fixture_tasks:
            max_concurrent = 0
            for i, t1 in enumerate(fixture_tasks):
                concurrent = sum(1 for j, t2 in enumerate(fixture_tasks)
                                 if i != j and t2["start"] < t1["end"] and t2["end"] > t1["start"]) + 1
                max_concurrent = max(max_concurrent, concurrent)
            ok = "OK" if max_concurrent <= fixture.quantity else "OVER CAPACITY"
            print(f"    {fixture.name:22s}: {len(fixture_tasks):2d} uses  "
                  f"qty={fixture.quantity}  peak={max_concurrent}  {ok}")


def print_dispatch_report(assignments, day_assignments, operator_day_wc, days_with_work):
    """Print Layer 2 output: shift assignments, dispatch lists, operator workload."""
    sep = "-" * 85

    # -- Shift Assignments (the whiteboard) --
    print(f"\n  {sep}")
    print(f"  SHIFT ASSIGNMENTS (the whiteboard)")
    print(f"  {sep}")
    for day in days_with_work:
        print(f"\n    Day {day + 1}:")
        for wc in WORKCENTERS.values():
            op_ids = day_assignments.get((day, wc.id), [])
            if not op_ids:
                continue
            op_names = [OPERATORS[oid].name for oid in op_ids]
            day_tasks = [a for a in assignments if a["start"] // MINUTES_PER_DAY == day
                         and a["workcenter_id"] == wc.id]
            total_work = sum(t["operator_attended"] for t in day_tasks)
            print(f"      {wc.name:22s}  ->  {', '.join(op_names):20s}  "
                  f"({len(day_tasks)} ops, {total_work}m attended)")

    # -- Dispatch Lists by Day then Work Center --
    print(f"\n  {sep}")
    print(f"  DISPATCH LISTS")
    print(f"  {sep}")
    for day in days_with_work:
        print(f"\n    === Day {day + 1} ===")
        for wc in WORKCENTERS.values():
            day_wc = [a for a in assignments if a["start"] // MINUTES_PER_DAY == day
                       and a["workcenter"] == wc.name]
            if not day_wc:
                continue
            print(f"\n    {wc.name}:")
            print(f"      {'Time':12s}  {'Operator':10s}  {'Step':16s}  "
                  f"{'Part':6s}  {'Qty':3s}  {'Equip':22s}  WO")
            for t in day_wc:
                flags = ""
                if t["is_rework"]: flags += " *RW*"
                if t["qa_required"]: flags += " [QA]"
                print(f"      {fmt_time(t['start']):12s}  {t['operator']:10s}  "
                      f"{t['step']:16s}  P{t['part_id']:<5d}  x{t['quantity']:<2d}  "
                      f"{(t['equipment'] or ''):22s}  {t['work_order']}{flags}")

    # -- Operator Workload --
    print(f"\n  {sep}")
    print(f"  OPERATOR WORKLOAD")
    print(f"  {sep}")
    for op in OPERATORS.values():
        op_tasks = [a for a in assignments if a["operator_id"] == op.id]
        total_attended = sum(a["operator_attended"] for a in op_tasks)
        avail = MINUTES_PER_DAY * len(days_with_work) - op.available_from
        sorted_ops = sorted(op_tasks, key=lambda x: x["start"])
        switches = sum(1 for i in range(1, len(sorted_ops))
                      if sorted_ops[i]["workcenter_id"] != sorted_ops[i-1]["workcenter_id"])

        notes = []
        if op.is_qa_inspector: notes.append("QA")
        if op.available_from > 0: notes.append(f"late +{op.available_from}m")
        note_str = f"  ({', '.join(notes)})" if notes else ""

        stations = set()
        for d in days_with_work:
            if (d, op.id) in operator_day_wc:
                wc_name = WORKCENTERS[operator_day_wc[(d, op.id)]].name
                stations.add(f"D{d+1}:{wc_name}")

        print(f"    {op.name:8s}: {len(op_tasks):2d} ops  attended={total_attended:4d}m  "
              f"util={total_attended/max(avail,1)*100:.0f}%  switches={switches}{note_str}")
        if stations:
            print(f"              stationed: {', '.join(sorted(stations))}")

    unassigned = [a for a in assignments if a["operator_id"] is None]
    if unassigned:
        print(f"\n  UNASSIGNED ({len(unassigned)} tasks):")
        for t in unassigned:
            print(f"    P{t['part_id']} {t['step']} at D{t['start']//MINUTES_PER_DAY+1}")


# =====================================================================
# 8. MAIN
# =====================================================================

if __name__ == "__main__":
    print("=" * 85)
    print("CP-SAT Scheduling Playground")
    print("  Layer 1: Machine Schedule (CP-SAT solver)")
    print("  Layer 2: Operator Dispatch (shift-level assignment)")
    print("=" * 85)

    total_parts = sum(len(wo.parts) for wo in WORK_ORDERS)
    total_pieces = sum(p.quantity for wo in WORK_ORDERS for p in wo.parts)
    op_count = sum(1 for e in EQUIPMENT.values() if e.status == "IN_SERVICE")
    print(f"\n  Shop: {total_parts} part batches ({total_pieces} pieces), "
          f"{len(OPERATORS)} operators, {len(WORKCENTERS)} work centers, "
          f"{len(EQUIPMENT)} equipment ({op_count} operational)")
    print(f"  Schedule: {WORK_DAYS}-day week, {MINUTES_PER_DAY // 60}hr days, "
          f"{SHIFT.start_time.strftime('%H:%M')}-{SHIFT.end_time.strftime('%H:%M')}")

    print(f"\n  Steps:")
    for step in STEPS.values():
        t = step.timing
        fixture = FIXTURES[step.required_fixture_id].name if step.required_fixture_id else None
        fix_str = f"  fixture={fixture}" if fixture else ""
        if t.cycle_time > 0:
            print(f"    {step.name:20s}: setup={t.setup_minutes}m  cycle={t.cycle_time}m/cyc  "
                  f"x{t.pieces_per_cycle}pc/cyc  load={t.load_unload_per_piece}m/pc  "
                  f"attn={t.attention_type}{fix_str}")
        else:
            print(f"    {step.name:20s}: setup={t.setup_minutes}m  "
                  f"manual={t.load_unload_per_piece}m/pc  attn={t.attention_type}{fix_str}")

    if CONTINUOUS_MACHINES:
        print(f"\n  Continuous (lights-out) machines:")
        for cm in CONTINUOUS_MACHINES.values():
            print(f"    {cm.name:30s}: {cm.parts_per_hour} pcs/hr  "
                  f"changeover={cm.changeover_minutes}m  "
                  f"bar change={cm.bar_change_minutes}m every {cm.hours_per_magazine:.1f}hrs  "
                  f"operator touch={cm.operator_touch_per_day()}m/day")

    print(f"\n  Work orders:")
    for wo in WORK_ORDERS:
        print(f"    {wo.name} [{wo.customer}] P{wo.priority} due D{wo.due_date_minutes // MINUTES_PER_DAY}")
        for part in wo.parts:
            flags = ""
            if part.is_fpi_candidate: flags += " [FPI]"
            if part.total_rework_count > 0: flags += f" [REWORK x{part.total_rework_count}]"
            step_names = []
            for s in part.remaining_steps:
                if s in CONTINUOUS_STEPS:
                    step_names.append(f"[{CONTINUOUS_STEPS[s]['name']}]")
                else:
                    step_names.append(STEPS[s].name)
            print(f"      P{part.id} x{part.quantity}: {' -> '.join(step_names)}{flags}")

    # Layer 1: Machine Schedule
    result = build_machine_schedule()

    if result:
        # Layer 2: Operator Dispatch
        generate_dispatch(result)
