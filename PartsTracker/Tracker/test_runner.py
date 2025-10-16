from django.test.runner import DiscoverRunner
from django.db import connections
import psycopg2

class VectorAwareTestRunner(DiscoverRunner):
    """
    A test runner that creates the vector extension in the test database.
    The vector extension must be created BEFORE migrations run.
    """

    def setup_databases(self, verbosity=1, interactive=True, keepdb=False, debug_sql=False, parallel=0, aliases=None, serialized_aliases=None, **kwargs):
        """Create test databases and add vector extension before migrations"""
        from django.conf import settings

        # Get database settings
        db_settings = settings.DATABASES['default']

        # Create test database name
        test_db_name = f"test_{db_settings['NAME']}"

        # Connect to postgres database to create test database
        try:
            conn = psycopg2.connect(
                database='postgres',
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                host=db_settings['HOST'],
                port=db_settings['PORT']
            )
            conn.set_isolation_level(0)  # AUTOCOMMIT
            cur = conn.cursor()

            # Drop test database if it exists (from previous runs)
            cur.execute(f'DROP DATABASE IF EXISTS {test_db_name}')

            # Create test database
            cur.execute(f'CREATE DATABASE {test_db_name}')

            cur.close()
            conn.close()

            # Now connect to the test database and create vector extension
            test_conn = psycopg2.connect(
                database=test_db_name,
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                host=db_settings['HOST'],
                port=db_settings['PORT']
            )
            test_cur = test_conn.cursor()
            test_cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
            test_cur.close()
            test_conn.commit()
            test_conn.close()

            print(f"Created test database '{test_db_name}' with vector extension")

        except Exception as e:
            print(f"Warning during test database setup: {e}")

        # Now call parent setup_databases which will run migrations
        # Force keepdb=True since we already created the database
        # Remove keepdb from kwargs if it exists to avoid duplicates
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'keepdb'}

        return super().setup_databases(
            verbosity=verbosity,
            interactive=interactive,
            keepdb=True,  # Always True since we created the DB ourselves
            debug_sql=debug_sql,
            parallel=parallel,
            aliases=aliases,
            serialized_aliases=serialized_aliases,
            **filtered_kwargs
        )