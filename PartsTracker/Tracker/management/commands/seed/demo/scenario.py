"""
Demo scenario orchestrator.

Coordinates all demo seeders to create the interconnected story from DEMO_DATA_SYSTEM.md.
This is the main entry point for demo mode seeding.

The demo scenario creates:
1. Foundation: Users, companies
2. Manufacturing: Processes, steps, equipment
3. Orders: Three orders showing different states (pending, in-progress, completed)
4. Quality events: Failures, dispositions, SPC data
5. CAPAs: Linked to quality failures
6. Training records: Including expired certifications
7. Documents: Work instructions, approvals

All data is deterministic and interconnected to support demo narratives.
"""

from django.utils import timezone
from datetime import timedelta

from Tracker.models import Tenant, PartTypes, Processes

from ..base import BaseSeeder
from .users import DemoUserSeeder
from .company import DemoCompanySeeder
from .manufacturing import DemoManufacturingSeeder
from .orders import DemoOrdersSeeder
from .quality import DemoQualitySeeder
from .capa import DemoCapaSeeder
from .training_records import DemoTrainingRecordsSeeder
from .documents import DemoDocumentsSeeder
from .training_exercises import TrainingExercisesSeeder
from .sampling import DemoSamplingSeeder
from .reman import DemoRemanSeeder
from .life_tracking import DemoLifeTrackingSeeder
from .models_3d import DemoThreeDModelSeeder


class DemoScenario(BaseSeeder):
    """
    Main orchestrator for demo data seeding.

    Creates the full interconnected demo story with deterministic data
    that supports sales demos and training exercises.
    """

    def __init__(self, stdout, style, tenant=None, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self._verbose = False

        # Reference point for relative dates (e.g., "-7 days")
        self.today = timezone.now().date()

    def seed(self):
        """
        Execute the full demo scenario.

        Returns:
            dict with all created data organized by category
        """
        self.log("=" * 60)
        self.log("DEMO SCENARIO: Creating deterministic demo data")
        self.log("=" * 60)

        result = {
            'tenant': self.tenant,
            'users': {},
            'companies': {},
            'orders': [],
            'quality_reports': [],
            'capas': [],
        }

        # Phase 1: Foundation
        self.log("\n--- Phase 1: Foundation (Users, Companies) ---")
        result['companies'] = self._seed_companies()
        result['users'] = self._seed_users(result['companies'])

        # Phase 2: Manufacturing Setup
        self.log("\n--- Phase 2: Manufacturing Setup ---")
        result['manufacturing'] = self._seed_manufacturing(result['users'])

        # Phase 2b: Sampling Rules
        self.log("\n--- Phase 2b: Sampling Rules ---")
        result['sampling'] = self._seed_sampling(result['manufacturing'])

        # Phase 2c: Reman Setup
        self.log("\n--- Phase 2c: Remanufacturing Setup ---")
        result['reman'] = self._seed_reman(result['companies'], result['users'], result['manufacturing'])

        # Phase 2d: Life Tracking
        self.log("\n--- Phase 2d: Life Tracking ---")
        result['life_tracking'] = self._seed_life_tracking(result['manufacturing'], result['reman'])

        # Phase 3: Orders (The Story)
        self.log("\n--- Phase 3: Orders and Work Orders ---")
        result['orders'] = self._seed_orders(result['companies'], result['users'], result['manufacturing'])

        # Phase 4: Quality Events
        self.log("\n--- Phase 4: Quality Events ---")
        result['quality'] = self._seed_quality_events(result['orders'], result['users'], result['manufacturing'])

        # Phase 4b: 3D Models and Annotations
        self.log("\n--- Phase 4b: 3D Models and Annotations ---")
        result['models_3d'] = self._seed_3d_models(result['users'])

        # Phase 5: CAPAs
        self.log("\n--- Phase 5: CAPAs ---")
        result['capas'] = self._seed_capas(result['users'])

        # Phase 6: Training Records
        self.log("\n--- Phase 6: Training Records ---")
        result['training'] = self._seed_training(result['users'])

        # Phase 7: Documents and Approvals
        self.log("\n--- Phase 7: Documents and Approvals ---")
        result['documents'] = self._seed_documents(result['users'])

        # Phase 8: Training Exercise Data (TRAIN-* objects)
        self.log("\n--- Phase 8: Training Exercise Data ---")
        result['training_exercises'] = self._seed_training_exercises(
            result['companies'],
            result['users'],
            result['manufacturing']
        )

        self.log("\n" + "=" * 60)
        self.log("DEMO SCENARIO: Complete")
        self.log("=" * 60)

        return result

    def _seed_companies(self):
        """Create demo companies."""
        seeder = DemoCompanySeeder(self.stdout, self.style, self.tenant)
        seeder._verbose = self._verbose
        return seeder.seed()

    def _seed_users(self, companies):
        """Create demo users and link to companies."""
        seeder = DemoUserSeeder(self.stdout, self.style, self.tenant)
        seeder._verbose = self._verbose
        return seeder.seed(companies=companies.get('by_name', {}))

    def _seed_manufacturing(self, users):
        """
        Create demo manufacturing setup with deterministic data.

        Creates:
        - Part types: Common Rail Injector
        - Process: Injector Reman with 11 steps including rework loop
        - Equipment: Flow test stands, torque wrenches with calibration
        - Measurement definitions for SPC
        """
        seeder = DemoManufacturingSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(users)

    def _seed_sampling(self, manufacturing):
        """
        Create demo sampling rules.

        Creates:
        - Standard and Enhanced inspection rulesets
        - Sampling rules linked to inspection steps
        """
        part_types = manufacturing.get('part_types', [])
        processes = manufacturing.get('processes', [])
        process = processes[0] if processes else Processes.objects.filter(tenant=self.tenant).first()

        seeder = DemoSamplingSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(part_types, process)

    def _seed_reman(self, companies, users, manufacturing):
        """
        Create demo remanufacturing data.

        Creates:
        - DisassemblyBOMLines for component definitions
        - Cores with various statuses
        - HarvestedComponents with grades
        """
        part_types = manufacturing.get('part_types', [])
        seeder = DemoRemanSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(companies, users, part_types)

    def _seed_life_tracking(self, manufacturing, reman):
        """
        Create demo life tracking data.

        Creates:
        - LifeLimitDefinitions (hours, cycles, shelf life)
        - PartTypeLifeLimit associations
        - LifeTracking records on cores and parts
        """
        part_types = manufacturing.get('part_types', [])
        cores = reman.get('cores', []) if reman else []

        seeder = DemoLifeTrackingSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(part_types, cores)

    def _seed_3d_models(self, users):
        """
        Create demo 3D models and heatmap annotations.

        Creates:
        - ThreeDModel records for part types
        - HeatMapAnnotations with defect positions
        """
        seeder = DemoThreeDModelSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(users)

    def _seed_orders(self, companies, users, manufacturing):
        """
        Create demo orders with deterministic data.

        Creates:
        - ORD-2024-0042 (Midwest Fleet) - In progress, 24 parts at various stages
        - ORD-2024-0038 (Great Lakes) - Completed, triggered CAPA investigation
        - ORD-2024-0048 (Northern Trucking) - Pending, just received
        - Workflow execution data (StepExecution, StepTransitionLog, EquipmentUsage)
        """
        # Get company list from result
        company_list = companies.get('customers', [])

        # Get part types and process
        part_types = manufacturing.get('part_types', [])
        processes = manufacturing.get('processes', [])
        process = processes[0] if processes else Processes.objects.filter(tenant=self.tenant).first()
        equipment = manufacturing.get('equipment', [])

        seeder = DemoOrdersSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        result = seeder.seed(company_list, users, part_types, process, equipment)

        # Seed workflow execution data for created parts
        workflow_result = seeder.seed_workflow_execution(process, users, equipment)
        result['workflow_execution'] = workflow_result

        # Seed FPI records for work orders
        seeder.seed_fpi_records(result['work_orders'], part_types, users, equipment)

        return result

    def _seed_quality_events(self, orders, users, manufacturing):
        """
        Create demo quality events with deterministic data.

        Creates:
        - Quality reports for parts that failed inspection
        - Dispositions in various states (REWORK approved, pending)
        - SPC measurement data with Rule 2 violation pattern
        """
        seeder = DemoQualitySeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        result = seeder.seed(orders, users)

        # Also seed SPC data and baselines
        measurement_defs = manufacturing.get('measurement_definitions', [])
        if measurement_defs and result.get('quality_reports'):
            seeder.seed_spc_data(measurement_defs, result['quality_reports'], users)

        # Seed SPC baselines (frozen control limits)
        seeder.seed_spc_baselines(users)

        return result

    def _seed_capas(self, users):
        """
        Create demo CAPAs with deterministic data.

        Creates:
        - CAPA-2024-001: Closed with verification (torque wrench calibration)
        - CAPA-2024-003: In progress (nozzle defects, main demo)
        - CAPA-2024-005: Open, just initiated (customer complaint)
        """
        seeder = DemoCapaSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(users)

    def _seed_training(self, users):
        """
        Create demo training records with deterministic data.

        Creates:
        - Mike Rodriguez: NOZ-CERT expiring in 7 days
        - Dave Wilson: FLOW-CERT expired 15 days ago (blocking)
        - Other users: Current certifications
        """
        seeder = DemoTrainingRecordsSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(users)

    def _seed_documents(self, users):
        """
        Create demo documents with deterministic data.

        Creates:
        - WI-1001: Injector Disassembly (released)
        - WI-1002: Nozzle Inspection (released, updated per CAPA)
        - WI-1003: Flow Test Procedure (pending approval)
        """
        seeder = DemoDocumentsSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(users)

    def _seed_training_exercises(self, companies, users, manufacturing):
        """
        Create TRAIN-* objects for training guide exercises.

        These are deterministic records referenced by name in the training
        documentation (operator.md, qa-inspector.md, etc.).
        """
        # Get part types from the manufacturing result or query
        part_types = manufacturing.get('part_types', []) if manufacturing else []
        if not part_types:
            part_types = list(PartTypes.objects.filter(tenant=self.tenant))

        seeder = TrainingExercisesSeeder(self.stdout, self.style, self.tenant, scale=self.scale)
        return seeder.seed(companies, users, part_types)

    def relative_date(self, days_offset):
        """
        Get a date relative to today.

        Args:
            days_offset: Number of days from today (negative for past)

        Returns:
            date object
        """
        return self.today + timedelta(days=days_offset)

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        self._verbose = value
