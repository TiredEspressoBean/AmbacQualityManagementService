"""The 3D model list shows current versions only (docs audit 2026-10-28): a replaced
file left the old version listed and pickable. A by-id fetch of an old version still
works — annotations point at the version they were made on."""
from django.core.files.uploadedfile import SimpleUploadedFile

from Tracker.models import PartTypes, ThreeDModel
from Tracker.tests.base import TenantTestCase


class ThreeDModelListTests(TenantTestCase):

    def test_only_the_current_version_is_listed(self):
        pt = PartTypes.objects.create(tenant=self.tenant_a, name='Body')
        v1 = ThreeDModel.objects.create(
            tenant=self.tenant_a, name='Body', part_type=pt,
            file=SimpleUploadedFile('body.glb', b'GLB_STUB', content_type='model/gltf-binary'),
            original_filename='body.glb', original_format='glb')
        v2 = v1.create_new_version(user=self.user_a, change_description="new scan", name='Body rev B')
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_threedmodel', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get("/api/ThreeDModels/?limit=50")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([m["id"] for m in r.json()["results"]], [str(v2.id)])
        self.assertEqual(self.client.get(f"/api/ThreeDModels/{v1.id}/").status_code, 200)
