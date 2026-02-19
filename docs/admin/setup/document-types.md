# Document Types

Configure categories for documents with specific handling rules.

## What are Document Types?

Document Types define:
- **Categories** for organizing documents
- **Approval requirements** per type
- **Retention policies**
- **Access controls**

## Default Document Types

| Type | Purpose | Approval |
|------|---------|----------|
| **Work Instruction** | Step-by-step procedures | Required |
| **Specification** | Technical requirements | Required |
| **Drawing** | Engineering drawings | Required |
| **Form** | Blank forms/templates | Required |
| **Certificate** | Certifications, CoCs | Reference |
| **Report** | Test/inspection reports | Optional |
| **Contract** | Agreements, POs | Reference |
| **Manual** | Equipment manuals | Reference |

## Creating Document Types

1. Navigate to **Data Management** > **Document Types**
2. Click **+ New Document Type**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Name** | Type name |
| **Code** | Short code (WI, SPEC) |
| **Description** | When to use |
| **Requires Approval** | Yes/No |
| **Approval Template** | Which approval flow |

4. Save

## Document Type Settings

### Approval Settings

| Setting | Description |
|---------|-------------|
| **Requires Approval** | Documents need approval before release |
| **Approval Template** | Default approval workflow |
| **Auto-Archive Previous** | Archive old revision on new approval |

### Retention Settings

| Setting | Description |
|---------|-------------|
| **Retention Period** | How long to keep |
| **Retention Action** | Archive, Review, Delete |
| **Category** | Regulatory, Business, Operational |

### Access Settings

| Setting | Description |
|---------|-------------|
| **Default Visibility** | Public, Internal, Confidential |
| **Customer Visible** | Show to customers |

## Document Numbering

Configure automatic numbering per type:

| Pattern | Example | Result |
|---------|---------|--------|
| `{TYPE}-{YEAR}-{SEQ}` | WI-2026-0001 | Per type per year |
| `{SEQ}` | 00001 | Simple sequential |
| Manual | User enters | No auto-numbering |

## Permissions by Type

Control who can access document types:

1. Edit document type
2. Go to **Permissions**
3. Set per group:
   - View
   - Create
   - Edit
   - Approve

Example:
- **Work Instructions**: QA can approve, Operators can view
- **Contracts**: Admin only

## Usage Guidelines

Add guidance for each type:

```markdown
## Work Instruction (WI)
Used for: Step-by-step procedures for manufacturing operations
Approval: Engineering review, QA approval
Examples: WI-001 Assembly Process, WI-002 Packaging
```

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documenttype` | View document types |
| `add_documenttype` | Create document types |
| `change_documenttype` | Edit document types |
| `delete_documenttype` | Remove document types |

## Best Practices

1. **Clear definitions** - When to use each type
2. **Appropriate controls** - Match approval to risk
3. **Consistent naming** - Standard codes
4. **Review periodically** - Adjust as needed
