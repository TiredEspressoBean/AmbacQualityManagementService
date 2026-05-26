"""
ScheduledContentProvider — abstract base for things that produce content
to be delivered on a NotificationSchedule cadence.

Distinct from the `ReportAdapter` system (`Tracker/reports/adapters/base.py`)
because that one is strictly PDF/Typst. Scheduled content is email-body
HTML+text, returned by value, never persisted as a Document.

A provider knows:
- What param shape it expects (DRF Serializer class, validated at write time)
- How to render content for a given (validated_params, tenant, recipient) tuple
  — recipient is passed so providers can personalize the greeting line; the
  query work is identical across recipients for snapshot-style content.

Providers MAY return None to signal "nothing to report this cycle" — the
fire dispatcher then skips writing an outbox row for that recipient. This
matches the legacy weekly-report behavior of skipping customers with no
active orders.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import ClassVar

from rest_framework import serializers


@dataclass(frozen=True)
class RenderedContent:
    """A fully-rendered piece of scheduled content, ready to write to outbox."""
    subject: str
    html: str
    text: str


class ScheduledContentProvider(abc.ABC):
    """Subclass + register in SCHEDULED_CONTENT_PROVIDERS to add a new provider.

    Attributes the subclass MUST set:
        name:                   registry key (e.g. 'customer_active_orders')
        title:                  human-friendly admin UI label
        description:            UI hint, one sentence
        param_serializer_class: DRF Serializer subclass validating params

    Method the subclass MUST implement:
        build_content(*, validated_params, tenant, recipient) → RenderedContent | None
    """

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    param_serializer_class: ClassVar[type[serializers.Serializer]]

    def validate_params(self, params: dict, *, tenant) -> dict:
        """Run the registered param serializer with a tenant in context.

        Param serializers may implement tenant-scoped existence checks
        (e.g. 'customer_id must belong to this tenant'); pass tenant via
        the serializer's `context` so those validators have what they need.
        """
        serializer = self.param_serializer_class(
            data=params, context={"tenant": tenant}
        )
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

    @abc.abstractmethod
    def build_content(
        self,
        *,
        validated_params: dict,
        tenant,
        recipient,
    ) -> RenderedContent | None:
        """Render content for one recipient. Return None to skip.

        `recipient` is a duck-typed object exposing `.email` and either
        `.get_full_name()` (User) or `.name` (ExternalContact). Providers
        that don't personalize per recipient can ignore it; passing it
        through is cheap and keeps the door open for personalization.
        """
        raise NotImplementedError
