"""
Barcode and QR code rendering for report templates.

Typst has no native barcode support, so 1D barcodes and QR codes are
rendered server-side as SVG and embedded in templates via `#image.decode(...)`.

Keep this module intentionally thin: it takes a string and returns SVG bytes.
The *caller* decides what to encode — the service has no opinion about
AIAG data-identifier prefixes, URL wrapping, or encoding philosophy.
That keeps barcode generation reusable across any label type.

USAGE FROM AN ADAPTER
=====================

    from Tracker.reports.services.barcodes import render_barcode_svg, render_qr_svg

    barcode_svg = render_barcode_svg("SN-0847291")
    qr_svg = render_qr_svg("https://tenant.example.com/parts/0847291")

    # Put the string into the Pydantic context so the template can read it:
    return MyContext(
        ...,
        barcode_svg=barcode_svg,
        qr_svg=qr_svg,
    )

USAGE FROM A TYPST TEMPLATE
===========================

    #image(bytes(data.barcode_svg), width: 2in)

    #image(bytes(data.qr_svg), width: 0.8in)

The template receives the raw SVG source as a string in the context and
decodes it via Typst's `image()` function which accepts bytes + a format
inferred from the content.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1D barcodes (Code 128)
# ---------------------------------------------------------------------------


def render_barcode_svg(
    value: str,
    *,
    barcode_type: str = "code128",
    module_height: float = 10.0,
    write_text: bool = False,
    quiet_zone: float = 2.0,
) -> str:
    """
    Render a 1D barcode as SVG and return the SVG source as a string.

    Args:
        value: the string to encode. For labels, typically a pointer
            ID like a part serial or work order number. Callers are
            responsible for any AIAG DI prefixing (future).
        barcode_type: python-barcode class name. Defaults to 'code128'
            which handles full alphanumeric shop-floor IDs. Other common
            types: 'code39', 'ean13', 'upca', 'itf'.
        module_height: height of each barcode bar in mm. Larger is
            easier to scan but takes more label space.
        write_text: whether the barcode image itself includes a text
            rendering below. Usually False — the label template renders
            the human-readable text separately with its own styling.
        quiet_zone: white-space margin in mm on each side of the
            barcode. Code 128 requires ≥ 10×module_width; 2mm is
            typically safe.

    Returns:
        SVG markup as a string, ready to embed in a Typst template
        via `#image(bytes(data.barcode_svg))`.

    Raises:
        ValueError: if `value` is empty or contains characters not
            supported by the selected barcode_type.
    """
    if not value:
        raise ValueError("Barcode value cannot be empty")

    import barcode
    from barcode.writer import SVGWriter

    try:
        BarcodeClass = barcode.get_barcode_class(barcode_type)
    except barcode.errors.BarcodeNotRecognizedError as exc:
        raise ValueError(f"Unknown barcode type: {barcode_type!r}") from exc

    bio = io.BytesIO()
    try:
        instance = BarcodeClass(value, writer=SVGWriter())
        instance.write(
            bio,
            options={
                "module_height": module_height,
                "write_text": write_text,
                "quiet_zone": quiet_zone,
            },
        )
    except Exception as exc:
        logger.exception("Failed to render %s barcode for %r", barcode_type, value)
        raise ValueError(
            f"Cannot encode {value!r} as {barcode_type}: {exc}"
        ) from exc

    return bio.getvalue().decode("utf-8")


# ---------------------------------------------------------------------------
# QR codes (2D)
# ---------------------------------------------------------------------------

_ERROR_CORRECTION_LEVELS = {
    # Shorter codes, denser, less damage resistance
    "L": None,  # ~7% damage tolerance
    "M": None,  # ~15% — default, recommended for labels
    "Q": None,  # ~25%
    "H": None,  # ~30% — use when labels get abused (dirty, scratched)
}


def render_qr_svg(
    value: str,
    *,
    error_correction: str = "M",
    box_size: int = 10,
    border: int = 2,
) -> str:
    """
    Render a QR code as SVG and return the SVG source as a string.

    Args:
        value: the string to encode. Typically a URL pointing back
            into the system (`https://tenant.example.com/parts/<id>`)
            or a self-contained data payload. Callers choose.
        error_correction: 'L' (7%), 'M' (15%, default), 'Q' (25%),
            or 'H' (30%). Use 'H' for labels that might get dirty or
            partially occluded; 'M' is fine for normal shop use.
        box_size: pixels per QR module in the SVG source. Mostly
            cosmetic since the template resizes via `#image(width: ...)`.
        border: quiet-zone modules around the QR. Minimum is 4 per
            QR spec; 2 works in practice for label use where space
            is tight. Defaults to 2 for label density.

    Returns:
        SVG markup as a string.

    Raises:
        ValueError: if `value` is empty or `error_correction` is invalid.
    """
    if not value:
        raise ValueError("QR code value cannot be empty")

    if error_correction not in _ERROR_CORRECTION_LEVELS:
        raise ValueError(
            f"error_correction must be one of "
            f"{list(_ERROR_CORRECTION_LEVELS)}; got {error_correction!r}"
        )

    import qrcode
    import qrcode.image.svg

    level_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }

    qr = qrcode.QRCode(
        version=None,           # auto-size
        error_correction=level_map[error_correction],
        box_size=box_size,
        border=border,
    )
    qr.add_data(value)
    qr.make(fit=True)

    img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
    bio = io.BytesIO()
    img.save(bio)
    return bio.getvalue().decode("utf-8")
