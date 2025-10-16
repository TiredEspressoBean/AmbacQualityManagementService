import sys
from django.db import connection, connections
from django.test.runner import DiscoverRunner
from django.test.utils import setup_databases
from django.db.backends.postgresql.creation import DatabaseCreation


class VectorAwareTestRunner(DiscoverRunner):
    """
    A test runner that creates the vector extension in the test database.
    The vector extension must be created BEFORE migrations run.
    """

    def setup_databases(self, **kwargs):
        """Override to add vector extension after DB creation but before migrations"""

        # Store the original _execute_create_test_db method
        original_create = DatabaseCreation._execute_create_test_db

        def _execute_create_test_db_with_vector(self, cursor, parameters, keepdb=False):
            """Wrapper that adds vector extension after database creation"""
            # Call original method to create the database
            original_create(self, cursor, parameters, keepdb)

            # Now add the vector extension to the newly created database
            # Extract database name without quotes
            test_db_name = parameters.get('dbname', '').strip('"')

            if not test_db_name:
                return

            try:
                # Connect to the newly created test database using Django's connection
                # Close existing connection first
                if self.connection.connection is not None:
                    self.connection.close()

                # Temporarily change connection settings to point to test database
                old_db_name = self.connection.settings_dict['NAME']
                self.connection.settings_dict['NAME'] = test_db_name

                # Connect and create extension
                with self.connection.cursor() as cur:
                    cur.execute('CREATE EXTENSION IF NOT EXISTS vector')

                # Restore original settings
                self.connection.settings_dict['NAME'] = old_db_name
                self.connection.close()

                print(f"Added vector extension to {test_db_name}")
            except Exception as e:
                print(f"Warning: Could not create vector extension: {e}")
                # Restore settings even on error
                try:
                    self.connection.settings_dict['NAME'] = old_db_name
                    self.connection.close()
                except:
                    pass

        # Monkey-patch the database creation method
        DatabaseCreation._execute_create_test_db = _execute_create_test_db_with_vector

        try:
            # Call parent setup_databases
            return super().setup_databases(**kwargs)
        finally:
            # Restore original method
            DatabaseCreation._execute_create_test_db = original_create