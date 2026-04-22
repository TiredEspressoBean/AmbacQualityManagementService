"""
Versioning signals.

`revision_created` fires at the end of every successful
`create_new_version` operation — both the base `SecureModel` method
and any composite overrides in services.

Downstream consumers (webhooks, auto-training-requirement creation,
analytics, AI change-summary generation, etc.) subscribe here so they
don't have to monkey-patch individual composite service functions or
add `post_save`-with-version-increment-detection handlers.

Signal kwargs:
    sender: the model class (e.g. `Processes`, `DocumentType`)
    old_version: the prior version row (is_current_version now False,
        version = new.version - 1). May be None only if a downstream
        caller crafts a non-standard version-1 row via this signal,
        but in practice always set.
    new_version: the newly-created row (is_current_version=True,
        incremented version). In composites this starts in the
        composite's draft state (e.g. DRAFT for Processes).
    user: the user who triggered the revision (may be None for
        system-initiated calls like management commands).
    change_description: the human narrative of what changed and why.
        Required at the service layer; may be None for legacy callers
        but service functions should enforce non-empty.

Receivers should use `receiver(revision_created, sender=MyModel)` to
filter by type, or leave sender=None to react to all versioned model
revisions.
"""
from __future__ import annotations

import django.dispatch


revision_created = django.dispatch.Signal()
