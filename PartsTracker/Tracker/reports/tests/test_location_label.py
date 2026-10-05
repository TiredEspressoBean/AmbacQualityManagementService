"""Tests for LocationLabelAdapter — both layouts via ReportAdapterTestMixin (fixture
validation, template compile, determinism)."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.location_label import LocationLabelAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin

_SKIP = ("Each entry is resolved with locations.find_location, which filters by tenant; "
         "the DB-backed refusal is covered in tests/test_locations_scan.py.")


class TestLocationLabelThermal(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = LocationLabelAdapter
    fixture_name = "location_label_thermal_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)


class TestLocationLabelSheet(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = LocationLabelAdapter
    fixture_name = "location_label_sheet_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)
