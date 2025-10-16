from django.test import TestCase
from django.db import connections

class VectorTestCase(TestCase):
    """
    Custom TestCase that ensures pgvector extension is available.
    Use this as the base class for any tests that depend on vector fields.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure vector extension exists in test database
        with connections['default'].cursor() as cursor:
            try:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')
            except Exception as e:
                print(f"Warning: Could not create vector extension: {e}")
                # Tests will be skipped via @skipIf decorator if extension unavailable
