"""Forms for Lead model and Lead conversion process."""

import logging

import pycountry
from django import forms
from django.apps import apps
from django.db import models
from django.urls import reverse, reverse_lazy

from horilla_core.mixins import OwnerQuerysetMixin
from horilla_core.models import HorillaUser
from horilla_crm.accounts.models import Account
from horilla_crm.contacts.models import Contact
from horilla_crm.opportunities.models import Opportunity
from horilla_generics.forms import HorillaModelForm, HorillaMultiStepForm
from horilla_mail.models import HorillaMailConfiguration

from .models import (
    EmailToLeadConfig,
    Lead,
    LeadStatus,
    ScoringCondition,
    ScoringCriterion,
)

logger = logging.getLogger(__name__)


class LeadFormClass(OwnerQuerysetMixin, HorillaMultiStepForm):
    """Form class for Lead model"""

    class Meta:
        """Meta class for LeadFormClass"""

        model = Lead
        fields = "__all__"

    step_fields = {
        1: [
            "lead_owner",
            "title",
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "fax",
            "lead_source",
            "lead_status",
        ],
        2: ["lead_company", "no_of_employees", "industry", "annual_revenue"],
        3: ["country", "state", "city", "zip_code"],
        4: ["requirements"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.current_step < len(self.step_fields):
            self.fields["created_by"].required = False
            self.fields["updated_by"].required = False

        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("horilla_core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        )
        self.fields["state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "country" in self.data:
            country_code = self.data.get("country")
            self.fields["state"].choices = self.get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.country:
            self.fields["state"].choices = self.get_subdivision_choices(
                self.instance.country.code
            )

    def get_subdivision_choices(self, country_code):
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except:
            return []


class LeadSingleForm(HorillaModelForm):
    """
    Custom form for Lead to add HTMX attributes
    Inherits from HorillaModelForm to preserve all existing behavior.
    """

    class Meta:
        """Meta class for LeadStatusForm"""

        model = Lead
        fields = [
            "lead_owner",
            "title",
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "lead_source",
            "lead_status",
            "lead_company",
            "no_of_employees",
            "industry",
            "annual_revenue",
            "country",
            "state",
            "city",
            "zip_code",
            "fax",
            "requirements",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("horilla_core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        )
        self.fields["state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "country" in self.data:
            country_code = self.data.get("country")
            self.fields["state"].choices = self.get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.country:
            self.fields["state"].choices = self.get_subdivision_choices(
                self.instance.country.code
            )

    def get_subdivision_choices(self, country_code):
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except:
            return []


class LeadConversionForm(forms.Form):
    """Form for converting a Lead into Account, Contact, and Opportunity"""

    # Account fields
    account_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    account_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs  w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Enter Account Name",
            }
        ),
    )
    existing_account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        empty_label="Select Account",
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full text-sm",
                "hx-get": "",  # Will be set dynamically
                "hx-target": "#opportunity-field",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
            }
        ),
    )

    # Contact fields
    contact_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Enter First Name",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Enter Last Name",
            }
        ),
    )
    existing_contact = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        empty_label="Select Contact",
        widget=forms.Select(attrs={"class": "normal-seclect"}),
    )

    # Opportunity fields
    opportunity_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    opportunity_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Enter Opportunity Name",
            }
        ),
    )
    existing_opportunity = forms.ModelChoiceField(
        queryset=Opportunity.objects.none(),  # Start with empty queryset
        required=False,
        empty_label="Select Opportunity",
        widget=forms.Select(attrs={"class": "normal-seclect"}),
    )

    # Owner field
    owner = forms.ModelChoiceField(
        queryset=HorillaUser.objects.all(),
        required=True,
        empty_label="Select Owner",
        widget=forms.Select(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.lead = kwargs.pop("lead", None)
        self.selected_account = kwargs.pop("selected_account", None)
        super().__init__(*args, **kwargs)

        if self.lead:
            # Pre-populate fields with lead data
            self.fields["account_name"].initial = self.lead.lead_company
            self.fields["first_name"].initial = self.lead.first_name
            self.fields["last_name"].initial = self.lead.last_name
            self.fields["opportunity_name"].initial = (
                f"{self.lead.lead_company} - Opportunity"
            )
            self.fields["owner"].initial = self.lead.lead_owner

            # Set HTMX URL for account selection
            self.fields["existing_account"].widget.attrs["hx-get"] = reverse(
                "leads:convert_lead", kwargs={"pk": self.lead.pk}
            )

        # Filter opportunities based on selected account
        if self.selected_account:
            self.fields["existing_opportunity"].queryset = Opportunity.objects.filter(
                account=self.selected_account
            )
        else:
            self.fields["existing_opportunity"].queryset = None

    def clean(self):
        cleaned_data = super().clean()

        # Validate account
        account_action = cleaned_data.get("account_action")
        if account_action == "create_new":
            if not cleaned_data.get("account_name"):
                self.add_error(
                    "account_name",
                    "Account name is required when creating new account.",
                )
        elif account_action == "select_existing":
            if not cleaned_data.get("existing_account"):
                self.add_error("existing_account", "Please select an existing account.")

        # Validate contact
        contact_action = cleaned_data.get("contact_action")
        if contact_action == "create_new":
            if not cleaned_data.get("first_name"):
                self.add_error(
                    "first_name", "First name is required when creating new contact."
                )
            if not cleaned_data.get("last_name"):
                self.add_error(
                    "last_name", "Last name is required when creating new contact."
                )
        elif contact_action == "select_existing":
            if not cleaned_data.get("existing_contact"):
                self.add_error("existing_contact", "Please select an existing contact.")

        # Validate opportunity
        opportunity_action = cleaned_data.get("opportunity_action")
        if opportunity_action == "create_new":
            if not cleaned_data.get("opportunity_name"):
                self.add_error(
                    "opportunity_name",
                    "Opportunity name is required when creating new opportunity.",
                )
        elif opportunity_action == "select_existing":
            if not cleaned_data.get("existing_opportunity"):
                self.add_error(
                    "existing_opportunity", "Please select an existing opportunity."
                )

        return cleaned_data


class LeadStatusForm(HorillaModelForm):
    """
    Custom form for LeadStatus to add HTMX attributes to is_final field.
    Inherits from HorillaModelForm to preserve all existing behavior.
    """

    class Meta:
        """Meta class for LeadStatusForm"""

        model = LeadStatus
        fields = ["name", "probability", "is_final", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add HTMX attributes to is_final field to toggle order field visibility
        if "is_final" in self.fields:
            self.fields["is_final"].widget.attrs.update(
                {
                    "hx-post": reverse_lazy("leads:toggle_order_field"),
                    "hx-target": "#order_container",
                    "hx-swap": "outerHTML",
                    "hx-trigger": "change",
                }
            )


class EmailToLeadForm(HorillaModelForm):
    """
    Inherits from HorillaModelForm to preserve all existing behavior.
    """

    class Meta:
        """Meta class for LeadStatusForm"""

        model = EmailToLeadConfig
        fields = ["mail", "lead_owner", "accept_emails_from", "keywords"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mail"].queryset = HorillaMailConfiguration.objects.filter(
            mail_channel="incoming", is_active=True
        )


class ScoringCriterionForm(HorillaModelForm):
    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = ScoringCondition
        self.instance_obj = kwargs.get("instance")

        model_name = None
        request = kwargs.get("request")
        if request:
            model_name = request.GET.get("model_name") or request.POST.get("model_name")
        if self.instance_obj:
            model_name = self.instance_obj.rule.module

        condition_field_choices = {
            "field": self._get_model_field_choices(model_name),
            "operator": [
                ("", "---------"),
                ("equals", "Equals"),
                ("not_equals", "Not Equals"),
                ("contains", "Contains"),
                ("not_contains", "Does Not Contain"),
                ("starts_with", "Starts With"),
                ("ends_with", "Ends With"),
                ("greater_than", "Greater Than"),
                ("greater_than_equal", "Greater Than or Equal"),
                ("less_than", "Less Than"),
                ("less_than_equal", "Less Than or Equal"),
                ("is_empty", "Is Empty"),
                ("is_not_empty", "Is Not Empty"),
            ],
            "logical_operator": [
                ("", "---------"),
                ("and", "AND"),
                ("or", "OR"),
            ],
        }
        kwargs["condition_field_choices"] = condition_field_choices

        super().__init__(*args, **kwargs)
        self.model_name = model_name or ""
        self._add_htmx_to_field_selects()

        if self.instance_obj and self.instance_obj.pk:
            self._set_initial_condition_values()

    def _set_initial_condition_values(self):
        """Set initial values for condition fields in edit mode"""
        if not self.instance_obj or not self.instance_obj.pk:
            return

        existing_conditions = self.instance_obj.conditions.all().order_by("order")
        if hasattr(self, "row_id") and self.row_id != "0":
            return

        if existing_conditions.exists():
            first_condition = existing_conditions.first()
            for field_name in self.condition_fields:
                if field_name in self.fields:
                    value = getattr(first_condition, field_name, "")
                    self.fields[field_name].initial = value
                    field_key_0 = f"{field_name}_0"
                    if field_key_0 in self.fields:
                        self.fields[field_key_0].initial = value

    def _add_htmx_to_field_selects(self):
        """Add HTMX attributes to field select widgets for dynamic value field updates"""
        model_name = getattr(self, "model_name", "")
        row_id = getattr(self, "row_id", "0")

        for field_name, field in self.fields.items():
            if field_name.startswith("field") or field_name == "field":
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs.update(
                        {
                            "name": f"field_{row_id}",
                            "id": f"id_field_{row_id}",
                            "hx-get": reverse_lazy(
                                "horilla_generics:get_field_value_widget"
                            ),
                            "hx-target": f"#id_value_{row_id}_container",
                            "hx-swap": "innerHTML",
                            "hx-include": f'[name="field_{row_id}"],#id_value_{row_id}',
                            "hx-vals": f'{{"model_name": "{model_name}", "row_id": "{row_id}"}}',
                            "hx-trigger": "change,load",
                        }
                    )

    def _get_model_field_choices(self, model_name):
        """Get field choices for the specified model"""
        field_choices = [("", "---------")]

        if model_name:
            try:
                model = None
                for app_config in apps.get_app_configs():
                    try:
                        model = apps.get_model(
                            app_label=app_config.label, model_name=model_name
                        )
                        break
                    except LookupError:
                        continue

                if model:
                    model_fields = [
                        (field.name, field.verbose_name or field.name)
                        for field in model._meta.get_fields()
                        if field.concrete and not field.is_relation
                    ]
                    field_choices.extend(model_fields)

            except Exception as e:
                logger.error(
                    f"Error fetching model {model_name}: {str(e)}", exc_info=True
                )

        return field_choices

    def _add_condition_fields(self):
        """Override to add HTMX-enabled condition fields with proper initialization"""
        for field_name in self.condition_fields:
            try:
                model_field = self.condition_model._meta.get_field(field_name)

                # Create base field (for row 0 and template access)
                if field_name == "field" and field_name in self.condition_field_choices:
                    model_name = getattr(self, "model_name", "")
                    form_field = forms.ChoiceField(
                        choices=self.condition_field_choices[field_name],
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                                "hx-get": reverse_lazy(
                                    "horilla_generics:get_field_value_widget"
                                ),
                                "hx-target": f"#id_value_0_container",
                                "hx-swap": "innerHTML",
                                "hx-vals": f'{{"model_name": "{model_name}", "row_id": "0"}}',
                                "hx-include": f'[name="{field_name}_0"]',
                                "hx-trigger": "change,load",
                            }
                        ),
                    )
                elif field_name == "value":
                    form_field = forms.CharField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                                "data-container-id": f"value-field-container-0",
                            }
                        ),
                    )
                elif field_name in self.condition_field_choices:
                    form_field = forms.ChoiceField(
                        choices=self.condition_field_choices[field_name],
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif hasattr(model_field, "choices") and model_field.choices:
                    form_field = forms.ChoiceField(
                        choices=[("", "---------")] + list(model_field.choices),
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.CharField):
                    form_field = forms.CharField(
                        max_length=model_field.max_length,
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.IntegerField):
                    form_field = forms.IntegerField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.NumberInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.BooleanField):
                    form_field = forms.BooleanField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.CheckboxInput(
                            attrs={
                                "class": "sr-only peer",
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                else:
                    form_field = forms.CharField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )

                form_field.is_custom_field = True
                self.fields[field_name] = form_field

            except Exception as e:
                logger.error(f"Error adding condition field {field_name}: {str(e)}")

        # Set initial values for edit mode
        self._set_initial_condition_values()

    def clean(self):
        """Process multiple condition rows from form data"""
        cleaned_data = super().clean()

        condition_rows = self._extract_condition_rows()

        if not condition_rows:
            raise forms.ValidationError("At least one condition must be provided.")

        cleaned_data["condition_rows"] = condition_rows

        return cleaned_data

    def _extract_condition_rows(self):
        condition_rows = []
        condition_fields = ["field", "operator", "value", "logical_operator"]

        if not self.data:
            return condition_rows

        row_ids = set()

        for key in self.data.keys():
            for field_name in condition_fields:
                if key.startswith(f"{field_name}_"):
                    row_id = key.replace(f"{field_name}_", "")
                    if row_id.isdigit():
                        row_ids.add(row_id)

        if any(f in self.data for f in condition_fields) or any(
            f"{f}_0" in self.data for f in condition_fields
        ):
            row_ids.add("0")

        for row_id in sorted(row_ids, key=lambda x: int(x)):
            row_data = {}
            has_required_data = True

            for field_name in condition_fields:
                if row_id == "0":
                    field_key = (
                        f"{field_name}_0"
                        if f"{field_name}_0" in self.data
                        else field_name
                    )
                else:
                    field_key = f"{field_name}_{row_id}"

                value = self.data.get(field_key, "").strip()
                row_data[field_name] = value

                if field_name in ["field", "operator"] and not value:
                    has_required_data = False

            if has_required_data and row_data.get("field") and row_data.get("operator"):
                row_data["order"] = int(row_id)
                condition_rows.append(row_data)

        return condition_rows

    class Meta:
        model = ScoringCriterion
        fields = ["rule", "points", "operation_type"]
        widgets = {
            "points": forms.NumberInput(
                attrs={
                    "class": "text-color-600 p-2 w-full border border-dark-50 rounded-md mt-1"
                }
            ),
        }
