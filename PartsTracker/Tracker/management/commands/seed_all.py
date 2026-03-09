"""
Seed database with test data.

Harness command that can run both seed_dev and seed_demo commands.
- seed_dev: Random Faker data for development/testing
- seed_demo: Deterministic preset data for demos and training

Usage:
    # Seed both dev and demo tenants
    python manage.py seed

    # Seed only dev tenant
    python manage.py seed --only dev

    # Seed only demo tenant
    python manage.py seed --only demo

    # With options passed through
    python manage.py seed --scale medium --no-clear
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed database with test data (runs seed_dev and/or seed_demo)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            type=str,
            choices=['dev', 'demo'],
            help='Seed only one tenant: dev (random) or demo (deterministic)',
        )
        parser.add_argument(
            '--scale',
            type=str,
            default='small',
            choices=['small', 'medium', 'large'],
            help='Scale of data generation for dev tenant. Default: small',
        )
        parser.add_argument(
            '--no-clear',
            action='store_true',
            help='Skip clearing existing data',
        )
        parser.add_argument(
            '--skip-historical',
            action='store_true',
            help='Skip generating historical FPY trend data (dev only)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually doing it',
        )

    def handle(self, *args, **options):
        only = options.get('only')
        scale = options['scale']
        no_clear = options['no_clear']
        skip_historical = options['skip_historical']
        dry_run = options['dry_run']
        verbosity = options.get('verbosity', 1)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SEED DATABASE")
        self.stdout.write("=" * 60)

        if only:
            self.stdout.write(f"Mode: {only} only")
        else:
            self.stdout.write("Mode: both dev and demo")

        # Seed dev tenant
        if only != 'demo':
            self.stdout.write("\n" + "-" * 60)
            self.stdout.write("Running seed_dev...")
            self.stdout.write("-" * 60)
            call_command(
                'seed_dev',
                scale=scale,
                no_clear=no_clear,
                skip_historical=skip_historical,
                dry_run=dry_run,
                verbosity=verbosity,
            )

        # Seed demo tenant
        if only != 'dev':
            self.stdout.write("\n" + "-" * 60)
            self.stdout.write("Running seed_demo...")
            self.stdout.write("-" * 60)
            call_command(
                'seed_demo',
                scale=scale,
                no_clear=no_clear,
                dry_run=dry_run,
                verbosity=verbosity,
            )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("SEEDING COMPLETE"))
        self.stdout.write("=" * 60)
