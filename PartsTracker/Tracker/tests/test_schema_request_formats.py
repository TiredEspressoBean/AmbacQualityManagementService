"""A request body the generated client sends as form-data must be flat (2026-10-05).

The client picks a request's format from the first content type the schema lists
for it, and zodios' form-data plugin does `FormData.append(key, value)` per top-level
key — a list of rows arrives as the string "[object Object],[object Object]".
Backend tests post JSON, so they never see it; this reads the committed schema.yaml
(what the client is generated from) instead. Four MaterialLots actions were broken
this way from 2026-09-15 to 2026-10-05.

Fix a failure by giving the action `parser_classes=[parsers.JSONParser]` (or putting
JSONParser first), then regenerate the schema and the client.
"""
from pathlib import Path

import yaml
from django.test import SimpleTestCase

SCHEMA = Path(__file__).resolve().parents[2] / "schema.yaml"


class FormDataBodiesAreFlatTests(SimpleTestCase):
    def test_no_form_data_request_has_a_nested_field(self):
        doc = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        schemas = doc["components"]["schemas"]

        def resolve(s):
            while "$ref" in s:
                s = schemas[s["$ref"].rsplit("/", 1)[-1]]
            if "allOf" in s:
                s = resolve(s["allOf"][0])
            return s

        def nested_fields(body):
            for name, prop in (resolve(body).get("properties") or {}).items():
                prop = resolve(prop)
                if prop.get("type") == "array":
                    item = resolve(prop.get("items", {}))
                    # A list of files is how multipart sends several uploads.
                    if item.get("format") != "binary":
                        yield name
                elif prop.get("type") == "object" or "properties" in prop:
                    yield name

        offenders = []
        for path, ops in doc["paths"].items():
            for method, op in ops.items():
                content = (op.get("requestBody") or {}).get("content") or {}
                if content and next(iter(content)) == "multipart/form-data":
                    fields = list(nested_fields(content["multipart/form-data"]["schema"]))
                    # bulk-reconcile posts with its own fetch (a file, or JSON rows).
                    if fields and path != "/api/User/bulk-reconcile/":
                        offenders.append(f"{method.upper()} {path}: {', '.join(fields)}")
        self.assertEqual(offenders, [], (
            "These requests generate as form-data but carry a list or object, which "
            "form-data can't send. Give the action parser_classes=[parsers.JSONParser] "
            "and regenerate schema.yaml:\n  " + "\n  ".join(offenders)))
