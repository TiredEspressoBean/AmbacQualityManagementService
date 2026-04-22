"""
GeneratedReport aggregate services.

Post-generation bookkeeping: mark completed with the stored document,
mark failed with an error message, or record that the report was
emailed.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import GeneratedReport


def mark_report_completed(report: GeneratedReport, document) -> GeneratedReport:
    report.document = document
    report.status = GeneratedReport.ReportStatus.COMPLETED
    report.save(update_fields=['document', 'status'])
    return report


def mark_report_failed(report: GeneratedReport, error_message: str) -> GeneratedReport:
    report.status = GeneratedReport.ReportStatus.FAILED
    report.error_message = error_message
    report.save(update_fields=['status', 'error_message'])
    return report


def mark_report_emailed(report: GeneratedReport, email_address: str) -> GeneratedReport:
    report.emailed_to = email_address
    report.emailed_at = timezone.now()
    report.save(update_fields=['emailed_to', 'emailed_at'])
    return report
