from integrations.adapters.base import ADAPTER_API_VERSION

MANIFEST = {
    # Identity
    'id': 'hubspot',
    'name': 'HubSpot CRM',
    'category': 'CRM',
    'description': 'Sync deals, contacts, and companies from HubSpot CRM',
    'long_description': (
        'Connect your HubSpot CRM to automatically sync deals as orders, '
        'contacts as portal users, and companies. Pipeline stage changes '
        'sync bidirectionally — update a stage in either system and the '
        'other stays in sync.'
    ),
    'version': '1.0.0',
    'adapter_api_version': ADAPTER_API_VERSION,
    'author': 'uqmes',
    'icon': 'hubspot.svg',

    # Auth
    'auth_type': 'api_key',
    'auth_label': 'Private App Access Token',
    'auth_instructions': (
        'In HubSpot, go to Settings → Integrations → Private Apps. '
        'Create a new private app, grant it CRM scopes (contacts, companies, deals), '
        'and copy the access token.'
    ),
    'auth_docs_url': 'https://developers.hubspot.com/docs/api/private-apps',

    # What syncs
    'data_flows': [
        {'direction': 'inbound', 'label': 'Deals → Orders', 'description': 'HubSpot deals become orders with name, close date, and stage'},
        {'direction': 'inbound', 'label': 'Contacts → Portal Users', 'description': 'Deal contacts become customer portal users'},
        {'direction': 'inbound', 'label': 'Companies → Companies', 'description': 'Associated companies are created or matched by name'},
        {'direction': 'inbound', 'label': 'Pipeline Stages → Milestones', 'description': 'Deal pipeline stages sync to order milestones'},
        {'direction': 'outbound', 'label': 'Stage Changes → Deal Updates', 'description': 'Milestone changes push back to HubSpot deal stage'},
        {'direction': 'inbound', 'label': 'Webhooks → Real-time Updates', 'description': 'Deal stage changes in HubSpot update orders immediately'},
    ],

    # How it works
    'sync_details': {
        'frequency': 'Every hour (automatic), or trigger manually',
        'method': 'Scheduled bulk sync + real-time webhooks for stage changes',
        'first_sync': 'Creates orders from your existing HubSpot deals',
    },

    # Requirements
    'requirements': [
        'HubSpot account with API access (any paid plan, or free with Private Apps)',
        'Private App with CRM scopes: crm.objects.contacts.read, crm.objects.companies.read, crm.objects.deals.read, crm.objects.deals.write',
    ],

    # What gets created
    'creates': [
        'Orders (from HubSpot deals)',
        'Companies (from deal-associated companies)',
        'Portal Users (from deal-associated contacts)',
        'Milestones (from pipeline stages)',
    ],

    # Limitations
    'limitations': [
        'Attachments and notes are not synced',
        'Companies are matched by name — duplicates possible if naming differs',
        'Portal users receive placeholder passwords — configure SSO for customer access',
    ],

    # Internal wiring
    'link_models': {
        'order': 'integrations.models.links.hubspot.HubSpotOrderLink',
        'company': 'integrations.models.links.hubspot.HubSpotCompanyLink',
        'pipeline_stage': 'integrations.models.links.hubspot.HubSpotPipelineStage',
    },
    'config_serializer': 'integrations.adapters.hubspot.serializers.HubSpotConfigSerializer',
}
