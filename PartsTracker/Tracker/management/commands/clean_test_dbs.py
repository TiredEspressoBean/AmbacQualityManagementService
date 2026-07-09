"""Drop stale Django test databases left behind by killed test runs.

A test run that dies mid-flight (Ctrl-C, tool timeout, crashed parallel
worker) orphans its test databases — `test_<name>` plus one clone per
`--parallel` worker — and often leaves Postgres backends attached to them.
Every subsequent run then fails with "database ... already exists" (or, without
--noinput, hangs forever on the interactive delete prompt).

This command terminates those backends and drops every database whose name
starts with `test_`. Test databases are disposable by definition, so this is
always safe; it never touches the real database.

Usage:
    python manage.py clean_test_dbs            # drop all stale test DBs
    python manage.py clean_test_dbs --list     # show them without dropping
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Terminate connections to and drop stale test_* databases."

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true',
                            help='List stale test databases without dropping them.')

    def handle(self, *args, **options):
        import psycopg2

        db = settings.DATABASES['default']
        conn = psycopg2.connect(
            dbname='postgres', user=db['USER'], password=db['PASSWORD'],
            host=db.get('HOST') or 'localhost', port=db.get('PORT') or 5432,
        )
        conn.autocommit = True
        try:
            cur = conn.cursor()
            cur.execute("SELECT datname FROM pg_database WHERE datname LIKE 'test_%'")
            targets = [row[0] for row in cur.fetchall()]

            if not targets:
                self.stdout.write("No stale test databases.")
                return

            if options['list']:
                for name in targets:
                    self.stdout.write(name)
                return

            for name in targets:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
                self.stdout.write(f"dropped {name}")
        finally:
            conn.close()
