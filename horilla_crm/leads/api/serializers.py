"""
Serializers for horilla_crm.leads models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.leads.models import Lead, LeadStatus, ScoringCriterion, ScoringRule


class LeadStatusSerializer(serializers.ModelSerializer):
    """Serializer for LeadStatus model"""

    class Meta:
        model = LeadStatus
        fields = "__all__"


class ScoringRuleSerializer(serializers.ModelSerializer):
    """Serializer for ScoringRule model"""

    class Meta:
        model = ScoringRule
        fields = "__all__"


class ScoringCriterionSerializer(serializers.ModelSerializer):
    """Serializer for ScoringCriterion model"""

    class Meta:
        model = ScoringCriterion
        fields = "__all__"
