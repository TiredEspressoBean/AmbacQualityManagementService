"""
Versioning helpers.

Two utilities used across the services + models layer:

- `apply_versioned_update(instance, validated_data, non_versioning_fields)` —
  the leaf-style serializer routing primitive. Content edits create a new
  version; edits limited to a known "non-versioning" set (archive toggles,
  operational status flips) apply in place. Used from ~15 serializer
  `update()` overrides; one line per serializer instead of the full 6-line
  dispatch block.

- `raise_not_versioned(self, **_)` — a defensive `create_new_version`
  override for SecureModels that inherit the base but should never be
  versioned (transactional records like CAPA, FPIRecord, HarvestedComponent,
  etc.). Assigning this method on a model class makes accidental
  `model.create_new_version()` calls raise a clear error instead of
  silently producing a semantically-broken row.

Neither abstraction existed before being forced by real duplication —
`apply_versioned_update` emerged after 15 identical serializer blocks;
`raise_not_versioned` emerged after we realized non-versioned SecureModels
silently accept versioning calls that produce inconsistent data.
"""
from __future__ import annotations


def apply_versioned_update(
    instance,
    validated_data: dict,
    *,
    non_versioning_fields,
    default_update,
):
    """Route a serializer update through either `default_update` or
    `create_new_version()` depending on which fields are being edited.

    - Empty `validated_data` → noop, return the instance unchanged.
    - Every edited key is in `non_versioning_fields` → delegate to
      `default_update(instance, validated_data)`. Typically this is
      `super().update` from a DRF `ModelSerializer`, which handles M2M
      assignment, writable-nested fields, and regular `save()`. Used
      for archive toggles and similar metadata/operational flips that
      shouldn't version.
    - Any edited key is a content field → route through
      `instance.create_new_version(**validated_data)`. The model's
      override (or the base) handles atomic copy, child migration, and
      the `revision_created` signal.

    Args:
        instance: The model instance being updated. Must support
            `create_new_version(**kwargs)` (SecureModel does).
        validated_data: DRF's post-validation dict from `update()`.
        non_versioning_fields: Iterable of field names whose edits
            should NOT version (archive, status toggles, quantity
            remaining, etc.). Typically `frozenset({'archived'})` on
            leaves; composites with operational fields add more.
        default_update: Callable `(instance, validated_data) -> instance`
            applied when only non-versioning fields are touched.
            Typically `super().update` from the calling serializer.

    Returns:
        The instance (either the same row, if only non-versioning
        fields were touched, or the new version row otherwise).
    """
    if not validated_data:
        return instance

    if set(validated_data.keys()) <= frozenset(non_versioning_fields):
        return default_update(instance, validated_data)

    return instance.create_new_version(**validated_data)


def raise_not_versioned(self, **_):
    """Defensive `create_new_version` override for non-versioned models.

    SecureModel provides a working `create_new_version` out of the box,
    which is correct for the ~22 versioned models in the versioning doc.
    For every other SecureModel (transactional records like CAPA, FPI,
    HarvestedComponent, NotificationTask, etc.), calling
    `create_new_version` is semantically wrong — it would produce a
    "row 2" of a CAPA that has no lifecycle meaning. Assigning this
    method as `create_new_version` on such a class makes accidental
    calls raise instead of silently producing inconsistent data.

    Usage on a model that should NOT support versioning:

        from Tracker.services.core.versioning import raise_not_versioned

        class CAPA(SecureModel):
            create_new_version = raise_not_versioned
            ...

    The override replaces the inherited method. Real versioned models
    that define their own `create_new_version` override naturally
    supersede this default too.
    """
    raise NotImplementedError(
        f"{type(self).__name__} is not a versioned model. "
        f"SecureModel's `create_new_version` is inherited but should not "
        f"be called on this aggregate — it records transactional or "
        f"operational data, not controlled specifications. If you need "
        f"to modify this row, edit it directly and rely on "
        f"django-auditlog for change history."
    )
