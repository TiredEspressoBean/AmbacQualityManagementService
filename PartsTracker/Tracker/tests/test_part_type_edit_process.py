"""A part's routing still resolves after its part type is edited.

VERSIONING_ARCHITECTURE.md flagged `part_type.processes` coming back empty after a part
type edit (a new version is a new row, and the processes stayed on the old one). The
version-link registry now moves them to the new version; this pins the part's view of it.
"""
from django.test import TestCase

from Tracker.tests.base import TenantContextMixin


class PartTypeEditProcessTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Tenant
        self.tenant = Tenant.objects.create(name="PT edit", slug="pt-edit-process")
        self.set_tenant_context(self.tenant)

    def test_a_part_resolves_its_process_after_its_part_type_is_edited(self):
        from Tracker.models import Parts, PartTypes, Processes
        from Tracker.serializers.mes_lite import PartsSerializer
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        proc = Processes.objects.create(tenant=self.tenant, name="Build", part_type=pt,
                                        status="APPROVED")
        part = Parts.objects.create(tenant=self.tenant, ERP_id="P-1", part_type=pt)
        new_pt = pt.create_new_version(user=None, change_description="Renamed",
                                       name="Injector Mk2")
        part.refresh_from_db()
        self.assertEqual(part.part_type_id, new_pt.id)
        self.assertEqual(PartsSerializer().get_process(part), proc.id)
