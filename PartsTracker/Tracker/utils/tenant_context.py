"""
Tenant context utilities for background jobs (Celery tasks).

The TenantMiddleware sets RLS context for HTTP requests, but Celery tasks
run outside the request/response cycle. These utilities ensure background
jobs have proper tenant isolation.

Usage in Celery tasks:

    # Option 1: Context manager (when you have the tenant)
    @shared_task
    def my_task(tenant_id, document_id):
        with tenant_context(tenant_id):
            doc = Documents.objects.get(id=document_id)
            # ... RLS is enforced

    # Option 2: Decorator (auto-extracts tenant from first model)
    @shared_task
    @with_tenant_from_model(Documents)
    def embed_document(document_id):
        doc = Documents.objects.get(id=document_id)
        # ... RLS is enforced

    # Option 3: Task base class
    class TenantAwareTask(Task):
        def __call__(self, tenant_id, *args, **kwargs):
            with tenant_context(tenant_id):
                return super().__call__(tenant_id, *args, **kwargs)
"""

import functools
import logging
from contextlib import contextmanager
from typing import Union
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction

logger = logging.getLogger(__name__)


@contextmanager
def tenant_context(tenant_or_id: Union['Tenant', str, UUID, None]):
    """
    Context manager that sets PostgreSQL RLS context for the current tenant.

    This is required for Celery tasks and any code that runs outside
    the HTTP request/response cycle.

    Works with ATOMIC_REQUESTS and SET LOCAL - the context variable is
    automatically cleared when the transaction commits/rolls back.

    Args:
        tenant_or_id: Tenant instance, UUID, or string UUID. If None, no
                      context is set (allows queries to proceed without
                      tenant filtering - use with caution).

    Usage:
        with tenant_context(tenant_id):
            # All queries inside this block are tenant-scoped
            docs = Documents.objects.filter(status='ACTIVE')

    Note:
        - Requires ATOMIC_REQUESTS=True or explicit transaction.atomic()
        - Only effective when ENABLE_RLS=True
        - Superuser database connections bypass RLS regardless
    """
    # Resolve tenant ID
    tenant_id = _resolve_tenant_id(tenant_or_id)

    if tenant_id is None:
        # No tenant context - proceed without RLS filtering
        # This is intentional for some tasks (e.g., cross-tenant reports)
        logger.debug("tenant_context called with None - proceeding without tenant isolation")
        yield
        return

    # Check if RLS is enabled
    if not getattr(settings, 'ENABLE_RLS', False):
        # RLS disabled - just yield without setting context
        logger.debug(f"RLS disabled, skipping tenant context for {tenant_id}")
        yield
        return

    # Set RLS context within a transaction
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(tenant_id)]
                )
                logger.debug(f"Set RLS context for tenant {tenant_id}")

            yield

            # Transaction commits here, SET LOCAL is automatically cleared

    except Exception as e:
        logger.error(f"Error in tenant_context for {tenant_id}: {e}")
        raise


def _resolve_tenant_id(tenant_or_id) -> Union[UUID, str, None]:
    """
    Resolve various tenant representations to a UUID/string ID.

    Accepts:
        - Tenant model instance -> returns tenant.id
        - UUID object -> returns as-is
        - String UUID -> returns as-is
        - None -> returns None
    """
    if tenant_or_id is None:
        return None

    # Check if it's a Tenant model instance
    if hasattr(tenant_or_id, 'id') and hasattr(tenant_or_id, 'slug'):
        return tenant_or_id.id

    # Already a UUID or string
    return tenant_or_id


def get_tenant_from_model_instance(instance) -> Union[UUID, None]:
    """
    Extract tenant_id from a model instance.

    Args:
        instance: Any model instance that may have a tenant field

    Returns:
        UUID of the tenant, or None if model has no tenant
    """
    if instance is None:
        return None

    # Direct tenant field
    if hasattr(instance, 'tenant_id') and instance.tenant_id:
        return instance.tenant_id

    # Tenant object
    if hasattr(instance, 'tenant') and instance.tenant:
        return instance.tenant.id

    return None


def with_tenant_from_model(model_class, id_param='pk'):
    """
    Decorator that sets tenant context based on a model lookup.

    Useful when you need to query a model to get the tenant, then
    use that tenant for subsequent queries.

    Args:
        model_class: The Django model class to look up
        id_param: Name of the task parameter containing the model ID

    Usage:
        @shared_task
        @with_tenant_from_model(Documents, id_param='document_id')
        def embed_document(document_id):
            # Tenant context is already set from the document's tenant
            doc = Documents.objects.get(id=document_id)
            ...

    Note:
        The initial lookup to get the tenant bypasses RLS (uses
        all_objects if available, or standard objects). This is
        necessary to bootstrap the tenant context.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the ID from args or kwargs
            model_id = kwargs.get(id_param)
            if model_id is None and args:
                # First positional arg after self (if bound task)
                model_id = args[0] if not hasattr(args[0], 'request') else args[1] if len(args) > 1 else None

            if model_id is None:
                logger.warning(f"with_tenant_from_model: Could not find {id_param} in task args")
                return func(*args, **kwargs)

            # Look up the model to get tenant (bypass RLS for this lookup)
            try:
                # Use all_objects to bypass soft delete filter if available
                manager = getattr(model_class, 'all_objects', model_class.objects)
                instance = manager.get(id=model_id)
                tenant_id = get_tenant_from_model_instance(instance)
            except model_class.DoesNotExist:
                logger.error(f"with_tenant_from_model: {model_class.__name__} {model_id} not found")
                tenant_id = None

            # Execute with tenant context
            with tenant_context(tenant_id):
                return func(*args, **kwargs)

        return wrapper
    return decorator


class TenantAwareTask:
    """
    Mixin for Celery Task classes that require tenant context.

    The task must receive tenant_id as first argument (after self).

    Usage:
        class RetryableTenantTask(TenantAwareTask, Task):
            autoretry_for = (ConnectionError,)
            max_retries = 3

        @shared_task(bind=True, base=RetryableTenantTask)
        def my_task(self, tenant_id, document_id):
            # Tenant context is automatically set
            doc = Documents.objects.get(id=document_id)
    """

    def __call__(self, *args, **kwargs):
        # Extract tenant_id from args
        # For bound tasks (bind=True), self is already bound, args[0] is tenant_id
        tenant_id = kwargs.pop('tenant_id', None)
        if tenant_id is None and args:
            tenant_id = args[0]
            args = args[1:]

        with tenant_context(tenant_id):
            return super().__call__(*args, **kwargs)


# =============================================================================
# TENANT LOOKUP HELPERS
# =============================================================================

def get_tenant_for_user(user) -> Union[UUID, None]:
    """
    Get the tenant ID for a user.

    Checks:
        1. user._current_tenant (set by middleware for current request)
        2. user.tenant (user's home tenant)

    Returns:
        UUID of tenant, or None
    """
    if user is None or not user.is_authenticated:
        return None

    # Current request tenant (set by TenantMiddleware)
    current_tenant = getattr(user, '_current_tenant', None)
    if current_tenant:
        return current_tenant.id if hasattr(current_tenant, 'id') else current_tenant

    # User's home tenant
    tenant = getattr(user, 'tenant', None)
    if tenant:
        return tenant.id if hasattr(tenant, 'id') else tenant

    return None


def get_tenant_for_object(obj) -> Union[UUID, None]:
    """
    Get the tenant ID from any object that might have a tenant.

    Traverses common relationships:
        - obj.tenant
        - obj.order.tenant (for Parts)
        - obj.work_order.tenant (for Parts)
        - obj.capa.tenant (for CapaTasks)
        - obj.document.tenant (for DocChunks)

    Returns:
        UUID of tenant, or None
    """
    if obj is None:
        return None

    # Direct tenant
    tenant_id = get_tenant_from_model_instance(obj)
    if tenant_id:
        return tenant_id

    # Common relationships
    relationships = [
        'order', 'work_order', 'capa', 'document', 'part',
        'quality_report', 'approval_request'
    ]

    for rel in relationships:
        related = getattr(obj, rel, None)
        if related:
            tenant_id = get_tenant_from_model_instance(related)
            if tenant_id:
                return tenant_id

    return None
