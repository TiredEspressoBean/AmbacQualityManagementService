"""
Modular seed data generation for PartsTracker.

Each module handles a specific domain:
- base: Shared utilities, tenant setup, audit helpers
- users: Companies, users, groups, admin
- manufacturing: Part types, processes, steps, equipment
- orders: Orders, work orders, parts workflow
- quality: Quality reports, measurements, sampling
- capa: CAPA, RCA, tasks, verification
- documents: Documents, approvals, document types
- training: Training types, requirements, records
- calibration: Calibration records
- models_3d: 3D models, heatmap annotations

Usage:
    from Tracker.management.commands.seed import (
        BaseSeeder,
        UserSeeder,
        ManufacturingSeeder,
        OrderSeeder,
        QualitySeeder,
        CapaSeeder,
        DocumentSeeder,
        ThreeDModelSeeder,
        TrainingSeeder,
        CalibrationSeeder,
    )
"""

from .base import BaseSeeder
from .users import UserSeeder
from .manufacturing import ManufacturingSeeder
from .orders import OrderSeeder
from .quality import QualitySeeder
from .capa import CapaSeeder
from .documents import DocumentSeeder
from .models_3d import ThreeDModelSeeder
from .training import TrainingSeeder
from .calibration import CalibrationSeeder

__all__ = [
    'BaseSeeder',
    'UserSeeder',
    'ManufacturingSeeder',
    'OrderSeeder',
    'QualitySeeder',
    'CapaSeeder',
    'DocumentSeeder',
    'ThreeDModelSeeder',
    'TrainingSeeder',
    'CalibrationSeeder',
]
