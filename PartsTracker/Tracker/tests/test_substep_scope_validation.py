"""1e: FPI ⊕ batch mutual exclusion.

A BATCH-scope substep can't live on a first-piece-inspection step — FPI means
"inspect the first piece, then run the rest," which is incompatible with a
batch substep that runs the whole lot at once. Enforced in
`SubstepSerializer.validate`.
"""
from rest_framework import serializers as drf_serializers

from Tracker.models import PartTypes, Steps, Tenant
from Tracker.serializers.dwi import SubstepSerializer
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class SubstepFpiBatchExclusionTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="FPI Excl", slug="fpi-excl", tier="PRO"
        )
        self.set_tenant_context(self.tenant)
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.fpi_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Inspect",
            requires_first_piece_inspection=True,
        )
        self.normal_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Assemble",
            requires_first_piece_inspection=False,
        )

    def test_batch_scope_rejected_on_fpi_step(self):
        ser = SubstepSerializer()
        with self.assertRaises(drf_serializers.ValidationError) as ctx:
            ser.validate({"scope": "batch", "step": self.fpi_step})
        self.assertIn("scope", ctx.exception.detail)

    def test_batch_scope_allowed_on_non_fpi_step(self):
        ser = SubstepSerializer()
        attrs = ser.validate({"scope": "batch", "step": self.normal_step})
        self.assertEqual(attrs["scope"], "batch")

    def test_sampled_scope_allowed_on_fpi_step(self):
        ser = SubstepSerializer()
        attrs = ser.validate({"scope": "sampled", "step": self.fpi_step})
        self.assertEqual(attrs["scope"], "sampled")
