"""
Document package generators.

Each generator handles a specific type of document package:
- PPAP: Production Part Approval Process (automotive)
- FAI: First Article Inspection (aerospace)
- CoC: Certificate of Conformance
- EightD: 8D Problem Solving Report
"""

from .base import BasePackageGenerator
from .ppap import PPAPPackageGenerator
from .fai import FAIPackageGenerator
from .coc import CoCPackageGenerator
from .eight_d import EightDPackageGenerator

__all__ = [
    "BasePackageGenerator",
    "PPAPPackageGenerator",
    "FAIPackageGenerator",
    "CoCPackageGenerator",
    "EightDPackageGenerator",
]
