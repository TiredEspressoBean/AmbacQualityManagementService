"""
Generic PDF generator using Playwright to render React pages.

This service generates pixel-perfect PDFs by loading actual frontend pages
in a headless browser and converting them to PDF.
"""
import logging
from typing import Optional
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


class PdfGenerator:
    """Generic PDF generator - works with any print route."""

    # Map report types to their print routes and selectors to wait for
    REPORT_CONFIG = {
        "spc": {
            "route": "/spc/print",
            "wait_selector": ".recharts-surface",  # Wait for charts to render
            "title": "SPC Report",
            "timeout": 30000,  # 30 seconds for charts
        },
        "capa": {
            "route": "/quality/capas/{id}/print",
            "wait_selector": "[data-print-ready]",
            "title": "CAPA Report",
            "timeout": 15000,
        },
        "quality_report": {
            "route": "/quality/reports/{id}/print",
            "wait_selector": "[data-print-ready]",
            "title": "Quality Report",
            "timeout": 15000,
        },
    }

    def __init__(self, frontend_url: Optional[str] = None):
        """
        Initialize the PDF generator.

        Args:
            frontend_url: Override the frontend URL (defaults to settings.FRONTEND_URL)
        """
        self.frontend_url = frontend_url or getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    def generate(self, report_type: str, params: dict, screenshot_path: str = None) -> bytes:
        """
        Generate PDF for any report type.

        Args:
            report_type: One of "spc", "capa", "quality_report", etc.
            params: Dict of parameters (varies by report type)

        Returns:
            PDF as bytes

        Raises:
            ValueError: If report_type is unknown
            Exception: If PDF generation fails
        """
        config = self.REPORT_CONFIG.get(report_type)
        if not config:
            raise ValueError(f"Unknown report type: {report_type}. Valid types: {list(self.REPORT_CONFIG.keys())}")

        # Build URL
        route = config["route"]

        # Handle path params like {id}
        for key, value in params.items():
            route = route.replace(f"{{{key}}}", str(value))

        # Remaining params go to query string
        query_params = {k: v for k, v in params.items() if f"{{{k}}}" not in config["route"]}
        url = f"{self.frontend_url}{route}"
        if query_params:
            url += f"?{urlencode(query_params)}"

        logger.info(f"Generating PDF for {report_type} from URL: {url}")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Launch browser (headless by default)
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",  # Required for Docker
                        "--disable-features=LayoutNGPrinting",  # Fix for PDF content cutoff bug
                    ]
                )
                # Use tall viewport to ensure all content renders (not just above-fold)
                page = browser.new_page(viewport={"width": 816, "height": 2000})

                # Navigate to the page
                page.goto(url, wait_until="networkidle")

                # Wait for content to render
                wait_selector = config.get("wait_selector")
                timeout = config.get("timeout", 15000)

                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=timeout)
                    except Exception as e:
                        logger.warning(f"Timeout waiting for selector '{wait_selector}': {e}")
                        # Continue anyway - page may still have rendered

                # For SPC reports, wait for all charts to render
                if report_type == "spc":
                    try:
                        # Wait for multiple chart surfaces (X-bar, R, Histogram)
                        page.wait_for_function(
                            "document.querySelectorAll('.recharts-surface').length >= 3",
                            timeout=timeout
                        )
                    except Exception as e:
                        logger.warning(f"Not all charts rendered: {e}")

                # Scroll to bottom to ensure all content is in viewport/rendered
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                # Brief pause for any animations to complete
                page.wait_for_timeout(500)

                # Debug: log page dimensions and chart count
                dimensions = page.evaluate("""() => {
                    return {
                        bodyHeight: document.body.scrollHeight,
                        bodyWidth: document.body.scrollWidth,
                        chartCount: document.querySelectorAll('.recharts-surface').length,
                        cardCount: document.querySelectorAll('[class*="card"], [class*="Card"]').length,
                    }
                }""")
                logger.info(f"Page dimensions: {dimensions}")
                print(f"  DEBUG - Body: {dimensions['bodyWidth']}x{dimensions['bodyHeight']}px, Charts: {dimensions['chartCount']}, Cards: {dimensions['cardCount']}")

                # Save debug screenshot if requested
                if screenshot_path:
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Screenshot saved to: {screenshot_path}")

                # Generate PDF - let content flow across multiple pages
                pdf_bytes = page.pdf(
                    format="Letter",
                    print_background=True,
                    prefer_css_page_size=False,  # Use format="Letter" not CSS @page size
                    margin={
                        "top": "0.5in",
                        "bottom": "0.5in",
                        "left": "0.5in",
                        "right": "0.5in"
                    }
                )

                browser.close()
                logger.info(f"Successfully generated PDF for {report_type} ({len(pdf_bytes)} bytes)")
                return pdf_bytes

        except ImportError:
            logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            logger.error(f"Failed to generate PDF for {report_type}: {e}")
            raise

    def get_filename(self, report_type: str, params: dict) -> str:
        """Generate a filename for the report."""
        config = self.REPORT_CONFIG.get(report_type, {})
        title = config.get("title", "Report")

        # Build identifier from params
        identifier_keys = ["id", "measurement_id", "process_id", "capa_id"]
        identifier = "unknown"
        for key in identifier_keys:
            if key in params:
                identifier = str(params[key])
                break

        # Sanitize filename
        safe_title = title.replace(" ", "_").replace("/", "-")
        return f"{safe_title}_{identifier}.pdf"

    def get_title(self, report_type: str) -> str:
        """Get human-readable title for a report type."""
        config = self.REPORT_CONFIG.get(report_type, {})
        return config.get("title", "Report")

    @classmethod
    def add_report_type(cls, name: str, route: str, wait_selector: str, title: str, timeout: int = 15000):
        """
        Add a new report type at runtime.

        Args:
            name: Unique name for the report type
            route: URL route (can include {param} placeholders)
            wait_selector: CSS selector to wait for before generating PDF
            title: Human-readable title
            timeout: Timeout in milliseconds for waiting
        """
        cls.REPORT_CONFIG[name] = {
            "route": route,
            "wait_selector": wait_selector,
            "title": title,
            "timeout": timeout,
        }
        logger.info(f"Added new report type: {name}")
