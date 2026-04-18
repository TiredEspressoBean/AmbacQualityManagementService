"""
HubSpot sync orchestration.

Uses the official hubspot-api-client SDK for extraction, DRF serializers for
transform/validate/load. Replaces Tracker/hubspot/sync.py.
"""

import logging

from django.utils import timezone
from hubspot import HubSpot
from hubspot.crm.deals import ApiException as DealsApiException

from integrations.models.config import IntegrationConfig, IntegrationSyncLog
from integrations.models.links.hubspot import (
    HubSpotOrderLink, HubSpotPipelineStage,
)
from .serializers import (
    HubSpotDealInboundSerializer, resolve_company, resolve_contact,
)

logger = logging.getLogger(__name__)


def get_client(integration):
    """Build a HubSpot SDK client from integration credentials."""
    return HubSpot(access_token=integration.api_key)


def sync_pipeline_stages(client, integration):
    """
    Sync pipeline stages from HubSpot to HubSpotPipelineStage.
    Replaces Tracker/hubspot/api.py:update_stages().
    """
    config = integration.config
    active_prefix = config.get('active_stage_prefix', 'Gate')

    # Get unique pipeline IDs to sync
    # If a specific pipeline_id is configured, only sync that one
    pipeline_id = config.get('pipeline_id')
    if pipeline_id:
        pipeline_ids = [pipeline_id]
    else:
        # Will be populated from deal data during sync_all_deals
        return 0

    stages_synced = 0
    for pid in pipeline_ids:
        try:
            response = client.crm.pipelines.pipeline_stages_api.get_all(
                object_type='deals', pipeline_id=pid
            )
        except Exception as e:
            logger.error(f"Error fetching pipeline stages for {pid}: {e}")
            continue

        for stage in response.results:
            include_in_progress = stage.label.startswith(active_prefix) if active_prefix else True

            HubSpotPipelineStage.objects.update_or_create(
                integration=integration,
                api_id=stage.id,
                defaults={
                    'stage_name': stage.label,
                    'pipeline_id': pid,
                    'display_order': stage.display_order,
                    'include_in_progress': include_in_progress,
                    'last_synced_at': timezone.now(),
                }
            )
            stages_synced += 1

    return stages_synced


def sync_all_deals(integration):
    """
    Sync all HubSpot deals for an integration.

    Uses the official SDK for extraction, batch APIs for associations,
    and DRF serializers for transform/validate/load.

    Args:
        integration: IntegrationConfig instance with provider='hubspot'

    Returns:
        dict: {'status': 'success'|'error', 'created': int, 'updated': int, ...}
    """
    tenant = integration.tenant
    config = integration.config
    is_debug = config.get('debug_mode', False)
    debug_deal_name = config.get('debug_deal_name', 'Ghost Pepper')

    # Concurrent sync protection
    if integration.sync_status == IntegrationConfig.SyncStatus.SYNCING:
        return {'status': 'skipped', 'reason': 'sync_already_running'}

    integration.sync_status = IntegrationConfig.SyncStatus.SYNCING
    integration.save(update_fields=['sync_status'])

    # Create sync log
    sync_log = IntegrationSyncLog.objects.create(
        integration=integration,
        sync_type=IntegrationSyncLog.SyncType.FULL,
    )

    try:
        client = get_client(integration)

        # Fetch all deals (SDK handles pagination + rate limits)
        try:
            deals = client.crm.deals.get_all(
                properties=["dealname", "dealstage", "pipeline", "closedate"]
            )
        except DealsApiException as e:
            raise RuntimeError(f"Failed to fetch deals: {e}")

        if not deals:
            sync_log.status = IntegrationSyncLog.Status.FAILED
            sync_log.error_message = 'No deals returned from HubSpot'
            sync_log.completed_at = timezone.now()
            sync_log.save()
            integration.sync_status = IntegrationConfig.SyncStatus.ERROR
            integration.last_sync_error = 'No deals returned'
            integration.save(update_fields=['sync_status', 'last_sync_error'])
            return {'status': 'error', 'message': 'No deals returned'}

        # Sync pipeline stages for each unique pipeline
        pipeline_ids = {d.properties.get('pipeline') for d in deals if d.properties.get('pipeline')}
        for pid in pipeline_ids:
            _sync_stages_for_pipeline(client, integration, pid, config.get('active_stage_prefix', 'Gate'))

        # Batch fetch associations (contacts + companies per deal)
        deal_ids = [d.id for d in deals]
        deal_to_contacts = _batch_get_associations(client, deal_ids, 'contacts')
        deal_to_companies = _batch_get_associations(client, deal_ids, 'companies')

        # Batch fetch contact details
        all_contact_ids = _extract_ids(deal_to_contacts)
        contact_dict = _batch_get_contacts(client, all_contact_ids) if all_contact_ids else {}

        # Collect all company IDs (from deals + from contacts)
        all_company_ids = set(_extract_ids(deal_to_companies))
        for cinfo in contact_dict.values():
            if cinfo.get('associated_company_id'):
                all_company_ids.add(cinfo['associated_company_id'])

        # Batch fetch company details
        company_dict = _batch_get_companies(client, list(all_company_ids)) if all_company_ids else {}

        # Process deals
        created_count = 0
        updated_count = 0
        errors = []

        for deal in deals:
            # Debug mode: skip all but the test deal
            if is_debug and deal.properties.get('dealname') != debug_deal_name:
                continue

            try:
                # Resolve stage
                current_stage = None
                stage_id = deal.properties.get('dealstage')
                if stage_id:
                    current_stage = HubSpotPipelineStage.objects.filter(
                        integration=integration, api_id=stage_id
                    ).first()

                # Resolve company (first associated company)
                company = None
                deal_company_ids = deal_to_companies.get(deal.id, [])
                if deal_company_ids:
                    company = resolve_company(
                        deal_company_ids[0], company_dict, integration, tenant
                    )

                # Resolve customer (first associated contact)
                customer = None
                deal_contact_ids = deal_to_contacts.get(deal.id, [])
                if deal_contact_ids:
                    contact_info = contact_dict.get(str(deal_contact_ids[0]))
                    if contact_info:
                        customer = resolve_contact(
                            contact_info, company_dict, integration, tenant
                        )

                # Find existing order by link
                existing_link = HubSpotOrderLink.objects.filter(
                    integration=integration, deal_id=deal.id
                ).select_related('order').first()

                # Build serializer context
                context = {
                    'integration': integration,
                    'deal_id': deal.id,
                    'current_stage': current_stage,
                    'company': company,
                    'customer': customer,
                }

                serializer = HubSpotDealInboundSerializer(
                    instance=existing_link.order if existing_link else None,
                    data=deal.properties,
                    context=context,
                )

                if serializer.is_valid():
                    serializer.save()
                    if existing_link:
                        updated_count += 1
                    else:
                        created_count += 1
                else:
                    errors.append({'deal_id': deal.id, 'errors': serializer.errors})
                    logger.warning(f"Validation failed for deal {deal.id}: {serializer.errors}")

            except Exception as e:
                errors.append({'deal_id': deal.id, 'error': str(e)})
                logger.error(f"Error processing deal {deal.id}: {e}", exc_info=True)

        # Update sync log
        processed = created_count + updated_count + len(errors)
        sync_log.status = IntegrationSyncLog.Status.SUCCESS
        sync_log.records_processed = processed
        sync_log.records_created = created_count
        sync_log.records_updated = updated_count
        sync_log.error_message = str(errors) if errors else None
        sync_log.completed_at = timezone.now()
        sync_log.save()

        # Update integration status
        integration.sync_status = IntegrationConfig.SyncStatus.IDLE
        integration.last_synced_at = timezone.now()
        integration.last_sync_error = None
        integration.last_sync_stats = {
            'created': created_count,
            'updated': updated_count,
            'errors': len(errors),
            'processed': processed,
        }
        integration.save(update_fields=[
            'sync_status', 'last_synced_at', 'last_sync_error', 'last_sync_stats'
        ])

        logger.info(f"HubSpot sync completed: {created_count} created, {updated_count} updated, {len(errors)} errors")

        return {
            'status': 'success',
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
            'processed': processed,
        }

    except Exception as e:
        sync_log.status = IntegrationSyncLog.Status.FAILED
        sync_log.error_message = str(e)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        integration.sync_status = IntegrationConfig.SyncStatus.ERROR
        integration.last_sync_error = str(e)
        integration.save(update_fields=['sync_status', 'last_sync_error'])

        logger.error(f"HubSpot sync failed: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}


# ---------------------------------------------------------------------------
# SDK helper functions (batch operations)
# ---------------------------------------------------------------------------

def _sync_stages_for_pipeline(client, integration, pipeline_id, active_prefix):
    """Sync stages for a single pipeline. Also creates/maps native Milestones."""
    from Tracker.models import MilestoneTemplate, Milestone

    try:
        response = client.crm.pipelines.pipeline_stages_api.get_all(
            object_type='deals', pipeline_id=pipeline_id
        )
    except Exception as e:
        logger.error(f"Error fetching stages for pipeline {pipeline_id}: {e}")
        return

    # Ensure a MilestoneTemplate exists for this pipeline
    template, _ = MilestoneTemplate.objects.get_or_create(
        tenant=integration.tenant,
        name=f"HubSpot Pipeline ({pipeline_id})",
        defaults={'description': 'Auto-created from HubSpot pipeline sync', 'is_default': True},
    )

    for stage in response.results:
        include_in_progress = stage.label.startswith(active_prefix) if active_prefix else True

        # Auto-strip prefix for customer display name
        # "Gate Two - Development & Quote" -> "Development & Quote"
        # Stages without the prefix keep blank (falls back to full name)
        customer_display = ''
        if active_prefix and stage.label.startswith(active_prefix):
            import re
            stripped = re.sub(rf'^{re.escape(active_prefix)}\s+\w+\s*[-–—]\s*', '', stage.label)
            if stripped != stage.label:
                customer_display = stripped

        # Create/update native Milestone
        milestone, _ = Milestone.objects.update_or_create(
            tenant=integration.tenant,
            template=template,
            display_order=stage.display_order,
            defaults={
                'name': stage.label,
                'customer_display_name': customer_display,
                'is_active': include_in_progress,
            }
        )

        # Create/update HubSpotPipelineStage with mapping to native milestone
        HubSpotPipelineStage.objects.update_or_create(
            integration=integration,
            api_id=stage.id,
            defaults={
                'stage_name': stage.label,
                'pipeline_id': pipeline_id,
                'display_order': stage.display_order,
                'include_in_progress': include_in_progress,
                'last_synced_at': timezone.now(),
                'mapped_milestone': milestone,
            }
        )


def _batch_get_associations(client, deal_ids, to_object_type):
    """Batch fetch deal associations (contacts or companies)."""
    if not deal_ids:
        return {}

    try:
        from hubspot.crm.associations.v4 import BatchInputPublicFetchAssociationsBatchRequest
        response = client.crm.associations.v4.batch_api.get_page(
            from_object_type='deals',
            to_object_type=to_object_type,
            batch_input_public_fetch_associations_batch_request=BatchInputPublicFetchAssociationsBatchRequest(
                inputs=[{"id": did} for did in deal_ids]
            )
        )
    except Exception as e:
        logger.error(f"Error fetching {to_object_type} associations: {e}")
        return {}

    result = {}
    for item in response.results:
        deal_id = item.from_.id if hasattr(item, 'from_') else item._from.id
        to_ids = [assoc.to_object_id for assoc in item.to]
        result[deal_id] = to_ids
    return result


def _extract_ids(deal_to_ids):
    """Flatten association dict to a list of all IDs."""
    ids = []
    for id_list in deal_to_ids.values():
        ids.extend(id_list)
    return ids


def _batch_get_contacts(client, contact_ids):
    """Batch fetch contact details."""
    if not contact_ids:
        return {}

    try:
        from hubspot.crm.contacts import BatchReadInputSimplePublicObjectId
        response = client.crm.contacts.batch_api.read(
            batch_read_input_simple_public_object_id=BatchReadInputSimplePublicObjectId(
                properties=["firstname", "lastname", "email", "associatedcompanyid"],
                inputs=[{"id": str(cid)} for cid in contact_ids],
            )
        )
    except Exception as e:
        logger.error(f"Error batch-reading contacts: {e}")
        return {}

    result = {}
    for contact in response.results:
        result[contact.id] = {
            'first_name': contact.properties.get('firstname', ''),
            'last_name': contact.properties.get('lastname', ''),
            'email': contact.properties.get('email'),
            'associated_company_id': contact.properties.get('associatedcompanyid'),
        }
    return result


def _batch_get_companies(client, company_ids):
    """Batch fetch company details."""
    if not company_ids:
        return {}

    try:
        from hubspot.crm.companies import BatchReadInputSimplePublicObjectId
        response = client.crm.companies.batch_api.read(
            batch_read_input_simple_public_object_id=BatchReadInputSimplePublicObjectId(
                properties=["name", "description"],
                inputs=[{"id": str(cid)} for cid in company_ids],
            )
        )
    except Exception as e:
        logger.error(f"Error batch-reading companies: {e}")
        return {}

    result = {}
    for company in response.results:
        result[company.id] = {
            'name': company.properties.get('name'),
            'description': company.properties.get('description', ''),
        }
    return result
