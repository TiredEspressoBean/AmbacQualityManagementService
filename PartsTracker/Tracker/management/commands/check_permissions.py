"""
Management command to diagnose and fix permission integrity issues.

Usage:
    python manage.py check_permissions          # Diagnose issues
    python manage.py check_permissions --fix    # Fix issues automatically
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count


class Command(BaseCommand):
    help = 'Check and optionally fix permission database integrity issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix issues (delete duplicates and orphans)',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        issues_found = False

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Permission Integrity Check ===\n'))

        # 1. Check for duplicate permissions
        self.stdout.write(self.style.MIGRATE_LABEL('1. Checking for duplicate permissions...'))
        duplicates = self._find_duplicate_permissions()
        if duplicates:
            issues_found = True
            self.stdout.write(self.style.ERROR(f'   Found {len(duplicates)} duplicate permission(s):'))
            for dup in duplicates:
                self.stdout.write(f"   - {dup['app_label']}.{dup['codename']} ({dup['count']} copies)")
                for perm in dup['permissions']:
                    self.stdout.write(
                        f"     ID={perm.id}, content_type={perm.content_type.model} "
                        f"(ct_id={perm.content_type_id})"
                    )

            if fix:
                self._fix_duplicate_permissions(duplicates)
        else:
            self.stdout.write(self.style.SUCCESS('   No duplicates found'))

        # 2. Check for orphaned content types
        self.stdout.write(self.style.MIGRATE_LABEL('\n2. Checking for orphaned content types...'))
        orphans = self._find_orphaned_content_types()
        if orphans:
            issues_found = True
            self.stdout.write(self.style.ERROR(f'   Found {len(orphans)} orphaned content type(s):'))
            for ct in orphans:
                perm_count = Permission.objects.filter(content_type=ct).count()
                self.stdout.write(f"   - {ct.app_label}.{ct.model} (id={ct.id}, {perm_count} permissions)")

            if fix:
                self._fix_orphaned_content_types(orphans)
        else:
            self.stdout.write(self.style.SUCCESS('   No orphaned content types found'))

        # 3. Check for permissions on wrong content types
        self.stdout.write(self.style.MIGRATE_LABEL('\n3. Checking custom permission content types...'))
        misplaced = self._find_misplaced_permissions()
        if misplaced:
            issues_found = True
            self.stdout.write(self.style.WARNING(f'   Found {len(misplaced)} misplaced permission(s):'))
            for item in misplaced:
                self.stdout.write(
                    f"   - {item['codename']}: on {item['actual_model']}, "
                    f"expected {item['expected_model']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS('   All custom permissions on correct content types'))

        # 4. Summary
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Summary ==='))
        if issues_found:
            if fix:
                self.stdout.write(self.style.SUCCESS('Issues fixed! Run migrations and try again.'))
            else:
                self.stdout.write(self.style.WARNING(
                    'Issues found. Run with --fix to automatically resolve.'
                ))
        else:
            self.stdout.write(self.style.SUCCESS('No permission integrity issues found!'))

    def _find_duplicate_permissions(self):
        """Find permissions with same app_label + codename but different content types."""
        duplicates = (
            Permission.objects
            .values('content_type__app_label', 'codename')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        result = []
        for d in duplicates:
            perms = Permission.objects.filter(
                content_type__app_label=d['content_type__app_label'],
                codename=d['codename']
            ).select_related('content_type')
            result.append({
                'app_label': d['content_type__app_label'],
                'codename': d['codename'],
                'count': d['count'],
                'permissions': list(perms),
            })
        return result

    def _fix_duplicate_permissions(self, duplicates):
        """Fix duplicates by keeping the one on the correct content type."""
        self.stdout.write(self.style.MIGRATE_LABEL('\n   Fixing duplicates...'))

        # Known correct content types for custom permissions
        expected_content_types = {
            'approve_qualityreports': 'qualityreports',
            'approve_own_qualityreports': 'qualityreports',
            'approve_disposition': 'quarantinedisposition',
            'close_disposition': 'quarantinedisposition',
            'initiate_capa': 'capa',
            'close_capa': 'capa',
            'approve_capa': 'capa',
            'verify_capa': 'capa',
            'conduct_rca': 'rcarecord',
            'review_rca': 'rcarecord',
            'respond_to_approval': 'approvalrequest',
            'create_approval_template': 'approvaltemplate',
            'manage_approval_workflow': 'approvaltemplate',
            'view_confidential_documents': 'documents',
            'view_restricted_documents': 'documents',
            'view_secret_documents': 'documents',
            'classify_documents': 'documents',
        }

        for dup in duplicates:
            perms = dup['permissions']
            codename = dup['codename']

            # Strategy 1: Delete ones with orphaned content types
            valid_perms = []
            for perm in perms:
                if perm.content_type.model_class() is None:
                    self.stdout.write(
                        f"   Deleting {perm.codename} (orphaned ct: {perm.content_type.model})"
                    )
                    perm.delete()
                else:
                    valid_perms.append(perm)

            # Strategy 2: If we know the expected content type, keep that one
            if len(valid_perms) > 1 and codename in expected_content_types:
                expected_model = expected_content_types[codename]
                keep = None
                to_delete = []

                for perm in valid_perms:
                    if perm.content_type.model == expected_model:
                        keep = perm
                    else:
                        to_delete.append(perm)

                if keep:
                    for perm in to_delete:
                        self.stdout.write(
                            f"   Deleting {perm.codename} on {perm.content_type.model} "
                            f"(keeping on {keep.content_type.model})"
                        )
                        perm.delete()
                    valid_perms = [keep]

            # Strategy 3: If still have duplicates, keep the first valid one
            if len(valid_perms) > 1:
                keep = valid_perms[0]
                for perm in valid_perms[1:]:
                    self.stdout.write(
                        f"   Deleting duplicate {perm.codename} "
                        f"(keeping id={keep.id} on {keep.content_type.model})"
                    )
                    perm.delete()

        self.stdout.write(self.style.SUCCESS('   Duplicates fixed!'))

    def _find_orphaned_content_types(self):
        """Find content types whose models no longer exist."""
        orphans = []
        for ct in ContentType.objects.filter(app_label='Tracker'):
            if ct.model_class() is None:
                orphans.append(ct)
        return orphans

    def _fix_orphaned_content_types(self, orphans):
        """Delete orphaned content types and their permissions."""
        self.stdout.write(self.style.MIGRATE_LABEL('\n   Fixing orphaned content types...'))

        for ct in orphans:
            # Delete permissions first
            perm_count = Permission.objects.filter(content_type=ct).delete()[0]
            self.stdout.write(f"   Deleted {perm_count} permissions for {ct.app_label}.{ct.model}")

            # Delete content type
            ct.delete()
            self.stdout.write(f"   Deleted content type {ct.app_label}.{ct.model}")

        self.stdout.write(self.style.SUCCESS('   Orphaned content types fixed!'))

    def _find_misplaced_permissions(self):
        """Find custom permissions attached to wrong content types."""
        # Map of custom permission -> expected model
        custom_permission_models = {
            'approve_qualityreports': 'qualityreports',
            'approve_own_qualityreports': 'qualityreports',
            'approve_disposition': 'quarantinedisposition',
            'close_disposition': 'quarantinedisposition',
            'initiate_capa': 'capa',
            'close_capa': 'capa',
            'approve_capa': 'capa',
            'verify_capa': 'capa',
            'conduct_rca': 'rcarecord',
            'review_rca': 'rcarecord',
            'respond_to_approval': 'approvalrequest',
            'create_approval_template': 'approvaltemplate',
            'manage_approval_workflow': 'approvaltemplate',
            'view_confidential_documents': 'documents',
            'view_restricted_documents': 'documents',
            'view_secret_documents': 'documents',
            'classify_documents': 'documents',
        }

        misplaced = []
        for codename, expected_model in custom_permission_models.items():
            try:
                perm = Permission.objects.get(
                    content_type__app_label='Tracker',
                    codename=codename
                )
                if perm.content_type.model != expected_model:
                    misplaced.append({
                        'codename': codename,
                        'expected_model': expected_model,
                        'actual_model': perm.content_type.model,
                    })
            except Permission.DoesNotExist:
                pass  # Will be caught by other checks
            except Permission.MultipleObjectsReturned:
                pass  # Will be caught by duplicate check

        return misplaced
