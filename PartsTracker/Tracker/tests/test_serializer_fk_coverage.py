"""
Coverage guard: writable FK serializer fields targeting tenant-scoped models
must use TenantScopedPrimaryKeyRelatedField (directly, or via auto-generation
from a base that sets `serializer_related_field` — i.e. SecureModelMixin).

Why
---
`SecureModel` sets `default_manager_name = 'unscoped'`, so a plain
`ModelSerializer` auto-generates FK fields whose lookup queryset spans ALL
tenants. A tenant-A request body can then reference a tenant-B row by PK.
`SecureModelMixin` closes this by setting `serializer_related_field`, so its
auto-generated FKs re-scope to the current tenant. This test fails if any
serializer reintroduces an unscoped writable FK to a tenant-scoped model.

`KNOWN_UNSCOPED_FK` is the burn-down baseline of fields still unscoped when this
guard was added (serializers that inherit plain `serializers.ModelSerializer`
instead of `SecureModelMixin`). It is DEBT — shrink it by switching those
serializers to `SecureModelMixin`. The guard is two-directional:
  * a NEW unscoped writable FK that isn't in the baseline fails the test;
  * a baseline entry that becomes scoped (or disappears) fails the test until
    it's removed from the baseline.

`User` is excluded: users legitimately belong to multiple tenants and User
lookups are not tenant-bound (consistent with the scoping lint's exclusions).
"""

import importlib
import pkgutil

from django.test import SimpleTestCase
from rest_framework import serializers

import Tracker.serializers as serializers_pkg
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField


# Burn-down baseline: (SerializerClassName, field_name) pairs still unscoped.
# Each is a serializer inheriting plain ModelSerializer; fix by switching it to
# SecureModelMixin, then delete the line here.
#
# Fully burned down (2026-06): every tenant-scoped writable FK now routes
# through SecureModelMixin's scoped field. The guard now enforces ZERO gaps —
# keep it empty; add an entry only as documented, temporary debt.
KNOWN_UNSCOPED_FK = frozenset()


class SerializerFKTenantScopingTests(SimpleTestCase):
    @staticmethod
    def _tenant_scoped(model):
        return any(
            getattr(f, "related_model", None) is not None
            and f.related_model.__name__ == "Tenant"
            and f.name == "tenant"
            for f in model._meta.get_fields()
        )

    @classmethod
    def _all_model_serializers(cls):
        for mod in pkgutil.iter_modules(serializers_pkg.__path__, serializers_pkg.__name__ + "."):
            try:
                importlib.import_module(mod.name)
            except Exception:
                pass

        def subclasses(c):
            for s in c.__subclasses__():
                yield s
                yield from subclasses(s)

        return set(subclasses(serializers.ModelSerializer))

    def _current_unscoped_fk(self):
        """Set of (serializer_name, field_name) for writable FK fields whose
        target model is tenant-scoped and which are NOT the scoped variant."""
        found = set()
        for ser in self._all_model_serializers():
            meta = getattr(ser, "Meta", None)
            if not meta or not getattr(meta, "model", None):
                continue
            try:
                fields = ser().fields
            except Exception:
                continue
            for name, field in fields.items():
                if not isinstance(field, serializers.RelatedField):
                    continue
                if isinstance(field, TenantScopedPrimaryKeyRelatedField):
                    continue
                if field.read_only:
                    continue
                qs = getattr(field, "queryset", None)
                if qs is None:
                    continue
                if qs.model.__name__ == "User":
                    continue
                if self._tenant_scoped(qs.model):
                    found.add((ser.__name__, name))
        return found

    def test_no_unscoped_writable_fk_to_tenant_models(self):
        current = self._current_unscoped_fk()

        new_gaps = current - KNOWN_UNSCOPED_FK
        fixed_but_baselined = KNOWN_UNSCOPED_FK - current

        msgs = []
        if new_gaps:
            msgs.append(
                "New unscoped writable FK field(s) to tenant-scoped models. "
                "Make the serializer inherit SecureModelMixin (or declare the "
                "field as TenantScopedPrimaryKeyRelatedField):\n  "
                + "\n  ".join(f"{s}.{f}" for s, f in sorted(new_gaps))
            )
        if fixed_but_baselined:
            msgs.append(
                "These are now scoped (or gone) - remove them from "
                "KNOWN_UNSCOPED_FK:\n  "
                + "\n  ".join(f"{s}.{f}" for s, f in sorted(fixed_but_baselined))
            )
        if msgs:
            self.fail("\n\n".join(msgs))
