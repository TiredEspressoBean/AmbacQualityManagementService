"""
HelloWorldAdapter — dummy adapter used to smoke-test the full dispatch path.

Exists so that:
  - The registry has at least one entry (real Phase 2 adapters will join it)
  - The viewset's /download/ and /generate/ endpoints have something
    to exercise
  - Future adapters can copy this as the minimal template

It intentionally has no tenant-scoped queries — it accepts a number
parameter and renders a hello-world PDF. Delete this adapter once
real reports are in place, or keep it around as a health check.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context model (the shape passed to the Typst template)
# ---------------------------------------------------------------------------


class HelloWorldContext(BaseModel):
    """Matches what templates/hello_world.typ expects in sys.inputs.data."""

    name: str = Field(default="World", min_length=1, max_length=100)
    number: int = Field(default=0, ge=0, le=1_000_000)


# ---------------------------------------------------------------------------
# Param serializer (what the HTTP client sends)
# ---------------------------------------------------------------------------


class HelloWorldParamsSerializer(serializers.Serializer):
    """
    Validates {name, number} from the request body.

    No tenant scoping because HelloWorld has no tenant-scoped data.
    Real adapters MUST check that any IDs they accept belong to
    `request.user.tenant`.
    """

    name = serializers.CharField(
        required=False, default="World", max_length=100, min_length=1,
    )
    number = serializers.IntegerField(
        required=False, default=0, min_value=0, max_value=1_000_000,
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class HelloWorldAdapter(ReportAdapter):
    """Renders templates/hello_world.typ with {name, number} context."""

    name = "hello_world"
    title = "Hello World Report"
    template_path = "hello_world.typ"
    context_model_class = HelloWorldContext
    param_serializer_class = HelloWorldParamsSerializer

    def build_context(self, validated_params, user, tenant) -> HelloWorldContext:
        return HelloWorldContext(
            name=validated_params.get("name", "World"),
            number=validated_params.get("number", 0),
        )

    def get_filename(self, validated_params) -> str:
        name = validated_params.get("name", "World").replace(" ", "_")
        return f"hello_world_{name}.pdf"
