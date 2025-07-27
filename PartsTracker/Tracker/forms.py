from django.urls import reverse_lazy
from django import forms
from django.forms import modelformset_factory, formset_factory

from Tracker.generic_views import map_generic_form_input_styles, apply_styles_to_form
from Tracker.models import Parts, Orders, Processes, PartTypes, Documents, QualityReports, QualityErrorsList


class PartsFormforDeals(forms.ModelForm):

    estimated_completion = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = Parts
        exclude = ['deal', 'customer', 'archived', 'part_type', 'step']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)

            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes


class DealForm(forms.ModelForm):
    estimated_completion = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    required_css_class = "after:content-['*'] after:text-red-600 after:ml-2 after:text-2xl"

    class Meta:
        model = Orders
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)

            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes


class ProcessForm(forms.ModelForm):
    class Meta:
        model = Processes
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes


class PartTypeForm(forms.ModelForm):
    class Meta:
        model = PartTypes
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes


class LineItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)
    part_type = forms.ModelChoiceField(queryset=PartTypes.objects.all(), required=False)
    enumeration_start = forms.IntegerField(min_value=0)
    process = forms.ModelChoiceField(queryset=Processes.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define the base form control classes (your Tailwind input style)
        input_classes = map_generic_form_input_styles(None)

        # HTMX dynamic swap setup for part_type
        self.fields['part_type'].widget.attrs.update({
            'hx-get': reverse_lazy('parttype_select_partial'),
            'hx-trigger': 'refresh-parttypes from:body',
            'hx-target': 'this',
            'hx-swap': 'innerHTML',
            'class': input_classes,   # <-- Make sure it REAPPLIES classes after swap
        })

        # HTMX dynamic swap setup for process
        self.fields['process'].widget.attrs.update({
            'hx-get': reverse_lazy('process_select_partial'),
            'hx-trigger': 'refresh-processes from:body',
            'hx-target': 'this',
            'hx-swap': 'innerHTML',
            'class': input_classes,   # <-- same here
        })

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes


LineItemFormSet = formset_factory(
    LineItemForm,
    extra=1,
    can_delete=True
)


class PartDocForm(forms.ModelForm):
    class Meta:
        model = Documents
        fields = ['is_image', 'file_name', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes

class ErrorReportForm(forms.ModelForm):
    operator = forms.CharField(required=False, help_text="Full name (e.g., John Smith)")
    other_error = forms.CharField(required=False, label="Other error (not listed)")

    errors_associated = forms.ModelMultipleChoiceField(
        queryset=QualityErrorsList.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Common Error Types (for this part)"
    )
    errors_unassociated = forms.ModelMultipleChoiceField(
        queryset=QualityErrorsList.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Other Error Types"
    )

    class Meta:
        model = QualityReports
        fields = ['machine', 'description', 'file']

    def __init__(self, *args, **kwargs):
        part_type = kwargs.pop('part_type', None)
        super().__init__(*args, **kwargs)
        if part_type:
            self.fields['errors_associated'].queryset = QualityErrorsList.objects.filter(part_type=part_type)
            self.fields['errors_unassociated'].queryset = QualityErrorsList.objects.exclude(part_type=part_type)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes

class PartForm(forms.ModelForm):
    class Meta:
        model = Parts
        fields = ["ERP_id", "part_type", "step", "part_status"]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css_classes = map_generic_form_input_styles(field)
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += f" {css_classes}"
            else:
                field.widget.attrs["class"] = css_classes

PartFormSet = modelformset_factory(Parts, form=PartForm, extra=0)