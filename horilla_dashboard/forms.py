"""Forms for dashboards app."""

import json
import logging

from django import forms
from django.apps import apps
from django.db import models
from django.urls import reverse_lazy

from horilla.registry.feature import FEATURE_REGISTRY
from horilla_core.models import HorillaContentType
from horilla_generics.forms import HorillaModelForm

from .models import ComponentCriteria, DashboardComponent

logger = logging.getLogger(__name__)


def get_dashboard_component_models():
    """
    Return a list of (module_key, model_class) for every model that
    is registered for dashboard components.
    """
    models = []
    for model_cls in FEATURE_REGISTRY.get("dashboard_component_models", []):
        key = model_cls.__name__.lower()
        models.append((key, model_cls))
    return models


class DashboardCreateForm(HorillaModelForm):
    """Dashboard Create Form"""

    htmx_field_choices_url = "horilla_dashboard:get_module_field_choices"

    class Meta:
        """Meta class for DashboardCreateForm"""

        model = DashboardComponent
        fields = "__all__"
        exclude = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "additional_info",
        ]
        widgets = {
            "component_type": forms.Select(
                attrs={
                    "id": "id_component_type",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = ComponentCriteria
        self.instance_obj = kwargs.get("instance")
        request = kwargs.get("request")
        self.request = request

        super().__init__(*args, **kwargs)

        # Get model_name after base class initialization
        model_name = getattr(self, "model_name", None)

        if "module" in self.fields and request and hasattr(request, "user"):
            user = request.user
            allowed_modules = []

            for module_key, model_cls in get_dashboard_component_models():
                app_label = model_cls._meta.app_label
                model_name = model_cls._meta.model_name

                view_perm = f"{app_label}.view_{model_name}"
                view_own_perm = f"{app_label}.view_own_{model_name}"

                if user.has_perm(view_perm) or user.has_perm(view_own_perm):
                    label = model_cls._meta.verbose_name.title()
                    allowed_modules.append((module_key, label))

            if not self.instance_obj or not self.instance_obj.pk:
                self.fields["module"].choices = [("", "---------")] + allowed_modules
                self.fields["module"].initial = ""
            else:
                self.fields["module"].choices = allowed_modules

        def hide_fields(field_list, nullify=False):
            for name in field_list:
                if name in self.fields:
                    self.fields[name].widget = forms.HiddenInput(
                        attrs={"required": False}
                    )
                    if nullify:
                        self.fields[name].initial = None
                        if self.data:
                            self.data = self.data.copy()
                            self.data[name] = None

        # Hide fields based on component_type
        component_type = self.request.GET.get("component_type") or (
            self.instance_obj.component_type if self.instance_obj else ""
        )

        nullify_values = (
            self.request.method == "GET" if hasattr(self, "request") else True
        )
        if component_type != "chart":
            hide_fields(
                ["chart_type", "secondary_grouping", "grouping_field"],
                nullify=nullify_values,
            )

        if component_type != "kpi":
            hide_fields(["icon", "metric_type"], nullify=nullify_values)

        if component_type == "table_data":
            hide_fields(
                ["grouping_field", "metric_field", "metric_type"],
                nullify=nullify_values,
            )

        if component_type != "table_data":
            hide_fields(["columns"], nullify=nullify_values)
        else:
            if "columns" in self.fields:
                if (
                    self.instance_obj
                    and self.instance_obj.pk
                    and self.instance_obj.columns
                ):
                    instance_model_name = None
                    if self.instance_obj.module:
                        instance_model_name = self.instance_obj.module.model

                    if instance_model_name:
                        if isinstance(self.instance_obj.columns, str):
                            if self.instance_obj.columns.startswith("["):
                                columns_list = json.loads(self.instance_obj.columns)
                            else:
                                columns_list = [
                                    col.strip()
                                    for col in self.instance_obj.columns.split(",")
                                    if col.strip()
                                ]
                        else:
                            columns_list = (
                                self.instance_obj.columns
                                if isinstance(self.instance_obj.columns, list)
                                else []
                            )

                        # Find the model
                        model = None
                        for app_config in apps.get_app_configs():
                            try:
                                model = apps.get_model(
                                    app_label=app_config.label,
                                    model_name=instance_model_name.lower(),
                                )
                                break
                            except LookupError:
                                continue

                        if model:
                            column_choices = []
                            for field in model._meta.get_fields():
                                if field.concrete and not field.is_relation:
                                    field_name = field.name
                                    field_label = field.verbose_name or field.name
                                    if hasattr(field, "get_internal_type"):
                                        field_type = field.get_internal_type()
                                        if field_type in [
                                            "CharField",
                                            "TextField",
                                            "BooleanField",
                                            "DateField",
                                            "DateTimeField",
                                            "TimeField",
                                            "EmailField",
                                            "URLField",
                                        ]:
                                            column_choices.append(
                                                (field_name, field_label)
                                            )
                                        elif (
                                            hasattr(field, "choices") and field.choices
                                        ):
                                            column_choices.append(
                                                (field_name, field_label)
                                            )
                                elif (
                                    hasattr(field, "related_model")
                                    and field.many_to_one
                                ):
                                    field_name = field.name
                                    field_label = field.verbose_name or field.name
                                    column_choices.append((field_name, field_label))

                            # Recreate the field with choices
                            self.fields["columns"] = forms.MultipleChoiceField(
                                choices=column_choices,
                                required=False,
                                widget=forms.SelectMultiple(
                                    attrs={
                                        "class": "js-example-basic-multiple headselect",
                                        "id": "id_columns",
                                        "name": "columns",
                                        "data-placeholder": "Add Columns",
                                        "tabindex": "-1",
                                        "aria-hidden": "true",
                                        "multiple": True,
                                    }
                                ),
                            )

                            # Set the initial value with the saved columns
                            self.initial["columns"] = columns_list
                else:
                    # New instance - set up empty multi-select
                    self.fields["columns"].widget = forms.SelectMultiple(
                        attrs={
                            "class": "js-example-basic-multiple headselect",
                            "id": "id_columns",
                            "name": "columns",
                            "data-placeholder": "Add Columns",
                            "tabindex": "-1",
                            "aria-hidden": "true",
                            "multiple": True,
                        }
                    )

        if "module" in self.fields:
            module_field = self.fields.get("module")
            if module_field and hasattr(module_field.widget, "attrs"):
                module_field.widget.attrs.update(
                    {
                        "hx-get-grouping": reverse_lazy(
                            "horilla_dashboard:get_grouping_field_choices"
                        ),
                        "hx-target-grouping": "#id_grouping_field_container",
                        "hx-get-columns": reverse_lazy(
                            "horilla_dashboard:get_columns_field_choices"
                        ),
                        "hx-target-columns": "#columns_container",
                        "hx-get-secondary-grouping": reverse_lazy(
                            "horilla_dashboard:get_secondary_grouping_field_choices"
                        ),
                        "hx-target-secondary-grouping": "#id_secondary_grouping_container",
                    }
                )

        if self.instance_obj and self.instance_obj.pk and model_name:
            self._initialize_select_fields_for_edit(model_name)

    def _initialize_select_fields_for_edit(self, model_name):
        """Initialize select fields in edit mode by mimicking HTMX view behavior"""
        try:
            # Get component_type to check which fields should be visible
            component_type = self.request.GET.get("component_type") or (
                self.instance_obj.component_type if self.instance_obj else ""
            )

            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except LookupError:
                    continue

            if not model:
                return

            # Only initialize grouping_field if component_type is 'chart'
            if "grouping_field" in self.fields and component_type == "chart":
                grouping_fields = []
                for field in model._meta.get_fields():
                    if field.concrete and not field.is_relation:
                        field_name = field.name
                        field_label = field.verbose_name or field.name

                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()
                            if field_type in [
                                "CharField",
                                "TextField",
                                "BooleanField",
                                "DateField",
                                "DateTimeField",
                                "TimeField",
                                "EmailField",
                                "URLField",
                            ]:
                                grouping_fields.append((field_name, field_label))
                            elif hasattr(field, "choices") and field.choices:
                                grouping_fields.append((field_name, f"{field_label}"))

                    elif hasattr(field, "related_model") and field.many_to_one:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        grouping_fields.append((field_name, f"{field_label}"))

                current_value = (
                    getattr(self.instance_obj, "grouping_field", "")
                    if self.instance_obj
                    else ""
                )
                self.fields["grouping_field"] = forms.ChoiceField(
                    choices=[("", "Select Grouping Field")] + grouping_fields,
                    required=False,
                    initial=current_value,
                    widget=forms.Select(
                        attrs={
                            "class": "js-example-basic-single headselect",
                            "id": "id_grouping_field",
                            "name": "grouping_field",
                        }
                    ),
                )

            # Only initialize secondary_grouping if component_type is 'chart'
            if "secondary_grouping" in self.fields and component_type == "chart":
                secondary_grouping_fields = []
                for field in model._meta.get_fields():
                    if field.concrete and not field.is_relation:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()
                            if field_type in [
                                "CharField",
                                "TextField",
                                "BooleanField",
                                "DateField",
                                "DateTimeField",
                                "TimeField",
                                "EmailField",
                                "URLField",
                            ]:
                                secondary_grouping_fields.append(
                                    (field_name, field_label)
                                )
                            elif hasattr(field, "choices") and field.choices:
                                secondary_grouping_fields.append(
                                    (field_name, f"{field_label}")
                                )
                    elif hasattr(field, "related_model") and field.many_to_one:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        secondary_grouping_fields.append((field_name, f"{field_label}"))

                current_value = (
                    getattr(self.instance_obj, "secondary_grouping_field", "")
                    if self.instance_obj
                    else ""
                )
                self.fields["secondary_grouping"] = forms.ChoiceField(
                    choices=[("", "Select Secondary Grouping Field")]
                    + secondary_grouping_fields,
                    required=False,
                    initial=current_value,
                    widget=forms.Select(
                        attrs={
                            "class": "js-example-basic-single headselect",
                            "id": "id_secondary_grouping",
                            "name": "secondary_grouping",
                        }
                    ),
                )

        except Exception as e:
            logger.error("Error initializing select fields for edit: {%s}", e)

    def clean(self):
        """Process columns field and extract condition_rows"""
        cleaned_data = super().clean()

        # Extract condition_rows using base class method
        if self.condition_fields:
            condition_rows = self._extract_condition_rows()
            cleaned_data["condition_rows"] = condition_rows

        # Handle columns field (convert list to comma-separated string)
        raw_columns = self.data.getlist("columns")
        if raw_columns and "columns" in cleaned_data:
            cleaned_data["columns"] = raw_columns

        return cleaned_data

    def clean_columns(self):
        """Clean the columns field to store as comma-separated values"""
        raw_columns = self.data.getlist("columns")
        columns = self.cleaned_data.get("columns")

        if raw_columns:
            columns = raw_columns

        elif isinstance(columns, str):
            columns = [col.strip() for col in columns.split(",") if col.strip()]

        elif not isinstance(columns, (list, tuple)):
            columns = raw_columns if raw_columns else [columns]

        if not columns:
            return ""

        column_list = [str(col) for col in columns if col]
        result = ",".join(column_list)
        return result
