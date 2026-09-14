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
    version_kwargs: dict | None = None,
):
    """Route a serializer update through either `default_update` or
    `create_new_version()` depending on which fields are being edited.

    Routing is on the fields whose values actually CHANGED, not on the fields
    merely present in `validated_data`. A serializer update is normally fed by a
    form that posts every field it renders, so keying on presence meant a save
    that only flipped a non-versioning flag — or changed nothing at all — still
    forked a new version. See `_changed_keys`.

    - Empty `validated_data` → noop, return the instance unchanged.
    - Nothing actually differs from the row → `default_update`, no new version.
    - Every *changed* key is in `non_versioning_fields` → delegate to
      `default_update(instance, validated_data)`. Typically this is
      `super().update` from a DRF `ModelSerializer`, which handles M2M
      assignment, writable-nested fields, and regular `save()`. Used
      for archive toggles and similar metadata/operational flips that
      shouldn't version.
    - Any edited key is a content field → route through
      `instance.create_new_version(**validated_data, **version_kwargs)`.
      The model's override (or the base) handles atomic copy, child
      migration, and the `revision_created` signal.

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
        version_kwargs: Extra keyword arguments forwarded to
            `create_new_version` when versioning is invoked. Used by
            callers that need to pass non-field context (e.g. the
            editing `process` for Step junction-flip in PCR flows).
            Not forwarded to `default_update` since non-versioning
            paths don't need them.

    Returns:
        The instance (either the same row, if only non-versioning
        fields were touched, or the new version row otherwise).
    """
    if not validated_data:
        return instance

    touched = _changed_keys(instance, validated_data)

    if not touched:
        # Every submitted value already matches the row. Forking here would mint a
        # revision that records no change — which is worse than useless on a controlled
        # spec, because it pads the history an audit reads as evidence.
        return default_update(instance, validated_data)

    if touched <= frozenset(non_versioning_fields):
        return default_update(instance, validated_data)

    return instance.create_new_version(**validated_data, **(version_kwargs or {}))


def _changed_keys(instance, validated_data: dict) -> set:
    """Which submitted keys actually differ from what is on the row.

    Routing on the keys *present* rather than the keys *changed* was the original
    behaviour, and it is wrong for the way real forms submit: an edit dialog posts every
    field it renders, so a planner toggling one explicitly-non-versioning flag still
    sent the content keys alongside it and forked a new version. Observed on the work
    centre dialog, the shift settings tab (where a fork also repoints
    `User.default_shift` and blanks the calendar's headcount badges) and the step form.

    Conservative by construction: anything that cannot be compared cleanly counts as
    changed, so the failure mode is the old behaviour — an unnecessary version — rather
    than a real edit silently landing as a plain save on a controlled record.

    Assumes `instance` was loaded from the database, which is true of every serializer
    update (DRF hands `update()` the object `get_object()` fetched). The comparison is
    on Python values, so a row built in memory can hold an unconverted assignment — a
    `TimeField` assigned the string '06:00:00' stays a string until it round-trips —
    and would compare unequal to the `datetime.time` the serializer validated. That
    errs toward an extra version rather than a missed one, but it will bite a test that
    builds a row with `objects.create(...)` and serializes it without refreshing.
    """
    changed = set()
    for key, new in validated_data.items():
        field = None
        try:
            field = instance._meta.get_field(key)
        except Exception:
            changed.add(key)          # not a concrete field (writable nested, property)
            continue

        if field.many_to_many or field.one_to_many:
            # Comparing an M2M means a query per field and an order-insensitive diff of
            # pks. Cheap enough, and these are exactly the "placement" fields (a work
            # centre's equipment list) that are typically non-versioning anyway.
            try:
                current = set(getattr(instance, key).values_list('pk', flat=True))
                submitted = {getattr(o, 'pk', o) for o in (new or [])}
            except Exception:
                changed.add(key)
                continue
            if current != submitted:
                changed.add(key)
            continue

        current = getattr(instance, field.attname if field.many_to_one else key, None)
        if field.many_to_one:
            new = getattr(new, 'pk', new)   # DRF hands back the instance, not the id

        if current != new:
            changed.add(key)
    return changed


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
        f"be called on this aggregate - it records transactional or "
        f"operational data, not controlled specifications. If you need "
        f"to modify this row, edit it directly and rely on "
        f"django-auditlog for change history."
    )
