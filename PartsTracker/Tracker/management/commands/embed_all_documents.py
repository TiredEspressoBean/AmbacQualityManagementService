"""
Management command to embed all existing documents.

Usage:
    python manage.py embed_all_documents [options]

Options:
    --async     Use Celery async tasks (default)
    --sync      Use synchronous embedding (blocks until complete)
    --force     Re-embed documents that already have chunks
    --limit N   Only process first N documents
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Tracker.models import Documents, DocChunk


class Command(BaseCommand):
    help = 'Embed all documents that are marked as ai_readable'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            dest='use_async',
            default=True,
            help='Use Celery async tasks (default)',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            dest='use_sync',
            help='Use synchronous embedding (blocks until complete)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-embed documents that already have chunks',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Only process first N documents',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be embedded without actually doing it',
        )

    def handle(self, *args, **options):
        if not settings.AI_EMBED_ENABLED:
            self.stdout.write(
                self.style.ERROR('AI_EMBED_ENABLED is False in settings. Cannot proceed.')
            )
            return

        # Get documents to embed
        queryset = Documents.objects.filter(
            ai_readable=True,
            archived=False
        )

        if not options['force']:
            # Exclude documents that already have chunks
            embedded_doc_ids = DocChunk.objects.values_list('doc_id', flat=True).distinct()
            queryset = queryset.exclude(id__in=embedded_doc_ids)

        if options['limit']:
            queryset = queryset[:options['limit']]

        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No documents to embed.')
            )
            return

        self.stdout.write(
            self.style.NOTICE(f'Found {total_count} document(s) to embed.')
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No documents will be embedded\n'))
            for doc in queryset:
                self.stdout.write(f'  - [{doc.id}] {doc.file_name}')
            return

        # Choose embedding method
        use_async = options['use_async'] and not options['use_sync']

        if use_async:
            self.stdout.write('Using async embedding (Celery tasks)...\n')
            success_count = 0
            error_count = 0

            for doc in queryset:
                try:
                    task = doc.embed_async()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Queued: [{doc.id}] {doc.file_name} (task: {task.id})')
                    )
                    success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to queue: [{doc.id}] {doc.file_name} - {e}')
                    )
                    error_count += 1

            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Queued {success_count}/{total_count} documents for embedding.')
            )
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to queue {error_count} documents.')
                )
            self.stdout.write(
                self.style.NOTICE('\nNote: Embedding happens in background. Check Celery logs for progress.')
            )

        else:
            self.stdout.write('Using synchronous embedding (this may take a while)...\n')
            success_count = 0
            error_count = 0
            skip_count = 0

            for i, doc in enumerate(queryset, 1):
                self.stdout.write(f'[{i}/{total_count}] Processing: {doc.file_name}')

                try:
                    result = doc.embed_inline()
                    if result:
                        chunk_count = DocChunk.objects.filter(doc=doc).count()
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Embedded {chunk_count} chunks')
                        )
                        success_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⊘ Skipped (no text extracted or too large)')
                        )
                        skip_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error: {e}')
                    )
                    error_count += 1

            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully embedded: {success_count}')
            )
            if skip_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'⊘ Skipped: {skip_count}')
                )
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed: {error_count}')
                )
            self.stdout.write(f'{"="*60}')
