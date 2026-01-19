"""
Filtering utilities for horilla_generics.

Provides the HorillaFilterSet and operator choices used by generic filtering forms.
"""

# Standard library imports
import logging

# Third-party imports (Others)
import django_filters

# Third-party imports (Django)
from django.db import models
from django.db.models import Q

logger = logging.getLogger(__name__)
# Define operator choices by field type
OPERATOR_CHOICES = {
    "text": [
        ("icontains", "Contains"),
        ("exact", "Equals"),
        ("ne", "Not Equals"),
        ("istartswith", "Starts with"),
        ("iendswith", "Ends with"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "number": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "float": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "decimal": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "date": [
        ("exact", "Equals"),
        ("gt", "After"),
        ("lt", "Before"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "datetime": [
        ("exact", "Equals"),
        ("gt", "After"),
        ("lt", "Before"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "boolean": [("exact", "Equals")],
    "choice": [
        ("exact", "Equals"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "other": [
        ("exact", "Equals"),
        ("icontains", "Contains"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
}


class HorillaFilterSet(django_filters.FilterSet):
    """
    Custom FilterSet for Horilla with enhanced search and filtering capabilities.

    Provides field-type-specific operators and boolean value conversion
    for generic filtering across Horilla models.
    """

    search = django_filters.CharFilter(method="filter_search", label="Search")

    @classmethod
    def get_operators_for_field(cls, field_type):
        """Return appropriate operators for a given field type"""
        return OPERATOR_CHOICES.get(field_type, OPERATOR_CHOICES["other"])

    def _convert_boolean_value(self, value, model, field_name):
        """Convert boolean string values to proper format for filtering"""
        if value is None:
            return None

        # Check if the field is a BooleanField
        try:
            field = model._meta.get_field(field_name)
            if isinstance(field, models.BooleanField):
                # Convert lowercase "true"/"false" to proper boolean or capitalized string
                value_str = str(value).lower()
                return {"true": True, "false": False}.get(value_str)

        except (models.FieldDoesNotExist, AttributeError):
            pass

        return value

    def filter_queryset(self, queryset):
        """
        Override the default filter_queryset to handle our custom filtering approach.
        Process arrays of fields, operators, and values.
        """
        if hasattr(self, "form") and hasattr(self.form, "cleaned_data"):
            queryset = super().filter_queryset(queryset)

        request = getattr(self, "request", None)
        if not request and hasattr(self, "data") and hasattr(self.data, "_request"):
            request = self.data._request

        if not request:
            return queryset

        fields = self.data.getlist("field", []) or request.GET.getlist("field", [])
        operators = self.data.getlist("operator", []) or request.GET.getlist(
            "operator", []
        )
        values = self.data.getlist("value", []) or request.GET.getlist("value", [])
        start_values = self.data.getlist("start_value", []) or request.GET.getlist(
            "start_value", []
        )
        end_values = self.data.getlist("end_value", []) or request.GET.getlist(
            "end_value", []
        )

        for i, (field, operator) in enumerate(zip(fields, operators)):
            if not field or not operator:
                continue

            try:
                # Get the model from queryset
                model = queryset.model

                if operator == "ne":
                    value = values[i] if i < len(values) else None
                    if value is not None:
                        # Convert boolean value if needed
                        value = self._convert_boolean_value(value, model, field)
                        queryset = queryset.exclude(**{field: value})

                elif operator == "between":
                    start_value = start_values[i] if i < len(start_values) else None
                    end_value = end_values[i] if i < len(end_values) else None

                    if start_value and end_value:
                        queryset = queryset.filter(
                            **{f"{field}__gte": start_value, f"{field}__lte": end_value}
                        )
                    elif start_value:
                        queryset = queryset.filter(**{f"{field}__gte": start_value})
                    elif end_value:
                        queryset = queryset.filter(**{f"{field}__lte": end_value})

                elif operator == "isnull":
                    queryset = queryset.filter(**{f"{field}__isnull": True})

                elif operator == "isnotnull":
                    queryset = queryset.filter(**{f"{field}__isnull": False})

                else:
                    value = values[i] if i < len(values) else None
                    if value is not None:
                        # Convert boolean value if needed
                        value = self._convert_boolean_value(value, model, field)
                        queryset = queryset.filter(**{f"{field}__{operator}": value})

            except Exception as e:
                logger.error("Filter error for %s %s: %s", field, operator, e)

        search_query = self.data.get("search", "") or request.GET.get("search", "")
        if search_query:
            queryset = self.filter_search(queryset, "search", search_query)

        return queryset

    def filter_search(self, queryset, name, value):
        """Handle search across specified fields with smart full name matching"""
        search_fields = getattr(self.Meta, "search_fields", [])
        if not value or not search_fields:
            return queryset

        queries = Q()

        # Regular field search
        for field in search_fields:
            queries |= Q(**{f"{field}__icontains": value})

        if " " in value.strip():
            parts = value.strip().split(None, 1)  # Split on first space
            if len(parts) == 2:
                first, last = parts
                queries |= Q(first_name__icontains=first, last_name__icontains=last)

        return queryset.filter(queries)
