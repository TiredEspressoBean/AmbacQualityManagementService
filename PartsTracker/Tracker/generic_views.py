from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.apps import apps


@method_decorator(staff_member_required, name='dispatch')
class GenericCreateEntry(CreateView):
    """
    GenericCreateEntry
    ------------------

    A generic admin-only view for dynamically rendering and handling a model creation form
    for any model in the Tracker app. Enables rapid form generation and submission for
    CRUD pages without requiring individual views per model.

    This view is secured via `@staff_member_required` to restrict access to authorized users.

    URL Pattern:
        /create/<str:model_name>/

    Template:
        tracker/generics/generic_create.html

    Context:
        - model_verbose_name: Human-readable model name used in the page heading.
        - form: Dynamically constructed model form.
    """

    template_name = 'tracker/generics/generic_create.html'
    model = None  # Set dynamically based on the model_name in the URL

    def dispatch(self, request, *args, **kwargs):
        """
        Overrides dispatch to dynamically assign the model class based on the `model_name` parameter
        in the URL. Raises Http404 if the model is not found in the Tracker app.

        Parameters:
            request (HttpRequest): The incoming HTTP request.
            args: Additional positional arguments.
            kwargs: Dictionary containing 'model_name'.

        Returns:
            HttpResponse: Result of calling the parent dispatch method.
        """
        model_name = kwargs.get('model_name')
        try:
            self.model = apps.get_model("Tracker", model_name)
        except LookupError:
            raise Http404(f"Model '{model_name}' not found.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        """
        Dynamically generates a ModelForm for the selected model using all fields.

        Returns:
            ModelForm class
        """
        return modelform_factory(self.model, fields="__all__")

    def get_form(self, form_class=None):
        """
        Overrides form generation to apply custom CSS classes to all widgets
        using the `map_generic_form_input_styles()` utility function.

        Parameters:
            form_class (ModelForm): Optional form class.

        Returns:
            Form instance with styled widgets.
        """
        form = super().get_form(form_class)
        for field in form.fields.values():
            css_classes = map_generic_form_input_styles(field)
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css_classes}".strip()
        return form

    def get_success_url(self):
        """
        Determines the redirection target after a successful form submission.
        Defaults to the HTTP Referer if available; otherwise, redirects to
        the model's edit page.

        Returns:
            str: URL to redirect to.
        """
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return referer
        # Fallback if no referer is found
        return reverse_lazy('edit_model_page', kwargs={'model_name': self.model.__name__})

    def form_valid(self, form):
        """
        Called when submitted form is valid. Saves the object and redirects to the success URL.

        Parameters:
            form (ModelForm): Valid form instance.

        Returns:
            HttpResponseRedirect: Redirect to success URL.
        """
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        """
        Injects the model's verbose name into the context for use in templates.

        Parameters:
            kwargs: Additional context variables.

        Returns:
            dict: Template context with verbose model name.
        """
        context = super().get_context_data(**kwargs)
        context["model_verbose_name"] = self.model._meta.verbose_name.title()
        return context


class GenericUpdateEntry(UpdateView):
    """
    GenericUpdateEntry
    ------------------

    A generic staff-only view for editing any model instance from the Tracker app.
    Dynamically loads the model and the object by primary key, and renders a styled form
    for editing all fields.

    URL Pattern:
        /update/<str:model_name>/<int:pk>/

    Template:
        tracker/generics/generic_update.html

    Context:
        - model_verbose_name: Human-readable model name.
        - object_display: String representation of the object being edited.
        - form: Model form for editing.
    """

    template_name = 'tracker/generics/generic_update.html'

    def get_context_data(self, **kwargs):
        """
        Adds model metadata and display string to the context for template rendering.

        Returns:
            dict: Context with verbose name and object display string.
        """
        context = super().get_context_data(**kwargs)

        # Safe check for object and its model metadata
        obj = self.get_object()
        context["model_verbose_name"] = obj._meta.verbose_name.title()
        context["object_display"] = str(obj)

        return context

    def get_form(self, form_class=None):
        """
        Applies consistent CSS classes to form fields using the styling utility.

        Parameters:
            form_class (ModelForm): Optional form class.

        Returns:
            Form instance with styled fields.
        """
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            existing_classes = map_generic_form_input_styles(field)
            field.widget.attrs['class'] = existing_classes
        return form

    def get_form_class(self):
        """
        Dynamically generates the form class using the model specified in the URL.

        Returns:
            ModelForm class for the selected model.
        """
        model_name = self.kwargs.get('model_name')
        model = apps.get_model("Tracker", model_name)

        if not model:
            raise Http404(f"Model '{model_name}' not found.")

        return modelform_factory(model, fields="__all__")

    def get_success_url(self):
        """
        Redirects to the main edit dashboard after successful update.

        Returns:
            str: URL to redirect to.
        """
        return reverse_lazy('edit')

    def get_queryset(self):
        """
        Provides the queryset restricted to the object being edited by its primary key.

        Returns:
            QuerySet: Queryset containing only the target object.
        """
        model_name = self.kwargs.get('model_name')
        model = apps.get_model("Tracker", model_name)

        if not model:
            raise Http404(f"Model '{model_name}' not found.")

        # This assumes you're trying to fetch an object by its primary key.
        pk = self.kwargs.get('pk')
        return model.objects.filter(pk=pk)

    def form_valid(self, form):
        """
        Saves the updated object and redirects to the edit dashboard.

        Parameters:
            form (ModelForm): Valid form instance.

        Returns:
            HttpResponseRedirect: Redirect to success URL.
        """
        form.save()
        # Now redirect to the success URL (edit page)
        return redirect(self.get_success_url())


def GenericDeleteEntry(request, model_name, pk):
    """
    GenericDeleteEntry
    ------------------

    A generic view for deleting a model instance dynamically by model name and primary key.
    Intended for use in HTMX-enabled interfaces but also works with regular requests.

    Parameters:
        request (HttpRequest): The incoming request.
        model_name (str): The name of the model to delete from the 'Tracker' app.
        pk (int): The primary key of the instance to delete.

    Returns:
        HttpResponse:
            - 204 No Content if the request is an HTMX call (client-side handles removal).
            - 200 OK with a success message if a regular request.
            - Raises 404 if the model or object is not found.
    """

    try:
        Model = apps.get_model("Tracker", model_name)
        obj = Model.objects.get(pk=pk)
    except Exception:
        raise Http404("Object not found")

    obj.delete()

    if request.headers.get("Hx-Request"):
        return HttpResponse(status=204)  # HTMX: remove row or element via JS
    return HttpResponse("Deleted successfully.")


@method_decorator(login_required, name='dispatch')
class GenericViewEntry(DetailView):
    """
    GenericViewEntry
    ----------------

    A generic read-only detail view for displaying a model instance dynamically based
    on the model name and primary key provided in the URL.

    Requires the user to be logged in.

    URL Params:
        model_name (str): The name of the model class in the 'Tracker' app.
        pk (int): The primary key of the instance to view.

    Template:
        tracker/generics/generic_view.html

    Context:
        fields (list of tuples): Each tuple includes:
            - Field label (str)
            - Field value (str or URL)
            - Boolean flag indicating if the value is downloadable
            - Field name (used for download links, if applicable)
        model_name (str): Lowercase model name (used for template logic or links)
    """

    template_name = 'tracker/generics/generic_view.html'

    def get_model(self):
        """
        Retrieves the model class dynamically from the 'Tracker' app using the model_name from URL.
        Raises 404 if not found.
        """
        model_name = self.kwargs.get('model_name')
        model = apps.get_model("Tracker", model_name)
        if not model:
            raise Http404(f"Model '{model_name}' not found.")
        return model

    def get_queryset(self):
        """
        Returns a queryset containing only the instance with the specified primary key.
        """
        model = self.get_model()
        pk = self.kwargs.get('pk')
        return model.objects.filter(pk=pk)

    def get_context_data(self, **kwargs):
        """
        Builds the context for rendering the detail template. Dynamically extracts
        and formats each field from the object.
        """
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        fields = []
        for field in obj._meta.fields:
            label = field.verbose_name.title()
            raw_value = getattr(obj, field.name)

            if hasattr(raw_value, "url"):
                # Field is likely a FileField or ImageField
                fields.append((
                    label,
                    raw_value.url,
                    True,  # is_downloadable
                    field.name
                ))
            else:
                # Try to use get_<field>_display if available (for choices)
                value = getattr(obj, f"get_{field.name}_display", lambda: raw_value)()
                fields.append((label, value, False, None))

        model_name = obj._meta.model_name
        context["fields"] = fields
        context["model_name"] = model_name

        # Enable HTMX table view for specific models
        if model_name in ["orders", "processes"]:
            model_name = "Orders" if model_name == "orders" else "Processes"
            related_table = "Parts" if model_name == "Orders" else "Steps"
            context["has_related_table"] = True
            context["table_partial_url"] = reverse_lazy("generic_table_view", kwargs={"model_name": related_table})
            context["related_object_id"] = obj.pk

        return context



def map_generic_form_input_styles(field, fieldtype=None):
    """
    Apply Tailwind-compatible classes to a Django form field based on its type.
    Optionally accepts `fieldtype` to override autodetection.
    """
    fieldtype = fieldtype or type(field)

    classes = ""

    base_input_class = "rounded-md border border-gray-300 shadow-sm focus:outline-none"

    type_class_map = {
        forms.CharField: f"{base_input_class} focus:border-green-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1 m-1.5",
        forms.IntegerField: f"{base_input_class} max-w-sm focus:border-yellow-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5 w-20",
        forms.FloatField: f"{base_input_class} focus:border-yellow-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.BooleanField: "h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 m-1.5",
        forms.DateField: f"{base_input_class} focus:border-green-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.DateTimeField: f"{base_input_class} focus:border-green-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.EmailField: f"{base_input_class} focus:border-purple-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.URLField: f"{base_input_class} focus:border-indigo-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.TimeField: f"{base_input_class} focus:border-pink-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.ChoiceField: f"{base_input_class} focus:border-indigo-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.TypedChoiceField: f"{base_input_class} focus:border-indigo-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.ModelChoiceField: f"{base_input_class} focus:border-indigo-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.Textarea: f"{base_input_class} focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
        forms.FileField: "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 m-1.5",
        forms.DurationField: f"{base_input_class} focus:border-orange-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 m-1.5",
    }

    # Match via subclass (e.g., a custom MyIntegerField)
    for base_type, css_classes in type_class_map.items():
        if isinstance(field, base_type):
            classes = css_classes
        else:
            f"{base_input_class} focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
    if field and field.required:
        classes += " after:content-['*'] after:ml-0.5 after:text-red-500"

    return classes


def apply_styles_to_form(form):
    for field in form.fields.values():
        field.widget.attrs['class'] = map_generic_form_input_styles(field)


def apply_styles_to_formset(formset):
    for form in formset:
        apply_styles_to_form(form)
