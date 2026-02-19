"""
Sequence number generation utilities with race condition protection.

These utilities use SELECT FOR UPDATE to prevent duplicate sequence numbers
when multiple requests try to generate numbers concurrently.

IMPORTANT: The sequence number field MUST have a unique constraint to ensure
duplicates cannot be created. The SELECT FOR UPDATE only protects against
races when records already exist - for the first record or under high
concurrency, the unique constraint is the final safeguard.
"""

import logging
from django.db import transaction, IntegrityError

logger = logging.getLogger(__name__)

# Maximum retry attempts when unique constraint violation occurs
MAX_SEQUENCE_RETRIES = 3


def generate_next_sequence(queryset, number_field, prefix, padding=4, tenant=None):
    """
    Generate the next sequence number with race condition protection.

    Uses SELECT FOR UPDATE to lock the last record while generating the next number,
    preventing duplicate numbers under concurrent load.

    IMPORTANT: The model's sequence number field MUST have a unique constraint.
    This function relies on the database to prevent duplicates as a final safeguard.

    Args:
        queryset: Base QuerySet for the model
        number_field: Name of the field containing the sequence number (e.g., 'approval_number')
        prefix: String prefix to filter and prepend (e.g., 'APR-2025-')
        padding: Zero-padding width for the sequence number (default: 4)
        tenant: Optional tenant to filter by

    Returns:
        str: The next sequence number (e.g., 'APR-2025-0001')

    Example:
        >>> generate_next_sequence(
        ...     ApprovalRequest.objects,
        ...     'approval_number',
        ...     f'APR-{year}-',
        ...     padding=4,
        ...     tenant=tenant
        ... )
        'APR-2025-0042'
    """
    with transaction.atomic():
        # Build the query
        qs = queryset.filter(**{f'{number_field}__startswith': prefix})
        if tenant:
            qs = qs.filter(tenant=tenant)

        # Lock the last record to prevent race conditions
        # Using select_for_update() ensures only one transaction can read this at a time
        last_record = (
            qs
            .select_for_update()
            .order_by(f'-{number_field}')
            .first()
        )

        if last_record:
            last_number = getattr(last_record, number_field)
            try:
                # Extract the numeric portion by removing the prefix
                # This is more robust than split('-')[-1] which breaks on variable formats
                suffix = last_number[len(prefix):]
                last_seq = int(suffix)
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                logger.warning(
                    f"Could not parse sequence number '{last_number}' with prefix '{prefix}', "
                    f"falling back to 1"
                )
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:0{padding}d}"


def generate_next_child_sequence(queryset, number_field, prefix, separator='-T', padding=3, tenant=None):
    """
    Generate the next child sequence number (e.g., CAPA-CA-2025-001-T001).

    Similar to generate_next_sequence but handles child records where the
    separator may differ from '-'.

    IMPORTANT: The model's sequence number field MUST have a unique constraint.
    This function relies on the database to prevent duplicates as a final safeguard.

    Args:
        queryset: Base QuerySet for the model
        number_field: Name of the field containing the sequence number
        prefix: String prefix including parent identifier (e.g., 'CAPA-CA-2025-001-T')
        separator: String used to split and find the sequence part (default: '-T')
            Note: This parameter is now unused but kept for API compatibility.
            The function now uses prefix length for more robust parsing.
        padding: Zero-padding width for the sequence number (default: 3)
        tenant: Optional tenant to filter by

    Returns:
        str: The next sequence number (e.g., 'CAPA-CA-2025-001-T002')
    """
    with transaction.atomic():
        qs = queryset.filter(**{f'{number_field}__startswith': prefix})
        if tenant:
            qs = qs.filter(tenant=tenant)

        last_record = (
            qs
            .select_for_update()
            .order_by(f'-{number_field}')
            .first()
        )

        if last_record:
            last_number = getattr(last_record, number_field)
            try:
                # Extract the numeric portion by removing the prefix
                # This is more robust than split(separator)[-1]
                suffix = last_number[len(prefix):]
                last_seq = int(suffix)
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                logger.warning(
                    f"Could not parse child sequence number '{last_number}' with prefix '{prefix}', "
                    f"falling back to 1"
                )
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:0{padding}d}"
