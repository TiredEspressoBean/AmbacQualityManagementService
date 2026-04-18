
"""
CP-SAT Component Decision Engine -- Reman "Which Component?" Playground

Uses CP-SAT to optimize component allocation across multiple work orders,
with data structures matching the actual Django models:
  - HarvestedComponent (condition_grade, core, component_type, is_scrapped)
  - Core (condition_grade, core_credit_value, source_type)
  - Parts (part_status, total_rework_count, is_fpi_candidate)
  - WorkOrder (priority, expected_completion, workorder_status)
  - QualityReports (status: PASS/FAIL, step, part)
  - MeasurementResult (value_numeric, is_within_spec)
  - MeasurementDefinition (nominal, upper_tol, lower_tol)
  - QuarantineDisposition (disposition_type, severity, rework_attempt_at_step)
  - DisassemblyBOMLine (expected_fallout_rate, expected_qty)
  - ComponentFlag (flag choices from grading)
  - ComponentCost (source, unit_cost, lead_time_days)

Solver considers:
  - Quality risk (grade + measurements + flags + pass rate history)
  - Defect severity (CRITICAL/MAJOR/MINOR weighting from QualityReportDefect)
  - Core condition context (component grade relative to core grade)
  - Position history (some positions in core run hotter, see more wear)
  - Rework cycle limits (Steps.max_visits, last-chance penalty)
  - Part rework history (Parts.total_rework_count compounds risk)
  - FIFO (older inventory preferred, seals degrade over time)
  - Inventory constraints (each component used at most once)
  - Supply scarcity (DisassemblyBOMLine.expected_fallout_rate predicts future supply)
  - Cross-order allocation (competing demand for scarce Grade A)
  - Schedule pressure (urgent orders penalize rework risk)
  - Cost comparison (harvested cost vs ComponentCost.new_unit_cost)
  - Rework probability (from QualityReports + QuarantineDisposition history)
  - Customer approval risk (QuarantineDisposition.requires_customer_approval adds delay)
  - Margin check (WorkOrder.sale_price vs total expected cost)

Run: python Documents/cpsat_component_decision.py
"""

from ortools.sat.python import cp_model
from dataclasses import dataclass, field
from datetime import date, timedelta


# ===================================================================
# SIMULATED DJANGO MODEL DATA
# These match the actual field names and relationships in:
#   Tracker/models/reman.py
#   Tracker/models/mes_lite.py
#   Tracker/models/qms.py
# ===================================================================

# -- Core (reman.py) --
@dataclass
class Core:
    id: int
    core_number: str
    core_type_id: int          # FK -> PartTypes
    condition_grade: str       # A, B, C, SCRAP
    source_type: str           # CUSTOMER_RETURN, PURCHASED, WARRANTY, TRADE_IN
    core_credit_value: float   # financial value of the core
    status: str                # RECEIVED, IN_DISASSEMBLY, DISASSEMBLED, SCRAPPED
    received_date: date = None
    condition_notes: str = ""


# -- HarvestedComponent (reman.py) --
@dataclass
class HarvestedComponent:
    id: int
    core_id: int               # FK -> Core
    component_type_id: int     # FK -> PartTypes
    component_type_name: str   # denormalized for display
    condition_grade: str       # A, B, C, SCRAP
    is_scrapped: bool
    scrap_reason: str = ""
    position: str = ""         # e.g., "Cyl 1", "Nozzle Bay 3"
    original_part_number: str = ""
    condition_notes: str = ""
    # Derived from component_part -> Parts creation date
    days_in_inventory: int = 0
    # From ComponentFlag model
    flags: list = field(default_factory=list)
    # From MeasurementResult joined through component_part -> Parts -> QualityReports
    # Stored as {measurement_label: deviation_pct} where deviation is 0.0-1.0
    # deviation = abs(value_numeric - nominal) / ((upper_tol - lower_tol) / 2)
    measurement_deviations: dict = field(default_factory=dict)


# -- DisassemblyBOMLine (reman.py) --
@dataclass
class DisassemblyBOMLine:
    id: int
    core_type_id: int          # FK -> PartTypes (the core)
    component_type_id: int     # FK -> PartTypes (expected component)
    expected_qty: int
    expected_fallout_rate: float  # 0.10 = 10%


# -- WorkOrder (mes_lite.py) --
@dataclass
class WorkOrder:
    id: int
    ERP_id: str
    workorder_status: str      # PENDING, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED
    priority: int              # 1=URGENT, 2=HIGH, 3=NORMAL, 4=LOW
    expected_completion: date
    process_id: int            # FK -> Processes
    quantity: int
    related_order_id: int = None  # FK -> Orders
    sale_price: float = 0.0    # from Orders or directly on WO
    customer_name: str = ""


# -- ComponentSlot (derived: each part in a WO that needs a component) --
@dataclass
class ComponentSlot:
    """Represents a part on a work order that needs a specific component type."""
    id: int
    part_id: int               # FK -> Parts
    work_order: WorkOrder
    component_type_id: int     # FK -> PartTypes
    component_type_name: str
    total_rework_count: int = 0  # from Parts.total_rework_count
    remaining_steps: list = field(default_factory=list)  # step IDs still to complete
    remaining_labor_cost: float = 0.0  # precomputed from StepExecution history + PFD + hourly rate


# -- ComponentCost (new model from OR_TOOLS_INTEGRATION.md) --
@dataclass
class ComponentCost:
    id: int
    component_type_id: int     # FK -> PartTypes
    source: str                # NEW, HARVESTED_A, HARVESTED_B, HARVESTED_C
    unit_cost: float
    lead_time_days: int = 0
    effective_date: date = None


# -- Historical quality data (aggregated from QualityReports + MeasurementResult) --
@dataclass
class QualityHistory:
    """Precomputed from QualityReports joined through HarvestedComponent -> component_part -> Parts.
    Split by component_type + grade + core source_type."""
    component_type_id: int
    condition_grade: str       # A, B, C, or NEW
    pass_rate: float           # from QualityReports.status == PASS / total
    avg_rework_minutes: float  # from StepExecution where visit_number > 1
    sample_count: int          # how many data points
    # From QuarantineDisposition history
    rework_success_rate: float  # dispositions where rework succeeded / total rework attempts
    # Per core source_type modifier
    source_pass_rate_modifier: dict = field(default_factory=dict)  # {source_type: +/- adjustment}
    # Defect severity distribution from QualityReportDefect
    # {severity: fraction} -- how failures distribute across severity levels
    defect_severity_distribution: dict = field(default_factory=dict)
    # Per-position modifier from HarvestedComponent.position history
    # {position: pass_rate_modifier}
    position_pass_rate_modifier: dict = field(default_factory=dict)
    # Whether dispositions for this grade typically require customer approval
    # From QuarantineDisposition.requires_customer_approval
    customer_approval_rate: float = 0.0


# -- Defect severity cost multiplier --
# A CRITICAL defect failure costs more than a MINOR one
# (rework is longer, may need customer approval, may require CAPA)
SEVERITY_COST_MULTIPLIER = {
    "CRITICAL": 3.0,   # 3x rework cost -- often involves CAPA, engineering review
    "MAJOR": 1.5,      # 1.5x -- standard rework but more careful
    "MINOR": 0.8,      # 0.8x -- quick fix, sometimes USE_AS_IS is viable
}

# -- Rework cycle limit data (from Steps.max_visits) --
# {component_type_id: max_visits at critical steps}
# If a component fails and this is the last allowed rework, scrap is mandatory
MAX_REWORK_VISITS = {
    20: 2,  # Nozzles: max 2 visits (original + 1 rework)
    21: 3,  # Plungers: max 3 visits (original + 2 reworks)
}

# -- Core condition context --
# A Grade B component from an overall Grade A core is likely better
# than a Grade B from a Grade C core
CORE_GRADE_MODIFIER = {
    # (component_grade, core_grade): score adjustment
    ("A", "A"): +5,    # expected -- component matches core
    ("A", "B"): +8,    # component graded higher than core -- likely cherry pick
    ("A", "C"): +3,    # survived a rough core -- resilient but unusual
    ("B", "A"): -5,    # graded lower than core -- something specific is wrong
    ("B", "B"): 0,     # expected
    ("B", "C"): +3,    # better than the core average
    ("C", "A"): -10,   # bad component from a good core -- concerning
    ("C", "B"): -5,    # expected-ish
    ("C", "C"): 0,     # expected
}

# -- Supply scarcity from DisassemblyBOMLine --
# When a component type has high fallout and low inventory, prefer harvested
# to preserve supply (penalize using Grade A when supply is tight)
SUPPLY_SCARCITY_THRESHOLD = 3  # if fewer than this many Grade A remain, add scarcity bonus


# ===================================================================
# SIMULATED SHOP DATA
# ===================================================================

# Cores that components were harvested from
CORES = [
    Core(1, "CORE-2026-001", core_type_id=10, condition_grade="B",
         source_type="CUSTOMER_RETURN", core_credit_value=250.00,
         status="DISASSEMBLED", received_date=date(2026, 1, 15)),
    Core(2, "CORE-2026-002", core_type_id=10, condition_grade="A",
         source_type="WARRANTY", core_credit_value=180.00,
         status="DISASSEMBLED", received_date=date(2026, 2, 1)),
    Core(3, "CORE-2026-003", core_type_id=10, condition_grade="C",
         source_type="PURCHASED", core_credit_value=120.00,
         status="DISASSEMBLED", received_date=date(2025, 12, 10)),
    Core(4, "CORE-2026-004", core_type_id=10, condition_grade="B",
         source_type="TRADE_IN", core_credit_value=200.00,
         status="DISASSEMBLED", received_date=date(2026, 2, 20)),
]

# Available harvested components (not scrapped, component_part is null = not yet assigned)
INVENTORY = [
    # Nozzles from various cores
    HarvestedComponent(
        1, core_id=2, component_type_id=20, component_type_name="Nozzle",
        condition_grade="A", is_scrapped=False, position="Bay 1",
        days_in_inventory=12, flags=[],
        measurement_deviations={"bore_diameter": 0.05, "spray_angle": 0.02}),
    HarvestedComponent(
        2, core_id=2, component_type_id=20, component_type_name="Nozzle",
        condition_grade="A", is_scrapped=False, position="Bay 2",
        days_in_inventory=3, flags=[],
        measurement_deviations={"bore_diameter": 0.15, "spray_angle": 0.08}),
    HarvestedComponent(
        3, core_id=1, component_type_id=20, component_type_name="Nozzle",
        condition_grade="B", is_scrapped=False, position="Bay 1",
        days_in_inventory=45, flags=["DISCOLORATION"],
        measurement_deviations={"bore_diameter": 0.35, "spray_angle": 0.12}),
    HarvestedComponent(
        4, core_id=4, component_type_id=20, component_type_name="Nozzle",
        condition_grade="B", is_scrapped=False, position="Bay 3",
        days_in_inventory=8, flags=["CLEAN_UNIT"],
        measurement_deviations={"bore_diameter": 0.10, "spray_angle": 0.05}),
    HarvestedComponent(
        5, core_id=1, component_type_id=20, component_type_name="Nozzle",
        condition_grade="B", is_scrapped=False, position="Bay 2",
        days_in_inventory=60, flags=[],
        measurement_deviations={"bore_diameter": 0.25, "spray_angle": 0.18}),
    HarvestedComponent(
        6, core_id=3, component_type_id=20, component_type_name="Nozzle",
        condition_grade="C", is_scrapped=False, position="Bay 1",
        days_in_inventory=90, flags=["WEAR_PATTERN"],
        measurement_deviations={"bore_diameter": 0.55, "spray_angle": 0.40}),
    HarvestedComponent(
        7, core_id=3, component_type_id=20, component_type_name="Nozzle",
        condition_grade="C", is_scrapped=False, position="Bay 2",
        days_in_inventory=30, flags=["CORROSION"],
        measurement_deviations={"bore_diameter": 0.70, "spray_angle": 0.45}),

    # Plungers
    HarvestedComponent(
        8, core_id=2, component_type_id=21, component_type_name="Plunger",
        condition_grade="A", is_scrapped=False, position="Cyl 1",
        days_in_inventory=5, flags=[],
        measurement_deviations={"diameter": 0.08, "runout": 0.03}),
    HarvestedComponent(
        9, core_id=1, component_type_id=21, component_type_name="Plunger",
        condition_grade="B", is_scrapped=False, position="Cyl 2",
        days_in_inventory=20, flags=[],
        measurement_deviations={"diameter": 0.22, "runout": 0.15}),
    HarvestedComponent(
        10, core_id=3, component_type_id=21, component_type_name="Plunger",
        condition_grade="B", is_scrapped=False, position="Cyl 1",
        days_in_inventory=55, flags=["TIGHT_TOLERANCE"],
        measurement_deviations={"diameter": 0.42, "runout": 0.35}),
    HarvestedComponent(
        11, core_id=3, component_type_id=21, component_type_name="Plunger",
        condition_grade="C", is_scrapped=False, position="Cyl 2",
        days_in_inventory=70, flags=["PREV_REPAIR"],
        measurement_deviations={"diameter": 0.60, "runout": 0.50}),
]

# Component costs (from ComponentCost model)
COMPONENT_COSTS = [
    ComponentCost(1, component_type_id=20, source="NEW", unit_cost=150.00, lead_time_days=14),
    ComponentCost(2, component_type_id=20, source="HARVESTED_A", unit_cost=35.00),
    ComponentCost(3, component_type_id=20, source="HARVESTED_B", unit_cost=35.00),
    ComponentCost(4, component_type_id=20, source="HARVESTED_C", unit_cost=35.00),
    ComponentCost(5, component_type_id=21, source="NEW", unit_cost=95.00, lead_time_days=10),
    ComponentCost(6, component_type_id=21, source="HARVESTED_A", unit_cost=22.00),
    ComponentCost(7, component_type_id=21, source="HARVESTED_B", unit_cost=22.00),
    ComponentCost(8, component_type_id=21, source="HARVESTED_C", unit_cost=22.00),
]

# Quality history (precomputed from QualityReports + QuarantineDisposition + QualityReportDefect)
QUALITY_HISTORY = [
    QualityHistory(20, "A", pass_rate=0.95, avg_rework_minutes=40, sample_count=120,
                   rework_success_rate=0.90,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.03,
                                              "WARRANTY": +0.02, "TRADE_IN": -0.01},
                   defect_severity_distribution={"MINOR": 0.70, "MAJOR": 0.25, "CRITICAL": 0.05},
                   position_pass_rate_modifier={"Bay 1": +0.02, "Bay 2": -0.01, "Bay 3": 0.0},
                   customer_approval_rate=0.05),
    QualityHistory(20, "B", pass_rate=0.82, avg_rework_minutes=45, sample_count=85,
                   rework_success_rate=0.78,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.05,
                                              "WARRANTY": +0.03, "TRADE_IN": -0.02},
                   defect_severity_distribution={"MINOR": 0.45, "MAJOR": 0.40, "CRITICAL": 0.15},
                   position_pass_rate_modifier={"Bay 1": +0.03, "Bay 2": -0.02, "Bay 3": -0.01},
                   customer_approval_rate=0.15),
    QualityHistory(20, "C", pass_rate=0.64, avg_rework_minutes=55, sample_count=40,
                   rework_success_rate=0.60,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.08,
                                              "WARRANTY": 0.0, "TRADE_IN": -0.05},
                   defect_severity_distribution={"MINOR": 0.20, "MAJOR": 0.45, "CRITICAL": 0.35},
                   position_pass_rate_modifier={"Bay 1": +0.02, "Bay 2": -0.05, "Bay 3": -0.03},
                   customer_approval_rate=0.40),
    QualityHistory(20, "NEW", pass_rate=0.99, avg_rework_minutes=30, sample_count=200,
                   rework_success_rate=0.95,
                   defect_severity_distribution={"MINOR": 0.90, "MAJOR": 0.10, "CRITICAL": 0.0},
                   customer_approval_rate=0.02),
    QualityHistory(21, "A", pass_rate=0.93, avg_rework_minutes=35, sample_count=95,
                   rework_success_rate=0.88,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.03,
                                              "WARRANTY": +0.02, "TRADE_IN": -0.01},
                   defect_severity_distribution={"MINOR": 0.65, "MAJOR": 0.28, "CRITICAL": 0.07},
                   position_pass_rate_modifier={"Cyl 1": +0.01, "Cyl 2": -0.02},
                   customer_approval_rate=0.08),
    QualityHistory(21, "B", pass_rate=0.78, avg_rework_minutes=42, sample_count=60,
                   rework_success_rate=0.72,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.05,
                                              "WARRANTY": +0.02, "TRADE_IN": -0.03},
                   defect_severity_distribution={"MINOR": 0.40, "MAJOR": 0.42, "CRITICAL": 0.18},
                   position_pass_rate_modifier={"Cyl 1": +0.02, "Cyl 2": -0.04},
                   customer_approval_rate=0.20),
    QualityHistory(21, "C", pass_rate=0.58, avg_rework_minutes=50, sample_count=25,
                   rework_success_rate=0.55,
                   source_pass_rate_modifier={"CUSTOMER_RETURN": 0.0, "PURCHASED": -0.08,
                                              "WARRANTY": 0.0, "TRADE_IN": -0.05},
                   defect_severity_distribution={"MINOR": 0.15, "MAJOR": 0.45, "CRITICAL": 0.40},
                   position_pass_rate_modifier={"Cyl 1": +0.01, "Cyl 2": -0.06},
                   customer_approval_rate=0.45),
    QualityHistory(21, "NEW", pass_rate=0.99, avg_rework_minutes=25, sample_count=150,
                   rework_success_rate=0.95,
                   defect_severity_distribution={"MINOR": 0.90, "MAJOR": 0.10, "CRITICAL": 0.0},
                   customer_approval_rate=0.02),
]

# DisassemblyBOMLine (expected yields)
BOM_LINES = [
    DisassemblyBOMLine(1, core_type_id=10, component_type_id=20, expected_qty=4, expected_fallout_rate=0.15),
    DisassemblyBOMLine(2, core_type_id=10, component_type_id=21, expected_qty=4, expected_fallout_rate=0.12),
]

# Work Orders
today = date(2026, 3, 15)
WORK_ORDERS = [
    WorkOrder(43, "WO-2026-0043", "IN_PROGRESS", priority=1,
              expected_completion=today + timedelta(days=2),
              process_id=1, quantity=2, sale_price=850.00,
              customer_name="AeroJet (AOG)"),
    WorkOrder(42, "WO-2026-0042", "IN_PROGRESS", priority=2,
              expected_completion=today + timedelta(days=5),
              process_id=1, quantity=3, sale_price=720.00,
              customer_name="AeroJet"),
    WorkOrder(41, "WO-2026-0041", "IN_PROGRESS", priority=3,
              expected_completion=today + timedelta(days=12),
              process_id=1, quantity=4, sale_price=650.00,
              customer_name="IndustrialCo"),
]

# Remaining steps and labor cost per slot
# In production: computed from Parts.step (current), process DAG, StepExecution avg durations
# remaining_labor_cost = sum(avg_duration * PFD * hourly_rate) for each remaining step
#
# Step avg durations (from StepExecution): inspection=28, flow=24, assembly=40, final=20, rework=45
# With 30% PFD and $35/hr:
#   inspection: 28*1.3*(35/60) = $21.23
#   flow test:  24*1.3*(35/60) = $18.20
#   assembly:   40*1.3*(35/60) = $30.33
#   final test: 20*1.3*(35/60) = $15.17
#   rework:     45*1.3*(35/60) = $34.12

SLOTS = [
    # WO-43 AOG: 2 parts, almost done
    ComponentSlot(1, part_id=201, work_order=WORK_ORDERS[0], component_type_id=20,
                 component_type_name="Nozzle",
                 remaining_steps=[4, 5, 6],               # flow + assembly + final
                 remaining_labor_cost=63.70),              # 18.20 + 30.33 + 15.17
    ComponentSlot(2, part_id=202, work_order=WORK_ORDERS[0], component_type_id=21,
                 component_type_name="Plunger",
                 remaining_steps=[5, 6],                   # assembly + final
                 remaining_labor_cost=45.50),              # 30.33 + 15.17

    # WO-42 HIGH: 3 parts at various stages
    ComponentSlot(3, part_id=101, work_order=WORK_ORDERS[1], component_type_id=20,
                 component_type_name="Nozzle",
                 remaining_steps=[3, 4, 5, 6],             # inspection + flow + assembly + final
                 remaining_labor_cost=84.93),              # 21.23 + 18.20 + 30.33 + 15.17
    ComponentSlot(4, part_id=102, work_order=WORK_ORDERS[1], component_type_id=20,
                 component_type_name="Nozzle",
                 remaining_steps=[4, 5, 6],
                 remaining_labor_cost=63.70),
    ComponentSlot(5, part_id=103, work_order=WORK_ORDERS[1], component_type_id=21,
                 component_type_name="Plunger",
                 remaining_steps=[5, 6],
                 remaining_labor_cost=45.50),

    # WO-41 NORMAL: 4 parts, one rework
    ComponentSlot(6, part_id=301, work_order=WORK_ORDERS[2], component_type_id=20,
                 component_type_name="Nozzle",
                 remaining_steps=[2, 3, 4, 5, 6],          # cleaning + inspection + flow + assembly + final
                 remaining_labor_cost=99.63),              # cleaning=15.17 + rest
    ComponentSlot(7, part_id=302, work_order=WORK_ORDERS[2], component_type_id=20,
                 component_type_name="Nozzle",
                 remaining_steps=[4, 5, 6],
                 remaining_labor_cost=63.70),
    ComponentSlot(8, part_id=303, work_order=WORK_ORDERS[2], component_type_id=21,
                 component_type_name="Plunger",
                 remaining_steps=[7, 5, 6],                # rework + assembly + final
                 remaining_labor_cost=79.62,               # 34.12 + 30.33 + 15.17
                 total_rework_count=1),
    ComponentSlot(9, part_id=304, work_order=WORK_ORDERS[2], component_type_id=21,
                 component_type_name="Plunger",
                 remaining_steps=[5, 6],
                 remaining_labor_cost=45.50),
]

# Config (from OptimizationConfig model)
HOURLY_RATE = 35.00       # default_hourly_rate
MIN_MARGIN = 0.15         # minimum_margin_pct
FIFO_BONUS_PER_DAY = 0.3  # points per day in inventory
MIN_PASS_RATE = 0.70      # min_pass_rate_for_harvested

# ComponentFlag choices and their quality impact
FLAG_IMPACTS = {
    "DISCOLORATION": -15,
    "CORROSION": -20,
    "SEAL_DAMAGE": -25,
    "TIGHT_TOLERANCE": -10,
    "CONTAMINATION": -15,
    "PREV_REPAIR": -20,
    "CLEAN_UNIT": +15,
    "WEAR_PATTERN": -10,
}


# ===================================================================
# DATA LAYER -- What data.py would produce
# ===================================================================

def get_quality_history(component_type_id, grade):
    """Lookup precomputed quality stats."""
    for qh in QUALITY_HISTORY:
        if qh.component_type_id == component_type_id and qh.condition_grade == grade:
            return qh
    return None


def get_component_cost(component_type_id, source):
    """Lookup ComponentCost."""
    for cc in COMPONENT_COSTS:
        if cc.component_type_id == component_type_id and cc.source == source:
            return cc
    return None


def get_core(core_id):
    """Lookup Core."""
    return next((c for c in CORES if c.id == core_id), None)


def get_adjusted_pass_rate(component):
    """
    Get pass rate adjusted for core source type.
    Joins: HarvestedComponent -> Core -> source_type
           + QualityHistory.source_pass_rate_modifier
    """
    qh = get_quality_history(component.component_type_id, component.condition_grade)
    if not qh:
        return 0.5  # no data fallback

    base_rate = qh.pass_rate
    core = get_core(component.core_id)
    if core and qh.source_pass_rate_modifier:
        modifier = qh.source_pass_rate_modifier.get(core.source_type, 0)
        return min(1.0, max(0.0, base_rate + modifier))
    return base_rate


def compute_quality_score(component):
    """
    Score a HarvestedComponent using data from:
    - HarvestedComponent.condition_grade
    - MeasurementResult (via measurement_deviations)
    - ComponentFlag (via flags)
    - QualityReports history (via QualityHistory)
    - QualityReportDefect.severity (via defect_severity_distribution)
    - Core.condition_grade (core condition context)
    - Core.source_type (via core_id)
    - HarvestedComponent.position (position-based history)

    Returns (score, reasons, adj_pass_rate, severity_weighted_rework_cost)
    """
    score = 0.0
    reasons = []

    # Grade baseline
    grade_scores = {"A": 90, "B": 70, "C": 40}
    base = grade_scores.get(component.condition_grade, 0)
    score += base
    reasons.append(f"Grade {component.condition_grade}: +{base}")

    # Measurement centrality
    for label, deviation in component.measurement_deviations.items():
        centrality = (1 - deviation) * 20
        score += centrality
        if deviation > 0.4:
            reasons.append(f"{label}: {deviation:.0%} from nominal")

    # Flags from ComponentFlag model
    for flag_name in component.flags:
        impact = FLAG_IMPACTS.get(flag_name, 0)
        score += impact
        if impact != 0:
            reasons.append(f"Flag {flag_name}: {impact:+d}")

    # Historical pass rate (adjusted for core source)
    adj_pass_rate = get_adjusted_pass_rate(component)
    pass_score = adj_pass_rate * 20
    score += pass_score
    reasons.append(f"Adj. pass rate {adj_pass_rate:.0%}: +{pass_score:.0f}")

    # --- NEW: Core condition context ---
    # A Grade B component from a Grade A core is suspicious (graded lower than core)
    # A Grade B component from a Grade C core is encouraging (better than core average)
    core = get_core(component.core_id)
    if core:
        core_mod = CORE_GRADE_MODIFIER.get(
            (component.condition_grade, core.condition_grade), 0)
        if core_mod != 0:
            score += core_mod
            direction = "above" if core_mod > 0 else "below"
            reasons.append(f"Core grade {core.condition_grade} context: {core_mod:+d} "
                          f"(component {direction} core avg)")
        reasons.append(f"Core {core.core_number} ({core.source_type})")

    # --- NEW: Position-based pass rate modifier ---
    # Some positions in the core historically yield better/worse components
    qh = get_quality_history(component.component_type_id, component.condition_grade)
    if qh and component.position and qh.position_pass_rate_modifier:
        pos_mod = qh.position_pass_rate_modifier.get(component.position, 0)
        if pos_mod != 0:
            adj_pass_rate = min(1.0, max(0.0, adj_pass_rate + pos_mod))
            pos_score = pos_mod * 100  # convert to score points
            score += pos_score
            reasons.append(f"Position {component.position}: {pos_mod:+.0%} pass rate adj")

    # --- NEW: Defect severity weighted rework cost ---
    # Not just "will it fail?" but "how badly will it fail?"
    # CRITICAL failures cost 3x, MAJOR 1.5x, MINOR 0.8x
    severity_multiplier = 1.0
    if qh and qh.defect_severity_distribution:
        severity_multiplier = sum(
            fraction * SEVERITY_COST_MULTIPLIER.get(sev, 1.0)
            for sev, fraction in qh.defect_severity_distribution.items()
        )
        if severity_multiplier > 1.3:
            reasons.append(f"Severity profile: {severity_multiplier:.1f}x rework cost "
                          f"(high CRITICAL/MAJOR rate)")

    # Compute severity-weighted rework cost
    base_rework_cost = (qh.avg_rework_minutes if qh else 45) * (HOURLY_RATE / 60)
    severity_weighted_rework = base_rework_cost * severity_multiplier

    return score, reasons, adj_pass_rate, severity_weighted_rework


# ===================================================================
# CP-SAT SOLVER
# ===================================================================

def solve_allocation():
    model = cp_model.CpModel()
    SCALE = 100  # CP-SAT needs integers

    # Precompute scores
    scores = {}
    reasons_map = {}
    pass_rates = {}
    severity_rework_costs = {}
    for comp in INVENTORY:
        s, r, pr, swr = compute_quality_score(comp)
        scores[comp.id] = s
        reasons_map[comp.id] = r
        pass_rates[comp.id] = pr
        severity_rework_costs[comp.id] = swr

    # Group inventory by component_type_id
    inv_by_type = {}
    for comp in INVENTORY:
        inv_by_type.setdefault(comp.component_type_id, []).append(comp)

    # -------------------------------------------------------
    # Decision variables: assign[slot_id][component_id or "NEW"] = BoolVar
    # -------------------------------------------------------
    assign = {}
    for slot in SLOTS:
        assign[slot.id] = {}
        available = inv_by_type.get(slot.component_type_id, [])

        for comp in available:
            # Skip if below minimum pass rate threshold
            if pass_rates[comp.id] < MIN_PASS_RATE:
                continue
            assign[slot.id][comp.id] = model.new_bool_var(
                f"assign_s{slot.id}_c{comp.id}")

        assign[slot.id]["NEW"] = model.new_bool_var(f"assign_s{slot.id}_NEW")

    # -------------------------------------------------------
    # Constraint: Each slot gets exactly one component
    # -------------------------------------------------------
    for slot in SLOTS:
        model.add_exactly_one(list(assign[slot.id].values()))

    # -------------------------------------------------------
    # Constraint: Each harvested component used at most once
    # -------------------------------------------------------
    for comp in INVENTORY:
        uses = [assign[slot.id][comp.id]
                for slot in SLOTS
                if comp.id in assign[slot.id]]
        if uses:
            model.add(sum(uses) <= 1)

    # -------------------------------------------------------
    # Constraint: Margin enforcement per work order
    # Total cost (material + rework risk + remaining labor) must leave
    # at least MIN_MARGIN of sale_price.
    # If even NEW can't meet margin, model goes infeasible = "don't take this order"
    # -------------------------------------------------------
    margin_count = 0
    wo_ids_seen = set()
    for slot in SLOTS:
        wo = slot.work_order
        if wo.id in wo_ids_seen:
            continue
        wo_ids_seen.add(wo.id)

        wo_slots = [s for s in SLOTS if s.work_order.id == wo.id]
        max_cost = int(wo.sale_price * (1 - MIN_MARGIN) * SCALE)

        # Sum material + rework risk for all slots (labor is fixed regardless of component)
        wo_cost_terms = []
        for ws in wo_slots:
            # Remaining labor is constant regardless of component choice
            labor_scaled = int(ws.remaining_labor_cost * SCALE)

            available = inv_by_type.get(ws.component_type_id, [])
            for comp in available:
                if comp.id not in assign[ws.id]:
                    continue
                var = assign[ws.id][comp.id]
                cost_key = f"HARVESTED_{comp.condition_grade}"
                cc = get_component_cost(comp.component_type_id, cost_key)
                mat = cc.unit_cost if cc else 35.0
                adj_pr = pass_rates[comp.id]
                swr = severity_rework_costs[comp.id]
                rework = (1 - adj_pr) * swr
                wo_cost_terms.append(var * int((mat + rework) * SCALE))

            # NEW option
            var_new = assign[ws.id]["NEW"]
            cc_new = get_component_cost(ws.component_type_id, "NEW")
            qh_new = get_quality_history(ws.component_type_id, "NEW")
            new_mat = cc_new.unit_cost if cc_new else 150.0
            new_pr = qh_new.pass_rate if qh_new else 0.99
            new_rw_min = qh_new.avg_rework_minutes if qh_new else 30
            new_rework = (1 - new_pr) * new_rw_min * (HOURLY_RATE / 60)
            wo_cost_terms.append(var_new * int((new_mat + new_rework) * SCALE))

            # Add fixed labor cost (same regardless of component)
            wo_cost_terms.append(labor_scaled)

        model.add(sum(wo_cost_terms) <= max_cost)
        margin_count += 1

    print(f"  Margin constraints: {margin_count} work orders "
          f"(min {MIN_MARGIN:.0%} of sale price)")

    # -------------------------------------------------------
    # Objective: Maximize total margin across all work orders
    #
    # Since revenue is fixed (sale_price per WO), maximizing margin =
    # minimizing total expected cost. The cost per assignment includes:
    #   - Material cost (harvested or new)
    #   - Expected rework cost (severity-weighted)
    #   - Risk penalties that translate to expected future cost
    #
    # Secondary factors (FIFO, scarcity, approval delay) adjust the
    # cost to reflect real economic impact beyond direct cost.
    #
    # Labor is NOT in the objective (it's fixed regardless of component
    # choice) but IS in the margin constraint.
    # -------------------------------------------------------
    objective_terms = []

    # Precompute supply scarcity per component type per grade
    supply_counts = {}
    for comp in INVENTORY:
        key = (comp.component_type_id, comp.condition_grade)
        supply_counts[key] = supply_counts.get(key, 0) + 1

    for slot in SLOTS:
        wo = slot.work_order
        priority_weight = {1: 3, 2: 2, 3: 1}.get(wo.priority, 1)
        available = inv_by_type.get(slot.component_type_id, [])

        for comp in available:
            if comp.id not in assign[slot.id]:
                continue
            var = assign[slot.id][comp.id]
            qh = get_quality_history(comp.component_type_id, comp.condition_grade)

            # Direct cost: material
            cost_key = f"HARVESTED_{comp.condition_grade}"
            cc = get_component_cost(comp.component_type_id, cost_key)
            material = int((cc.unit_cost if cc else 35.0) * SCALE)

            # Direct cost: expected rework (severity-weighted)
            swr = severity_rework_costs[comp.id]
            expected_rework = int((1 - pass_rates[comp.id]) * swr * SCALE)

            # Risk cost: if rework fails, the part is scrapped
            # Expected scrap loss = P(fail) * P(rework_fails) * (invested_labor + material)
            rework_success = qh.rework_success_rate if qh else 0.75
            scrap_risk = int(
                (1 - pass_rates[comp.id]) * (1 - rework_success)
                * (slot.remaining_labor_cost + (cc.unit_cost if cc else 35.0))
                * SCALE)

            # FIFO bonus (older stock = economic benefit of turning inventory)
            fifo_bonus = int(comp.days_in_inventory * FIFO_BONUS_PER_DAY * SCALE)

            # Rework cycle limit: if at last chance, scrap risk is ~certain on failure
            max_visits = MAX_REWORK_VISITS.get(comp.component_type_id, 3)
            remaining_attempts = max_visits - 1 - slot.total_rework_count
            last_chance_penalty = 0
            if remaining_attempts <= 0:
                # Next failure = mandatory scrap. Cost = all remaining labor + material wasted
                last_chance_penalty = int(
                    (1 - pass_rates[comp.id])
                    * (slot.remaining_labor_cost + (cc.unit_cost if cc else 35.0))
                    * SCALE)
            elif remaining_attempts == 1:
                # One attempt left. Amplify scrap risk.
                last_chance_penalty = int(scrap_risk * 0.5)

            # Part rework history compounds risk
            rework_history_penalty = int(slot.total_rework_count * 10 * SCALE)

            # Supply scarcity: save Grade A for urgent orders
            scarcity_penalty = 0
            grade_a_count = supply_counts.get((comp.component_type_id, "A"), 0)
            if comp.condition_grade == "A" and grade_a_count <= SUPPLY_SCARCITY_THRESHOLD:
                if wo.priority >= 3:
                    scarcity_penalty = int(30 * SCALE)

            # Customer approval delay risk on tight deadlines
            approval_penalty = 0
            if qh and qh.customer_approval_rate > 0.1:
                days_left = (wo.expected_completion - today).days
                if days_left <= 5:
                    approval_penalty = int(
                        (1 - pass_rates[comp.id]) * qh.customer_approval_rate * 50 * SCALE)

            # Total cost for this assignment
            # Priority weight amplifies all costs for urgent orders
            cost = ((material + expected_rework + scrap_risk) * priority_weight
                    + last_chance_penalty
                    + rework_history_penalty
                    + scarcity_penalty
                    + approval_penalty
                    - fifo_bonus)
            objective_terms.append(var * cost)

        # NEW option: high material cost, near-zero risk
        var_new = assign[slot.id]["NEW"]
        cc_new = get_component_cost(slot.component_type_id, "NEW")
        qh_new = get_quality_history(slot.component_type_id, "NEW")
        new_mat = int((cc_new.unit_cost if cc_new else 150.0) * SCALE)
        new_pass = qh_new.pass_rate if qh_new else 0.99
        new_swr = (qh_new.avg_rework_minutes if qh_new else 30) * (HOURLY_RATE / 60) * 0.82
        new_rework = int((1 - new_pass) * new_swr * SCALE)
        new_scrap_risk = int((1 - new_pass) * 0.05 * slot.remaining_labor_cost * SCALE)

        cost_new = (new_mat + new_rework + new_scrap_risk) * priority_weight
        objective_terms.append(var_new * cost_new)

    model.minimize(sum(objective_terms))

    # -------------------------------------------------------
    # Solve
    # -------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.solve(model)

    status_names = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
                    cp_model.INFEASIBLE: "INFEASIBLE"}

    print(f"\nStatus: {status_names.get(status, str(status))}")
    print(f"Solve time: {solver.wall_time:.3f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No solution found!")
        return

    # -------------------------------------------------------
    # Results
    # -------------------------------------------------------
    print("\n" + "=" * 90)
    print("COMPONENT ALLOCATION")
    print("=" * 90)

    used_ids = set()
    assignments = []

    for slot in SLOTS:
        for option_id, var in assign[slot.id].items():
            if solver.value(var) != 1:
                continue

            wo = slot.work_order
            if option_id == "NEW":
                cc = get_component_cost(slot.component_type_id, "NEW")
                qh = get_quality_history(slot.component_type_id, "NEW")
                assignments.append({
                    "slot": slot,
                    "chosen": "BUY NEW",
                    "grade": "NEW",
                    "material": cc.unit_cost if cc else 150.0,
                    "lead_time": cc.lead_time_days if cc else 14,
                    "pass_rate": qh.pass_rate if qh else 0.99,
                    "rework_cost": (1 - (qh.pass_rate if qh else 0.99)) * (qh.avg_rework_minutes if qh else 30) * (HOURLY_RATE / 60),
                    "age": None,
                    "flags": [],
                    "core_info": None,
                    "reasons": ["New component, near-zero quality risk"],
                    "score": 155.0,
                })
            else:
                comp = next(c for c in INVENTORY if c.id == option_id)
                used_ids.add(comp.id)
                core = get_core(comp.core_id)
                cost_key = f"HARVESTED_{comp.condition_grade}"
                cc = get_component_cost(comp.component_type_id, cost_key)
                qh = get_quality_history(comp.component_type_id, comp.condition_grade)
                adj_pr = pass_rates[comp.id]
                rw_cost = (1 - adj_pr) * (qh.avg_rework_minutes if qh else 45) * (HOURLY_RATE / 60)

                assignments.append({
                    "slot": slot,
                    "chosen": f"HC-{comp.id:04d}",
                    "grade": comp.condition_grade,
                    "material": cc.unit_cost if cc else 35.0,
                    "lead_time": 0,
                    "pass_rate": adj_pr,
                    "rework_cost": rw_cost,
                    "age": comp.days_in_inventory,
                    "flags": comp.flags,
                    "core_info": f"{core.core_number} ({core.source_type})" if core else "?",
                    "reasons": reasons_map[comp.id],
                    "score": scores[comp.id],
                })
            break

    # Print by work order
    current_wo_id = None
    for a in assignments:
        slot = a["slot"]
        wo = slot.work_order
        if wo.id != current_wo_id:
            current_wo_id = wo.id
            days_left = (wo.expected_completion - today).days
            print(f"\n  {wo.ERP_id} [{wo.customer_name}]  "
                  f"Priority: {wo.priority}  Due: {wo.expected_completion} ({days_left}d)  "
                  f"Sale: ${wo.sale_price:.0f}")
            print(f"  {'Part':>6s}  {'Type':>8s}  {'Assigned':>10s}  "
                  f"{'Grade':>5s}  {'Score':>6s}  {'Pass%':>6s}  "
                  f"{'Cost':>7s}  {'RwkRisk':>8s}  {'Age':>5s}  "
                  f"Core/Flags")
            print(f"  {'':->6s}  {'':->8s}  {'':->10s}  "
                  f"{'':->5s}  {'':->6s}  {'':->6s}  "
                  f"{'':->7s}  {'':->8s}  {'':->5s}  "
                  f"{'':->30s}")

        age_str = f"{a['age']}d" if a['age'] is not None else "-"
        flag_str = ", ".join(a["flags"]) if a["flags"] else ""
        core_str = a["core_info"] or ""
        extra = f"{core_str}  {flag_str}".strip()

        margin = (wo.sale_price - a["material"] - a["rework_cost"]) / wo.sale_price
        margin_flag = " !" if margin < MIN_MARGIN else ""

        print(f"  {slot.part_id:>6d}  {slot.component_type_name:>8s}  "
              f"{a['chosen']:>10s}  {a['grade']:>5s}  "
              f"{a['score']:>6.1f}  {a['pass_rate']:>5.0%}  "
              f"${a['material']:>6.2f}  ${a['rework_cost']:>7.2f}  "
              f"{age_str:>5s}  {extra}{margin_flag}")

    # -------------------------------------------------------
    # FIFO Analysis
    # -------------------------------------------------------
    print("\n" + "-" * 90)
    print("FIFO ANALYSIS")
    print("-" * 90)

    for type_name in ["Nozzle", "Plunger"]:
        type_inv = sorted(
            [c for c in INVENTORY if c.component_type_name == type_name],
            key=lambda c: -c.days_in_inventory)
        print(f"\n  {type_name}s (oldest first):")
        for comp in type_inv:
            status = "USED" if comp.id in used_ids else "stock"
            below_min = " <min pass rate" if pass_rates.get(comp.id, 1) < MIN_PASS_RATE else ""
            bar = "#" * min(comp.days_in_inventory // 3, 25)
            flag_str = f" [{', '.join(comp.flags)}]" if comp.flags else ""
            core = get_core(comp.core_id)
            src = core.source_type[:8] if core else "?"
            print(f"    HC-{comp.id:04d}  Gr.{comp.condition_grade}  "
                  f"{comp.days_in_inventory:>3d}d  {bar:25s}  "
                  f"{status:>5s}  {src:>8s}  "
                  f"pass:{pass_rates.get(comp.id, 0):.0%}{flag_str}{below_min}")

    # -------------------------------------------------------
    # Margin Analysis
    # -------------------------------------------------------
    print("\n" + "-" * 90)
    print("MARGIN ANALYSIS")
    print("-" * 90)

    for wo in WORK_ORDERS:
        wo_assignments = [a for a in assignments if a["slot"].work_order.id == wo.id]
        wo_slots = [s for s in SLOTS if s.work_order.id == wo.id]
        total_material = sum(a["material"] for a in wo_assignments)
        total_rework_risk = sum(a["rework_cost"] for a in wo_assignments)
        total_labor = sum(s.remaining_labor_cost for s in wo_slots)
        total_cost = total_material + total_rework_risk + total_labor
        margin = (wo.sale_price - total_cost) / wo.sale_price

        print(f"\n  {wo.ERP_id} [{wo.customer_name}]:")
        print(f"    Revenue:      ${wo.sale_price:.2f}")
        print(f"    Material:     ${total_material:.2f}")
        print(f"    Labor:        ${total_labor:.2f}  (remaining steps * PFD * hourly rate)")
        print(f"    Rework risk:  ${total_rework_risk:.2f}")
        print(f"    Total cost:   ${total_cost:.2f}")
        print(f"    Margin:       {margin:.1%}  "
              f"{'OK' if margin >= MIN_MARGIN else 'BELOW MINIMUM'}")

    # -------------------------------------------------------
    # Skipped Components (below minimum pass rate)
    # -------------------------------------------------------
    skipped = [c for c in INVENTORY
               if c.id not in used_ids
               and pass_rates.get(c.id, 1) < MIN_PASS_RATE]
    if skipped:
        print("\n" + "-" * 90)
        print(f"COMPONENTS EXCLUDED (below {MIN_PASS_RATE:.0%} pass rate threshold)")
        print("-" * 90)
        for comp in skipped:
            core = get_core(comp.core_id)
            flag_str = f" [{', '.join(comp.flags)}]" if comp.flags else ""
            print(f"  HC-{comp.id:04d}  {comp.component_type_name} Gr.{comp.condition_grade}  "
                  f"pass:{pass_rates.get(comp.id, 0):.0%}  "
                  f"from {core.source_type if core else '?'}"
                  f"{flag_str}")

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    print("\n" + "-" * 90)
    print("SUMMARY")
    print("-" * 90)

    total_mat = sum(a["material"] for a in assignments)
    total_rwk = sum(a["rework_cost"] for a in assignments)
    total_rev = sum(a["slot"].work_order.sale_price for a in assignments)
    new_count = sum(1 for a in assignments if a["grade"] == "NEW")
    harvested_count = len(assignments) - new_count
    avg_margin = sum(
        (a["slot"].work_order.sale_price - a["material"] - a["rework_cost"]) / a["slot"].work_order.sale_price
        for a in assignments) / len(assignments)

    print(f"\n  Slots filled:        {len(assignments)}")
    print(f"  Harvested used:      {harvested_count}")
    print(f"  New purchased:       {new_count}")
    print(f"  Total material:      ${total_mat:.2f}")
    print(f"  Expected rework:     ${total_rwk:.2f}")
    print(f"  Total revenue:       ${total_rev:.2f}")
    print(f"  Average margin:      {avg_margin:.1%}")

    remaining = [c for c in INVENTORY if c.id not in used_ids and not c.is_scrapped]
    print(f"\n  Inventory remaining: {len(remaining)} components")
    for type_name in ["Nozzle", "Plunger"]:
        rem = [c for c in remaining if c.component_type_name == type_name]
        if rem:
            by_grade = {}
            for c in rem:
                by_grade[c.condition_grade] = by_grade.get(c.condition_grade, 0) + 1
            gs = ", ".join(f"{g}:{n}" for g, n in sorted(by_grade.items()))
            print(f"    {type_name}: {len(rem)} ({gs})")


# ===================================================================
# MAIN
# ===================================================================

if __name__ == "__main__":
    print("=" * 90)
    print("CP-SAT Component Decision Engine")
    print("Data structures match Django models: reman.py, mes_lite.py, qms.py")
    print("=" * 90)

    # Demand summary
    print(f"\nDemand: {len(SLOTS)} slots across {len(WORK_ORDERS)} work orders")
    for wo in WORK_ORDERS:
        days_left = (wo.expected_completion - today).days
        wo_slots = [s for s in SLOTS if s.work_order.id == wo.id]
        types = {}
        for s in wo_slots:
            types[s.component_type_name] = types.get(s.component_type_name, 0) + 1
        type_str = ", ".join(f"{n}x {t}" for t, n in types.items())
        print(f"  {wo.ERP_id} [{wo.customer_name}]: {type_str}  "
              f"(P{wo.priority}, due {days_left}d, ${wo.sale_price})")

    # Inventory summary
    print(f"\nInventory: {len(INVENTORY)} harvested components from {len(CORES)} cores")
    for type_name in ["Nozzle", "Plunger"]:
        available = [c for c in INVENTORY if c.component_type_name == type_name]
        by_grade = {}
        for c in available:
            by_grade.setdefault(c.condition_grade, []).append(c)
        gs = ", ".join(f"{g}:{len(cs)}" for g, cs in sorted(by_grade.items()))
        demand = sum(1 for s in SLOTS if s.component_type_name == type_name)
        print(f"  {type_name}: {len(available)} avail ({gs}) -- {demand} needed")

    # Cost summary
    print(f"\nComponent costs (from ComponentCost model):")
    for type_name, type_id in [("Nozzle", 20), ("Plunger", 21)]:
        new_cc = get_component_cost(type_id, "NEW")
        harv_cc = get_component_cost(type_id, "HARVESTED_A")
        print(f"  {type_name}: New=${new_cc.unit_cost:.0f} ({new_cc.lead_time_days}d lead), "
              f"Harvested=${harv_cc.unit_cost:.0f}")

    print(f"\nSolver config: min_margin={MIN_MARGIN:.0%}, "
          f"min_pass_rate={MIN_PASS_RATE:.0%}, "
          f"fifo_bonus={FIFO_BONUS_PER_DAY}/day, "
          f"hourly_rate=${HOURLY_RATE}")

    solve_allocation()
