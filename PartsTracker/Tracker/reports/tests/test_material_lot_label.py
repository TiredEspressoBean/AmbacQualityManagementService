"""Tests for MaterialLotLabelAdapter — both layouts via ReportAdapterTestMixin
(fixture validation, template compile, determinism)."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.material_lot_label import MaterialLotLabelAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin

_SKIP_TENANT = (
    "Cross-tenant isolation is enforced by the tenant filter in "
    "MaterialLotLabelParamsSerializer.validate_lot_ids() and the ORM query in "
    "build_context(); covered by test_receiving_phase2 against the database.")


class TestMaterialLotLabelThermal(ReportAdapterTestMixin, SimpleTestCase):
    """One 4"×2" label per page, a lot counted in boxes with a heat number and use-by."""
    adapter_class = MaterialLotLabelAdapter
    fixture_name = "material_lot_label_thermal_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP_TENANT)


class TestMaterialLotLabelSheet(ReportAdapterTestMixin, SimpleTestCase):
    """Twelve labels on the Letter sheet layout — a full page of ten, then two."""
    adapter_class = MaterialLotLabelAdapter
    fixture_name = "material_lot_label_sheet_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP_TENANT)
