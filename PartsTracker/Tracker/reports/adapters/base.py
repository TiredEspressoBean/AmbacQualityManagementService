"""
Base class for report adapters.

Every report type (Certificate of Conformance, SPC, NCR, ...) is a
subclass of `ReportAdapter`. The adapter owns:

1. A Pydantic context model — the typed shape passed to the template
2. A DRF param serializer — validates incoming params are tenant-scoped
3. A `build_context()` method — queries the Django ORM, returns a
   populated instance of the context model
4. Class-level metadata — name, title, template path, etc.

The dispatcher (PdfGenerator) handles everything else:
- Looking up the adapter by name
- Running param validation via `param_serializer_class`
- Calling `build_context()`
- Serializing the Pydantic model to JSON via `.model_dump(mode='json')`
- Passing to the Typst compiler via `typst_generator`

Subclasses should place their Pydantic context model in the same file
unless it grows large enough to warrant its own module.
"""
from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel
from rest_framework import serializers


class ReportAdapter:
    """
    Abstract base for report adapters.

    Required subclass overrides:
        name                    — stable registry key (e.g. "cert_of_conformance")
        title                   — human-readable name for filenames + emails
        template_path           — path under Tracker/reports/templates/
        context_model_class     — Pydantic BaseModel subclass
        param_serializer_class  — DRF Serializer subclass
        build_context()         — ORM query + DTO construction

    Optional overrides:
        classification_default  — "INTERNAL" by default; set to PUBLIC,
                                  CONFIDENTIAL, RESTRICTED, SECRET for
                                  specific compliance documents
        get_filename()          — default uses {name}_{id}.pdf; override
                                  if a nicer pattern matters
    """

    name: ClassVar[str]
    title: ClassVar[str]
    template_path: ClassVar[str]
    context_model_class: ClassVar[type[BaseModel]]
    param_serializer_class: ClassVar[type[serializers.Serializer]]
    classification_default: ClassVar[str] = "INTERNAL"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validate that non-abstract subclasses declare all required
        class attributes. Catches missing configuration at class-load
        time rather than at request time.
        """
        super().__init_subclass__(**kwargs)

        # Allow intermediate abstract bases: a subclass is considered
        # concrete if `name` is defined on it (or any of its direct
        # ancestors other than ReportAdapter).
        if "name" not in cls.__dict__ and not any(
            "name" in b.__dict__ for b in cls.__mro__[1:] if b is not ReportAdapter
        ):
            return  # abstract intermediate — skip validation

        required = [
            "name", "title", "template_path",
            "context_model_class", "param_serializer_class",
        ]
        missing = [
            attr for attr in required if not hasattr(cls, attr)
        ]
        if missing:
            raise TypeError(
                f"{cls.__name__} is missing required ReportAdapter "
                f"class attribute(s): {', '.join(missing)}"
            )

    def build_context(
        self,
        validated_params: dict,
        user,
        tenant,
    ) -> BaseModel:
        """
        Query the Django ORM and return a Pydantic instance matching
        `context_model_class`.

        The dispatcher will call `.model_dump(mode='json')` on the
        return value before passing to Typst. This method must NOT
        return a raw dict — returning a Pydantic instance is what
        gives us runtime validation at the adapter boundary.

        `validated_params` is the output of
        `param_serializer_class(data=...).validated_data` — every ID
        in it has already been confirmed to belong to `tenant`.

        Defense in depth: every ORM query inside this method should
        still filter by `tenant` explicitly. Do not rely solely on the
        param serializer's validation.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement build_context()"
        )

    def get_filename(self, validated_params: dict) -> str:
        """
        Return the filename used for email attachments and DMS storage.
        Default: {name}_{id}.pdf, or {name}_unknown.pdf if no id present.
        Subclasses can override for nicer names (e.g. "CoC-{number}.pdf").

        Receives validated params only, not the built context —
        filename computation doesn't need to wait on ORM queries.
        For filenames that depend on derived data (e.g. a generated
        certificate number), compute that deterministically from the
        params here rather than running build_context() twice.
        """
        identifier = validated_params.get("id", "unknown")
        return f"{self.name}_{identifier}.pdf"
