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
        "action_url_template": "/details/Parts/{{ payload.part_id }}",
        "severity": "warn",
    },
    "in_app": {
        "subject": "{{ payload.part_number }} failed at {{ payload.step_name }}",
        "body_text": "Part {{ payload.part_number }} failed inspection at \"{{ payload.step_name }}\".",
        "action_url_template": "/details/Parts/{{ payload.part_id }}",
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
        "action_url_template": "/editor/equipment/{{ payload.id }}/edit",
        "severity": "critical",
    },
    "in_app": {
        "subject": "Calibration overdue: {{ payload.gage_id }}",
        "body_text": "{{ payload.days_overdue }} days past due. Should be removed from service.",
        "action_url_template": "/editor/equipment/{{ payload.id }}/edit",
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

# ---------------------------------------------------------------------------
# The andon's calls (user decision 2026-11-11): a refused start, and a first piece
# waiting for QA. Each names what's held and links to the work order's control page.
# ---------------------------------------------------------------------------

START_REFUSED = {
    "event_code": "start.refused",
    "email": {
        "subject": "Work can't start: {% firstof payload.part_number payload.step_name %} — waiting on {{ payload.waiting_on }}",
        "body_text": """Work was refused at its start, and it's waiting on {{ payload.waiting_on }}.

Part:        {{ payload.part_number|default:'—' }}
Step:        {{ payload.step_name|default:'—' }}
Work order:  {{ payload.work_order_number|default:'—' }}
Why:         {{ payload.message }}

A machine and an operator may be idle until it's cleared.

Open the work order: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Work can't start",
            body="""<p style="margin: 0 0 16px;">It's waiting on <strong>{{ payload.waiting_on }}</strong>.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Part</td><td><strong>{{ payload.part_number|default:'—' }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Step</td><td>{{ payload.step_name|default:'—' }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Work order</td><td>{{ payload.work_order_number|default:'—' }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Why</td><td>{{ payload.message }}</td></tr>
      </table>""",
            action_label="Open the work order",
        ),
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "warning",
    },
    "in_app": {
        "subject": "Can't start {% firstof payload.part_number payload.step_name %}: waiting on {{ payload.waiting_on }}",
        "body_text": "{{ payload.message }}{% if payload.step_name %} ({{ payload.step_name }}{% if payload.work_order_number %}, {{ payload.work_order_number }}{% endif %}){% endif %}",
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "warning",
        "icon": "octagon-alert",
    },
}

FPI_REQUESTED = {
    "event_code": "fpi.requested",
    "email": {
        "subject": "First piece waiting: {{ payload.step_name }} on {{ payload.work_order_number }}",
        "body_text": """A first piece is waiting for QA's buy-off. The rest of the run waits on it.

Work order:  {{ payload.work_order_number }}
Step:        {{ payload.step_name }}{% if payload.equipment_name %}
Machine:     {{ payload.equipment_name }}{% endif %}{% if payload.pieces %}
Pieces:      {{ payload.pieces }}{% endif %}

Open the work order: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="First piece waiting",
            body="""<p style="margin: 0 0 16px;">A first piece is waiting for QA's buy-off. The rest of the run waits on it.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        {% if payload.pieces %}<tr><td style="color: #666; padding: 4px 12px 4px 0;">Pieces</td><td><strong>{{ payload.pieces }}</strong></td></tr>{% endif %}
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Work order</td><td><strong>{{ payload.work_order_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Step</td><td>{{ payload.step_name }}</td></tr>
        {% if payload.equipment_name %}<tr><td style="color: #666; padding: 4px 12px 4px 0;">Machine</td><td>{{ payload.equipment_name }}</td></tr>{% endif %}
      </table>""",
            action_label="Open the work order",
        ),
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "warning",
    },
    "in_app": {
        "subject": "First piece waiting: {{ payload.step_name }}",
        "body_text": "{% if payload.pieces %}{{ payload.pieces }} — {% endif %}{{ payload.work_order_number }}{% if payload.equipment_name %} on {{ payload.equipment_name }}{% endif %}: QA to buy off the first piece; the run waits on it.",
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "warning",
        "icon": "clipboard-check",
    },
}

FPI_DECIDED = {
    "event_code": "fpi.decided",
    "email": {
        "subject": "First piece {{ payload.status|lower }}: {{ payload.step_name }} on {{ payload.work_order_number }}",
        "body_text": """QA has {{ payload.status|lower }} the first piece.{% if payload.status == 'FAILED' %} Correct the setup and re-run the first piece; the run stays held.{% else %} The run may go ahead.{% endif %}

Work order:  {{ payload.work_order_number }}
Step:        {{ payload.step_name }}{% if payload.equipment_name %}
Machine:     {{ payload.equipment_name }}{% endif %}

Open the work order: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="First piece {{ payload.status|lower }}",
            body="""<p style="margin: 0 0 16px;">{% if payload.status == 'FAILED' %}Correct the setup and re-run the first piece; the run stays held.{% else %}The run may go ahead.{% endif %}</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Work order</td><td><strong>{{ payload.work_order_number }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Step</td><td>{{ payload.step_name }}</td></tr>
        {% if payload.equipment_name %}<tr><td style="color: #666; padding: 4px 12px 4px 0;">Machine</td><td>{{ payload.equipment_name }}</td></tr>{% endif %}
      </table>""",
            action_label="Open the work order",
        ),
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "info",
    },
    "in_app": {
        "subject": "First piece {{ payload.status|lower }}: {{ payload.step_name }}",
        "body_text": "{% if payload.pieces %}{{ payload.pieces }} — {% endif %}{{ payload.work_order_number }}{% if payload.equipment_name %} on {{ payload.equipment_name }}{% endif %}: {% if payload.status == 'FAILED' %}correct the setup and re-run the first piece; the run stays held.{% else %}the run may go ahead.{% endif %}",
        "action_url_template": "{% if payload.work_order_id %}/workorder/{{ payload.work_order_id }}/control{% endif %}",
        "severity": "info",
        "icon": "clipboard-check",
    },
}

TOOL_LIFE_WARNING = {
    "event_code": "tool_life.warning",
    "email": {
        "subject": "Tool near its life limit: {{ payload.equipment_name }} ({{ payload.current }} of {{ payload.hard_limit|default:'—' }})",
        "body_text": """{{ payload.equipment_name }} reached its soft life limit. Plan its refurbishment before the hard limit stops the work that needs it.

Tool:        {{ payload.equipment_name }}
Limit:       {{ payload.limit_name }}
Used:        {{ payload.current }}
Soft limit:  {{ payload.soft_limit }}
Hard limit:  {{ payload.hard_limit|default:'—' }}

Open the tool: {{ action_url }}

- {{ branding.company_name|default:'UQMES' }}""",
        "body_html": _html(
            title="Tool near its life limit",
            body="""<p style="margin: 0 0 16px;"><strong>{{ payload.equipment_name }}</strong> reached its soft life limit. Plan its refurbishment before the hard limit stops the work that needs it.</p>
      <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; margin: 16px 0; width: 100%; font-size: 14px;">
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Limit</td><td>{{ payload.limit_name }}</td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Used</td><td><strong>{{ payload.current }}</strong></td></tr>
        <tr><td style="color: #666; padding: 4px 12px 4px 0;">Soft / hard limit</td><td>{{ payload.soft_limit }} / {{ payload.hard_limit|default:'—' }}</td></tr>
      </table>""",
            action_label="Open the tool",
        ),
        "action_url_template": "/editor/equipment/{{ payload.equipment_id }}/edit",
        "severity": "warning",
    },
    "in_app": {
        "subject": "Tool near its life limit: {{ payload.equipment_name }}",
        "body_text": "{{ payload.limit_name }}: {{ payload.current }} used, soft limit {{ payload.soft_limit }}{% if payload.hard_limit %}, hard limit {{ payload.hard_limit }}{% endif %}. Plan the refurbishment.",
        "action_url_template": "/editor/equipment/{{ payload.equipment_id }}/edit",
        "severity": "warning",
        "icon": "wrench",
    },
}

# ---------------------------------------------------------------------------
# Events that fell through to the wildcard (P6, user ruling 2026-11-12): each names
# its subject in the title and links to the page where it's acted on.
# ---------------------------------------------------------------------------

def _rows(*rows: tuple[str, str]) -> str:
    """An email detail table: (label, template value) per row."""
    cells = "".join(
        f'<tr><td style="color: #666; padding: 4px 12px 4px 0; white-space: nowrap;">{label}</td>'
        f'<td>{value}</td></tr>'
        for label, value in rows)
    return ('<table cellpadding="6" cellspacing="0" style="border-collapse: collapse; '
            f'margin: 16px 0; width: 100%; font-size: 14px;">{cells}</table>')


def _simple(event_code, *, subject, lead, rows, text_rows, url, action_label, severity,
            in_app_subject, in_app_body, icon):
    """A template whose email is a lead sentence plus a detail table."""
    signoff = "\n\n- {{ branding.company_name|default:'UQMES' }}"
    return {
        "event_code": event_code,
        "email": {
            "subject": subject,
            "body_text": f"{lead}\n\n{text_rows}\n\n{action_label}: {{{{ action_url }}}}{signoff}",
            "body_html": _html(title=subject,
                               body=f'<p style="margin: 0 0 16px;">{lead}</p>\n      {_rows(*rows)}',
                               action_label=action_label),
            "action_url_template": url,
            "severity": severity,
        },
        "in_app": {
            "subject": in_app_subject,
            "body_text": in_app_body,
            "action_url_template": url,
            "severity": severity,
            "icon": icon,
        },
    }


_WO_CONTROL = "/workorder/{{ payload.work_order_id }}/control"

WORKORDER_HELD = _simple(
    "workorder.held",
    subject="Work order {{ payload.work_order_number }} on hold{% if payload.hours_open %} for {{ payload.hours_open|floatformat:0 }} h{% endif %}",
    lead="{{ payload.work_order_number }} has been on hold past the threshold: {{ payload.reason }}.",
    rows=[("Work order", "<strong>{{ payload.work_order_number }}</strong>"),
          ("Reason", "{{ payload.reason }}"),
          ("On hold since", "{{ payload.placed_at|default:'—' }}")],
    text_rows="Work order:     {{ payload.work_order_number }}\nReason:         {{ payload.reason }}\nOn hold since:  {{ payload.placed_at|default:'—' }}",
    url=_WO_CONTROL, action_label="Open the work order", severity="warning",
    in_app_subject="{{ payload.work_order_number }} on hold{% if payload.hours_open %} {{ payload.hours_open|floatformat:0 }} h{% endif %}",
    in_app_body="Held: {{ payload.reason }}.", icon="pause-circle")

WORKORDER_OVERDUE = _simple(
    "workorder.overdue",
    subject="Work order {{ payload.work_order_number }} is overdue",
    lead="{{ payload.work_order_number }} is past its expected completion{% if payload.expected_completion %} ({{ payload.expected_completion }}){% endif %}.",
    rows=[("Work order", "<strong>{{ payload.work_order_number }}</strong>"),
          ("Was due", "{{ payload.expected_completion|default:'—' }}")],
    text_rows="Work order:  {{ payload.work_order_number }}\nWas due:     {{ payload.expected_completion|default:'—' }}",
    url=_WO_CONTROL, action_label="Open the work order", severity="warning",
    in_app_subject="{{ payload.work_order_number }} is overdue",
    in_app_body="Was due {{ payload.expected_completion|default:'—' }}.", icon="clock-alert")

_TRAINING_ROWS = [("Person", "<strong>{{ payload.user_name }}</strong>"),
                  ("Training", "{{ payload.training_type_name }} ({{ payload.level_display }})"),
                  ("Expires", "{{ payload.expires_date }}")]
_TRAINING_TEXT = ("Person:    {{ payload.user_name }}\n"
                  "Training:  {{ payload.training_type_name }} ({{ payload.level_display }})\n"
                  "Expires:   {{ payload.expires_date }}")
_TRAINING_URL = "/quality/training/records/{{ payload.record_id }}/edit"

TRAINING_EXPIRING_SOON = _simple(
    "training.expiring_soon",
    subject="{{ payload.user_name }}'s {{ payload.training_type_name }} expires in {{ payload.days_to_expiry }} days",
    lead="Schedule requalification before it lapses — after {{ payload.expires_date }}, {{ payload.user_name }} isn't qualified for work that needs it.",
    rows=_TRAINING_ROWS, text_rows=_TRAINING_TEXT,
    url=_TRAINING_URL, action_label="Open the training record", severity="info",
    in_app_subject="{{ payload.user_name }}'s {{ payload.training_type_name }} expires in {{ payload.days_to_expiry }} days",
    in_app_body="Expires {{ payload.expires_date }}. Schedule requalification.", icon="graduation-cap")

TRAINING_EXPIRED = _simple(
    "training.expired",
    subject="{{ payload.user_name }}'s {{ payload.training_type_name }} has expired",
    lead="{{ payload.user_name }} is no longer qualified for work that needs {{ payload.training_type_name }} until requalified.",
    rows=_TRAINING_ROWS, text_rows=_TRAINING_TEXT,
    url=_TRAINING_URL, action_label="Open the training record", severity="warning",
    in_app_subject="{{ payload.user_name }}'s {{ payload.training_type_name }} expired",
    in_app_body="Lapsed {{ payload.expires_date }}: not qualified for work that needs it until requalified.",
    icon="graduation-cap")

_LOT_ROWS = [("Lot", "<strong>{{ payload.lot_number }}</strong>"),
             ("Supplier", "{{ payload.supplier_name|default:'—' }}"),
             ("Part type", "{{ payload.part_type_name|default:'—' }}")]
_LOT_TEXT = ("Lot:        {{ payload.lot_number }}\n"
             "Supplier:   {{ payload.supplier_name|default:'—' }}\n"
             "Part type:  {{ payload.part_type_name|default:'—' }}")
_LOT_URL = "/production/material-lots/{{ payload.material_lot_id }}"

PART_UNAPPROVED = _simple(
    "part.unapproved",
    subject="Lot {{ payload.lot_number }} held: {{ payload.part_type_name }} isn't approved from {{ payload.supplier_name }}",
    lead="The lot was held at receiving: {{ payload.supplier_name }} has no active part approval (PPAP/FAI) for {{ payload.part_type_name }}.",
    rows=_LOT_ROWS, text_rows=_LOT_TEXT,
    url=_LOT_URL, action_label="Open the lot", severity="warning",
    in_app_subject="Lot {{ payload.lot_number }} held: part not approved",
    in_app_body="{{ payload.part_type_name }} from {{ payload.supplier_name }} has no active part approval (PPAP/FAI).",
    icon="package-x")

SUPPLIER_UNQUALIFIED = _simple(
    "supplier.unqualified",
    subject="Lot {{ payload.lot_number }} held: {{ payload.supplier_name }} isn't qualified",
    lead="The lot was held at receiving: {{ payload.supplier_name }} isn't qualified for {{ payload.part_type_name }}.",
    rows=_LOT_ROWS, text_rows=_LOT_TEXT,
    url=_LOT_URL, action_label="Open the lot", severity="warning",
    in_app_subject="Lot {{ payload.lot_number }} held: supplier not qualified",
    in_app_body="{{ payload.supplier_name }} isn't qualified for {{ payload.part_type_name }}.",
    icon="package-x")

_QUAL_ROWS = [("Supplier", "<strong>{{ payload.supplier_name }}</strong>"),
              ("Qualification", "{{ payload.qualification_number }}"),
              ("Scope", "{{ payload.scope }}"),
              ("Expiry", "{{ payload.expiry_date }}")]
_QUAL_TEXT = ("Supplier:       {{ payload.supplier_name }}\n"
              "Qualification:  {{ payload.qualification_number }}\n"
              "Scope:          {{ payload.scope }}\n"
              "Expiry:         {{ payload.expiry_date }}")
_QUAL_URL = "/production/supplier-qualifications/{{ payload.qualification_id }}/edit"

SUPPLIER_QUALIFICATION_EXPIRED = _simple(
    "supplier.qualification_expired",
    subject="{{ payload.supplier_name }}'s qualification for {{ payload.scope }} has expired",
    lead="{{ payload.supplier_name }} is off the approved supplier list for {{ payload.scope }} until re-qualified.",
    rows=_QUAL_ROWS, text_rows=_QUAL_TEXT,
    url=_QUAL_URL, action_label="Open the qualification", severity="warning",
    in_app_subject="{{ payload.supplier_name }} qualification expired: {{ payload.scope }}",
    in_app_body="Off the approved supplier list for {{ payload.scope }} until re-qualified.", icon="building")

SUPPLIER_QUALIFICATION_EXPIRING_SOON = _simple(
    "supplier.qualification_expiring_soon",
    subject="{{ payload.supplier_name }}'s qualification for {{ payload.scope }} expires in {{ payload.days_to_expiry }} days",
    lead="Re-qualify {{ payload.supplier_name }} before {{ payload.expiry_date }}, or it drops off the approved supplier list for {{ payload.scope }}.",
    rows=_QUAL_ROWS, text_rows=_QUAL_TEXT,
    url=_QUAL_URL, action_label="Open the qualification", severity="info",
    in_app_subject="{{ payload.supplier_name }} qualification expires in {{ payload.days_to_expiry }} days",
    in_app_body="{{ payload.scope }}: expires {{ payload.expiry_date }}. Re-qualify before then.", icon="building")

SUPPLIER_STANDING_REVIEW = _simple(
    "supplier.standing_review",
    subject="Review {{ payload.supplier_name }}'s standing (scorecard {{ payload.rating }})",
    lead="{{ payload.reason }} This is a recommendation — nothing changes until someone decides.",
    rows=[("Supplier", "<strong>{{ payload.supplier_name }}</strong>"),
          ("Scorecard", "{{ payload.rating }}")],
    text_rows="Supplier:   {{ payload.supplier_name }}\nScorecard:  {{ payload.rating }}",
    url="/production/supplier-quality", action_label="Open supplier quality", severity="info",
    in_app_subject="Review {{ payload.supplier_name }}'s standing ({{ payload.rating }})",
    in_app_body="{{ payload.reason }}", icon="building")

SUPPLIER_INSPECTION_DISCONTINUED = _simple(
    "supplier.inspection_discontinued",
    subject="Stop accepting {{ payload.supplier_name }} at {{ payload.step_name }}",
    lead="Tightened inspection ran 5 lots in a row without returning to normal (Z1.4). Stop accepting this supplier for the step and drive corrective action — a recommendation, not an automatic suspension.",
    rows=[("Supplier", "<strong>{{ payload.supplier_name }}</strong>"),
          ("Inspection step", "{{ payload.step_name }}")],
    text_rows="Supplier:         {{ payload.supplier_name }}\nInspection step:  {{ payload.step_name }}",
    url="/production/receiving-plans/{{ payload.step_id }}", action_label="Open the receiving plan",
    severity="critical",
    in_app_subject="Inspection discontinued: {{ payload.supplier_name }} at {{ payload.step_name }}",
    in_app_body="Tightened inspection ran 5 lots without returning to normal. Stop accepting and drive corrective action.",
    icon="octagon-alert")

CAPA_READY_FOR_VERIFICATION = _simple(
    "capa.ready_for_verification",
    subject="CAPA {{ payload.capa_number }} is ready for verification",
    lead="Its tasks and root cause analysis are complete. Verify the action was effective.",
    rows=[("CAPA", "<strong>{{ payload.capa_number }}</strong>"),
          ("Type", "{{ payload.capa_type_display }}"),
          ("Severity", "{{ payload.severity_display }}")],
    text_rows="CAPA:      {{ payload.capa_number }}\nType:      {{ payload.capa_type_display }}\nSeverity:  {{ payload.severity_display }}",
    url="/quality/capas/{{ payload.capa_id }}", action_label="Open the CAPA", severity="info",
    in_app_subject="CAPA {{ payload.capa_number }} ready for verification",
    in_app_body="{{ payload.severity_display }} {{ payload.capa_type_display }}: tasks and RCA complete.",
    icon="clipboard-check")


ALL_TEMPLATES = [
    WORKORDER_HELD,
    WORKORDER_OVERDUE,
    TRAINING_EXPIRING_SOON,
    TRAINING_EXPIRED,
    PART_UNAPPROVED,
    SUPPLIER_UNQUALIFIED,
    SUPPLIER_QUALIFICATION_EXPIRED,
    SUPPLIER_QUALIFICATION_EXPIRING_SOON,
    SUPPLIER_STANDING_REVIEW,
    SUPPLIER_INSPECTION_DISCONTINUED,
    CAPA_READY_FOR_VERIFICATION,
    START_REFUSED,
    FPI_REQUESTED,
    FPI_DECIDED,
    TOOL_LIFE_WARNING,
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
