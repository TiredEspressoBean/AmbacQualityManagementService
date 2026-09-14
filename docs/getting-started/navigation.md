# Navigation Tour

This guide introduces the uqmes interface and helps you find your way around.

## Interface Overview

The uqmes interface consists of three main areas:

```
┌──────────────┬──────────────────────────────────────────┐
│ Organization │  Header (sidebar toggle, notifications,  │
│   selector   │          theme)                          │
├──────────────┼──────────────────────────────────────────┤
│              │                                          │
│   Sidebar    │           Main Content Area              │
│  Navigation  │    (Pages, Forms, Tables, Charts)        │
│              │                                          │
├──────────────┤                                          │
│ Your profile │                                          │
└──────────────┴──────────────────────────────────────────┘
```

The organization selector sits at the **top of the sidebar**, and your profile
menu at the **bottom of the sidebar** — not in the header bar.

## Sidebar Navigation

The sidebar on the left is your main navigation. Sections you lack permission
for are hidden entirely, so your sidebar may be shorter than what follows.

Three links sit at the top with no section header:

- **Home** - Your role-aware landing page
- **Help & Docs** - This documentation
- **Tracker** - Order status and progress

### Personal
- **Inbox** - CAPA tasks and pending approvals (not work assignments—those come from your supervisor)

### Production
- **Work Orders** - Active work orders and their status
- **WO Control Center** - Shop-floor control view across work orders
- **Processes** - Manufacturing workflow definitions

### Scheduling
- **Schedule (Gantt)** - The planning board
- **Calendar** - Working windows and shifts
- **Capacity Planning** - Coarse long-range capacity
- **Staging List** - Kits staged for upcoming jobs
- **Operator Hours** - Labor hours reporting
- **Requirements** - Sourcing and production requirements

### Supply
- **Incoming Inspection** - Receiving inspection queue
- **Outside Processing** - Parts out at outside vendors
- **Materials** - Material lots by lifecycle status
- **Receiving Inspection Plans** - Inspection plans applied on receipt
- **Supplier Quality** - Supplier performance and issues
- **Approved Suppliers** - Supplier qualifications
- **Part Approvals** - Part approval records

### Remanufacturing
- **Dashboard** - Reman overview
- **Cores** - Core receiving and tracking
- **Components** - Harvested components

### Quality
- **Dashboard** - Quality KPIs at a glance
- **CAPAs** - Corrective and Preventive Actions
- **Quality Reports** - Non-conformance reports
- **Change Control** - Process change requests, orders, and notices
- **Dispositions** - Quarantine and disposition management
- **Training** - Training records and compliance
- **Calibrations** - Equipment calibration tracking
- **Heat Map** - Visual defect analysis

### Approvals
- **Overview** - Pending items requiring your approval
- **History** - Past approval decisions

Three more standalone links follow, again with no section header:

- **Documents** - Document library and management
- **Analytics** - Dashboards, trends, and analysis
- **AI Chat** - AI assistant for data exploration

### Admin
- **Settings** - Organization and system configuration
- **User Management** - Users, invitations, and roles
- **Work Centers** - Shop-floor work center master data
- **Data Management** - Access to all data editors
- **Audit Log** - System audit trail

!!! info "Section Visibility"
    You'll only see sections you have permission to access. If a section is missing, contact your administrator about your role assignments.

## Header Bar

The header bar at the top is deliberately sparse. It contains:

- **Toggle Sidebar** - Collapse the sidebar to icons (also `Ctrl`/`Cmd` + `B`)
- **Notifications** - Your notification feed
- **Toggle theme** - Switch between light and dark

### Organization Selector
At the **top of the sidebar**, click your organization name to:

- See the current organization
- Open **Organization settings**
- Switch between organizations (if you belong to multiple)

### Profile Menu
At the **bottom of the sidebar**, click your name to access:

- **Profile** - Your account settings
- **My Notifications** - Notification preferences
- **Help & Docs** - This documentation
- **Log out** - Sign out of uqmes

!!! note "No global search"
    uqmes has no application-wide search bar. Each list page has its own search
    and filter controls, and the Home page has a **Look up a work order or
    part…** box.

## Page Types

You'll encounter several types of pages:

### List Pages (Editors)
Tables showing multiple records with:

- **Search** - Filter by text
- **Filters** - Narrow by status, date, etc.
- **Sorting** - Click column headers
- **Pagination** - Navigate through large datasets
- **Actions** - Edit, delete, or perform actions on rows

### Detail Pages
View a single record with:

- **Header** - Key information and status
- **Tabs** - Organized sections (Details, Documents, History)
- **Related Items** - Links to associated records
- **Actions** - Buttons for available operations

### Form Pages
Create or edit records with:

- **Fields** - Input areas for data
- **Validation** - Red highlights for errors
- **Save/Cancel** - Confirm or discard changes

### Dashboard Pages
Visual summaries with:

- **KPI Cards** - Key metrics at a glance
- **Charts** - Trends and distributions
- **Tables** - Recent or important items

## Common Actions

### Creating Records
Most list pages have a **New <record type>** button in the top right - for
example **New Orders** on the Orders editor, **New CAPAs** on the CAPA list.
Click it to create a new record.

### Editing Records
Click a row to view details, then click **Edit** or use the action menu (three dots) on the row.

### Filtering Data
Use the filter controls above tables to narrow results:

1. Click **Filters** or the filter icon
2. Select your criteria
3. Click **Apply**

### Exporting Data
Many list pages support export. Click the **Export** menu and choose:

- **Export as Excel** (`.xlsx`) - includes reference sheets and formatting
- **Export as CSV** - plain data

Exports respect the filters, search, and sorting currently applied to the
table. Import templates (**Excel Template** / **CSV Template**) download from
the same menu.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl`/`Cmd` + `B` | Toggle the sidebar |
| `Esc` | Close modal or cancel |
| `Enter` | Submit form or confirm |

Some pages add their own shortcuts — the 3D model viewer, heat map viewer, and
operator step runtime each bind keys while open.

## Mobile Access

uqmes works on tablets and mobile devices:

- Sidebar collapses to a menu icon
- Tables scroll horizontally
- Touch-friendly buttons and controls

For the best experience with data-heavy pages, we recommend using a desktop or laptop.

## Next Steps

Now that you know your way around:

- **[Your First Order](first-order.md)** - Create and track an order
- **[Glossary](glossary.md)** - Reference for terms
