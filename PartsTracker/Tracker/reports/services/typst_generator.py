"""
Typst PDF generation service.

Thin wrapper around the `typst` Python package (messense/typst-py).
Provides a process-wide Compiler singleton to avoid re-initializing
the Rust-backed compiler on every request.

HOW TO USE
==========

From Python (e.g. a Celery task or sync viewset):

    from Tracker.reports.services.typst_generator import generate_typst_pdf

    context = {"name": "World", "number": 42}
    pdf_bytes = generate_typst_pdf("hello_world.typ", context)

The template file path is relative to the `templates/` directory.
Templates read the context at the top via:

    #let data = json.decode(sys.inputs.at("data"))

Note: use `json.decode(...)` (parses a string) NOT `json(...)` which
is the file-loader form and will interpret the JSON as a filesystem
path, failing on Windows with "os error 123".

CONCURRENCY
===========

The Compiler is instantiated lazily on the first call within a
process, protected by a double-checked lock. Celery prefork workers
each get their own Compiler at no extra cost. Threaded pools share
one Compiler, serialized by the lock — safe but serialized.

VERSION NOTES
=============

API confirmed against typst-py 0.14.8 (Feb 2026).
Compiler() and Compiler.compile(input=..., format=..., sys_inputs=...)
are the supported signatures. If you upgrade typst, re-verify.
"""
import json
import logging
import threading
from pathlib import Path

import typst
from django.conf import settings

logger = logging.getLogger(__name__)


TEMPLATES_DIR = Path(settings.BASE_DIR) / "Tracker" / "reports" / "templates"


# Process-wide Compiler. None until first compile call; thread-safe via lock.
_compiler: typst.Compiler | None = None
_compiler_lock = threading.Lock()


def get_compiler() -> typst.Compiler:
    """
    Return the process-wide Typst Compiler, creating it on first use.

    Double-checked locking: the happy-path read is lock-free; the
    initialization path is serialized. In Celery prefork mode each
    worker process gets its own Compiler. In threaded pools the
    Compiler is shared and compile calls serialize on the lock
    (Typst holds its own internal locks for parse/compile state).
    """
    global _compiler
    if _compiler is None:
        with _compiler_lock:
            if _compiler is None:  # re-check under lock
                _compiler = typst.Compiler()
                logger.info("Initialized Typst Compiler for this process")
    return _compiler


def generate_typst_pdf(template_name: str, context: dict) -> bytes:
    """
    Compile a Typst template to PDF bytes.

    Args:
        template_name: path under Tracker/reports/templates/, e.g.
            "hello_world.typ" or "cert_of_conformance.typ". Relative
            imports within the template (e.g. "_common/page-setup.typ")
            resolve from the template file's directory.
        context: JSON-serializable dict passed to the template via
            sys.inputs. The template reads it as:
                #let data = json(sys.inputs.at("data"))

    Returns:
        PDF bytes (starts with b"%PDF").

    Raises:
        FileNotFoundError: if template_name does not exist
        RuntimeError: if Typst compilation fails (wraps Typst error)
    """
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    sys_inputs = {"data": json.dumps(context, default=str, ensure_ascii=False)}

    try:
        pdf_bytes = get_compiler().compile(
            input=str(template_path),
            format="pdf",
            sys_inputs=sys_inputs,
        )
    except Exception as exc:
        logger.exception(
            "Typst compile failed for template %s", template_name
        )
        # Re-raise with template name so callers have context;
        # underlying Typst error is preserved as __cause__.
        raise RuntimeError(
            f"Typst compile failed for template '{template_name}': {exc}"
        ) from exc

    logger.info(
        "Generated PDF for template %s (%d bytes)",
        template_name,
        len(pdf_bytes),
    )
    return pdf_bytes
