"""3D model conversion to GLB (services/model_processor.py).

No database: the processor is pure file work, so these run without the test DB.
"""
import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from Tracker.services.model_processor import ACCEPTED_EXTENSIONS, ModelProcessor

FIXTURES = Path(__file__).parent / 'fixtures' / 'models'


class ModelProcessorTests(SimpleTestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _process(self, fixture):
        work = self.tmp / fixture  # the GLB is written beside the input
        shutil.copy(FIXTURES / fixture, work)
        return ModelProcessor().process(str(work))

    def test_the_upload_form_and_the_server_accept_the_same_cad_formats(self):
        for ext in ('.step', '.stp', '.iges', '.igs'):
            self.assertIn(ext, ACCEPTED_EXTENSIONS)

    def test_an_iges_file_converts_to_a_glb(self):
        """IGES goes through cascadio's bytes interface (cascadio >= 0.1); the
        0.0.x release this replaced read STEP only."""
        result = self._process('microstrip.igs')
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.original_format, 'igs')
        self.assertGreater(result.face_count, 0)
        self.assertTrue(Path(result.output_path).exists())
        self.assertEqual(Path(result.output_path).suffix, '.glb')

    def test_an_unsupported_format_is_refused_with_the_supported_list(self):
        work = self.tmp / 'part.fbx'
        work.write_bytes(b'not a model')
        result = ModelProcessor().process(str(work))
        self.assertFalse(result.success)
        self.assertIn('Unsupported format', result.error)
        self.assertIn('.igs', result.error)
