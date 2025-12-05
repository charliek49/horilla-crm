"""Filters for Lead and LeadStatus models."""

from horilla_crm.leads.models import Lead, LeadStatus, ScoringRule
from horilla_generics.filters import HorillaFilterSet


class LeadFilter(HorillaFilterSet):
    """Lead Filter"""

    class Meta:
        """Meta class for LeadFilter"""

        model = Lead
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["first_name", "email", "title"]


class LeadStatusFilter(HorillaFilterSet):
    """LeadStatus Filter"""

    class Meta:
        """Meta class for LeadStatusFilter"""

        model = LeadStatus
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class ScoringRuleFilter(HorillaFilterSet):
    class Meta:
        model = ScoringRule
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["customer_role_name"]
