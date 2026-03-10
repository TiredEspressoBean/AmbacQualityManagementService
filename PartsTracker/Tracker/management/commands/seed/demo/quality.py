"""
Demo quality seeder with preset quality reports and dispositions.

Creates:
- Quality reports for parts that failed inspection
- Dispositions (REWORK, USE_AS_IS, SCRAP) in various states
- Quality error lists (common defect types)
- QA approvals for approved dispositions
- SPC baselines (frozen control limits)
- SPC measurement data with rule violations

IMPORTANT: All enum values must be UPPERCASE to match model choices:
- QualityReports.status: 'PASS', 'FAIL', 'PENDING'
- QuarantineDisposition.current_state: 'OPEN', 'IN_PROGRESS', 'CLOSED'
- QuarantineDisposition.disposition_type: 'REWORK', 'REPAIR', 'SCRAP', 'USE_AS_IS', 'RETURN_TO_SUPPLIER'
- QuarantineDisposition.severity: 'CRITICAL', 'MAJOR', 'MINOR'
- MeasurementResult.value_pass_fail: 'PASS', 'FAIL'
"""

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    QualityReports, QuarantineDisposition, MeasurementResult,
    MeasurementDefinition, Parts, Steps, User, QualityErrorsList,
    QaApproval, SPCBaseline, ChartType, BaselineStatus,
    QualityReportDefect,
)

from ..base import BaseSeeder


# Demo quality reports matching DEMO_DATA_SYSTEM.md
# NOTE: All status values must be UPPERCASE: 'PASS', 'FAIL', 'PENDING'
# FPY is calculated from QualityReports, so we need PASS records for realistic FPY metrics
DEMO_QUALITY_REPORTS = [
    # PASSING inspections - completed parts that passed inspection
    # From ORD-2024-0042 (Midwest Fleet) - completed parts
    {'id': 'QR-0042-001-FT', 'part': 'INJ-0042-001', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 121 mL/min - within spec', 'days_ago': 5},
    {'id': 'QR-0042-002-FT', 'part': 'INJ-0042-002', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 118 mL/min - within spec', 'days_ago': 5},
    {'id': 'QR-0042-003-FT', 'part': 'INJ-0042-003', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 122 mL/min - within spec', 'days_ago': 5},
    {'id': 'QR-0042-004-FT', 'part': 'INJ-0042-004', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 119 mL/min - within spec', 'days_ago': 4},
    {'id': 'QR-0042-005-FT', 'part': 'INJ-0042-005', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 120 mL/min - nominal', 'days_ago': 4},
    {'id': 'QR-0042-006-FT', 'part': 'INJ-0042-006', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 117 mL/min - within spec', 'days_ago': 4},
    {'id': 'QR-0042-007-FT', 'part': 'INJ-0042-007', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 123 mL/min - within spec', 'days_ago': 3},
    {'id': 'QR-0042-008-FT', 'part': 'INJ-0042-008', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 121 mL/min - within spec', 'days_ago': 3},
    {'id': 'QR-0042-009-FT', 'part': 'INJ-0042-009', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 118 mL/min - within spec', 'days_ago': 3},
    {'id': 'QR-0042-010-FT', 'part': 'INJ-0042-010', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 120 mL/min - nominal', 'days_ago': 2},
    {'id': 'QR-0042-011-FT', 'part': 'INJ-0042-011', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 119 mL/min - within spec', 'days_ago': 2},
    {'id': 'QR-0042-012-FT', 'part': 'INJ-0042-012', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 122 mL/min - within spec', 'days_ago': 2},
    {'id': 'QR-0042-013-FT', 'part': 'INJ-0042-013', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 121 mL/min - within spec', 'days_ago': 1},
    {'id': 'QR-0042-014-FT', 'part': 'INJ-0042-014', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 118 mL/min - within spec', 'days_ago': 1},
    {'id': 'QR-0042-015-FT', 'part': 'INJ-0042-015', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 120 mL/min - nominal', 'days_ago': 1},
    {'id': 'QR-0042-016-FT', 'part': 'INJ-0042-016', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 117 mL/min - within spec', 'days_ago': 1},
    # From ORD-2024-0038 (Great Lakes) - completed parts that passed
    {'id': 'QR-0038-001-FT', 'part': 'INJ-0038-001', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 119 mL/min - within spec', 'days_ago': 20},
    {'id': 'QR-0038-002-FT', 'part': 'INJ-0038-002', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 121 mL/min - within spec', 'days_ago': 19},
    {'id': 'QR-0038-004-FT', 'part': 'INJ-0038-004', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 120 mL/min - nominal', 'days_ago': 19},
    {'id': 'QR-0038-005-FT', 'part': 'INJ-0038-005', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 118 mL/min - within spec', 'days_ago': 18},
    {'id': 'QR-0038-006-FT', 'part': 'INJ-0038-006', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 122 mL/min - within spec', 'days_ago': 17},
    {'id': 'QR-0038-009-FT', 'part': 'INJ-0038-009', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 119 mL/min - within spec', 'days_ago': 15},
    {'id': 'QR-0038-012-FT', 'part': 'INJ-0038-012', 'step': 'Flow Testing', 'status': 'PASS', 'description': 'Flow rate 120 mL/min - nominal', 'days_ago': 13},
    # FAILING inspections - From ORD-2024-0038 (Great Lakes) - these triggered CAPA-2024-003
    {
        'id': 'QR-0038-003-NI',
        'part': 'INJ-0038-003',
        'step': 'Nozzle Inspection',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Asymmetric spray pattern',
        'description': 'Spray pattern shows uneven distribution - 2 holes partially blocked',
        'days_ago': 18,
        'linked_to_capa': True,
    },
    {
        'id': 'QR-0038-007-NI',
        'part': 'INJ-0038-007',
        'step': 'Nozzle Inspection',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Hole blockage',
        'description': 'Carbon deposits blocking spray holes',
        'days_ago': 17,
        'linked_to_capa': True,
    },
    {
        'id': 'QR-0038-008-FT',
        'part': 'INJ-0038-008',
        'step': 'Flow Testing',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Flow rate out of spec',
        'description': 'Flow rate 145 mL/min exceeds USL of 140 mL/min',
        'days_ago': 16,
        'linked_to_capa': True,
    },
    {
        'id': 'QR-0038-010-NI',
        'part': 'INJ-0038-010',
        'step': 'Nozzle Inspection',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Spray angle drift',
        'description': 'Spray angle 20 degrees - outside 12-18 specification',
        'days_ago': 15,
        'linked_to_capa': True,
    },
    {
        'id': 'QR-0038-011-FT',
        'part': 'INJ-0038-011',
        'step': 'Flow Testing',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Flow rate out of spec',
        'description': 'Flow rate 138 mL/min - SPC rule violation detected',
        'days_ago': 14,
        'linked_to_capa': True,
    },
    # From ORD-2024-0042 (Midwest Fleet) - current order
    {
        'id': 'QR-0042-017-FT',
        'part': 'INJ-0042-017',
        'step': 'Flow Testing',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Flow rate out of spec',
        'description': 'Flow rate 98 mL/min - below LSL of 100 mL/min. Awaiting disposition.',
        'days_ago': 2,
        'linked_to_capa': False,
        'needs_disposition': True,
    },
    {
        'id': 'QR-0042-019-NI',
        'part': 'INJ-0042-019',
        'step': 'Nozzle Inspection',
        'status': 'FAIL',  # UPPERCASE enum value
        'defect': 'Spray pattern failure',
        'description': 'Irregular spray pattern - approved for rework',
        'days_ago': 3,
        'linked_to_capa': False,
        'disposition': 'REWORK',
    },
]

# Demo dispositions
# NOTE: All enum values must be UPPERCASE:
# - current_state: 'OPEN', 'IN_PROGRESS', 'CLOSED'
# - disposition_type: 'REWORK', 'REPAIR', 'SCRAP', 'USE_AS_IS', 'RETURN_TO_SUPPLIER'
# - severity: 'CRITICAL', 'MAJOR', 'MINOR'
DEMO_DISPOSITIONS = [
    {
        'quality_report': 'QR-0042-019-NI',
        'part': 'INJ-0042-019',
        'disposition_type': 'REWORK',  # UPPERCASE enum value
        'current_state': 'IN_PROGRESS',  # UPPERCASE enum value (approved -> in progress)
        'severity': 'MAJOR',  # UPPERCASE enum value - explicitly set, don't rely on default
        'resolution_notes': 'Spray pattern can be corrected by nozzle replacement',
        'days_ago': 2,
    },
    # Completed rework from prior order (shows resolution workflow)
    {
        'quality_report': 'QR-0038-003-NI',
        'part': 'INJ-0038-003',
        'disposition_type': 'REWORK',
        'current_state': 'CLOSED',  # Completed
        'severity': 'MAJOR',
        'resolution_notes': 'Nozzle replaced, spray pattern verified within spec',
        'days_ago': 16,
    },
    # Use-as-is disposition (shows customer approval workflow)
    {
        'quality_report': 'QR-0038-008-FT',
        'part': 'INJ-0038-008',
        'disposition_type': 'USE_AS_IS',
        'current_state': 'CLOSED',
        'severity': 'MINOR',
        'resolution_notes': 'Flow rate 145 mL/min acceptable per customer concession CON-2024-001',
        'days_ago': 14,
    },
    # Scrap disposition (shows irreparable defect workflow)
    {
        'quality_report': 'QR-0038-010-NI',
        'part': 'INJ-0038-010',
        'disposition_type': 'SCRAP',
        'current_state': 'CLOSED',
        'severity': 'CRITICAL',
        'resolution_notes': 'Nozzle damage beyond repair limits. Part scrapped per procedure QP-007.',
        'days_ago': 13,
    },
]

# Demo quality error types (common defect types)
DEMO_QUALITY_ERRORS = [
    {
        'error_name': 'Asymmetric spray pattern',
        'error_example': 'Spray pattern shows uneven distribution due to partially blocked holes',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': True,
    },
    {
        'error_name': 'Hole blockage',
        'error_example': 'Carbon deposits or debris blocking spray holes',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': True,
    },
    {
        'error_name': 'Flow rate out of spec',
        'error_example': 'Flow rate exceeds control limits (LSL: 100 mL/min, USL: 140 mL/min)',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': False,
    },
    {
        'error_name': 'Spray angle drift',
        'error_example': 'Spray angle outside specification (12-18 degrees)',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': True,
    },
    {
        'error_name': 'Surface porosity',
        'error_example': 'Visible pores in nozzle tip indicating casting defect',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': True,
    },
    {
        'error_name': 'Spray pattern failure',
        'error_example': 'Irregular or asymmetric spray pattern not meeting specification',
        'part_type': 'Fuel Injector',
        'requires_3d_annotation': True,
    },
]

# Demo SPC baselines (frozen control limits)
DEMO_SPC_BASELINES = [
    {
        'measurement': 'Flow Rate',
        'chart_type': ChartType.I_MR,
        'subgroup_size': 1,
        # I-MR control limits for Flow Rate (nominal: 120 mL/min)
        'individual_ucl': Decimal('129.000000'),
        'individual_cl': Decimal('120.000000'),
        'individual_lcl': Decimal('111.000000'),
        'mr_ucl': Decimal('10.170000'),
        'mr_cl': Decimal('3.108000'),
        'sample_count': 30,
        'notes': 'Initial baseline from production startup',
        'days_ago': 60,
    },
    {
        'measurement': 'Spray Angle',
        'chart_type': ChartType.I_MR,
        'subgroup_size': 1,
        # I-MR control limits for Spray Angle (nominal: 15 degrees, spec: 12-18)
        'individual_ucl': Decimal('17.500000'),
        'individual_cl': Decimal('15.000000'),
        'individual_lcl': Decimal('12.500000'),
        'mr_ucl': Decimal('3.267000'),
        'mr_cl': Decimal('1.000000'),
        'sample_count': 30,
        'notes': 'Baseline for nozzle spray angle measurement',
        'days_ago': 45,
    },
    {
        'measurement': 'Leak Test Pressure',
        'chart_type': ChartType.I_MR,
        'subgroup_size': 1,
        # I-MR control limits for Leak Test (nominal: 3000 psi, min: 2800)
        'individual_ucl': Decimal('3150.000000'),
        'individual_cl': Decimal('3000.000000'),
        'individual_lcl': Decimal('2850.000000'),
        'mr_ucl': Decimal('184.500000'),
        'mr_cl': Decimal('56.430000'),
        'sample_count': 30,
        'notes': 'Baseline for pressure hold test',
        'days_ago': 45,
    },
]


class DemoQualitySeeder(BaseSeeder):
    """
    Creates preset quality reports and dispositions.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, orders_result, users, part_types=None, equipment=None):
        """
        Create all demo quality data.

        Args:
            orders_result: dict with created orders/parts
            users: dict with user lists
            part_types: optional list of part types for error list creation
            equipment: optional list of equipment for linking to quality reports

        Returns:
            dict with created quality reports, dispositions, error lists, baselines, approvals
        """
        self.log("Creating demo quality data...")

        result = {
            'quality_reports': [],
            'dispositions': [],
            'error_lists': [],
            'spc_baselines': [],
            'qa_approvals': [],
        }

        # Get part lookup
        parts = Parts.objects.filter(tenant=self.tenant)
        part_map = {p.ERP_id: p for p in parts}

        # Get step lookup
        steps = Steps.objects.filter(tenant=self.tenant)
        step_map = {s.name: s for s in steps}

        # Build equipment lookup by step type
        equipment_map = {}
        if equipment:
            for eq in equipment:
                if 'Flow' in eq.name:
                    equipment_map['Flow Testing'] = eq
                elif 'Final' in eq.name or 'Test Bench' in eq.name:
                    equipment_map['Final Test'] = eq

        # Get QA staff and operators
        qa_users = users.get('qa_staff', [])
        qa_inspector = qa_users[0] if qa_users else None
        operators = users.get('employees', [])[:2]  # First 2 employees as operators

        # Create quality error lists first
        error_lists = self._create_quality_error_lists(part_types)
        result['error_lists'] = error_lists

        # Create quality reports
        qr_map = {}
        for qr_data in DEMO_QUALITY_REPORTS:
            part = part_map.get(qr_data['part'])
            step = step_map.get(qr_data['step'])

            if part and step:
                machine = equipment_map.get(qr_data['step'])
                qr = self._create_quality_report(qr_data, part, step, qa_inspector, machine, operators)
                result['quality_reports'].append(qr)
                qr_map[qr_data['id']] = qr

        # Create dispositions
        disp_map = {}
        for disp_data in DEMO_DISPOSITIONS:
            qr = qr_map.get(disp_data['quality_report'])
            part = part_map.get(disp_data['part'])

            if qr and part:
                disp = self._create_disposition(disp_data, qr, part, qa_inspector, step_map)
                result['dispositions'].append(disp)
                disp_map[disp_data['quality_report']] = disp

        # Create QA approvals for approved dispositions
        qa_approvals = self._create_qa_approvals(disp_map, qr_map, step_map, qa_users)
        result['qa_approvals'] = qa_approvals

        # Link FAIL quality reports to error types for Pareto analysis
        defect_links = self._create_defect_links(qr_map, result['error_lists'])
        result['defect_links'] = defect_links

        self.log(f"  Created {len(result['quality_reports'])} quality reports")
        self.log(f"  Created {len(result['defect_links'])} defect links")
        self.log(f"  Created {len(result['dispositions'])} dispositions")
        self.log(f"  Created {len(result['error_lists'])} quality error types")
        self.log(f"  Created {len(result['qa_approvals'])} QA approvals")

        return result

    def _create_quality_report(self, qr_data, part, step, inspector, machine=None, operators=None):
        """
        Create a quality report.

        QualityReports model fields:
        - report_number: auto-generated QR-YYYY-######
        - status: 'PASS', 'FAIL', or 'PENDING' (UPPERCASE)
        - detected_by: ForeignKey to User (required)
        - description: TextField
        - part, step: ForeignKeys
        - sampling_method: CharField (default 'manual')
        - is_first_piece: BooleanField (default False)
        - machine: ForeignKey to Equipments (optional)
        - operators: ManyToManyField to User (optional)

        NOTE: Uses update_or_create to ensure enum values are updated properly.
        """
        # Ensure status is UPPERCASE
        status = qr_data.get('status', 'PENDING').upper()

        qr, _ = QualityReports.objects.update_or_create(
            tenant=self.tenant,
            report_number=qr_data['id'],
            defaults={
                'part': part,
                'step': step,
                'status': status,  # UPPERCASE: 'PASS', 'FAIL', or 'PENDING'
                'description': qr_data.get('description', ''),
                'detected_by': inspector,
                'verified_by': None,  # Explicit - no second signature required for demo
                'sampling_method': 'manual',  # Explicit - don't rely on model default
                'is_first_piece': False,  # Explicit - don't rely on model default
                'machine': machine,  # Link to equipment used during inspection
                'file': None,  # Explicit - no attached document
                'sampling_audit_log': None,  # Explicit - not linked to sampling audit
            }
        )

        # Backdate created_at for historical data (FPY trend needs dated records)
        if qr_data.get('days_ago'):
            backdate = self.today - timedelta(days=qr_data['days_ago'])
            QualityReports.objects.filter(pk=qr.pk).update(created_at=backdate)

        # Add operators if provided (M2M field)
        if operators:
            qr.operators.set(operators)

        return qr

    def _create_disposition(self, disp_data, quality_report, part, approver, step_map=None):
        """
        Create a disposition for a quality report.

        QuarantineDisposition model fields (all enums must be UPPERCASE):
        - disposition_number: auto-generated
        - current_state: 'OPEN', 'IN_PROGRESS', or 'CLOSED' (UPPERCASE)
        - disposition_type: 'REWORK', 'REPAIR', 'SCRAP', 'USE_AS_IS', 'RETURN_TO_SUPPLIER' (UPPERCASE)
        - severity: 'CRITICAL', 'MAJOR', or 'MINOR' (UPPERCASE)
        - resolution_notes: TextField
        - assigned_to: ForeignKey to User
        - quality_reports: ManyToManyField (not single FK)
        - description: TextField
        - requires_customer_approval: BooleanField
        - customer_approval_received: BooleanField
        - scrap_verified: BooleanField
        - resolution_completed: BooleanField
        - rework_attempt_at_step: IntegerField
        - step: ForeignKey to Steps (for rework step)

        NOTE: Uses update_or_create to ensure enum values are updated properly.
        """
        # Get values from data, ensuring UPPERCASE for enums
        current_state = disp_data.get('current_state', 'OPEN').upper()
        disposition_type = disp_data.get('disposition_type', '').upper()
        severity = disp_data.get('severity', 'MAJOR').upper()

        # Generate a unique disposition number
        disp_number = f"DISP-{quality_report.report_number}"

        # Determine if resolution is completed (CLOSED state)
        resolution_completed = (current_state == 'CLOSED')

        # Determine customer approval requirements
        requires_customer_approval = disposition_type in ['RETURN_TO_SUPPLIER', 'USE_AS_IS']
        customer_approval_received = requires_customer_approval and current_state in ['IN_PROGRESS', 'CLOSED']

        # Determine scrap verification
        scrap_verified = (disposition_type == 'SCRAP' and current_state == 'CLOSED')

        # Get rework step if applicable
        rework_step = None
        if disposition_type == 'REWORK' and step_map:
            # Use the step from the quality report for rework
            rework_step = quality_report.step

        # Calculate timestamps for completed dispositions
        created_at = self.today - timedelta(days=disp_data.get('days_ago', 0))
        resolution_completed_at = created_at + timedelta(days=1) if resolution_completed else None
        containment_completed_at = created_at + timedelta(hours=2) if current_state != 'OPEN' else None
        customer_approval_date_val = (created_at + timedelta(hours=4)).date() if customer_approval_received else None
        scrap_verified_at = created_at + timedelta(hours=3) if scrap_verified else None

        disp, created = QuarantineDisposition.objects.update_or_create(
            tenant=self.tenant,
            disposition_number=disp_number,
            defaults={
                'part': part,
                'disposition_type': disposition_type,  # UPPERCASE enum
                'current_state': current_state,  # UPPERCASE enum
                'severity': severity,  # UPPERCASE enum - explicit, don't rely on default
                'resolution_notes': disp_data.get('resolution_notes', ''),
                'description': disp_data.get('description', quality_report.description),
                'assigned_to': approver,
                'step': rework_step,  # Step where rework will occur
                # Containment tracking - immediate action taken
                'containment_action': 'Part quarantined and segregated' if current_state != 'OPEN' else '',
                'containment_completed_at': containment_completed_at,
                'containment_completed_by': approver if current_state != 'OPEN' else None,
                # Customer approval fields
                'requires_customer_approval': requires_customer_approval,
                'customer_approval_received': customer_approval_received,
                'customer_approval_reference': 'CON-2024-001' if customer_approval_received else '',
                'customer_approval_date': customer_approval_date_val,
                # Scrap verification fields
                'scrap_verified': scrap_verified,
                'scrap_verification_method': 'Crushed and marked' if scrap_verified else '',
                'scrap_verified_by': approver if scrap_verified else None,
                'scrap_verified_at': scrap_verified_at,
                # Resolution tracking
                'resolution_completed': resolution_completed,
                'resolution_completed_by': approver if resolution_completed else None,
                'resolution_completed_at': resolution_completed_at,
                'rework_attempt_at_step': disp_data.get('rework_attempt', 1),
            }
        )

        # Link to quality report via M2M (always ensure it's linked)
        disp.quality_reports.add(quality_report)

        return disp

    def seed_spc_data(self, measurement_definitions, quality_reports, users):
        """
        Create SPC measurement data for capability analysis.

        Creates measurement results attached to quality reports. For proper SPC
        capability analysis, we need 25-30+ measurements with realistic variation.

        MeasurementResult model fields:
        - report: ForeignKey to QualityReports (required)
        - definition: ForeignKey to MeasurementDefinition
        - value_numeric: FloatField (for NUMERIC measurements)
        - value_pass_fail: 'PASS' or 'FAIL' (UPPERCASE, for PASS_FAIL measurements)
        - is_within_spec: BooleanField (auto-calculated on save, but we set explicitly)
        - created_by: ForeignKey to User

        NOTE: Uses update_or_create to ensure enum values are updated properly.
        All enum values must be UPPERCASE.
        """
        self.log("  Creating SPC measurement data...")

        # Build measurement definition lookup by label
        md_by_label = {md.label: md for md in measurement_definitions}

        # Get an inspector
        qa_users = users.get('qa_staff', [])
        inspector = qa_users[0] if qa_users else None

        results = []
        import random

        # Create measurements for each measurement definition that has tolerances
        for md in measurement_definitions:
            if not md.nominal or not md.upper_tol or not md.lower_tol:
                continue  # Skip definitions without spec limits

            nominal = float(md.nominal)
            lower_tol = float(md.lower_tol)
            upper_tol = float(md.upper_tol)
            lsl = nominal - lower_tol
            usl = nominal + upper_tol

            # Process variation as percentage of tolerance (realistic manufacturing)
            tolerance_range = upper_tol + lower_tol
            std_dev = tolerance_range / 6  # Cpk ~1.0 baseline

            # Create measurements for quality reports that have this step
            for i, qr in enumerate(quality_reports):
                random.seed(hash(f"{md.label}-{i}"))  # Deterministic per definition+index

                # Generate realistic values - mostly within spec
                if i % 15 == 0:
                    # Occasional out-of-spec (rule violation)
                    value = round(nominal + upper_tol * 1.1, 2)
                elif i % 7 == 0:
                    # Some values trending high (Rule 2 pattern)
                    value = round(nominal + std_dev * 1.5, 2)
                else:
                    # Normal variation around nominal
                    variation = random.gauss(0, std_dev)
                    value = round(nominal + variation, 2)

                # Calculate is_within_spec
                is_within_spec = lsl <= value <= usl
                value_pass_fail = 'PASS' if is_within_spec else 'FAIL'

                mr, _ = MeasurementResult.objects.update_or_create(
                    tenant=self.tenant,
                    report=qr,
                    definition=md,
                    defaults={
                        'value_numeric': value,
                        'value_pass_fail': value_pass_fail,
                        'is_within_spec': is_within_spec,
                        'created_by': inspector,
                    }
                )
                results.append(mr)

        self.log(f"    Created {len(results)} SPC measurement results")
        return results

    def _seed_spc_data_legacy(self, measurement_definitions, quality_reports, users):
        """Legacy method - kept for reference. Creates measurements only for Flow Rate."""
        self.log("  Creating SPC measurement data (legacy)...")

        # Find Flow Rate measurement definition (uses 'label' field, not 'name')
        flow_rate_def = None
        for md in measurement_definitions:
            if md.label == 'Flow Rate':
                flow_rate_def = md
                break

        if not flow_rate_def:
            self.log("    Warning: Flow Rate measurement definition not found")
            return []

        # Get an inspector
        qa_users = users.get('qa_staff', [])
        inspector = qa_users[0] if qa_users else None

        results = []
        nominal = float(flow_rate_def.nominal or 120)
        lower_tol = float(flow_rate_def.lower_tol or 20)
        upper_tol = float(flow_rate_def.upper_tol or 20)
        lsl = nominal - lower_tol
        usl = nominal + upper_tol

        # Create measurements for each quality report
        import random
        for i, qr in enumerate(quality_reports):
            # Generate value - mostly normal distribution around nominal
            if 3 <= i <= 5:
                # Simulate some variation above mean
                value = round(nominal + 5 + (i % 5), 1)
            else:
                # Normal variation
                random.seed(i)  # Deterministic
                variation = random.gauss(0, 3)
                value = round(nominal + variation, 1)

            # Calculate is_within_spec explicitly
            is_within_spec = lsl <= value <= usl

            # Determine value_pass_fail based on spec compliance (UPPERCASE)
            value_pass_fail = 'PASS' if is_within_spec else 'FAIL'

            mr, _ = MeasurementResult.objects.update_or_create(
                tenant=self.tenant,
                report=qr,
                definition=flow_rate_def,
                defaults={
                    'value_numeric': value,
                    'value_pass_fail': value_pass_fail,  # UPPERCASE: 'PASS' or 'FAIL'
                    'is_within_spec': is_within_spec,  # Explicit - model auto-calculates but we set it
                    'created_by': inspector,
                }
            )
            results.append(mr)

        self.log(f"    Created {len(results)} SPC measurement results")
        return results

    def _create_quality_error_lists(self, part_types):
        """
        Create quality error list entries (common defect types).

        Args:
            part_types: list of PartTypes objects or None

        Returns:
            list of created QualityErrorsList objects

        NOTE: Uses update_or_create to ensure values are updated properly.
        All fields are set explicitly - no reliance on model defaults.
        """
        from Tracker.models import PartTypes

        error_lists = []

        # Create part type lookup
        part_type_map = {}
        if part_types:
            part_type_map = {pt.name: pt for pt in part_types}
        else:
            # Fetch from database if not provided
            pts = PartTypes.objects.filter(tenant=self.tenant)
            part_type_map = {pt.name: pt for pt in pts}

        for error_data in DEMO_QUALITY_ERRORS:
            part_type = part_type_map.get(error_data['part_type'])

            error, _ = QualityErrorsList.objects.update_or_create(
                tenant=self.tenant,
                error_name=error_data['error_name'],
                part_type=part_type,
                defaults={
                    'error_example': error_data['error_example'],
                    # Explicit - don't rely on model default
                    'requires_3d_annotation': error_data.get('requires_3d_annotation', False),
                }
            )
            error_lists.append(error)

        return error_lists

    def _create_qa_approvals(self, disp_map, qr_map, step_map, qa_users):
        """
        Create QA approval records for approved dispositions.

        QaApproval tracks QA staff approval for work orders at specific steps.

        Args:
            disp_map: dict mapping quality report IDs to dispositions
            qr_map: dict mapping quality report IDs to quality reports
            step_map: dict mapping step names to Steps
            qa_users: list of QA staff users

        Returns:
            list of created QaApproval objects

        NOTE: Uses update_or_create to ensure values are updated properly.
        """
        approvals = []

        if not qa_users:
            return approvals

        qa_staff = qa_users[0] if qa_users else None

        # Create approvals for dispositions that have been approved (IN_PROGRESS or CLOSED state)
        # OPEN state means not yet approved
        approved_states = ['IN_PROGRESS', 'CLOSED']
        for disp_data in DEMO_DISPOSITIONS:
            current_state = disp_data.get('current_state', 'OPEN').upper()
            if current_state in approved_states:
                qr = qr_map.get(disp_data['quality_report'])
                if qr and qr.part and qr.part.work_order:
                    approval, _ = QaApproval.objects.update_or_create(
                        tenant=self.tenant,
                        step=qr.step,
                        work_order=qr.part.work_order,
                        qa_staff=qa_staff,
                    )
                    approvals.append(approval)

        return approvals

    def _create_defect_links(self, qr_map, error_lists):
        """
        Create QualityReportDefect records linking FAIL reports to error types.

        This enables Pareto analysis by connecting quality reports to their defect types.

        Args:
            qr_map: dict mapping quality report IDs to quality reports
            error_lists: list of QualityErrorsList objects

        Returns:
            list of created QualityReportDefect objects
        """
        defect_links = []

        # Build error type lookup by name
        error_by_name = {e.error_name: e for e in error_lists}

        # Link FAIL quality reports to their defect types
        for qr_data in DEMO_QUALITY_REPORTS:
            if qr_data.get('status') != 'FAIL':
                continue

            defect_name = qr_data.get('defect')
            if not defect_name:
                continue

            qr = qr_map.get(qr_data['id'])
            if not qr:
                continue

            # Find matching error type (try exact match first, then partial)
            error_type = error_by_name.get(defect_name)
            if not error_type:
                # Try partial match
                for name, err in error_by_name.items():
                    if defect_name.lower() in name.lower() or name.lower() in defect_name.lower():
                        error_type = err
                        break

            if error_type:
                defect_link, _ = QualityReportDefect.objects.update_or_create(
                    report=qr,
                    error_type=error_type,
                    defaults={
                        'count': 1,
                        'location': '',
                        'severity': 'MAJOR',
                    }
                )
                defect_links.append(defect_link)

        return defect_links

    def seed_spc_baselines(self, users):
        """
        Create SPC baselines (frozen control limits).

        Args:
            users: dict with user lists

        Returns:
            list of created SPCBaseline objects

        NOTE: Uses update_or_create to ensure values are updated properly.
        All fields are set explicitly - no reliance on model defaults.
        """
        self.log("  Creating SPC baselines...")

        baselines = []

        # Get QA staff for frozen_by field
        qa_users = users.get('qa_staff', [])
        qa_staff = qa_users[0] if qa_users else None

        # Get measurement definitions
        measurement_defs = MeasurementDefinition.objects.filter(tenant=self.tenant)
        measurement_map = {md.label: md for md in measurement_defs}

        for baseline_data in DEMO_SPC_BASELINES:
            measurement_def = measurement_map.get(baseline_data['measurement'])

            if not measurement_def:
                self.log(f"    Warning: Measurement definition '{baseline_data['measurement']}' not found")
                continue

            # Calculate frozen_at timestamp
            frozen_at = self.today - timedelta(days=baseline_data.get('days_ago', 0))

            baseline, _ = SPCBaseline.objects.update_or_create(
                tenant=self.tenant,
                measurement_definition=measurement_def,
                chart_type=baseline_data['chart_type'],
                defaults={
                    # Explicit values - don't rely on model defaults
                    'subgroup_size': baseline_data.get('subgroup_size', 1),
                    # I-MR chart limits
                    'individual_ucl': baseline_data.get('individual_ucl'),
                    'individual_cl': baseline_data.get('individual_cl'),
                    'individual_lcl': baseline_data.get('individual_lcl'),
                    'mr_ucl': baseline_data.get('mr_ucl'),
                    'mr_cl': baseline_data.get('mr_cl'),
                    # X-bar R/S chart limits
                    'xbar_ucl': baseline_data.get('xbar_ucl'),
                    'xbar_cl': baseline_data.get('xbar_cl'),
                    'xbar_lcl': baseline_data.get('xbar_lcl'),
                    'range_ucl': baseline_data.get('range_ucl'),
                    'range_cl': baseline_data.get('range_cl'),
                    'range_lcl': baseline_data.get('range_lcl'),
                    # Status and audit
                    'status': BaselineStatus.ACTIVE,
                    'frozen_by': qa_staff,
                    'sample_count': baseline_data.get('sample_count', 0),
                    'notes': baseline_data.get('notes', ''),
                    # Supersession tracking - explicit nulls for active baselines
                    'superseded_by': None,
                    'superseded_at': None,
                    'superseded_reason': '',
                }
            )

            # Backdate if needed
            if baseline_data.get('days_ago'):
                SPCBaseline.objects.filter(pk=baseline.pk).update(
                    frozen_at=frozen_at,
                    created_at=frozen_at,
                    updated_at=frozen_at
                )

            baselines.append(baseline)

        self.log(f"    Created {len(baselines)} SPC baselines")
        return baselines
