"""
Demo seeders for deterministic, preset data.

These seeders create the exact data specified in DEMO_DATA_SYSTEM.md
for sales demos and user training. All data is deterministic - same
result every time.

Usage:
    from .seed.demo import DemoScenario

    scenario = DemoScenario(stdout, style, tenant)
    scenario.seed()
"""

from .scenario import DemoScenario
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
from .receiving import DemoReceivingSeeder
from .supplier_quality import DemoSupplierQualitySeeder
from .outside_process import DemoOutsideProcessSeeder
from .reman import DemoRemanSeeder
from .life_tracking import DemoLifeTrackingSeeder
from .models_3d import DemoThreeDModelSeeder
from .dwi import DemoDwiSeeder
from .showcase import DemoShowcaseSeeder

__all__ = [
    'DemoScenario',
    'DemoUserSeeder',
    'DemoCompanySeeder',
    'DemoManufacturingSeeder',
    'DemoOrdersSeeder',
    'DemoQualitySeeder',
    'DemoCapaSeeder',
    'DemoTrainingRecordsSeeder',
    'DemoDocumentsSeeder',
    'TrainingExercisesSeeder',
    'DemoSamplingSeeder',
    'DemoReceivingSeeder',
    'DemoSupplierQualitySeeder',
    'DemoOutsideProcessSeeder',
    'DemoRemanSeeder',
    'DemoLifeTrackingSeeder',
    'DemoThreeDModelSeeder',
    'DemoDwiSeeder',
    'DemoShowcaseSeeder',
]
