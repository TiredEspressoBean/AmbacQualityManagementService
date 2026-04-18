"""
Data migration: Copy current_hubspot_gate → current_milestone for orders
that have a HubSpot gate with a matching HubSpotPipelineStage that has
a mapped_milestone.

This is reversible — the reverse operation clears current_milestone for
orders that were migrated (where current_hubspot_gate is still set).
The original current_hubspot_gate field is NOT modified in either direction.
"""

from django.db import migrations


def migrate_gates_to_milestones(apps, schema_editor):
    """
    For each order with current_hubspot_gate set but current_milestone empty:
    1. Find the matching HubSpotPipelineStage by api_id
    2. If it has a mapped_milestone, set order.current_milestone to that milestone
    """
    Orders = apps.get_model('Tracker', 'Orders')
    HubSpotPipelineStage = apps.get_model('integrations', 'HubSpotPipelineStage')

    # Build lookup: api_id → mapped_milestone_id
    stage_to_milestone = {}
    for stage in HubSpotPipelineStage.objects.filter(
        mapped_milestone__isnull=False
    ).values('api_id', 'mapped_milestone_id'):
        stage_to_milestone[stage['api_id']] = stage['mapped_milestone_id']

    if not stage_to_milestone:
        return  # No mapped stages yet — nothing to migrate

    # Find orders with a hubspot gate but no milestone
    orders_to_update = Orders.objects.filter(
        current_hubspot_gate__isnull=False,
        current_milestone__isnull=True,
    ).select_related('current_hubspot_gate')

    updated = 0
    for order in orders_to_update:
        gate_api_id = order.current_hubspot_gate.API_id
        milestone_id = stage_to_milestone.get(gate_api_id)
        if milestone_id:
            order.current_milestone_id = milestone_id
            order.save(update_fields=['current_milestone_id'])
            updated += 1

    if updated:
        print(f"  Migrated {updated} orders from current_hubspot_gate to current_milestone")


def reverse_migration(apps, schema_editor):
    """
    Clear current_milestone for orders that still have current_hubspot_gate set.
    This only undoes what the forward migration did — orders where milestone
    was set manually (without a hubspot gate) are left alone.
    """
    Orders = apps.get_model('Tracker', 'Orders')

    updated = Orders.objects.filter(
        current_hubspot_gate__isnull=False,
        current_milestone__isnull=False,
    ).update(current_milestone=None)

    if updated:
        print(f"  Reversed {updated} orders: cleared current_milestone (current_hubspot_gate preserved)")


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0017_milestone_orders_current_milestone_milestonetemplate_and_more'),
        ('integrations', '0003_hubspotpipelinestage_mapped_milestone'),
    ]

    operations = [
        migrations.RunPython(
            migrate_gates_to_milestones,
            reverse_code=reverse_migration,
        ),
    ]
