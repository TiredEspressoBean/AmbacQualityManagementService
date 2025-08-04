import csv
import io
import os
import uuid

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from auditlog.models import LogEntry
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView
from django.apps import apps
from Tracker.models import Parts, Orders, PartTypes, Steps, User, Companies, Equipments, QualityReports, \
    QualityErrorsList, Processes, Documents, StepTransitionLog
from Tracker.forms import DealForm, PartTypeForm, ProcessForm, LineItemForm, LineItemFormSet, PartDocForm, \
    ErrorReportForm, PartFormSet
from django.views.decorators.clickjacking import xframe_options_exempt


@login_required
def tracker(request):
    """
    View Name: tracker

    URL Pattern:
        path('tracker/', views.tracker, name='tracker')

    Decorators:
        - @login_required

    Purpose:
        Renders a personalized tracking dashboard showing `Orders` and `Parts` relevant to the logged-in user.
        Staff users see all orders and parts, while customers see only their own.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/tracker.html

    Context:
        {
            "parts": QuerySet of Parts relevant to the user (all if staff, or filtered by ownership),
            "deals": QuerySet of Orders relevant to the user (all if staff, or filtered by customer)
        }

    Notes:
        - Authentication is required; view is gated by `@login_required`.
        - Staff users get full access to all deals and parts.
        - Customers (non-staff users) only see deals and parts assigned to them.
        - May be used as a user landing page or activity overview.

    Example:
        <a href="{% url 'tracker' %}">My Dashboard</a>
    """
    context = {}
    user = request.user
    if user.is_authenticated:
        if user.is_staff:
            parts = Parts.objects.all()
            context.update({'parts': parts})
            deals = Orders.objects.all()
            context.update({'deals': deals})
        else:
            deals = Orders.objects.filter(customer=user)
            context.update({'deals': deals})
            parts = Parts.objects.filter(order__customer=user)
            context.update({'parts': parts})
    return render(request, template_name='tracker/tracker.html', context=context)


@login_required
def part_view(request, part_id):
    """
    View Name: part_view

    URL Pattern:
        path('parts/<int:part_id>/', views.part_view, name='part_view')

    Decorators:
        None

    Purpose:
        Displays detailed information about a specific `Part`, including its customer, company,
        and the current process step.

    Parameters:
        request (HttpRequest): The HTTP request object.
        part_id (int): The ID of the part to display.

    Raises:
        Http404:
            - If the part, its customer, company, or current step cannot be found.

    Template:
        tracker/part_view.html

    Context:
        {
            "part": Parts instance,
            "customer": User instance (owner of the order associated with the part),
            "company": Companies instance (linked to the part’s order),
            "current_step": Steps instance (the part’s current step)
        }

    Notes:
        - No access control is enforced here — consider adding a permission check to ensure only staff,
          QA, or the part's owner can access this view.
        - Retrieves all related objects explicitly via `get_object_or_404` for clarity and error handling.
        - Useful for displaying real-time status, operator instructions, or audit trails for the part.

    Example:
        <a href="{% url 'part_view' part.id %}">View Part Details</a>
    """
    context = {}
    part = get_object_or_404(Parts, id=part_id)
    customer = get_object_or_404(User, id=part.order.customer_id)
    company = get_object_or_404(Companies, id=part.order.company.id)
    current_step = get_object_or_404(Steps, id=part.step_id)
    context.update({'part': part})
    context.update({'customer': customer})
    context.update({'company': company})
    context.update({'current_step': current_step})
    return render(request, 'tracker/part_view.html', context=context)


@login_required
def deal_view(request, order_id):
    """
    View Name: deal_view

    URL Pattern:
        path('orders/<int:order_id>/', views.deal_view, name='deal_view')

    Decorators:
        - @login_required

    Purpose:
        Displays the detail view of a specific `Order` (deal), along with all associated `Parts`.

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the order to display.

    Raises:
        Http404:
            - If the order does not exist.
            - If no parts are found for the order.

    Template:
        tracker/deal_view.html

    Context:
        {
            "deal": Orders instance,
            "parts": List[Parts] (all parts associated with the order)
        }

    Notes:
        - Uses `get_list_or_404` for parts, which raises a 404 if there are no parts for the order.
        - Accessible only to authenticated users — may want to further restrict based on ownership or role.
        - This view serves as a centralized summary for an order and its part progress/status.

    Example:
        <a href="{% url 'deal_view' order.id %}">View Order Details</a>
    """
    context = {}
    deal = get_object_or_404(Orders, id=order_id)
    context.update({'deal': deal})
    parts = get_list_or_404(Parts, order_id=order_id)
    context.update({'parts': parts})

    return render(request, 'tracker/deal_view.html', context=context)


@staff_member_required(login_url="login")
def edit(request):
    """
    View Name: edit

    URL Pattern:
        path('edit/', views.edit, name='edit_dashboard')

    Decorators:
        None

    Purpose:
        Renders a dashboard listing all editable models in the system, with links and descriptions
        to assist users in navigating to the appropriate model editing interface.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/edit.html

    Context:
        {
            "models": List[Dict], each containing:
                - "name": Display name of the model (e.g., "Parts"),
                - "description": Brief explanation of what the model represents or controls,
                - "model_name": Internal model identifier used in routing to edit pages
        }

    Notes:
        - This view is typically used as an entry point for staff/admin users to access CRUD interfaces.
        - Likely paired with generic editing routes (e.g., `edit_model_page`) for each model.
        - Does not restrict access by default — consider wrapping in `@staff_member_required`.

    Example:
        <a href="{% url 'edit_dashboard' %}">Edit Models</a>
    """
    editable_models = [
        {
            "name": "Parts",
            "description": "Manage individual parts, track status and assign steps.",
            "model_name": "Parts"
        },
        {
            "name": "Orders",
            "description": "Edit customer orders, their status, and linked parts.",
            "model_name": "Orders"
        },
        {
            "name": "Part Types",
            "description": "Define categories of parts with versioned changes.",
            "model_name": "PartTypes"
        },
        {
            "name": "Processes",
            "description": "Configure manufacturing processes and auto-generate steps.",
            "model_name": "Processes"
        },
        {
            "name": "Steps",
            "description": "Manage steps within processes for part tracking.",
            "model_name": "Steps"
        },
        {
            "name": "Equipments",
            "description": "Manage tools, machines, and equipment types.",
            "model_name": "Equipments"
        },
        {
            "name": "Equipment Types",
            "description": "Manage the different types of equipment.",
            "model_name": "EquipmentType"
        },
        {
            "name": "Error Types",
            "description": "Manage types of errors that may occur.",
            "model_name": "QualityErrorsList"
        },
        {
            "name": "Work Orders",
            "description": "Track and manage work orders and their associated parts.",
            "model_name": "WorkOrder"
        }
    ]

    return render(request, "tracker/edit.html", {
        "models": editable_models
    })


@staff_member_required(login_url="login")
def edit_deal(request, order_id):
    deal = get_object_or_404(Orders, id=order_id)
    order_items = Parts.objects.filter(order_id=order_id)
    customers = get_list_or_404(User, groups__name='Customers')
    companies = get_list_or_404(Companies)

    if request.method == "POST":
        # Update Orders Fields
        Orders.customer_id = request.POST.get("customer")
        Orders.estimated_completion = request.POST.get("estimated_delivery")
        Orders.save()

        # Update Orders Items
        updated_parts = request.POST.getlist("Deals_items")  # Get all selected parts

        # Remove any items that were not included in the form
        order_items.exclude(part_id__in=updated_parts).delete()

        # Add new items if necessary
        existing_parts = order_items.values_list("part_id", flat=True)
        for part_id in updated_parts:
            if int(part_id) not in existing_parts:
                part = get_object_or_404(Parts, id=part_id)
                order_items.objects.create(Deals=Orders, part=part)

        messages.success(request, "Orders updated successfully!")
        return redirect("edit_Deals", Deals_id=deal.id)  # Redirect back after saving

    return render(
        request,
        "tracker/edit_deal.html",
        {"deal": deal, "deal_items": order_items, "parts": Parts.objects.all(), "customers": customers,
         "companies": companies},
    )


@staff_member_required(login_url="login")
def edit_part(request, part_id):
    part = get_object_or_404(Parts, id=part_id)

    if request.method == "POST":
        part.name = request.POST.get('name')
        part.part_type_id = request.POST.get('part_type')
        part.step_id = request.POST.get('step')
        part.is_complete = 'is_complete' in request.POST
        part.assigned_emp_id = request.POST.get('assigned_emp') or None
        part.customer_id = request.POST.get('customer')
        part.Deals_id = request.POST.get('Orders')
        part.estimated_completion = request.POST.get('estimated_completion') or None
        part.status = request.POST.get('status')
        part.save()
        return redirect('/edit_part/' + str(part.id))

    context = {
        'part': part,
        'part_types': PartTypes.objects.all(), 'steps': Steps.objects.filter(part_type_id=part.part_type.id),
        'employees': User.objects.filter(groups__name='Employees'),
        'customers': User.objects.filter(groups__name='Customers'),
        'Dealss': Orders.objects.all(),
        'status': Parts.Status.values,
    }
    return render(request, 'tracker/edit_part.html', context)


def home(request):
    """
    View Name: home

    URL Pattern:
        path('', views.home, name='home')

    Decorators:
        None

    Purpose:
        Renders the home page of the application, including the current localized server time.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/home.html

    Context:
        {
            "current_time": datetime (localized current time)
        }

    Notes:
        - Can be used as a landing page or dashboard entry point.
        - Uses Django's `timezone.localtime()` to provide the current local server time.

    Example:
        <a href="{% url 'home' %}">Home</a>
    """

    return render(request, 'tracker/home.html', {"current_time": timezone.localtime()})


@method_decorator(staff_member_required, name='dispatch')
class qa_page(View):
    """
    View Name: qa_page

    URL Pattern:
        path('qa/', views.qa_page.as_view(), name='QA')

    Inherits:
        - django.views.View

    Decorators:
        - @staff_member_required (applied to dispatch)

    Purpose:
        Provides a QA interface for staff to view and manage all non-archived `Parts`.
        Supports pagination and allows inline actions: advancing a part's step, archiving a part,
        or redirecting to the error reporting form.

    Parameters:
        request (HttpRequest): The HTTP request object.

    GET:
        - Lists all non-archived parts, paginated (25 per page), for QA review.
        - Renders a table with ERP ID, part type, company, customer, step, and status.

    POST:
        - Handles actions for a single part, based on `part_id` and `action`:
            - `"Pass"`: Moves the part to the next step (via `increment_step()`), and logs the transition.
            - `"Error"`: Redirects to the error reporting form.
            - `"Archive"`: Archives the part with a predefined reason and logs the action.

    Raises:
        Http404: If the submitted `part_id` does not correspond to an existing part.

    Template:
        tracker/QA.html

    Context (GET):
        {
            "headers": List[str]  # Column labels for the QA table,
            "fields": List[str]   # Dot-notation field paths to render for each part,
            "rows": Page.object_list  # Paginated list of Part instances,
            "page_obj": Page  # For pagination controls,
            "table_id": str,  # Unique table identifier for the frontend,
            "href_field": str,  # Method or attribute to use for row links,
            "query": str,  # Placeholder for search queries (currently unused),
            "filter_fields": List[str],  # Not implemented here,
            "filter_values": Dict[str, List],  # Not implemented here,
            "model_name": str  # "Parts"
        }

    Notes:
        - Access is restricted to staff users.
        - The `Pass` action calls `part.increment_step()` and logs a `StepTransitionLog`.
        - The `Error` action redirects to `error_form`, preserving part context.
        - The `Archive` action uses `part.archive()` with a standard reason and notes.
        - You may want to add search/filter features in the future.

    Example Usage:
        <a href="{% url 'QA' %}">Go to QA Dashboard</a>
    """

    def get(self, request):
        parts = Parts.objects.filter(archived=False).order_by('id')

        paginator = Paginator(parts, 25)
        page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "headers": ["ERP ID", "Part Type", "Company", "Customer", "Step", "Status"],
            "fields": ["ERP_id", "part_type", "order.company.name", "order.customer", "step", "status"],
            "rows": page_obj.object_list,
            "page_obj": page_obj,
            "table_id": "qa-parts-table",
            "href_field": "get_absolute_url",
            "query": "",
            "filter_fields": [],
            "filter_values": {},
            "model_name": "Parts",
        }
        return render(request, 'tracker/QA.html', context)

    def post(self, request, *args, **kwargs):
        part = get_object_or_404(Parts, id=request.POST.get('part_id'))
        action = request.POST.get("action")

        if action == "Pass":
            try:
                result = part.increment_step()
                StepTransitionLog.objects.create(part=part, step=part.step, operator=request.user)

                if result == "completed":
                    messages.success(request, f"Part {part.ERP_id} marked as completed.")
                else:
                    messages.info(request, f"Part {part.ERP_id} moved to next step.")
            except ValueError as e:
                messages.error(request, f"Could not advance step: {str(e)}")

        elif action == "Error":
            return redirect('error_form', part_id=part.id)

        elif action == "Archive":
            part.archive(user=request.user, reason="user_error", notes="Archived via QA page")
            messages.success(request, f"Part {part.ERP_id} archived.")

        return redirect('QA')


@method_decorator(staff_member_required(login_url="login"), name='dispatch')
class ErrorFormView(FormView):
    """
    View Name: ErrorFormView

    URL Pattern:
        path('parts/<int:part_id>/report_error/', views.ErrorFormView.as_view(), name='report_error')

    Inherits:
        - django.views.generic.edit.FormView

    Decorators:
        - @staff_member_required(login_url="login") (applied via method_decorator to `dispatch`)

    Purpose:
        Provides a form interface for staff to report quality errors on a specific `Part`.
        Handles the creation of an `ErrorReport`, automatic association of selected and manually entered errors,
        and optional operator assignment based on name.

    Parameters:
        request (HttpRequest): The HTTP request object.
        part_id (int): The ID of the `Part` being reported on (passed via URL kwargs).

    Raises:
        Http404: If the part with the given ID does not exist.

    Template:
        tracker/error_form.html

    Form Class:
        ErrorReportForm

    Context:
        {
            "form": ErrorReportForm instance,
            "part": Parts instance (the part being reported on),
            "employees": QuerySet of staff Users (for operator selection/autocomplete)
        }

    Notes:
        - Only accessible by staff users.
        - Automatically associates the created report with the given part and optional operator (matched by name).
        - Combines both `errors_associated` and `errors_unassociated` fields into a single error set.
        - Appends "Other error" text input to the description if provided.
        - Shows a success message on valid submission and redirects to the part detail view.
        - Expects a clean split of operator names into [first, last]; more complex name handling may need improvement.

    Example Usage:
        <a href="{% url 'report_error' part.id %}">Report Error</a>
    """
    template_name = "tracker/error_form.html"
    form_class = ErrorReportForm

    def dispatch(self, request, *args, **kwargs):
        self.part = get_object_or_404(Parts, id=kwargs["part_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['part_type'] = self.part.part_type
        return kwargs

    def form_valid(self, form):
        operator = None
        operator_input = form.cleaned_data.get("operator", "").strip().split()
        if len(operator_input) >= 2:
            operator = User.objects.filter(
                first_name=operator_input[0],
                last_name=operator_input[-1]
            ).first()

        report = form.save(commit=False)
        report.part = self.part
        report.operator = operator

        other_error = form.cleaned_data.get("other_error", "").strip()
        if other_error:
            report.description = (report.description or "") + f"\nOther error: {other_error}"

        report.save()

        # Combine selected errors from both groups
        selected_errors = list(form.cleaned_data['errors_associated']) + list(form.cleaned_data['errors_unassociated'])
        report.errors.set(selected_errors)

        messages.success(self.request, "Error report submitted successfully.")
        return redirect("part_view", part_id=self.part.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["part"] = self.part
        context["employees"] = User.objects.filter(is_staff=True)
        return context


@staff_member_required(login_url="login")
def qa_orders(request):
    """
    View Name: qa_orders

    URL Pattern:
        path('qa/orders/', views.qa_orders, name='qa_orders')

    Decorators:
        - @staff_member_required(login_url="login")

    Purpose:
        Displays a list of all `Orders` (deals) for QA staff to review or access quality control workflows.
        Intended as the entry point to QA-specific order views.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/qa_orders.html

    Context:
        {
            "deals": QuerySet of all Orders
        }

    Notes:
        - Restricted to staff users only.
        - Consider filtering the queryset to only include active or relevant orders (e.g., not archived).
        - You may want to extend this to include additional metadata like counts of parts, status flags, or recent QA activity.

    Example:
        <a href="{% url 'qa_orders' %}">QA Orders</a>
    """
    context = {}
    deals = Orders.objects.all()
    context["deals"] = deals

    return render(request, 'tracker/qa_orders.html', context=context)


@staff_member_required(login_url="login")
def bulk_edit_parts(request, order_id):
    """
    View Name: bulk_edit_parts

    URL Pattern:
        path('orders/<int:order_id>/bulk_edit/', views.bulk_edit_parts, name='bulk_edit_parts')

    Decorators:
        - @staff_member_required(login_url="login")

    Purpose:
        Renders the bulk editing interface for parts associated with a specific `Order`.
        This view is restricted to staff users and intended to serve as an entry point for mass updates.

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the order whose parts are being edited.

    Raises:
        Http404: If the specified order does not exist.

    Template:
        tracker/bulk_edit.html

    Context:
        {
            "deal": Orders instance
        }

    Notes:
        - Access is restricted to users marked as staff in Django's admin system.
        - The actual bulk editing logic is likely handled in the frontend or via AJAX/HTMX calls from this page.
        - You may want to extend this to pre-load parts or pass additional metadata for client-side rendering.

    Example:
        <a href="{% url 'bulk_edit_parts' order.id %}">Bulk Edit Parts</a>
    """
    context = {}
    deal = get_object_or_404(Orders, id=order_id)
    context["deal"] = deal
    return render(request, 'tracker/bulk_edit.html', context=context)


def archive_deal(request, order_id):
    """
    View Name: archive_deal

    URL Pattern:
        path('orders/<int:order_id>/archive/', views.archive_deal, name='archive_deal')

    Decorators:
        None

    Purpose:
        Archives an `Order` (deal) and all associated `Parts`. This is a soft-delete approach that marks
        the deal and its parts as inactive without removing them from the database.

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the deal to be archived.

    Raises:
        Http404: If the deal does not exist.

    Template:
        None (redirects to 'deal_view' for the archived deal)

    Context:
        None

    Notes:
        - Sets the `archived` field to `True` on the `Orders` instance.
        - Also bulk-updates all `Parts` linked via `deal` to set `archived=True`.
        - The redirect still goes to `deal_view`, which may need to account for archived deals in its logic.
        - No authentication or permission checks are included—should be enforced externally.

    Example:
        <a href="{% url 'archive_deal' order.id %}">Archive Order</a>
    """
    deal = get_object_or_404(Orders, id=order_id)

    # Set deal as archived
    deal.archived = True
    deal.save()

    # Archive all related parts
    Parts.objects.filter(deal=deal).update(archived=True)

    return redirect('deal_view', order_id=deal.id)


def add_lineitem_partial(request):
    """
    View Name: add_lineitem_partial

    URL Pattern:
        path('partials/add_lineitem/', views.add_lineitem_partial, name='add_lineitem_partial')

    Decorators:
        None

    Purpose:
        Dynamically generates a new line item form row for use in a frontend formset.
        Intended for use with JavaScript or HTMX to append new form rows without a full page reload.

    Parameters:
        request (HttpRequest): The HTTP request object.

    GET Parameters:
        total_forms (int): The current number of line item forms. Used to generate a unique prefix for the new form.

    Raises:
        None

    Template:
        tracker/partials/lineitem_row.html (rendered as a string for JSON response)

    Context:
        {
            "form": LineItemForm instance with a unique prefix
        }

    Response (JsonResponse):
        {
            "html": str,        # Rendered HTML for the new form row
            "new_index": int    # Index to be used for updating TOTAL_FORMS on the frontend
        }

    Notes:
        - This view assumes that the frontend will update the management form’s TOTAL_FORMS using the `new_index` value.
        - The prefix format is `"lineitem-{index}"`, which helps Django properly group form fields server-side.
        - Compatible with HTMX or traditional JavaScript dynamic form logic.

    Example (JavaScript):
        fetch("{% url 'add_lineitem_partial' %}?total_forms=3")
            .then(response => response.json())
            .then(data => {
                document.querySelector("#lineitem-rows").insertAdjacentHTML("beforeend", data.html);
                document.querySelector("#id_lineitem-TOTAL_FORMS").value = data.new_index;
            });
    """
    total_forms = int(request.GET.get("total_forms", 0))  # Expect JS to pass current count
    form = LineItemForm(prefix=f"lineitem-{total_forms}")

    html = render_to_string("tracker/partials/lineitem_row.html", {"form": form})
    return JsonResponse({
        "html": html,
        "new_index": total_forms + 1,  # Client should update TOTAL_FORMS accordingly
    })


class BulkCreateParts(View):
    """
    View Name: BulkCreateParts

    URL Pattern:
        path('parts/bulk_create/', views.BulkCreateParts.as_view(), name='bulk_create_parts')

    Inherits:
        - django.views.View

    Purpose:
        Allows users to create multiple part line items in a single operation using a formset.
        Renders the formset on GET and processes the creation on POST.

    Parameters:
        request (HttpRequest): The HTTP request object.

    GET:
        - Renders an unbound LineItemFormSet for user input.

    POST:
        - Validates and saves each form in the LineItemFormSet.
        - Redirects after success (currently no redirect target is defined).
        - On failure, re-renders the formset with validation errors.

    Raises:
        None

    Templates:
        - GET: tracker/bulk_create_parts.html
        - POST (on error): tracker/deal_form.html (consider unifying this for consistency)

    Context:
        {
            "lineitem_formset": LineItemFormSet instance (bound or unbound)
        }

    Notes:
        - Uses `prefix="lineitem"` for formset scoping.
        - Missing a redirect target in the success branch (`redirect()` is incomplete).
        - POST logic uses `save(commit=False)` but doesn’t appear to customize `item` before saving.
        - Could be integrated into larger workflows, like bulk part import or pre-order staging.

    Example Usage:
        <a href="{% url 'bulk_create_parts' %}">Bulk Add Parts</a>
    """

    def get(self, request):
        lineitem_formset = LineItemFormSet(prefix="lineitem")
        return render(request, "tracker/bulk_create_parts.html", {
            "lineitem_formset": lineitem_formset
        })

    def post(self, request):
        lineitem_formset = LineItemFormSet(request.POST, prefix="lineitem")

        if lineitem_formset.is_valid():
            for form in lineitem_formset:
                item = form.save(commit=False)
                item.save()
            return redirect()

        return render(request, "tracker/deal_form.html", {
            "lineitem_formset": lineitem_formset,
        })


class OrderCreateView(View):
    """
    View Name: OrderCreateView

    URL Pattern:
        path('orders/new/', views.OrderCreateView.as_view(), name='order_create')

    Inherits:
        - django.views.View

    Purpose:
        Renders a form for creating a new `Order` (Deal) along with line items that generate `Parts`.
        Handles both displaying the form (GET) and processing form submission (POST).

    Parameters:
        request (HttpRequest): The HTTP request object.

    GET:
        - Renders an empty DealForm and LineItemFormSet.

    POST:
        - Expects valid DealForm and LineItemFormSet data.
        - For each line item with valid data, creates `Parts` based on quantity, part type, and process.
        - Each part gets a generated ERP ID using the part type’s ID prefix and enumeration start.

    Raises:
        None directly, but silently skips parts where:
            - Required data is missing
            - `Steps(step=1)` for the process does not exist
            - `Parts.objects.create(...)` raises an exception

    Templates:
        tracker/deal_form.html

    Context (GET and POST):
        {
            "deal_form": DealForm instance (bound or unbound),
            "lineitem_formset": LineItemFormSet instance (bound or unbound),
            "deal": None  # Used for compatibility with deal_form.html
        }

    Notes:
        - Uses `enumeration_start` to number newly created parts.
        - Automatically links each created part to the first step in the selected process.
        - ERP IDs follow the format `{ID_prefix}-{number}`, defaulting to "PART" if prefix is missing.
        - Logs part creation errors to the console with `print()` — consider using logging in production.

    Example Usage:
        <a href="{% url 'order_create' %}">Create New Order</a>
    """

    def get(self, request):
        order_form = DealForm()
        lineitem_formset = LineItemFormSet(prefix="lineitem")
        return render(request, "tracker/deal_form.html", {
            "deal_form": order_form,
            "lineitem_formset": lineitem_formset,
            "deal": None,
        })

    def post(self, request):
        order_form = DealForm(request.POST)
        lineitem_formset = LineItemFormSet(request.POST, prefix="lineitem")

        if order_form.is_valid() and lineitem_formset.is_valid():
            order = order_form.save()

            for form in lineitem_formset:
                quantity = form.cleaned_data.get("quantity")
                part_type = form.cleaned_data.get("part_type")
                process = form.cleaned_data.get("process")
                enumeration_start = form.cleaned_data.get("enumeration_start") or 1

                if quantity and part_type and process:
                    try:
                        first_step = Steps.objects.get(process=process, step=1)
                    except Steps.DoesNotExist:
                        continue

                    for i in range(quantity):
                        erp_id = f"{part_type.ID_prefix or 'PART'}-{enumeration_start + i}"
                        try:
                            Parts.objects.create(
                                ERP_id=erp_id,
                                part_type=part_type,
                                step=first_step,
                                order=order,
                            )
                        except Exception as e:
                            print(f"Error creating part {erp_id}: {e}")
                            continue

            return redirect("deal_view", order_id=order.id)

        return render(request, "tracker/deal_form.html", {
            "deal_form": order_form,
            "lineitem_formset": lineitem_formset,
            "deal": None,
        })


PART_EDIT_THRESHOLD = 200


class OrderUpdateView(View):
    """
    View Name: OrderUpdateView

    URL Pattern:
        path('orders/<int:order_id>/edit/', views.OrderUpdateView.as_view(), name='order_edit')

    Inherits:
        - django.views.View

    Purpose:
        Allows users to update an existing `Order` (formerly Deal) and its associated `Parts`.
        Depending on the number of parts, the view either renders a formset for inline editing or switches to a CSV upload mode.

    GET Parameters:
        None

    POST Parameters:
        - Order form fields from DealForm
        - Part formset fields from PartFormSet (if under threshold)
        - CSV file upload (if over threshold)

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the order to be updated.

    Raises:
        Http404: If the specified Order does not exist.

    Templates:
        tracker/deal_form.html

    Context (GET and POST):
        {
            "deal_form": DealForm instance (bound or unbound),
            "part_formset": PartFormSet instance or None,
            "lineitem_formset": LineItemFormSet (unbound),
            "use_csv": bool,  # True if CSV upload mode is used
            "deal": Order instance,
        }

    Notes:
        - Uses `PART_EDIT_THRESHOLD` to decide between inline editing vs. CSV upload mode.
        - CSV upload logic is currently stubbed out and should be implemented under the POST flow.
        - Assumes authenticated access but does not enforce it via decorator — ensure proper URL protection.
        - Uses `LineItemFormSet` for dynamic line item creation, rendered even if part_formset is not shown.

    Example Usage:
        <a href="{% url 'order_edit' order.id %}">Edit Order</a>
    """

    def get(self, request, order_id):
        order = get_object_or_404(Orders, pk=order_id)
        order_form = DealForm(instance=order)
        parts_qs = Parts.objects.filter(order=order, archived=False)
        lineitem_formset = LineItemFormSet(prefix="lineitem")

        if parts_qs.count() <= PART_EDIT_THRESHOLD:
            part_formset = PartFormSet(queryset=parts_qs)
            use_csv = False
        else:
            part_formset = None
            use_csv = True

        return render(request, "tracker/deal_form.html", {
            "deal_form": order_form,
            "part_formset": part_formset,
            "lineitem_formset": lineitem_formset,
            "use_csv": use_csv,
            "deal": order,
        })

    def post(self, request, order_id):
        lineitem_formset = LineItemFormSet(prefix="lineitem")
        order = get_object_or_404(Orders, pk=order_id)
        order_form = DealForm(request.POST, instance=order)
        parts_qs = Parts.objects.filter(order=order, archived=False)

        # Handle CSV if part count is high
        if parts_qs.count() > PART_EDIT_THRESHOLD:
            if order_form.is_valid():
                order_form.save()
                # Handle CSV upload (stub for now)
                if "csv_file" in request.FILES:
                    # Handle CSV parsing logic here
                    pass
                return redirect("deal_view", order_id=order.id)
            return render(request, "tracker/deal_form.html", {
                "deal_form": order_form,
                "use_csv": True,
                "deal": order,
            })

        # Inline formset flow
        part_formset = PartFormSet(request.POST, queryset=parts_qs)

        if order_form.is_valid() and part_formset.is_valid() and lineitem_formset.is_valid():
            order_form.save()
            part_formset.save()

            for form in lineitem_formset:
                quantity = form.cleaned_data.get("quantity")
                part_type = form.cleaned_data.get("part_type")
                process = form.cleaned_data.get("process")
                enumeration_start = form.cleaned_data.get("enumeration_start") or 1

                if quantity and part_type and process:
                    try:
                        first_step = Steps.objects.get(process=process, step=1)
                    except Steps.DoesNotExist:
                        continue

                    for i in range(quantity):
                        erp_id = f"{part_type.ID_prefix or 'PART'}-{enumeration_start + i}"
                        try:
                            Parts.objects.create(
                                ERP_id=erp_id,
                                part_type=part_type,
                                step=first_step,
                                order=order,
                            )
                        except Exception as e:
                            print(f"Error creating part {erp_id}: {e}")
                            continue

            return redirect("deal_view", order_id=order.id)

        return render(request, "tracker/deal_form.html", {
            "deal_form": order_form,
            "part_formset": part_formset,
            "use_csv": False,
            "deal": order,
        })


def add_parttype_partial(request):
    """
    View Name: add_parttype_partial

    URL Pattern:
        path('partials/add_parttype/', views.add_parttype_partial, name='add_parttype_partial')

    Decorators:
        None

    Purpose:
        Handles GET and POST requests to dynamically add a new `PartType` via an inline form.
        Intended for HTMX-based UIs that support adding new part types without reloading the page.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Templates:
        - GET: tracker/partials/parttype_row.html (returns a blank form)
        - POST:
            - On success:
                - If HTMX: returns a new blank form and sets `HX-Trigger: refresh-lineitems`
                - Else: redirects to `deal_form`
            - On failure: re-renders form with validation errors

    Context:
        {
            "form": PartTypeForm instance (bound or unbound)
        }

    Notes:
        - GET request returns a blank form with a unique prefix for form management.
        - POST request must include the correct prefix to properly bind and validate the form.
        - If the form is valid and submitted via HTMX, a new blank form is returned and `refresh-lineitems` is triggered.
        - If not an HTMX request, redirects to the fallback view (`deal_form`).
        - Designed to support progressive part type creation in deal workflows.

    Example (HTMX):
        <button hx-get="{% url 'add_parttype_partial' %}" hx-target="#parttype-rows" hx-swap="beforeend">
            Add Part Type
        </button>
    """
    if request.method == "GET":
        # Regular GET -> render a blank form (to add a new one dynamically)
        form = PartTypeForm(prefix=f"parttype-{uuid.uuid4().hex[:6]}")
        return render(request, "tracker/partials/parttype_row.html", {"form": form})

    elif request.method == "POST":
        form = PartTypeForm(request.POST, prefix=request.POST.get("prefix"))

        if form.is_valid():
            parttype = form.save()

            if request.headers.get('Hx-Request'):
                new_form = PartTypeForm(prefix=f"parttype-{uuid.uuid4().hex[:6]}")
                response = render(request, "tracker/partials/parttype_row.html", {"form": new_form})
                response["HX-Trigger"] = "refresh-lineitems"
                return response
            else:
                # Regular POST fallback
                return redirect("deal_form")

        else:
            # Form invalid: return the form with errors
            return render(request, "tracker/partials/parttype_row.html", {"form": form})


def add_process_partial(request):
    """
    View Name: add_process_partial

    URL Pattern:
        path('partials/add_process/', views.add_process_partial, name='add_process_partial')

    Decorators:
        None

    Purpose:
        Handles both GET and POST requests for dynamically adding a new `Process` via an inline form.
        Used in HTMX-driven interfaces to add process rows without a full page reload.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Templates:
        - GET: tracker/partials/process_row.html (renders a blank process form)
        - POST:
            - On valid submission:
                - If HTMX, returns a new blank form row and triggers `refresh-lineitems`
                - If not HTMX, redirects to 'deal_form'
            - On invalid submission: re-renders the form with errors

    Context:
        {
            "form": ProcessForm instance (bound or unbound)
        }

    Notes:
        - GET requests return a new form with a unique prefix (required for formsets or dynamic behavior).
        - POST requests must include the prefix in the payload to properly bind and validate the form.
        - On success, the `generate_steps()` method is called on the saved Process object.
        - If triggered via HTMX, the view returns a fresh blank row and sets `"HX-Trigger": "refresh-lineitems"` in the response header.

    Example (HTMX):
        <button hx-get="{% url 'add_process_partial' %}" hx-target="#process-rows" hx-swap="beforeend">
            Add Process
        </button>
    """
    if request.method == "GET":
        form = ProcessForm(prefix=f"process-{uuid.uuid4().hex[:6]}")  # <-- fixed the wrong prefix
        return render(request, "tracker/partials/process_row.html", {"form": form})

    elif request.method == "POST":
        form = ProcessForm(request.POST, prefix=request.POST.get("prefix"))

        if form.is_valid():
            process = form.save()
            process.generate_steps()

            if request.headers.get('Hx-Request'):
                new_form = ProcessForm(prefix=f"process-{uuid.uuid4().hex[:6]}")
                response = render(request, "tracker/partials/process_row.html", {"form": new_form})
                response["HX-Trigger"] = "refresh-lineitems"
                return response
            else:
                return redirect("deal_form")

        else:
            return render(request, "tracker/partials/process_row.html", {"form": form})


def parttype_select_partial(request):
    """
    View Name: process_select_partial

    URL Pattern:
        path('partials/process_select/', views.process_select_partial, name='process_select_partial')

    Decorators:
        None

    Purpose:
        Renders a partial HTML snippet containing all `Processes` as `<option>` elements.
        Typically used to dynamically populate a `<select>` input via HTMX or AJAX.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/partials/process_select_options.html

    Context:
        {
            "processes": QuerySet of all Process instances
        }

    Notes:
        - Intended for use in dynamic form rendering or field refreshes.
        - Does not filter or paginate—returns all Process records.
        - Ensure this is called via an HTMX request or embedded into a form with proper context.

    Example (HTMX):
        <select id="process-select" hx-get="{% url 'process_select_partial' %}" hx-trigger="load" hx-swap="innerHTML">
            <!-- options will be populated here -->
        </select>
    """
    part_types = PartTypes.objects.all()
    return render(request, "tracker/partials/parttype_select_options.html", {"part_types": part_types})


def process_select_partial(request):
    def process_select_partial(request):
        """
        View Name: process_select_partial

        URL Pattern:
            path('partials/process_select/', views.process_select_partial, name='process_select_partial')

        Decorators:
            None

        Purpose:
            Renders a partial HTML snippet containing all `Processes` as `<option>` elements.
            Typically used to dynamically populate a `<select>` input via HTMX or AJAX.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Raises:
            None

        Template:
            tracker/partials/process_select_options.html

        Context:
            {
                "processes": QuerySet of all Process instances
            }

        Notes:
            - Intended for use in dynamic form rendering or field refreshes.
            - Does not filter or paginate—returns all Process records.
            - Ensure this is called via an HTMX request or embedded into a form with proper context.

        Example (HTMX):
            <select id="process-select" hx-get="{% url 'process_select_partial' %}" hx-trigger="load" hx-swap="innerHTML">
                <!-- options will be populated here -->
            </select>
        """

    processes = Processes.objects.all()
    return render(request, "tracker/partials/process_select_options.html", {"processes": processes})


def refresh_parttype_process_selects(request):
    def refresh_parttype_process_selects(request):
        """
        View Name: refresh_parttype_process_selects

        URL Pattern:
            path('partials/refresh_lineitems/', views.refresh_parttype_process_selects, name='refresh_parttype_process_selects')

        Decorators:
            None

        Purpose:
            Renders the line item formset partial with fresh select fields. Typically used to dynamically refresh
            part type or process dropdowns in a line item table (e.g., via HTMX or AJAX).

        Parameters:
            request (HttpRequest): The HTTP request object.

        Raises:
            None

        Template:
            tracker/partials/lineitem_table.html

        Context:
            {
                "lineitem_formset": A new LineItemFormSet instance with prefix="lineitem"
            }

        Notes:
            - Does not depend on request method—always returns a newly initialized formset.
            - Likely intended for use in dynamic frontend updates (e.g., updating select options when a parent field changes).
            - This view assumes no initial data; existing line items must be handled separately.

        Example (HTMX):
            <button hx-get="{% url 'refresh_parttype_process_selects' %}" hx-target="#lineitem-table" hx-swap="outerHTML">
                Refresh Line Items
            </button>
        """

    lineitem_formset = LineItemFormSet(prefix="lineitem")
    return render(request, "tracker/partials/lineitem_table.html", {
        "lineitem_formset": lineitem_formset,
    })


@staff_member_required(login_url="login")
def upload_part_doc(request):
    """
    View Name: upload_part_doc

    URL Pattern:
        path('documents/upload/', views.upload_part_doc, name='upload_part_doc')

    Decorators:
        None

    Purpose:
        Handles the upload of a new `Document` related to a `Part`. Uses a form to accept file uploads
        and metadata, then saves the document with the current user as the uploader.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Raises:
        None

    Template:
        tracker/part_doc_upload.html

    Context:
        {
            "form": PartDocForm instance (bound or unbound depending on request method)
        }

    Notes:
        - On successful POST and form validation, redirects to the document list view (`list_part_docs`).
        - The form must support file uploads (use `enctype="multipart/form-data"`).
        - Sets `uploaded_by` to the currently authenticated user.
        - Does not include authentication or permissions in this view itself—must be enforced externally if needed.

    Example:
        <form action="{% url 'upload_part_doc' %}" method="post" enctype="multipart/form-data">
            {% csrf_token %}
            {{ form.as_p }}
            <button type="submit">Upload</button>
        </form>
    """

    if request.method == 'POST':
        form = PartDocForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
            return redirect('list_part_docs')
    else:
        form = PartDocForm()

    return render(request, 'tracker/part_doc_upload.html', {'form': form})


def list_part_docs(request):
    """
    View Name: list_part_docs

    URL Pattern:
        path('documents/', views.list_part_docs, name='list_part_docs')

    Decorators:
        None

    Purpose:
        Displays a list of all `Documents` in the system, with optional filtering by associated `Part`.

    Parameters:
        request (HttpRequest): The HTTP request object.

    GET Parameters:
        part (int, optional): The ID of the `Part` to filter documents by.

    Raises:
        None

    Template:
        tracker/part_doc_list.html

    Context:
        {
            "docs": QuerySet of Document instances, optionally filtered by part_id
        }

    Notes:
        - If `?part=<id>` is included in the query string, only documents linked to that part are shown.
        - This view is unauthenticated unless protected by the URL conf or middleware.

    Example:
        <a href="{% url 'list_part_docs' %}?part=42">View Documents for Part 42</a>
    """
    docs = Documents.objects.all()

    # Optional filter by part
    part_id = request.GET.get('part')
    if part_id:
        docs = docs.filter(part_id=part_id)

    return render(request, 'tracker/part_doc_list.html', {'docs': docs})


def export_parts_csv(request, order_id):
    """
    View Name: export_parts_csv

    URL Pattern:
        path('orders/<int:order_id>/export_parts_csv/', views.export_parts_csv, name='export_parts_csv')

    Decorators:
        None

    Purpose:
        Exports all non-archived `Parts` associated with a given `Order` as a CSV file for download.

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the order whose parts should be exported.

    Raises:
        None

    Template:
        None (returns a streamed CSV file via HttpResponse)

    Context:
        None

    Notes:
        - Filters out archived parts automatically.
        - The CSV includes columns: `ERP_id`, `part_type_id`, `step_id`, `status`.
        - Sets the `Content-Disposition` header to trigger a file download with a filename format like `order_123_parts.csv`.

    Example:
        <a href="{% url 'export_parts_csv' order.id %}">Download Parts CSV</a>
    """
    parts = Parts.objects.filter(order_id=order_id, archived=False)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="order_{order_id}_parts.csv"'

    writer = csv.writer(response)
    writer.writerow(["ERP_id", "part_type_id", "step_id", "status"])

    for part in parts:
        writer.writerow([
            part.ERP_id,
            part.part_type_id,
            part.step_id,
            part.status
        ])

    return response


def upload_parts_csv(request, order_id):
    """
    View Name: upload_parts_csv

    URL Pattern:
        path('orders/<int:order_id>/upload_parts_csv/', views.upload_parts_csv, name='upload_parts_csv')

    Decorators:
        None

    Purpose:
        Handles CSV uploads for bulk-updating `Parts` linked to a specific `Orders` instance. Each row in the CSV
        must contain valid `ERP_id`, `part_type_id`, `step_id`, and `status` fields.

    Parameters:
        request (HttpRequest): The HTTP request object.
        order_id (int): The ID of the order to which the parts belong.

    Raises:
        Http404: If the specified Order does not exist.

    Template:
        None (redirects to 'deal_view' after processing)

    Context:
        None

    Notes:
        - Only processes the CSV if the request method is POST and contains a file under the key "csv_file".
        - Expects the CSV to have columns: `ERP_id`, `part_type_id`, `step_id`, and `status`.
        - Silently skips rows where `Parts` with the given `ERP_id` and `order` do not exist.
        - Does not perform validation beyond simple existence and ID assignment.
        - Can be used in a form with enctype="multipart/form-data".

    Example:
        <form action="{% url 'upload_parts_csv' order.id %}" method="post" enctype="multipart/form-data">
            {% csrf_token %}
            <input type="file" name="csv_file">
            <button type="submit">Upload</button>
        </form>
    """
    order = get_object_or_404(Orders, pk=order_id)

    if request.method == "POST" and "csv_file" in request.FILES:
        file = request.FILES["csv_file"]
        decoded_file = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded_file))

        for row in reader:
            try:
                part = Parts.objects.get(order=order, ERP_id=row["ERP_id"])
                part.part_type_id = row["part_type_id"]
                part.step_id = row["step_id"]
                part.status = row["status"]
                part.save()
            except Parts.DoesNotExist:
                continue  # Skip invalid ERP IDs

    return redirect("deal_view", order_id=order.id)


@login_required
def generic_table_view(request, model_name):
    """
    View Name: generic_table_view

    URL Pattern:
        path('table/<str:model_name>/', views.generic_table_view, name='generic_table_view')

    Decorators:
        - @login_required

    Purpose:
        Dynamically renders a paginated, searchable, and optionally filterable table view for a specified model,
        based on a predefined configuration. Designed for reuse across many models with a common UI layout.

    Parameters:
        request (HttpRequest): The HTTP request object.
        model_name (str): The name of the model to render in table form. Must exist in the CONFIG dict.

    Raises:
        Http404: If the model is not configured or invalid.

    Template:
        tracker/partials/generic_table.html

    Context:
        {
            "headers": List[str],               # Table headers
            "fields": List[str],                # Fields to display in the table rows
            "rows": QuerySet,                   # Paginated queryset of model instances
            "page_obj": Page,                   # Paginator object for rendering pagination controls
            "table_id": str,                    # A unique table ID used in HTML
            "link_prefix": str,                 # Prefix used for row links/actions
            "query": str,                       # The current search query string
            "filter_fields": List[str],         # List of fields with dropdown filters
            "filter_values": Dict[str, List],   # Values for filter dropdowns
            "model_name": str,                  # The name of the model being displayed
            "qa_mode": bool,                    # Whether the QA row actions should be shown
            "edit_mode": bool,                  # Whether edit row actions should be shown
            "row_actions": str|None,            # Partial template for row action buttons
        }

    Notes:
        - Access is restricted to authenticated users.
        - Non-staff users can only see their own Orders or Parts, if applicable.
        - Supports optional query filtering via `q` GET parameter and multiple field filters.
        - Uses different row action templates depending on `qa_mode` or `edit_mode` GET parameters.
        - Relies on a predefined CONFIG dictionary mapping model names to rendering details.

    Example:
        <a href="{% url 'generic_table_view' 'Parts' %}?q=123&status=Active&qa_mode=true">Filtered Parts Table</a>
    """
    # Support either 'ModelName' or 'app_label.ModelName'
    if '_' in model_name:
        app_label, model_str = model_name.split('_', 1)
    else:
        app_label = 'Tracker'  # default app
        model_str = model_name

    try:
        Model = apps.get_model(app_label, model_str)
    except LookupError:
        raise Http404("Model not found.")

    CONFIG = {
        "auditlog_logentry": {
            "headers": ["Timestamp", "Actor Email", "Action", "Object", "Changes", "Remote IP"],
            "fields": ["timestamp", "actor_email", "action", "object_repr", "changes_text", "remote_addr"],
            "link_prefix": "auditlog_logentry",
            "search_fields": [
                "actor_email",
                "object_repr",
                "changes_text",
                "remote_addr",
                "action",
                "additional_data"
            ],
            "filter_fields": ["action", "actor_email"]
        },
        "Orders": {
            "headers": ["Name", "Estimated Completion", "Status"],
            "fields": ["name", "estimated_completion", "status"],
            "link_prefix": "Orders",
            "search_fields": ["name", "status"],
            "filter_fields": ["status"]
        },
        "Parts": {
            "headers": ["ERP ID", "Part Type", "Step", "Status"],
            "fields": ["ERP_id", "part_type", "step", "status"],
            "link_prefix": "Parts",
            "search_fields": ["ERP_id", "status", "part_type__name"],
            "filter_fields": ["status", "part_type__name"]
        },
        "Documents": {
            "headers": ["File Name", "File", "Part", "Upload Date", "Uploaded By"],
            "fields": ["file_name", "file", "part", "upload_date", "uploaded_by"],
            "link_prefix": "Documents",
            "search_fields": ["file_name", "file", "part__part_type__ID_prefix", "part__part_type__name",
                              "part__order__name", "uploaded_by__first_name", "uploaded_by__last_name",
                              "uploaded_by__email", "uploaded_by__username"],
        },
        "WorkOrder": {
            "headers": ["ERP ID", "Operator", "Related Order", "Status", "Expected Completion"],
            "fields": ["ERP_id", "operator", "related_order", "status", "expected_completion"],
            "link_prefix": "WorkOrder",
            "search_fields": ["ERP_id", "operator__username", "related_order__name", "status"],
            "filter_fields": ["status", "operator__username"]
        },
        "PartTypes": {
            "headers": ["Name", "Updated Last", "Glovia ID Prefix"],
            "fields": ["name", "updated_at", "ID_prefix"],
            "link_prefix": "PartTypes",
            "search_fields": ["Name", "ID_prefix"],
        },
        "QualityErrorsList": {
            "headers": ["Error Name", "Error Example", "Part Type"],
            "fields": ["error_name", "error_example", "part_type"],
            "link_prefix": "QualityErrorsList",
            "search_fields": ["error_name", "error_example", "part_type__name"],
        },
        "Processes": {
            "headers": ["Name", "Remanufactured Process", "Number of Steps", "Version", "Part Type"],
            "fields": ["name", "is_remanufactured", "num_steps", "version", "part_type__name"],
            "link_prefix": "Processes",
            "search_fields": ["name", "num_steps", "version", "part_type__name", ],
        },
        "Equipments": {
            "headers": ["Name", "Equipment Type"],
            "fields": ["name", "equipment_type__name"],
            "link_prefix": "Equipments",
            "search_fields": [],
        },
        "EquipmentType": {
            "headers": ["Name"],
            "fields": ["name"],
            "link_prefix": "EquipmentType",
            "search_fields": ["name"],
        },
        "Steps": {
            "headers": ["Step", "Part Type", "Process"],
            "fields": ["step", "part_type__name", "process__name"],
            "link_prefix": "Steps",
            "search_fields": ["part_type__name", "process__name"],
        }
    }

    if model_name not in CONFIG:
        raise Http404("Unknown model.")

    config = CONFIG[model_name]

    qs = Model.objects.all().order_by("id")

    # Only show non-archived items if applicable
    if "archived" in [field.name for field in Model._meta.fields]:
        qs = qs.filter(archived=False)

    # Restrict customer visibility
    if not request.user.is_staff:
        if model_name == "Orders":
            qs = qs.filter(customer=request.user)
        elif model_name == "Parts":
            qs = qs.filter(order__customer=request.user)
        else:
            return Http404("Unknown model.")

    # Search
    query = request.GET.get("q", "")
    if query:
        q_filter = Q()
        for field in config["search_fields"]:
            q_filter |= Q(**{f"{field}__icontains": query})
        qs = qs.filter(q_filter)

    # Filters
    for field in config.get("filter_fields", []):
        value = request.GET.get(field)
        if value:
            qs = qs.filter(**{field: value})

    # Filter values for dropdowns
    filter_values = {}
    for field in config.get("filter_fields", []):
        try:
            values = Model.objects.order_by().values_list(field, flat=True).distinct()
            filter_values[field] = [v for v in values if v is not None]
        except Exception:
            filter_values[field] = []

    sort = request.GET.get("sort")
    direction = request.GET.get("direction", "asc")

    if sort and sort in config["fields"]:
        if direction == "desc":
            qs = qs.order_by(f"-{sort}")
        else:
            qs = qs.order_by(sort)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Modes
    qa_mode = request.GET.get("qa_mode") == "true"
    edit_mode = request.GET.get("edit_mode") == "true"

    header_field_pairs = list(zip(
        config["headers"] + ["Actions"] if (qa_mode or edit_mode) else config["headers"],
        config["fields"] + [""] if (qa_mode or edit_mode) else config["fields"]
    ))

    context = {
        "header_field_pairs": header_field_pairs,
        "headers": config["headers"] + ["Actions"] if (qa_mode or edit_mode) else config["headers"],
        "fields": config["fields"],
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "table_id": f"{model_name.lower()}-table",
        "link_prefix": config.get("link_prefix"),
        "query": query,
        "filter_fields": config.get("filter_fields", []),
        "filter_values": filter_values,
        "model_name": model_name,
        "qa_mode": qa_mode,
        "edit_mode": edit_mode,
        "row_actions": (
            "tracker/partials/qa_row_actions.html" if qa_mode == True
            else "tracker/partials/edit_row_actions.html" if edit_mode == True
            else None
        )
    }

    return render(request, "tracker/partials/generic_table.html", context)


def get_client_ip(request):
    """Utility to safely extract the client IP address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")

@xframe_options_exempt
@staff_member_required(login_url="login")
def download_file(request, model_name, pk, field):
    """
    View Name: download_file

    URL Pattern:
        path('admin/download/<str:model_name>/<int:pk>/<str:field>/', views.download_file, name='download_file')

    Decorators:
        - @staff_member_required(login_url="login)

    Purpose:
        Securely allows staff members to download a file associated with a specific model instance and field.

    Parameters:
        request (HttpRequest): The HTTP request object.
        model_name (str): The name of the model in the 'Tracker' app.
        pk (int): The primary key of the model instance.
        field (str): The name of the file field on the model instance.

    Raises:
        Http404: If the model is invalid, the object does not exist, the field is missing, or the file is not found.

    Template:
        None (returns a FileResponse)

    Context:
        None

    Notes:
        - Only accessible by staff.
        - Assumes the field is a `FileField` or similar and has a valid `.path` attribute.
        - The model must be registered in the "Tracker" app.

    Example:
        <a href="{% url 'download_file' 'PartTypes' 123 'document' %}">Download Spec</a>
    """
    Model = apps.get_model("Tracker", model_name)
    if not Model:
        raise Http404("Invalid model")

    obj = get_object_or_404(Model, pk=pk)

    file_field = getattr(obj, field, None)
    if not file_field or not hasattr(file_field, "path") or not os.path.exists(file_field.path):
        raise Http404("File not found")

    # ✅ Log the download
    try:
        LogEntry.objects.create(
            actor=request.user,
            actor_email=request.user.email if request.user.is_authenticated else None,
            action=LogEntry.Action.ACCESS,
            content_type=ContentType.objects.get_for_model(type(obj), for_concrete_model=False),  # ✅ THIS LINE FIXES IT
            object_pk=str(obj.pk),
            object_id=obj.pk,
            object_repr=str(obj),
            timestamp=now(),
            remote_addr=get_client_ip(request),
            changes_text=f"Downloaded file from field '{field}'",
            changes={"downloaded": True},
            additional_data={
                "filename": file_field.name,
                "field": field,
                "model": model_name,
            }
        )
    except Exception as e:
        print(f"Failed to log download: {e}")

    return FileResponse(open(file_field.path, "rb"), as_attachment=True, filename=os.path.basename(file_field.name))


@staff_member_required(login_url="login")
def edit_model_page(request, model_name):
    """
    View Name: edit_model_page

    URL Pattern:
        path('admin/edit/<str:model_name>/', views.edit_model_page, name='edit_model_page')

    Decorators:
        - @staff_member_required(login_url="login)

    Purpose:
        Renders a generic edit page for staff to modify certain allowed models.

    Parameters:
        request (HttpRequest): The HTTP request object.
        model_name (str): The name of the model to edit. Must be in allowed_models.

    Raises:
        Http404: If model_name is not in the allowed list.

    Template:
        tracker/generics/generic_edit_page.html

    Context:
        {
            "model_name": model_name
        }

    Notes:
        - Only accessible by staff members.
        - Likely intended to be extended with JavaScript or HTMX for CRUD functionality.

    Example:
        <a href="{% url 'edit_model_page' 'Parts' %}">Edit Parts</a>
    """
    allowed_models = ["Parts", "Orders", "PartTypes", "Processes", "Steps", "Equipments", "QualityErrorsList",
                      "EquipmentType", "WorkOrder", "auditlog_logentry"]
    if model_name not in allowed_models:
        raise Http404("Invalid model")

    return render(request, "tracker/generics/generic_edit_page.html", {"model_name": model_name})


def deal_pass(request, order_id):
    order = get_object_or_404(Orders, pk=order_id)
    parts = Parts.objects.filter(order_id=order.pk)
    for part in parts:
        part.increment_step()
    return redirect("qa_orders")

def history(request):
    return render(request, "tracker/history.html")