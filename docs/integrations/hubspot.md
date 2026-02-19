# HubSpot Integration

Connect Ambac Tracker with HubSpot CRM for deal and order synchronization.

## Overview

The HubSpot integration enables:
- Create orders from HubSpot deals
- Sync company information
- Track order status in HubSpot
- Unified customer data

## Integration Features

### Deal to Order
When deals close in HubSpot:
- Order created in Ambac Tracker
- Company linked/created
- Contact information synced
- Deal properties mapped

### Company Sync
Company data synchronized:
- Company name and details
- Contact information
- Custom properties

### Status Updates
Order status reflects in HubSpot:
- Order progress
- Completion status
- Shipping information

## Configuration

### Prerequisites
- HubSpot account with API access
- Ambac Tracker admin access
- API key or OAuth credentials

### Setup Steps

1. **Get HubSpot API Credentials**
   - HubSpot Settings > Integrations > API Key
   - Or configure OAuth app

2. **Configure in Ambac Tracker**
   - Navigate to Settings > Integrations
   - Enter HubSpot credentials
   - Configure mapping

3. **Map Fields**
   - Map HubSpot deal properties to order fields
   - Map company properties
   - Configure custom fields

4. **Test Connection**
   - Create test deal in HubSpot
   - Verify order creation
   - Check field mapping

## Field Mapping

### Deal to Order

| HubSpot Field | Ambac Tracker Field |
|---------------|---------------------|
| Deal name | Order number/name |
| Associated company | Customer |
| Close date | Order date |
| Amount | Order value |
| Deal stage | Order status |

### Company Mapping

| HubSpot Field | Ambac Tracker Field |
|---------------|---------------------|
| Company name | Company name |
| Domain | Website |
| Phone | Phone |
| Address | Address |

## Workflow

### Automatic Order Creation

1. Deal moves to "Closed Won" in HubSpot
2. Webhook triggers Ambac Tracker
3. Order created with mapped data
4. Company linked or created
5. Confirmation in both systems

### Manual Order Creation

1. View deal in HubSpot
2. Click "Create Order in Ambac Tracker"
3. Review/modify order details
4. Create order
5. Link established

## Sync Settings

### Direction
- **HubSpot → Ambac Tracker**: Deal creates order
- **Ambac Tracker → HubSpot**: Status updates back

### Triggers
- On deal stage change
- On deal property change
- Manual trigger

### Frequency
- Real-time (webhook)
- Scheduled sync (configurable)

## Error Handling

### Sync Failures
- Logged in integration log
- Retry automatically
- Alert on persistent failure

### Data Conflicts
- HubSpot data preferred (configurable)
- Manual resolution option
- Audit trail of conflicts

## Viewing Integration Status

Navigate to Settings > Integrations > HubSpot:
- Connection status
- Recent sync activity
- Error log
- Sync history

## Troubleshooting

### "Connection failed"
- Verify API credentials
- Check API key permissions
- Confirm network access

### "Company not found"
- Company may need creation
- Check company name matching
- Verify sync settings

### "Fields not mapping"
- Review field mapping configuration
- Check field types match
- Verify custom properties exist

## Permissions

| Permission | Allows |
|------------|--------|
| `manage_integrations` | Configure HubSpot (admin) |
| `view_integrations` | View integration status |

## Best Practices

1. **Test in sandbox** - Before production
2. **Map carefully** - Verify field alignment
3. **Monitor logs** - Watch for errors
4. **Document configuration** - For maintenance
5. **Train users** - On integrated workflow
