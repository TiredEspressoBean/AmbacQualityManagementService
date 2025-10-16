from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import QualityReports, QuarantineDisposition, ThreeDModel, Documents
import os
from django.core.files.base import ContentFile
from pathlib import Path

try:
    import cascadio
    CASCADIO_AVAILABLE = True
except ImportError:
    CASCADIO_AVAILABLE = False


@receiver(post_save, sender=QualityReports)
def auto_create_disposition(sender, instance, created, **kwargs):
    """Create disposition when QualityReport fails"""
    if instance.status == 'FAIL':
        # Check if disposition already exists for this quality report
        if not instance.dispositions.filter(current_state__in=['OPEN', 'IN_PROGRESS']).exists():
            # Find a QA user to assign to (or use the operator)
            qa_user = User.objects.filter(groups__name='QA').first()
            assigned_user = qa_user or instance.operator.first()

            if assigned_user:
                # Calculate rework attempt number for this step
                existing_rework_count = 0
                if instance.part and instance.step:
                    existing_rework_count = QuarantineDisposition.objects.filter(
                        part=instance.part,
                        step=instance.step,
                        disposition_type='REWORK'
                    ).count()

                disposition = QuarantineDisposition.objects.create(
                    assigned_to=assigned_user,
                    part=instance.part,
                    step=instance.step,  # Link to the step where failure occurred
                    rework_attempt_at_step=existing_rework_count + 1,
                    description=f"Auto-created for failed quality report: {instance.description or 'No description'}"
                )
                disposition.quality_reports.add(instance)


@receiver(post_save, sender=ThreeDModel)
def convert_step_to_glb(sender, instance, created, **kwargs):
    """Convert uploaded STEP files to GLB using cascadio Python library"""
    if not created or not instance.file:
        return

    # Skip if cascadio is not available
    if not CASCADIO_AVAILABLE:
        print("Cascadio not available - skipping STEP to GLB conversion")
        return

    file_path = instance.file.path
    file_ext = Path(file_path).suffix.lower()

    # Only process STEP files
    if file_ext not in ['.step', '.stp']:
        return

    try:
        # Output path for GLB
        output_path = file_path.rsplit('.', 1)[0] + '.glb'

        # Convert using cascadio Python library
        # Parameters: linear_deflection (0.1), angular_deflection (0.5)
        cascadio.step_to_glb(file_path, output_path, 0.1, 0.5)

        if os.path.exists(output_path):
            # Read the converted GLB file
            with open(output_path, 'rb') as glb_file:
                glb_content = glb_file.read()

            # Update the model instance with GLB file
            glb_filename = Path(output_path).name
            instance.file.save(glb_filename, ContentFile(glb_content), save=False)
            instance.file_type = 'glb'
            instance.save(update_fields=['file', 'file_type'])

            # Clean up the temporary GLB file
            os.remove(output_path)
        else:
            print(f"Cascadio conversion failed - output file not created")

    except Exception as e:
        print(f"Error converting STEP to GLB: {str(e)}")


@receiver(post_save, sender=Documents)
def auto_embed_document(sender, instance, created, **kwargs):
    """
    Automatically trigger async embedding when a document is saved with ai_readable=True.

    This signal handles:
    - New document uploads
    - File updates on existing documents
    - Documents marked as ai_readable after creation
    """
    from django.conf import settings

    # Only embed if AI embedding is enabled globally
    if not settings.AI_EMBED_ENABLED:
        return

    # Only embed if document is marked as ai_readable and not archived
    if not instance.ai_readable or instance.archived:
        return

    # Trigger async embedding
    # Note: The signal runs after save, so the file should be available
    instance.embed_async()