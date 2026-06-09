import logging
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser from environment variables and attach to the resolved tenant'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(
                self.style.ERROR(
                    'Missing required environment variables: '
                    'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD'
                )
            )
            return

        tenant = self._resolve_tenant()

        try:
            existing = User.objects.filter(username=username).first()
            if existing is not None:
                # Don't overwrite an existing admin's password / fields, but
                # do backfill the tenant link if it's missing — covers the
                # case where this command ran on a fresh DB before a tenant
                # row existed, leaving the superuser tenant-less.
                if tenant is not None and existing.tenant_id is None:
                    existing.tenant = tenant
                    existing.save(update_fields=['tenant'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Backfilled superuser "{username}" tenant -> {tenant.slug}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Superuser "{username}" already exists')
                    )
                return

            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )

            # Attach to the resolved tenant so the user actually shows up
            # under one in dedicated installs. Without this, the user has
            # `tenant=None` and frontend tenant-scoped queries return empty
            # results even though the data is there.
            if tenant is not None:
                user.tenant = tenant
                user.save(update_fields=['tenant'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created superuser "{username}" attached to tenant {tenant.slug}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created superuser "{username}" (no tenant resolved; will need manual assignment)'
                    )
                )

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))

    def _resolve_tenant(self):
        """Pick the tenant to attach the temp admin to.

        Resolution order:
        1. The single tenant in the DB, if exactly one exists.
           Dedicated installs typically have exactly one row, and this
           handles the case where someone renamed `DEFAULT_TENANT_SLUG`
           or the env was never set.
        2. The tenant whose slug matches `DEFAULT_TENANT_SLUG`.
        3. None — caller logs and leaves the user un-attached.
        """
        from Tracker.models import Tenant

        existing = list(Tenant.objects.all()[:2])
        if len(existing) == 1:
            return existing[0]

        slug = getattr(settings, 'DEFAULT_TENANT_SLUG', None)
        if slug:
            tenant = Tenant.objects.filter(slug=slug).first()
            if tenant is not None:
                return tenant

        if not existing:
            self.stdout.write(
                self.style.WARNING(
                    'No Tenant rows exist yet. The middleware will auto-create '
                    'one on first HTTP request — re-run this command after that '
                    'to attach the admin, or use `setup_tenant` to bootstrap explicitly.'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Multiple tenants exist and DEFAULT_TENANT_SLUG={slug!r} '
                    'did not match any of them. Leaving the admin un-attached.'
                )
            )
        return None
