import logging
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone

from Tracker.hubspot.api import (
    get_all_deals, get_contacts_from_deal_id, get_company_ids_from_deal_id, extract_ids,
    get_company_info_from_company_ids, get_contact_info_from_contact_ids, update_stages
)
from Tracker.models import Orders, Companies, User, ExternalAPIOrderIdentifier, HubSpotSyncLog

logger = logging.getLogger(__name__)


def _prepare_order_from_deal(deal, deal_to_contacts, deal_to_companies, contact_dict, company_dict):
    """Extract order data from HubSpot deal (eliminates code duplication)."""
    deal_id = deal['id']

    # Get pipeline stage
    try:
        current_gate = ExternalAPIOrderIdentifier.objects.get(API_id=deal["properties"]["dealstage"])
    except ObjectDoesNotExist:
        current_gate = None

    # Get company (use first if multiple)
    company = None
    if deal_id in deal_to_companies and deal_to_companies[deal_id]:
        company_id = deal_to_companies[deal_id][0]
        company_info = company_dict.get(str(company_id))
        if company_info:
            # Use company ID as fallback if name is missing
            company_name = company_info.get('name') or f"Company {company_id}"
            company, _ = Companies.objects.get_or_create(
                name=company_name,
                defaults={}
            )

    # Get customer (use first contact)
    customer = None
    if deal_id in deal_to_contacts and deal_to_contacts[deal_id]:
        contact_info = contact_dict.get(str(deal_to_contacts[deal_id][0]))
        if contact_info and contact_info.get('email'):
            customer, _ = User.objects.get_or_create(
                email=contact_info['email'],
                defaults={
                    'first_name': contact_info.get('first_name', ''),
                    'last_name': contact_info.get('last_name', ''),
                    'username': contact_info['email']
                }
            )

    return {
        'name': deal['properties'].get('dealname', f'Deal {deal_id}'),
        'company': company,
        'customer': customer,
        'current_hubspot_gate': current_gate,
        'archived': deal.get('archived', False),
        'hubspot_last_synced_at': timezone.now(),
    }



def sync_all_deals():
    """Sync deals from HubSpot. Only touches orders with hubspot_deal_id."""
    # Create sync log
    sync_log = HubSpotSyncLog.objects.create(sync_type='full', status='running')

    try:
        # Fetch deals
        deals_data = get_all_deals()
        if not deals_data:
            sync_log.status = 'failed'
            sync_log.error_message = 'Failed to retrieve deals'
            sync_log.completed_at = timezone.now()
            sync_log.save()
            return {'status': 'error', 'message': 'Failed to retrieve deals'}

        # Sync pipeline stages ONCE per unique pipeline (not per deal)
        pipelines = {deal["properties"]["pipeline"] for deal in deals_data if deal["properties"].get("pipeline")}
        for pipeline_id in pipelines:
            update_stages(pipeline_id)

        # Batch fetch associated data
        deal_id_list = [deal['id'] for deal in deals_data]
        deal_to_contacts = get_contacts_from_deal_id(deal_id_list)
        deal_to_companies = get_company_ids_from_deal_id(deal_id_list)

        contact_dict = get_contact_info_from_contact_ids(extract_ids(deal_to_contacts))
        company_dict = get_company_info_from_company_ids(extract_ids(deal_to_companies))

        # Process deals
        created_count = 0
        updated_count = 0
        is_debug = getattr(settings, "HUBSPOT_DEBUG", False)

        for deal in deals_data:
            # Skip if debug mode and not the debug deal
            if is_debug and deal["properties"].get("dealname") != "Ghost Pepper":
                continue

            # Use helper to prepare order data
            order_data = _prepare_order_from_deal(deal, deal_to_contacts, deal_to_companies, contact_dict, company_dict)

            # Create or update order
            obj, created = Orders.objects.update_or_create(
                hubspot_deal_id=deal["id"],
                defaults=order_data
            )

            # Set flag to prevent infinite loop
            obj._skip_hubspot_push = True
            obj.save()

            if created:
                created_count += 1
            else:
                updated_count += 1

        # Update sync log
        sync_log.status = 'success'
        sync_log.deals_processed = len(deals_data) if not is_debug else (created_count + updated_count)
        sync_log.deals_created = created_count
        sync_log.deals_updated = updated_count
        sync_log.completed_at = timezone.now()
        sync_log.save()

        logger.info(f"HubSpot sync completed: {created_count} created, {updated_count} updated")

        return {
            'status': 'success',
            'created': created_count,
            'updated': updated_count,
            'processed': sync_log.deals_processed
        }

    except Exception as e:
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        sync_log.completed_at = timezone.now()
        sync_log.save()
        logger.error(f"HubSpot sync failed: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}
