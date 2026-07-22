"""System-authored notification templates.

Five events ship with custom-authored copy; everything else falls through
to the wildcard template (`event_code='*'`) which renders a generic but
branded layout from the event label + payload.

Templates are loaded into `NotificationTemplate` rows with `tenant=NULL`
by `setup_system_templates()`, called from `apps.py:setup_defaults` on
`post_migrate` and also exposed as a management command:

    python manage.py setup_notification_templates

Re-running is idempotent: `update_or_create` on
`(tenant=NULL, event_code, channel, language)`.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email body shells — shared HTML chrome across all custom templates.
# Tenant branding (logo, primary color, signature, footer) interpolates at
# render time; per-event content slots into {{ content }}.
# ---------------------------------------------------------------------------

EMAIL_HTML_SHELL = """<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a;">
  <tr>
    <td style="padding: 24px; max-width: 600px;">
      {% if branding.logo_url %}<img src="{{ branding.logo_url }}" alt="{{ branding.company_name }}" style="max-height: 40px; margin-bottom: 24px;"/>{% endif %}
      <h2 style="color: {{ branding.primary_color|default:'#003366' }}; margin: 0 0 16px; font-size: 20px;">{TITLE}</h2>
      {BODY}
      {% if action_url %}<p style="margin: 24px 0;"><a href="{{ action_url }}" style="background-color: {{ branding.primary_color|default:'#003366' }}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">{ACTION_LABEL}</a></p>{% endif %}
      {% if branding.email_signature_html %}<div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #eee;">{{ branding.email_signature_html|safe }}</div>{% endif %}
      {% if branding.footer_disclaimer_html %}<p style="font-size: 11px; color: #999; margin-top: 24px;">{{ branding.footer_disclaimer_html|safe }}</p>{% endif %}
    </td>
  </tr>
</table>"""


def _html(title: str, body: str, action_label: str = "View") -> str:
    return (
        EMAIL_HTML_SHELL.replace("{TITLE}", title)
        .replace("{BODY}", body)
        .replace("{ACTION_LABEL}", action_label)
    )


# ---------------------------------------------------------------------------
# Five curated events
# ---------------------------------------------------------------------------

NCR_OPENED = {
    "event_code": "ncr.opened",
    "email": {
        "subject": "[{{ payload.severity|upper }}] NCR on {{ payload.part_number }}",
        "body_text": """A nonconformance has been opened.

Part:       {{ payload.part_number }}
Work order: {{ payload.work_order_number }}
Step:       {{ payload.step_name }}
Severity:   {{ payload.severity }}
Opened by:  {{ payload.opened_by_name }}

{{ payload.description }}

View the NCR: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Nonconformance Opened",
            body="""<p style="margin: 0 0 16px;">A nonconformance has been opened against part <strong>{{ payload.part_number }}</strong>.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">Severity</td><td><strong>{{ payload.severity }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Work order</td><td>{{ payload.work_order_number }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Step</td><td>{{ payload.step_name }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Opened by</td><td>{{ payload.opened_by_name }}</td></tr>
      </table>
      <p style="margin: 16px 0; padding: 12px; background-color: #f7f7f7; border-left: 3px solid {{ branding.primary_color|default:'#003366' }};">{{ payload.description }}</p>""",
            action_label="View this NCR",
        ),
        "action_url_template": "/quality/ncrs/{{ payload.id }}",
        "severity": "warn",
    },
    "in_app": {
        "subject": "NCR opened on {{ payload.part_number }} ({{ payload.severity }})",
        "body_text": "{{ payload.opened_by_name }} opened a {{ payload.severity }} NCR on {{ payload.part_number }} at step \"{{ payload.step_name }}\".",
        "action_url_template": "/quality/ncrs/{{ payload.id }}",
        "severity": "warn",
        "icon": "alert-triangle",
    },
}

STEP_FAILURE = {
    "event_code": "quality.step_failure",
    "email": {
        "subject": "Part {{ payload.part_number }} failed at {{ payload.step_name }}",
        "body_text": """A part has failed quality inspection at a process step.

Part:       {{ payload.part_number }}
Step:       {{ payload.step_name }}
Work Order: {{ payload.work_order_number|default:'(none)' }}

Review the part: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Part Failed at Step",
            body="""<p style="margin: 0 0 16px;">A part has failed quality inspection at a process step.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">Part</td><td><strong>{{ payload.part_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Step</td><td>{{ payload.step_name }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Work Order</td><td>{{ payload.work_order_number|default:'(none)' }}</td></tr>
      </table>""",
            action_label="Review the part",
        ),
        "action_url_template": "/parts/{{ payload.part_id }}",
        "severity": "warn",
    },
    "in_app": {
        "subject": "{{ payload.part_number }} failed at {{ payload.step_name }}",
        "body_text": "Part {{ payload.part_number }} failed inspection at \"{{ payload.step_name }}\".",
        "action_url_template": "/parts/{{ payload.part_id }}",
        "severity": "warn",
        "icon": "alert-triangle",
    },
}

CAPA_ASSIGNED = {
    "event_code": "capa.assigned",
    "email": {
        "subject": "CAPA {{ payload.capa_number }} assigned to you",
        "body_text": """{% if payload.is_reassignment %}A CAPA has been reassigned to you.{% else %}A CAPA has been assigned to you.{% endif %}

CAPA:       {{ payload.capa_number }}
Type:       {{ payload.capa_type_display }}
Severity:   {{ payload.severity_display }}
Due date:   {% if payload.due_date %}{{ payload.due_date }}{% else %}Not set{% endif %}
Opened by:  {{ payload.initiated_by_name|default:'System' }}

Problem statement:
{{ payload.problem_statement }}

Open the CAPA: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="CAPA Assigned",
            body="""<p style="margin: 0 0 16px;">{% if payload.is_reassignment %}A CAPA has been reassigned to <strong>{{ payload.assigned_to_name }}</strong>.{% else %}A CAPA has been assigned to <strong>{{ payload.assigned_to_name }}</strong>.{% endif %}</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">CAPA</td><td><strong>{{ payload.capa_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Type</td><td>{{ payload.capa_type_display }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Severity</td><td>{{ payload.severity_display }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Due date</td><td>{% if payload.due_date %}{{ payload.due_date }}{% else %}<em>Not set</em>{% endif %}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Opened by</td><td>{{ payload.initiated_by_name|default:'System' }}</td></tr>
      </table>
      <p style="margin: 16px 0 8px; font-weight: 600;">Problem statement</p>
      <p style="margin: 0 0 16px; white-space: pre-wrap;">{{ payload.problem_statement }}</p>""",
            action_label="Open the CAPA",
        ),
        "action_url_template": "/quality/capas/{{ payload.capa_id }}",
        "severity": "warn",
    },
    "in_app": {
        "subject": "CAPA {{ payload.capa_number }} assigned to you",
        "body_text": "{{ payload.severity_display }} CAPA, due {% if payload.due_date %}{{ payload.due_date }}{% else %}TBD{% endif %}.",
        "action_url_template": "/quality/capas/{{ payload.capa_id }}",
        "severity": "info",
        "icon": "clipboard-list",
    },
}

CAPA_OPENED = {
    "event_code": "capa.opened",
    "email": {
        "subject": "CAPA {{ payload.capa_number }} assigned to you",
        "body_text": """A CAPA has been assigned to you.

CAPA:       {{ payload.capa_number }}
Severity:   {{ payload.severity }}
Due date:   {{ payload.due_date }}
Assignee:   {{ payload.assigned_to_name }}

Open the CAPA: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="CAPA Assigned",
            body="""<p style="margin: 0 0 16px;">A CAPA has been assigned to <strong>{{ payload.assigned_to_name }}</strong>.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">CAPA</td><td><strong>{{ payload.capa_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Severity</td><td>{{ payload.severity }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Due date</td><td>{{ payload.due_date }}</td></tr>
      </table>""",
            action_label="Open the CAPA",
        ),
        "action_url_template": "/quality/capas/{{ payload.id }}",
        "severity": "warn",
    },
    "in_app": {
        "subject": "CAPA {{ payload.capa_number }} assigned to {{ payload.assigned_to_name }}",
        "body_text": "{{ payload.severity }} CAPA, due {{ payload.due_date }}.",
        "action_url_template": "/quality/capas/{{ payload.id }}",
        "severity": "info",
        "icon": "clipboard-list",
    },
}

DOCUMENT_APPROVAL_REQUIRED = {
    "event_code": "document.approval_required",
    "email": {
        "subject": "Approval requested: {{ payload.document_title|default:payload.document_number }}",
        "body_text": """{{ payload.requested_by_name }} has routed a document for your approval.

Document:    {{ payload.document_title }}
Number:      {{ payload.document_number }}
Type:        {{ payload.document_type }}
Requested:   {{ payload.requested_at }}

Approve or reject: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Approval Requested",
            body="""<p style="margin: 0 0 16px;"><strong>{{ payload.requested_by_name }}</strong> has routed a document for your approval.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">Document</td><td><strong>{{ payload.document_title }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Number</td><td>{{ payload.document_number }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Type</td><td>{{ payload.document_type }}</td></tr>
      </table>""",
            action_label="Review and decide",
        ),
        "action_url_template": "/documents/approvals/{{ payload.id }}",
        "severity": "info",
    },
    "in_app": {
        "subject": "Approval requested: {{ payload.document_title }}",
        "body_text": "{{ payload.requested_by_name }} needs your approval on {{ payload.document_number }}.",
        "action_url_template": "/documents/approvals/{{ payload.id }}",
        "severity": "info",
        "icon": "file-check",
    },
}

ORDER_SHIPPED = {
    "event_code": "order.shipped",
    "email": {
        "subject": "Shipment Notification - Order {{ payload.order_number }}",
        "body_text": """Your order has shipped.

Order number:   {{ payload.order_number }}
Shipped on:     {{ payload.shipped_at }}
Carrier:        {{ payload.carrier|default:'-' }}
Tracking:       {{ payload.tracking_number|default:'-' }}
Expected:       {{ payload.expected_delivery|default:'-' }}

Track this shipment: {{ action_url }}

Thank you for your business.

- {{ branding.company_name|default:'UQMES' }}
{% if branding.support_email %}Questions? Contact {{ branding.support_email }}{% endif %}""",
        "body_html": _html(
            title="Shipment Notification",
            body="""<p style="margin: 0 0 16px;">Your order has shipped. Tracking and delivery details are below.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">Order</td><td><strong>{{ payload.order_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Shipped on</td><td>{{ payload.shipped_at }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Carrier</td><td>{{ payload.carrier|default:'-' }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Tracking</td><td>{{ payload.tracking_number|default:'-' }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Expected delivery</td><td>{{ payload.expected_delivery|default:'-' }}</td></tr>
      </table>
      <p style="margin: 16px 0;">Thank you for your business.</p>""",
            action_label="Track shipment",
        ),
        "action_url_template": "/orders/{{ payload.order_number }}",
        "severity": "info",
    },
    "in_app": {
        "subject": "Order {{ payload.order_number }} shipped",
        "body_text": "{{ payload.carrier|default:'Carrier' }} picked up the shipment. Tracking: {{ payload.tracking_number|default:'pending' }}.",
        "action_url_template": "/orders/{{ payload.order_number }}",
        "severity": "info",
        "icon": "truck",
    },
}

GAGE_CALIBRATION_OVERDUE = {
    "event_code": "gage.calibration_overdue",
    "email": {
        "subject": "Calibration overdue: {{ payload.gage_id }} ({{ payload.days_overdue }}d)",
        "body_text": """{{ payload.gage_id }} is past its calibration due date.

Equipment:      {{ payload.gage_id }}
Description:    {{ payload.description }}
Due date:       {{ payload.calibration_due }}
Days overdue:   {{ payload.days_overdue }}
Owner:          {{ payload.owner_name|default:'unassigned' }}

This equipment should be removed from service until calibration is completed.

Open the calibration record: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Calibration Overdue",
            body="""<p style="margin: 0 0 16px;"><strong>{{ payload.gage_id }}</strong> is <strong style="color: #b91c1c;">{{ payload.days_overdue }} days</strong> past its calibration due date.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">Equipment</td><td><strong>{{ payload.gage_id }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Description</td><td>{{ payload.description }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Due date</td><td>{{ payload.calibration_due }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Owner</td><td>{{ payload.owner_name|default:'unassigned' }}</td></tr>
      </table>
      <p style="margin: 16px 0; padding: 12px; background-color: #fef2f2; border-left: 3px solid #b91c1c; color: #7f1d1d;">This equipment should be removed from service until calibration is completed.</p>""",
            action_label="Open calibration record",
        ),
        "action_url_template": "/equipment/{{ payload.id }}/calibration",
        "severity": "critical",
    },
    "in_app": {
        "subject": "Calibration overdue: {{ payload.gage_id }}",
        "body_text": "{{ payload.days_overdue }} days past due. Should be removed from service.",
        "action_url_template": "/equipment/{{ payload.id }}/calibration",
        "severity": "critical",
        "icon": "alert-octagon",
    },
}

# ---------------------------------------------------------------------------
# Wildcard fallback — used for any event without a curated template.
# Renders the event label as a title and the payload as a structured table.
# ---------------------------------------------------------------------------

WILDCARD_GENERIC = {
    "event_code": "*",
    "email": {
        "subject": "{{ event.label }}",
        "body_text": """{{ event.label }}

{% for key, value in payload.items %}{% if key != 'tenant_id' and key != 'attachments' %}{{ key }}: {{ value }}
{% endif %}{% endfor %}
{% if action_url %}View: {{ action_url }}{% endif %}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="{{ event.label }}",
            body="""<p style="margin: 0 0 16px; color: #666;">{{ event.domain }} event</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        {% for key, value in payload.items %}{% if key != 'tenant_id' and key != 'attachments' %}<tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">{{ key }}</td><td>{{ value }}</td></tr>{% endif %}{% endfor %}
      </table>""",
            action_label="Open in UQMES",
        ),
        "action_url_template": "",
        "severity": "info",
    },
    "in_app": {
        "subject": "{{ event.label }}",
        # `firstof` (vs chained `|default:`) is necessary here because Django's
        # `default` filter applies to the *resolved* value — if a payload key is
        # missing, `Variable.resolve` raises `VariableDoesNotExist` BEFORE
        # `default` sees the falsy fallback. `firstof` short-circuits on missing.
        "body_text": "{{ event.domain }} event fired at {% firstof payload.opened_at payload.created_at 'now' %}.",
        "action_url_template": "",
        "severity": "info",
        "icon": "bell",
    },
}


SHIFT_NOTE_PUBLISHED = {
    "event_code": "shift_note.published",
    "in_app": {
        "subject": "Shift note from {{ payload.author_name }}",
        "body_text": "{{ payload.body_preview }}",
        "action_url_template": "/production/operator",
        "severity": "info",
        "icon": "sticky-note",
    },
}

ALL_TEMPLATES = [
    NCR_OPENED,
    STEP_FAILURE,
    CAPA_ASSIGNED,
    CAPA_OPENED,
    DOCUMENT_APPROVAL_REQUIRED,
    ORDER_SHIPPED,
    GAGE_CALIBRATION_OVERDUE,
    SHIFT_NOTE_PUBLISHED,
    WILDCARD_GENERIC,
]


# ---------------------------------------------------------------------------
# Loader — idempotent upsert into NotificationTemplate (tenant=NULL).
# ---------------------------------------------------------------------------

def setup_system_templates() -> dict[str, int]:
    """Upsert every system template into the database.

    Returns a counts dict suitable for logging:
        {'created': N, 'updated': M}
    """
    from Tracker.models import NotificationTemplate
    from Tracker.utils.tenant_context import set_current_tenant_id, reset_current_tenant

    # NotificationTemplate is a SecureModel; its save() auto-fills tenant_id
    # from the ContextVar when None. We want tenant=NULL system rows, so
    # clear the ContextVar for the duration of the upsert.
    token = set_current_tenant_id(None)
    created = 0
    updated = 0
    try:
        for spec in ALL_TEMPLATES:
            event_code = spec["event_code"]
            for channel in ("email", "in_app"):
                fields = spec.get(channel)
                if not fields:
                    continue
                obj, was_created = NotificationTemplate.unscoped.update_or_create(
                    tenant=None,
                    event_code=event_code,
                    channel=channel,
                    language="en",
                    defaults={
                        "subject": fields.get("subject", ""),
                        "body_text": fields.get("body_text", ""),
                        "body_html": fields.get("body_html", ""),
                        "action_url_template": fields.get("action_url_template", ""),
                        "severity": fields.get("severity", "info"),
                        "icon": fields.get("icon", ""),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
    finally:
        reset_current_tenant(token)

    logger.info(
        "system notification templates: %d created, %d updated", created, updated,
    )
    return {"created": created, "updated": updated}
