"""Tests for the outbound shipment paperwork adapters — fixture validation, template
compile, determinism. The context built from real records is covered in
test_customer_shipping."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.shipment_documents import PackingListAdapter, ShipmentCocAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin

_SKIP = ("Enforced by ShipmentParamsSerializer.validate_shipment_id() and "
         "build_context()'s tenant filter.")


class TestPackingListAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = PackingListAdapter
    fixture_name = "shipment_document_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)


class TestShipmentCocAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = ShipmentCocAdapter
    fixture_name = "shipment_document_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)
