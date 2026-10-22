"""
Demo remanufacturing seeder with preset, deterministic reman data.

Creates:
- DisassemblyBOMLines for Common Rail Injector disassembly
- Cores with different statuses (RECEIVED, IN_DISASSEMBLY, DISASSEMBLED)
- HarvestedComponents from cores with grades (A, B, C, SCRAP)

All data is deterministic - same result every time for demo consistency.
"""

from Tracker.services.reman.core_part import create_core, sync_part_status
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    Core, HarvestedComponent, DisassemblyBOMLine,
    PartTypes,
)

from ..base import BaseSeeder


# The customer orders the repair-and-return units are here for. A unit that goes back
# to its customer is received against their order (services/reman/core.py
# receipt_order_refusal), so each such core names one; exchange cores name none.
REPAIR_ORDERS = {
    'ORD-2024-0044': {'name': 'Midwest Fleet warranty returns', 'customer': 'Midwest Fleet Services',
                      'due_days': 14},
    'ORD-2024-0046': {'name': 'Great Lakes injector repairs', 'customer': 'Great Lakes Diesel',
                      'due_days': 14},
    'ORD-2024-0047': {'name': 'Northern Trucking injector repairs', 'customer': 'Northern Trucking Co',
                      'due_days': 18},
}


# Component definitions for injector disassembly (reverse BOM).
#
# Names and prefixes MATCH the assembly BOM in seed/demo/showcase.py. Both seeders
# resolve PartTypes by name, so agreeing here means teardown yields the very rows the
# rebuild consumes — and disagreeing (as this did) leaves every `allow_harvested` line
# on the assembly BOM unsatisfiable, with the rebuild proposing you buy a unit's own
# parts back. The Injector Body has no assembly line on purpose: it is the housing the
# rebuild goes INTO, not a component that goes in.
DEMO_DISASSEMBLY_BOM = [
    {
        'component_name': 'Injector Body',
        'component_prefix': 'BODY',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.05'),  # 5%
        'line_number': 1,
        'notes': 'Main housing - check for cracks and corrosion',
    },
    {
        'component_name': 'Injector Nozzle Assembly',
        'component_prefix': 'NZL',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.15'),  # 15%
        'line_number': 2,
        'notes': 'Critical wear item - verify spray pattern capability',
    },
    {
        'component_name': 'Control Valve Assembly',
        'component_prefix': 'VLV',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.08'),  # 8%
        'line_number': 3,
        'notes': 'Electronic component - test resistance and response time',
    },
]


# Preset demo cores with specific narratives
DEMO_CORES = [
    # Recently received cores
    {
        'core_number': 'CORE-240225-0001',
        'serial_number': 'SN-CRI-A47F92E1',
        'received_days_ago': 2,
        'status': 'RECEIVED',
        'condition_grade': 'B',
        'condition_notes': 'Good condition with normal wear patterns. Light corrosion on external surfaces.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45821',
        'customer_name': 'Midwest Fleet Services',
        'core_credit_value': Decimal('125.00'),
        'core_credit_issued': False,
    },
    {
        'core_number': 'CORE-240225-0002',
        'serial_number': 'SN-CRI-B23D14C8',
        'received_days_ago': 2,
        'status': 'RECEIVED',
        'condition_grade': 'C',
        'condition_notes': 'Fair condition. Heavy wear on nozzle tip. Carbon deposits present.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45821',
        'customer_name': 'Midwest Fleet Services',
        'core_credit_value': Decimal('75.00'),
        'core_credit_issued': False,
    },
    # Cores in disassembly
    {
        'core_number': 'CORE-240220-0003',
        'serial_number': 'SN-CRI-C89A55F3',
        'received_days_ago': 7,
        'status': 'IN_DISASSEMBLY',
        'disassembly_started_days_ago': 6,
        'condition_grade': 'A',
        'condition_notes': 'Excellent condition. Minimal wear. All components present.',
        'source_type': 'PURCHASED',
        'source_reference': 'PO-78432',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': Decimal('175.00'),
        'core_credit_issued': False,
    },
    {
        'core_number': 'CORE-240220-0004',
        'serial_number': 'SN-CRI-D12B77A9',
        'received_days_ago': 7,
        'status': 'IN_DISASSEMBLY',
        'disassembly_started_days_ago': 5,
        'condition_grade': 'B',
        'condition_notes': 'Good condition. Some carbon buildup. Standard cleaning required.',
        'source_type': 'PURCHASED',
        'source_reference': 'PO-78432',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': Decimal('135.00'),
        'core_credit_issued': False,
    },
    # Fully disassembled cores (components harvested)
    {
        'core_number': 'CORE-240215-0005',
        'serial_number': 'SN-CRI-E56F88D2',
        'received_days_ago': 12,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 11,
        'disassembly_completed_days_ago': 10,
        'condition_grade': 'B',
        'condition_notes': 'Good condition with normal wear patterns.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45103',
        'customer_name': 'Northern Trucking Co',
        'core_credit_value': Decimal('110.00'),
        'core_credit_issued': True,
        # Exchange: Northern already had a unit from stock; this one is a parts source.
        'release': 'INVENTORY',
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Excellent. Ready for reuse without rework.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Injector Nozzle Assembly',
                'condition_grade': 'B',
                'disposition': 'REFURBISH',
                'condition_notes': 'Good condition. Minor surface wear acceptable.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Control Valve Assembly',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Pristine condition. Passes all dimensional checks.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        'core_number': 'CORE-240215-0006',
        'serial_number': 'SN-CRI-F91C22B5',
        'received_days_ago': 12,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 11,
        'disassembly_completed_days_ago': 9,
        'condition_grade': 'C',
        'condition_notes': 'Fair condition. Significant corrosion. May have high fallout.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45103',
        'customer_name': 'Northern Trucking Co',
        'core_credit_value': Decimal('60.00'),
        'core_credit_issued': True,
        'components': [
            {
                # QA reman-addition exhibit: a good body waiting to be accepted to stock.
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'PENDING',
                'condition_notes': 'Light wear, within new-part limits. Ready for acceptance.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Injector Nozzle Assembly',
                # Graded scrap at teardown, not yet scrapped: the inspector scraps it.
                'condition_grade': 'SCRAP',
                'disposition': 'SCRAP',
                'condition_notes': 'Exceeded maximum wear limits.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Control Valve Assembly',
                'condition_grade': 'C',
                'disposition': 'PENDING',
                'condition_notes': 'Fair condition. Near tolerance limits.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        'core_number': 'CORE-240210-0007',
        'for_order': 'ORD-2024-0044',
        'serial_number': 'SN-CRI-G33E44F8',
        'received_days_ago': 17,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 16,
        'disassembly_completed_days_ago': 15,
        'condition_grade': 'A',
        'condition_notes': 'Excellent condition. Very clean. No visible damage.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'WTY-63271',
        'customer_name': 'Midwest Fleet Services',
        # A warranty unit: Midwest's own injector, repaired and sent back to them —
        # so no exchange credit, and its parts never enter the harvest pool.
        'fulfilment_mode': 'REPAIR_RETURN',
        'core_credit_value': None,
        'core_credit_issued': False,
        'release': 'REBUILD',
        # No finding seeded. The operator finds the nozzle seat pitted at Nozzle
        # Inspection (Operator track R2), and recorded there it applies at once:
        # NZL-RECON is pre-approved at that check. Recording it off-check left it
        # waiting on a lead, a state the check never produces.
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Excellent. Ready for reuse without rework.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Injector Nozzle Assembly',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Minimal wear. Within all tolerances.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Control Valve Assembly',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Pristine condition. Passes all dimensional checks.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        # QA Manager R1 exhibit: a customer's own unit, in rebuild, waiting on their
        # answer. The bench found the nozzle cracked after teardown passed it; a
        # replacement is not pre-approved at Nozzle Inspection and not part of the
        # standard rebuild they bought, so the unit is sent for authorisation
        # (release.request_authorisation). The QA Manager records the answer.
        'core_number': 'CORE-240212-0009',
        'for_order': 'ORD-2024-0046',
        'serial_number': 'SN-CRI-J52B18C4',
        'received_days_ago': 15,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 14,
        'disassembly_completed_days_ago': 13,
        'condition_grade': 'B',
        'condition_notes': 'Good condition. Normal wear on the nozzle tip.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45912',
        'customer_name': 'Great Lakes Diesel',
        'fulfilment_mode': 'REPAIR_RETURN',
        'core_credit_value': None,
        'core_credit_issued': False,
        'release': 'REBUILD',
        'finding': {'component': 'Injector Nozzle Assembly', 'grade': 'SCRAP',
                    'finding': 'Hairline crack at the needle guide, found under '
                               'magnification after cleaning.',
                    'apply': True, 'authorise': True},
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Within new-part limits.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Injector Nozzle Assembly',
                'condition_grade': 'B',
                'disposition': 'REUSE',
                'condition_notes': 'Normal tip wear at teardown.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Control Valve Assembly',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Passes all dimensional checks.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        # Shipping R1 exhibit: Midwest Fleet's own unit, declined. Its nozzle was found
        # cracked and the customer said no to replacing it, so it goes back unrepaired
        # (DECLINED), on the same dispatch step a rebuilt unit takes. Torn down on a
        # work order of its own so the shared teardown batch is untouched.
        'core_number': 'CORE-240215-0011',
        'for_order': 'ORD-2024-0044',
        'own_teardown': True,
        'serial_number': 'SN-CRI-M08C51B2',
        'received_days_ago': 12,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 11,
        'disassembly_completed_days_ago': 10,
        'condition_grade': 'B',
        'condition_notes': 'Fair. Heavy carbon on the tip.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-46102',
        'customer_name': 'Midwest Fleet Services',
        'fulfilment_mode': 'REPAIR_RETURN',
        'core_credit_value': None,
        'core_credit_issued': False,
        'release': 'REBUILD',
        'finding': {'component': 'Injector Nozzle Assembly', 'grade': 'SCRAP',
                    'finding': 'Cracked nozzle body at the seat, found after cleaning.',
                    'apply': True, 'authorise': True,
                    'decline': {'contact': 'Tom Bradley', 'method': 'phone',
                                'reference': 'MF-WR-118',
                                'note': 'Unit is being retired from the fleet; return as is.'}},
        'components': [
            {'component_name': 'Injector Body', 'condition_grade': 'B', 'disposition': 'REUSE',
             'condition_notes': 'Within limits.', 'position': '',
             'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Injector Nozzle Assembly', 'condition_grade': 'B',
             'disposition': 'REUSE', 'condition_notes': 'Heavy carbon at teardown.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Control Valve Assembly', 'condition_grade': 'A',
             'disposition': 'REUSE', 'condition_notes': 'Passes dimensional checks.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
        ],
    },
    {
        # Production Manager R2 exhibit: an exchange unit in rebuild whose nozzle was
        # scrapped at the bench. Recovered stock holds a serviceable nozzle (from
        # CORE-240215-0005), so its rebuild plan is a real choice: draw the recovered
        # one or buy new. An exchange unit may take recovered stock; a customer's own
        # unit may not, which is why the walked units never showed the choice.
        'core_number': 'CORE-240216-0012',
        'own_teardown': True,
        'serial_number': 'SN-CRI-P44E07C1',
        'received_days_ago': 10,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 9,
        'disassembly_completed_days_ago': 8,
        'condition_grade': 'B',
        'condition_notes': 'Good condition. Nozzle tip eroded.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-46150',
        'customer_name': 'Great Lakes Diesel',
        'fulfilment_mode': 'EXCHANGE',
        'core_credit_value': Decimal('60.00'),
        'core_credit_issued': False,
        'release': 'REBUILD',
        'components': [
            {'component_name': 'Injector Body', 'condition_grade': 'A', 'disposition': 'REUSE',
             'condition_notes': 'Within new-part limits.', 'position': '',
             'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Injector Nozzle Assembly', 'condition_grade': 'SCRAP',
             'disposition': 'SCRAP', 'condition_notes': 'Tip eroded through; spray holes oversize.',
             'position': '', 'original_part_number': '', 'is_scrapped': True,
             'scrap_reason': 'Tip eroded through'},
            {'component_name': 'Control Valve Assembly', 'condition_grade': 'A',
             'disposition': 'REUSE', 'condition_notes': 'Seat clean, passes dimensional checks.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
        ],
    },
    {
        # Shipping R2 exhibit: Northern Trucking's own unit, rebuilt and ready to go
        # back. Torn down on its own work order and released into rebuild here; the
        # operator walk (ops_walk._rebuilt_unit) takes it through every rebuild step
        # to Complete, so it reaches the shipping board the way a real one does.
        'core_number': 'CORE-240217-0013',
        'for_order': 'ORD-2024-0047',
        'own_teardown': True,
        'serial_number': 'SN-CRI-R21A66D9',
        'received_days_ago': 14,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 13,
        'disassembly_completed_days_ago': 12,
        'condition_grade': 'A',
        'condition_notes': 'Good condition. Light carbon on the tip.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-46088',
        'customer_name': 'Northern Trucking Co',
        'fulfilment_mode': 'REPAIR_RETURN',
        'core_credit_value': None,
        'core_credit_issued': False,
        'release': 'REBUILD',
        'components': [
            {'component_name': 'Injector Body', 'condition_grade': 'A', 'disposition': 'REUSE',
             'condition_notes': 'Within new-part limits.', 'position': '',
             'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Injector Nozzle Assembly', 'condition_grade': 'A',
             'disposition': 'REUSE', 'condition_notes': 'Spray holes clear after cleaning.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Control Valve Assembly', 'condition_grade': 'A',
             'disposition': 'REUSE', 'condition_notes': 'Seat clean, passes dimensional checks.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
        ],
    },
    # Scrapped core
    {
        'core_number': 'CORE-240218-0008',
        'serial_number': 'SN-CRI-H77A99D1',
        'received_days_ago': 9,
        'status': 'SCRAPPED',
        'condition_grade': 'SCRAP',
        'condition_notes': 'Severe damage. Cracked body - not salvageable. Heavy corrosion damage throughout.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45673',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': None,
        'core_credit_issued': False,
    },
    {
        # Shift Lead R1 exhibit: Northern Trucking's own unit, torn down on a teardown
        # work order of its own (one lot), released into rebuild, cleaned in its own
        # load. At Nozzle Inspection the operator finds the nozzle beyond repair and
        # records it there (ops_walk). Replacing it isn't pre-approved at that check,
        # so the finding waits for the lead and the unit holds until it's decided.
        'core_number': 'CORE-240214-0010',
        'for_order': 'ORD-2024-0047',
        'own_teardown': True,
        'serial_number': 'SN-CRI-K17D90A3',
        'received_days_ago': 9,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 8,
        'disassembly_completed_days_ago': 7,
        'condition_grade': 'B',
        'condition_notes': 'Good condition. Light carbon on the tip.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-46021',
        'customer_name': 'Northern Trucking Co',
        'fulfilment_mode': 'REPAIR_RETURN',
        'core_credit_value': None,
        'core_credit_issued': False,
        'release': 'REBUILD',
        'components': [
            {'component_name': 'Injector Body', 'condition_grade': 'A', 'disposition': 'REUSE',
             'condition_notes': 'Clean bore, within all tolerances.', 'position': '',
             'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Injector Nozzle Assembly', 'condition_grade': 'B',
             'disposition': 'REUSE', 'condition_notes': 'Carbon on the tip; spray holes clear.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
            {'component_name': 'Control Valve Assembly', 'condition_grade': 'A',
             'disposition': 'REUSE', 'condition_notes': 'Seat clean, passes dimensional checks.',
             'position': '', 'original_part_number': '', 'is_scrapped': False, 'scrap_reason': ''},
        ],
    },
]


class DemoRemanSeeder(BaseSeeder):
    """
    Creates preset remanufacturing data for the demo scenario.

    All data is deterministic and tied to specific demo narratives:
    - Fresh cores from Midwest Fleet (recently received)
    - Cores in active disassembly
    - Completed disassembly with harvested components
    - One scrapped core example
    """

    WALKED_STATUSES = ('IN_DISASSEMBLY', 'DISASSEMBLED')

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, companies, users, part_types):
        """
        Create all demo reman data.

        Args:
            companies: dict with company lists (from DemoCompanySeeder)
            users: dict with user lists (from DemoUsersSeeder)
            part_types: list of PartTypes

        Returns:
            dict with created cores, components, and BOM lines
        """
        self.log("Creating demo remanufacturing data...")

        result = {
            'bom_lines': [],
            'cores': [],
            'components': [],
        }

        # Get component part types (create if needed)
        component_types = self._ensure_component_part_types()

        # Create DisassemblyBOMLines
        result['bom_lines'] = self._create_disassembly_bom_lines(part_types, component_types)

        # The repair orders the repair-and-return cores are received against
        self._repair_orders = self._create_repair_orders(companies)

        # Create cores
        result['cores'] = self._create_cores(companies, users)

        # Repair codes + the rebuild level that groups them
        result['repair_codes'] = self._create_repair_codes(part_types)

        # Make teardown startable at all
        self._flag_disassembly_process(part_types)

        # Classify the item master: what can actually come back out of a core
        self._classify_recoverability()

        # Cores further along than RECEIVED get there through the teardown services,
        # on a work order. Before the RECEIVED-core batch below, which would take them.
        result['components'] = self._walk_teardown(result['cores'], users)

        # A core on a work order — without one, every reman workflow is unreachable
        result['teardown_wo'] = self._start_a_teardown_batch(result['cores'], users)

        self.log(f"  Created {len(result['bom_lines'])} disassembly BOM lines")
        self.log(f"  Created {len(result['cores'])} cores")
        self.log(f"  Created {len(result['components'])} harvested components")

        return result

    def _walk_teardown(self, cores, users):
        """Take the cores whose story is past RECEIVED there through the services.

        One teardown work order (start_teardown_batch) for all of them. The ones that
        finished teardown are harvested and completed (complete_core_disassembly),
        then leave the way their fulfilment mode says (services/reman/release): an
        exchange core marked 'release': 'INVENTORY' gives its components to stock, a
        repair-and-return core goes into rebuild on the same work order. One stays
        DISASSEMBLED with a component decision still pending — on the work order,
        where "Complete teardown" and the release actions live. The exits themselves
        run later (release_walked_cores): rebuild needs the released assembly BOM.

        Returns the harvested components.
        """
        from Tracker.services.reman.core import complete_core_disassembly
        from Tracker.services.reman.teardown import start_teardown_batch

        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            self.log("  Skipped teardown walk: no employees", warning=True)
            return []
        config = {c['core_number']: c for c in DEMO_CORES}
        walked = [c for c in cores
                  if config[c.core_number]['status'] in self.WALKED_STATUSES
                  and c.status == 'RECEIVED' and c.part_id and c.part.work_order_id is None]
        # A core marked own_teardown is torn down on a work order of its own: a lot of
        # one, so its rebuild doesn't wait on the other units' lot.
        batches = [[c for c in walked if not config[c.core_number].get('own_teardown')]]
        batches += [[c] for c in walked if config[c.core_number].get('own_teardown')]
        components = []
        for batch in batches:
            if batch:
                components += self._tear_down(batch, config, employees, users)
        return components

    def _tear_down(self, batch, config, employees, users):
        """One teardown work order for `batch`, walked as _walk_teardown describes."""
        from Tracker.services.reman.core import complete_core_disassembly
        from Tracker.services.reman.teardown import start_teardown_batch

        wo = start_teardown_batch(batch, self._actor('casey.dual@demo.ambac.com', employees[0]))

        components = []
        for core in batch:
            data = config[core.core_number]
            if data['status'] == 'DISASSEMBLED':
                core.refresh_from_db()
                complete_core_disassembly(core, self._actor('dave.wilson@demo.ambac.com', employees[0]))
                # A torn-down unit stands on its last teardown step — rebuild picks up at
                # the step after it (release._first_rebuild_step). The batch put it at
                # the route's first step; teardown itself isn't walked here.
                self._place_after_teardown(core, wo)
            # The services stamp now(); the story has dates.
            received = self.today - timedelta(days=data['received_days_ago'])
            stamps = {'disassembly_started_at': received + timedelta(
                days=data['received_days_ago'] - data['disassembly_started_days_ago'])}
            if 'disassembly_completed_days_ago' in data:
                stamps['disassembly_completed_at'] = received + timedelta(
                    days=data['received_days_ago'] - data['disassembly_completed_days_ago'])
            Core.objects.filter(pk=core.pk).update(**stamps)
            core.refresh_from_db()
            if data['status'] == 'DISASSEMBLED':
                # After the dates are set: components take the teardown's completion time.
                components += self._create_harvested_components([core], users)

        self.log(f"  Walked {len(batch)} core(s) through teardown on {wo.ERP_id}")
        return components

    def _place_after_teardown(self, core, wo):
        """Stand a torn-down core on its process's last teardown step."""
        from Tracker.models import Parts, ProcessStep
        last = (ProcessStep.objects.filter(process=wo.process, step__name='Component Grading')
                .select_related('step').first()) if wo.process_id else None
        if last is not None and core.part_id:
            Parts.objects.filter(pk=core.part_id).update(step=last.step)
            core.refresh_from_db()

    def _actor(self, email, fallback):
        """A named member of the cast, or `fallback`. employees[0] is the Tenant Admin
        and employees[1] the QA Manager: neither receives or tears down cores."""
        from Tracker.models import User
        return User.objects.filter(email=email).first() or fallback

    def release_walked_cores(self, users):
        """The torn-down cores' exits, and a bench finding on the one in rebuild.

        A separate phase because rebuild needs a released assembly BOM to resolve a
        scope from (release_core_to_rebuild refuses without one), and the showcase
        seeder releases it — after this seeder's main phase.
        """
        from Tracker.services.reman.release import release_core_to_inventory, release_core_to_rebuild

        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            return 0
        # Releasing a unit, deciding a finding and sending it for the customer's
        # answer are a shift lead's acts; the bench finding is an operator's. Not
        # employees[0] (the Tenant Admin) or employees[-1] (the document controller).
        by_email = users.get('by_email', {})
        lead = by_email.get('casey.dual@demo.ambac.com') or employees[0]
        operator = (users.get('operators') or employees)[0]
        released = 0
        for data in DEMO_CORES:
            release = data.get('release')
            core = Core.objects.filter(tenant=self.tenant, core_number=data['core_number'],
                                       status='DISASSEMBLED').first()
            if core is None or release is None:
                continue
            if release == 'INVENTORY':
                release_core_to_inventory(core, lead)
            elif release == 'REBUILD':
                release_core_to_rebuild(core, lead)
            released += 1
            if data.get('finding'):
                target = self._raise_finding(core, data['finding'], operator)
                if target is not None and data['finding'].get('apply'):
                    from Tracker.services.reman.findings import apply_finding
                    apply_finding(target, user=lead)
                if target is not None and data['finding'].get('authorise'):
                    from Tracker.services.reman.release import request_authorisation
                    core.refresh_from_db()
                    request_authorisation(core, lead)
                    answer = data['finding'].get('decline')
                    if answer:
                        # The customer's no, recorded by whoever took the call.
                        from Tracker.services.reman.release import record_authorisation
                        core.refresh_from_db()
                        record_authorisation(
                            core, False, by_email.get('jennifer.mgr@demo.ambac.com') or lead,
                            note=answer['note'], contact=answer['contact'],
                            method=answer['method'], reference=answer['reference'])
        self.log(f"  Released {released} torn-down core(s)")
        return released

    def _raise_finding(self, core, spec, user):
        """Record one bench finding on this core's own component, named exactly.

        No fallback: a finding whose component isn't on the unit is a seed bug. Falling
        back to "any component" once put a nozzle finding on the injector body, and the
        exhibit it was for silently stopped existing.
        """
        from Tracker.services.reman.findings import record_finding

        target = (core.harvested_components.filter(is_scrapped=False)
                  .filter(component_type__name=spec['component']).first())
        if target is None:
            self.log(f"  {core.core_number}: no {spec['component']!r} to raise a finding on "
                     "- finding skipped", warning=True)
            return None
        if target.condition_grade == spec['grade']:
            self.log(f"  {core.core_number}: {spec['component']} is already grade "
                     f"{spec['grade']} - finding skipped", warning=True)
            return None
        return record_finding(target, grade=spec['grade'], finding=spec['finding'], user=user)

    def _start_a_teardown_batch(self, cores, users):
        """Put RECEIVED cores onto a teardown work order and open disassembly.

        Every core in the demo sat at RECEIVED or at an end state, and none was ever
        on a work order. The core detail page says it plainly — "Cores join one when
        teardown starts" — so with no teardown started, the whole reman lane had no
        entry point: no unit to open in the DWI runtime, nothing to grade at the
        bench, no scope to resolve, and nothing to send for over-and-above
        authorisation.

        Driven through `start_teardown_batch` rather than by writing rows: it creates
        the WO, moves each unit onto the route's entry step (a core's position is its
        part's — without that there is nowhere to open it), and runs the real
        disassembly transition per core. Setting the fields by hand would reproduce
        the shape and none of the behaviour, which is what left the rest of the demo
        hollow.
        """
        from Tracker.services.reman.teardown import start_teardown_batch

        employees = users.get('employees', []) if isinstance(users, dict) else []
        user = self._actor('casey.dual@demo.ambac.com', employees[0] if employees else None)
        if user is None:
            self.log("  Skipped teardown batch: no employees", warning=True)
            return None

        # Same core type, RECEIVED, and on no work order — `_validate_batch`'s rules.
        # A core has no work_order of its own: its position is its part's, so the
        # check reads through `core.part.work_order_id`.
        candidates = [
            c for c in cores
            if c.status == 'RECEIVED' and c.part_id is not None
            and c.part.work_order_id is None
        ]
        by_type = {}
        for core in candidates:
            by_type.setdefault(core.core_type_id, []).append(core)
        batch = next((v for v in by_type.values() if v), [])
        if not batch:
            self.log("  Skipped teardown batch: no RECEIVED cores free of a work order",
                     warning=True)
            return None

        try:
            wo = start_teardown_batch(batch, user)
        except Exception as e:                      # validation differences across seeds
            self.log(f"  Skipped teardown batch: {e}", warning=True)
            return None

        # ASCII only: the seed log goes to a Windows console, where a non-ASCII dash
        # comes out as mojibake.
        self.log(f"  Started teardown {wo.ERP_id} with {len(batch)} core(s) "
                 f"- the reman lane now has a unit to work")
        return wo

    def _classify_recoverability(self):
        """Mark which component types can be recovered from a torn-down core.

        The MRO rotable/expendable split: assemblies come back out and go back in;
        seals, springs and coils are fitted once. Without this every component defaults
        to NOT recoverable, which is the safe direction but means the RECOVER lane sees
        nothing.
        """
        from Tracker.models import PartTypes

        recoverable = [
            'Injector Body', 'Injector Nozzle Assembly', 'Control Valve Assembly',
            'Solenoid Valve', 'Plunger Assembly',
        ]
        n = PartTypes.objects.filter(
            tenant=self.tenant, name__in=recoverable, is_current_version=True,
        ).update(can_recover=True)
        self.log(f"  Marked {n} component types recoverable")

    def _flag_disassembly_process(self, part_types):
        """Mark the reman process teardown-eligible and make it the core type's default.

        Without `Processes.is_disassembly=True` somewhere, `start_teardown_batch`
        cannot resolve a process and teardown cannot be started AT ALL on seeded data —
        the whole reman loop was undemonstrable from a clean seed. The reman process is
        the right one to flag: it carries the whole visit, teardown through rebuild,
        which is how a repair-and-return unit keeps one thread from arrival to shipment.
        """
        from Tracker.models import PartTypes, Processes

        injector = next(
            (pt for pt in part_types if pt.name == 'Common Rail Injector'), None)
        if injector is None:
            return
        # By intent, not by name: with the new-build process also approved,
        # order_by('name') picked "Injector Build" and every teardown ran on it.
        process = Processes.objects.filter(
            tenant=self.tenant, part_type=injector, status='APPROVED',
            is_current_version=True, archived=False, is_remanufactured=True,
        ).order_by('name').first()
        if process is None:
            self.log("  No approved injector process — teardown will not be startable")
            return
        if not process.is_disassembly:
            process.is_disassembly = True
            process.save(update_fields=['is_disassembly'])
        current = PartTypes.objects.filter(pk=injector.pk).first()
        if current and current.default_disassembly_process_id != process.id:
            current.default_disassembly_process = process
            current.save(update_fields=['default_disassembly_process'])
        self.log(f"  Teardown process: {process.name}")

    def _create_repair_codes(self, part_types):
        """Repair codes and a default rebuild level for the injector.

        Without these the rebuild planner has no scope to resolve and falls back to
        the whole BOM. The set is deliberately small but shows the two layers: base
        operations every unit gets, a level that adds one, and a finding-raised code
        that only fires when a component comes out reconditionable.
        """
        from Tracker.models import PartTypes, RepairCode, RebuildScopePreset, Steps

        injector = next(
            (pt for pt in part_types if pt.name == 'Common Rail Injector'), None)
        if injector is None:
            self.log("  No Common Rail Injector part type — skipping repair codes")
            return []

        nozzle = PartTypes.objects.filter(
            tenant=self.tenant, name='Injector Nozzle Assembly').first()

        # BASE-REBUILD and FLOW-VERIFY are base/level scope: every op on the route runs
        # anyway, so they carry no Repair node and route nothing. NZL-RECON and
        # NZL-REPLACE are repairs: each is carried by a Repair node off Nozzle
        # Inspection (seed/demo/manufacturing DEMO_REPAIR_BRANCHES).
        specs = [
            # (code, name, component_type, trigger, Repair node)
            ('BASE-REBUILD', 'Base rebuild operations', None, 'ALWAYS', None),
            ('FLOW-VERIFY', 'Flow-test the finished unit', None, 'PRESET', None),
            ('NZL-RECON', 'Recondition injector nozzle', nozzle, 'RECONDITION',
             'Nozzle Recondition'),
            ('NZL-REPLACE', 'Replace injector nozzle', nozzle, 'REPLACE_BUY',
             'Nozzle Replacement'),
        ]

        codes = {}
        for code, name, ctype, trigger, repair_node in specs:
            obj, _ = RepairCode.objects.update_or_create(
                tenant=self.tenant, code=code,
                defaults={'name': name, 'component_type': ctype, 'trigger': trigger},
            )
            if repair_node:
                Steps.objects.filter(
                    tenant=self.tenant, part_type=injector, name=repair_node,
                ).update(repair_code=obj)
            codes[code] = obj

        preset, _ = RebuildScopePreset.objects.update_or_create(
            tenant=self.tenant, core_type=injector, name='Standard rebuild',
            defaults={
                'is_default': True,
                'notes': 'What the shop sells as a standard injector rebuild. '
                         'Findings extend it.',
            },
        )
        preset.codes.set([codes['FLOW-VERIFY']])

        self.log(f"  Created {len(codes)} repair codes and 1 rebuild level")
        return list(codes.values())

    def _ensure_component_part_types(self):
        """Ensure component part types exist for harvesting."""
        component_types = {}

        for comp_data in DEMO_DISASSEMBLY_BOM:
            comp_name = comp_data['component_name']
            comp_prefix = comp_data['component_prefix']

            # Use update_or_create for deterministic creation
            comp_type, _ = PartTypes.objects.update_or_create(
                tenant=self.tenant,
                name=comp_name,
                defaults={
                    'ID_prefix': comp_prefix,
                }
            )
            component_types[comp_name] = comp_type

        return component_types

    def _create_disassembly_bom_lines(self, part_types, component_types):
        """Create DisassemblyBOMLines defining expected yields."""
        bom_lines = []

        # Find the Common Rail Injector part type (core type)
        cri_type = None
        for pt in part_types:
            if 'Common Rail' in pt.name:
                cri_type = pt
                break

        if not cri_type:
            self.log("  Warning: Common Rail Injector part type not found, skipping BOM lines")
            return bom_lines

        for bom_data in DEMO_DISASSEMBLY_BOM:
            comp_type = component_types.get(bom_data['component_name'])
            if not comp_type:
                continue

            bom_line, _ = DisassemblyBOMLine.objects.update_or_create(
                tenant=self.tenant,
                core_type=cri_type,
                component_type=comp_type,
                defaults={
                    'expected_qty': bom_data['expected_qty'],
                    'expected_fallout_rate': bom_data['expected_fallout_rate'],
                    'line_number': bom_data['line_number'],
                    'notes': bom_data['notes'],
                }
            )
            bom_lines.append(bom_line)

        return bom_lines

    def _create_repair_orders(self, companies):
        """One open order per customer whose own units are here for repair, with a line
        for the units it covers. Received cores name it (create_core(order=...))."""
        from Tracker.models import Orders, OrdersStatus, OrderLine, OrderLineStatus
        by_name = companies.get('by_name', {}) if isinstance(companies, dict) else {}
        core_type = PartTypes.objects.filter(tenant=self.tenant, name__icontains='Common Rail').first()
        units = {}
        for c in DEMO_CORES:
            if c.get('for_order'):
                units[c['for_order']] = units.get(c['for_order'], 0) + 1
        orders = {}
        for number, spec in REPAIR_ORDERS.items():
            company = by_name.get(spec['customer'])
            due = (self.today + timedelta(days=spec['due_days'])).date()
            order, _ = Orders.objects.update_or_create(
                tenant=self.tenant, order_number=number,
                defaults={'name': spec['name'], 'company': company,
                          'order_status': OrdersStatus.IN_PROGRESS, 'estimated_completion': due})
            if core_type is not None:
                OrderLine.objects.update_or_create(
                    tenant=self.tenant, order=order, line_number=1,
                    defaults={'part_type': core_type, 'quantity': units.get(number, 1),
                              'due_date': due, 'status': OrderLineStatus.OPEN,
                              'notes': 'Customer-owned injectors, repaired and returned.'})
            orders[number] = order
        return orders

    def _create_cores(self, companies, users):
        """Create preset demo cores."""
        cores = []

        # Get company lookup
        if isinstance(companies, dict):
            company_map = companies.get('by_name', {})
        else:
            company_map = {c.name: c for c in companies} if companies else {}

        # Get employees for received_by, disassembled_by
        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            self.log("  Warning: No employees available for core creation")
            return cores

        # Get Common Rail Injector part type
        core_type = PartTypes.objects.filter(
            tenant=self.tenant,
            name__icontains='Common Rail'
        ).first()

        if not core_type:
            self.log("  Warning: Common Rail Injector part type not found")
            return cores

        for core_data in DEMO_CORES:
            core = self._create_single_core(core_data, core_type, company_map, employees)
            if core:
                cores.append(core)

        return cores

    def _create_single_core(self, core_data, core_type, company_map, employees):
        """Create a single core from configuration."""
        # Get customer company
        customer = company_map.get(core_data.get('customer_name'))

        # Calculate dates
        received_date = (self.today - timedelta(days=core_data['received_days_ago'])).date()
        received_datetime = timezone.make_aware(
            timezone.datetime.combine(received_date, timezone.datetime.min.time())
        ) + timedelta(hours=9)  # 9 AM receipt

        # Received at the core dock by the shift lead, not employees[0] (the Tenant Admin)
        received_by = self._actor('casey.dual@demo.ambac.com', employees[0] if employees else None)

        # Calculate disassembly timestamps if applicable
        disassembly_started_at = None
        disassembly_completed_at = None
        disassembled_by = None

        if 'disassembly_started_days_ago' in core_data:
            disassembly_started_at = received_datetime + timedelta(
                days=core_data['received_days_ago'] - core_data['disassembly_started_days_ago']
            )

        if 'disassembly_completed_days_ago' in core_data:
            disassembly_completed_at = received_datetime + timedelta(
                days=core_data['received_days_ago'] - core_data['disassembly_completed_days_ago']
            )
            disassembled_by = self._actor('dave.wilson@demo.ambac.com', employees[0])

        # Calculate core credit issued timestamp if applicable
        core_credit_issued_at = None
        if core_data.get('core_credit_issued') and disassembly_completed_at:
            core_credit_issued_at = disassembly_completed_at + timedelta(days=1)

        # Teardown states are reached through the teardown services (_walk_teardown),
        # not written: a core written as IN_DISASSEMBLY/DISASSEMBLED sat on no work
        # order, so nothing in the product could complete or release it.
        walked = core_data['status'] in self.WALKED_STATUSES

        # Create the core with ALL fields explicitly set. A core is a part: a new one goes
        # through create_core so it has its part; an existing one is updated in place.
        core_fields = {
                'serial_number': core_data['serial_number'],
                'core_type': core_type,
                'received_date': received_date,
                'received_by': received_by,
                'customer': customer,
                'source_type': core_data['source_type'],
                'source_reference': core_data['source_reference'],
                'condition_grade': core_data['condition_grade'],
                'condition_notes': core_data['condition_notes'],
                'status': 'RECEIVED' if walked else core_data['status'],
                'disassembly_started_at': None if walked else disassembly_started_at,
                'disassembly_completed_at': None if walked else disassembly_completed_at,
                'disassembled_by': None if walked else disassembled_by,
                'fulfilment_mode': core_data.get('fulfilment_mode', 'EXCHANGE'),
                'core_credit_value': core_data.get('core_credit_value'),
                'core_credit_issued': core_data.get('core_credit_issued', False),
                'core_credit_issued_at': core_credit_issued_at,
        }
        core = Core.objects.filter(tenant=self.tenant,
                                   core_number=core_data['core_number']).first()
        order = getattr(self, '_repair_orders', {}).get(core_data.get('for_order'))
        if core is None:
            core = create_core(tenant=self.tenant, core_number=core_data['core_number'],
                               order=order, **core_fields)
        else:
            if walked and core.part_id and core.part.work_order_id:
                # Already walked on an earlier run: don't drag it back to RECEIVED.
                for f in ('status', 'disassembly_started_at', 'disassembly_completed_at',
                          'disassembled_by'):
                    core_fields.pop(f)
            Core.objects.filter(pk=core.pk).update(**core_fields)
            core.refresh_from_db()
        sync_part_status(core)

        # Backdate the created_at timestamp
        Core.objects.filter(pk=core.pk).update(created_at=received_datetime)

        core.refresh_from_db()
        return core

    def _create_harvested_components(self, cores, users):
        """Create harvested components from disassembled cores."""
        components = []

        # Get employees for disassembled_by
        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            return components

        # Only process cores that have component definitions
        for core in cores:
            core_data = next((c for c in DEMO_CORES if c['core_number'] == core.core_number), None)
            if not core_data or 'components' not in core_data:
                continue

            # Get component type lookup
            component_types = {
                ct.name: ct for ct in PartTypes.objects.filter(tenant=self.tenant)
            }

            for comp_data in core_data['components']:
                comp_type = component_types.get(comp_data['component_name'])
                if not comp_type:
                    # Loud, not silent: a name that matched no part type used to drop
                    # the component, and a finding meant for it landed on another.
                    self.log(f"  {core.core_number}: no part type named "
                             f"{comp_data['component_name']!r} - component skipped", warning=True)
                    continue

                component = self._create_single_component(
                    core, comp_type, comp_data, employees
                )
                if component:
                    components.append(component)

        return components

    def _create_single_component(self, core, comp_type, comp_data, employees):
        """Create a single harvested component."""
        # Use disassembly completion time or approximate
        if core.disassembly_completed_at:
            disassembled_at = core.disassembly_completed_at
        elif core.disassembly_started_at:
            disassembled_at = core.disassembly_started_at + timedelta(hours=2)
        else:
            disassembled_at = timezone.now()

        # Torn down by an operator, not employees[1] (the QA Manager)
        disassembled_by = self._actor('dave.wilson@demo.ambac.com', employees[0])

        # Determine scrap timestamps if scrapped
        scrapped_at = None
        scrapped_by = None
        if comp_data['is_scrapped']:
            scrapped_at = disassembled_at + timedelta(minutes=30)
            scrapped_by = self._actor('dave.wilson@demo.ambac.com', employees[0])

        # Create the component with ALL fields explicitly set
        component, _ = HarvestedComponent.objects.update_or_create(
            tenant=self.tenant,
            core=core,
            component_type=comp_type,
            position=comp_data.get('position', ''),
            defaults={
                'component_part': None,
                'disassembled_by': disassembled_by,
                'condition_grade': comp_data['condition_grade'],
                'condition_notes': comp_data['condition_notes'],
                'is_scrapped': comp_data['is_scrapped'],
                'scrap_reason': comp_data['scrap_reason'],
                'scrapped_at': scrapped_at,
                'scrapped_by': scrapped_by,
                'original_part_number': comp_data.get('original_part_number', ''),
            }
        )

        # Backdate timestamps
        HarvestedComponent.objects.filter(pk=component.pk).update(
            disassembled_at=disassembled_at,
            created_at=disassembled_at,
        )

        component.refresh_from_db()
        return component
