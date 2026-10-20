"""Who may read which audit-log entries.

`LogEntry` has no tenant and no row security of its own, so an entry is only as
private as the endpoint makes it. Two rules:

- **Row visibility follows the record.** An entry is shown only if the reader may open
  the record it is about — the same `for_user()` that decides the record's own
  visibility (tenant, order relationship, export control, classification). Without
  this, the change history of a record you cannot open was readable field by field.
- **Browsing the trail is its own permission.** Per-record history (an edit page's
  History card, a detail page's audit trail) asks for one record and needs only
  `view_logentry` plus visibility of that record. Listing the tenant's changes across
  records needs `view_auditlog` (Tenant Admin, Document Controller, QA Manager, Auditor).

Credentials are kept out of `changes` going forward (AUDITLOG_EXCLUDE_TRACKING_FIELDS);
rows written before that are not rewritten — the trail stays immutable — but their
credential values are masked on the way out.
"""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Q
from django.db.models.functions import Cast

BROWSE_PERM = 'view_auditlog'
MASK = '[redacted]'


def credential_fields() -> frozenset[str]:
    from django.conf import settings
    return frozenset(getattr(settings, 'AUDITLOG_EXCLUDE_TRACKING_FIELDS', ()))


def mask_changes(changes):
    """`changes` with any credential field's values replaced, for display."""
    if not isinstance(changes, dict):
        return changes
    hidden = credential_fields()
    return {k: ([MASK, MASK] if k in hidden else v) for k, v in changes.items()}


def can_browse(user) -> bool:
    return user.is_superuser or user.has_tenant_perm(BROWSE_PERM)


def _sees_whole_table(model, user) -> bool:
    """True when `for_user` would return every tenant row of `model` — so a content-type
    match suffices and no per-row subquery is needed."""
    name = model._meta.model_name
    if name in ('documents', 'docchunk'):          # classification filter
        return False
    if hasattr(model, 'itar_controlled') or hasattr(model, 'eccn'):  # export control
        return False
    if user.is_staff:
        return True
    return (user.has_tenant_perm(f'view_{name}')
            and user.has_tenant_perm('full_tenant_access'))


def _rule_for(ct: ContentType, user) -> Q | None:
    """The Q admitting `ct`'s entries the user may see, or None for none of them."""
    model = ct.model_class()
    if model is None:
        return None
    manager = getattr(model, 'objects', None)
    if manager is None or not hasattr(manager, 'for_user'):
        # Not a SecureModel: no row security, so the model-level view perm decides.
        perm = f'view_{model._meta.model_name}'
        return Q(content_type=ct) if user.has_tenant_perm(perm) else None
    if _sees_whole_table(model, user):
        return Q(content_type=ct)
    visible = (manager.for_user(user, include_archived=True)
               .annotate(_pk_text=Cast('pk', CharField())).values('_pk_text'))
    return Q(content_type=ct, object_pk__in=visible)


def visible_entries(qs, user, *, content_type_id=None):
    """Narrow a tenant-scoped LogEntry queryset to the entries `user` may read."""
    if user.is_superuser:
        return qs
    if content_type_id:
        ct_ids = [content_type_id]
    else:
        ct_ids = list(qs.order_by().values_list('content_type_id', flat=True).distinct())
    rule = Q(pk__in=[])
    for ct in ContentType.objects.filter(pk__in=ct_ids):
        q = _rule_for(ct, user)
        if q is not None:
            rule |= q
    return qs.filter(rule)


def can_open_record(content_type_id, object_id, user) -> bool:
    """True when `user` may open the record `(content_type_id, object_id)` — the rule a
    per-record history (audit entries, correction reasons) is read under."""
    if user.is_superuser:
        return True
    ct = ContentType.objects.filter(pk=content_type_id).first()
    q = _rule_for(ct, user) if ct else None
    if q is None:
        return False
    model = ct.model_class()
    manager = getattr(model, 'objects', None)
    if manager is None or not hasattr(manager, 'for_user'):
        return True
    if _sees_whole_table(model, user):
        return manager.filter(pk=object_id).exists() if hasattr(manager, 'filter') else True
    return manager.for_user(user, include_archived=True).filter(pk=object_id).exists()
