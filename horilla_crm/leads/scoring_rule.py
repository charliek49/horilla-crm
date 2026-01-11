"""
This view handles the methods for team role view
"""

import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.leads.filters import ScoringRuleFilter
from horilla_crm.leads.forms import ScoringCriterionForm
from horilla_crm.leads.models import ScoringCondition, ScoringCriterion, ScoringRule
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class ScoringRuleView(LoginRequiredMixin, HorillaView):
    """
    Template view for scoring rule page
    """

    template_name = "scoring_rule/scoring_rule_view.html"
    nav_url = reverse_lazy("leads:scoring_rule_nav_view")
    list_url = reverse_lazy("leads:scoring_rule_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("leads.view_scoringrule"), name="dispatch")
class ScoringRuleNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar for scoring rule
    """

    nav_title = ScoringRule._meta.verbose_name_plural
    search_url = reverse_lazy("leads:scoring_rule_list_view")
    main_url = reverse_lazy("leads:scoring_rule_view")
    filterset_class = ScoringRuleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "ScoringRule"
    model_app_label = "leads"
    nav_width = False
    gap_enabled = False
    url_name = "scoring_rule_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("leads.add_scoringrule"):
            return {
                "url": f"""{ reverse_lazy('leads:scoring_rule_create_form')}?new=true""",
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("leads.view_scoringrule"):
            return [
                {
                    "action": _("Add column to list"),
                    "attrs": f"""
                            hx-get="{reverse_lazy('horilla_generics:column_selector')}?app_label={self.model_app_label}&model_name={self.model_name}&url_name={self.url_name}"
                            onclick="openModal()"
                            hx-vals='{{"exclude":"is_active"}}'
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            """,
                }
            ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.view_scoringrule"), name="dispatch"
)
class ScoringRuleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of scoring rule
    """

    model = ScoringRule
    view_id = "scoring_rule_list"
    filterset_class = ScoringRuleFilter
    search_url = reverse_lazy("leads:scoring_rule_list_view")
    main_url = reverse_lazy("leads:scoring_rule_view")
    table_width = False
    table_height = False
    table_height_as_class = "h-[500px]"
    bulk_select_option = False
    header_attrs = [
        {"description": {"style": "width: 300px;"}},
    ]

    columns = [
        "name",
        (_("Module"), "get_module_display"),
        (_("Is Active"), "is_active_col"),
        "description",
    ]

    @cached_property
    def col_attrs(self):
        attrs = {}
        if self.request.user.has_perm("leads.view_scoringrule"):
            attrs = {
                "hx-get": f"{{get_detail_view_url}}",
                "hx-target": "#scoring-rule-view",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#scoring-rule-view",
            }
        return [
            {
                "name": {
                    "style": "cursor:pointer",
                    "class": "hover:text-primary-600",
                    **attrs,
                }
            }
        ]

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "leads.change_scoringrule",
            "attrs": """
                    hx-get="{get_edit_url}?new=true"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal()"
                    """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "leads.delete_scoringrule",
            "attrs": """
                hx-post="{get_delete_url}"
                hx-target="#deleteModeBox"
                hx-swap="innerHTML"
                hx-trigger="click"
                hx-vals='{{"check_dependencies": "true"}}'
                onclick="openDeleteModeModal()"
            """,
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_scoringrule"), name="dispatch"
)
class ScoringRuleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for scoring rule
    """

    model = ScoringRule
    fields = ["name", "module", "description", "is_active"]
    full_width_fields = ["name", "module", "description"]
    modal_height = False

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:scoring_rule_update_form", kwargs={"pk": pk})
        return reverse_lazy("leads:scoring_rule_create_form")

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested data does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")

        return super().get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.delete_scoringrule", modal=True),
    name="dispatch",
)
class ScoringRuleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = ScoringRule

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(
    permission_required_or_denied("leads.view_scoringrule"), name="dispatch"
)
class ScoringRuleDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for user page
    """

    template_name = "scoring_rule/scoring_rule_detail_view.html"
    model = ScoringRule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_obj = self.get_object()
        scoring_criteria = ScoringCriterion.objects.filter(rule=current_obj)
        context["current_obj"] = current_obj
        context["scoring_criteria"] = scoring_criteria
        context["nav_url"] = reverse_lazy("leads:scoring_rule_detail_nav_view")
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return HttpResponse(headers={"HX-Refresh": "true"})
            raise HorillaHttp404(e)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("leads.view_scoringrule"), name="dispatch")
class ScoringRuleDetailNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar for scoring rule
    """

    search_url = reverse_lazy("leads:scoring_rule_list_view")
    main_url = reverse_lazy("leads:scoring_rule_view")
    filterset_class = ScoringRuleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "ScoringRule"
    model_app_label = "leads"
    nav_width = False
    gap_enabled = False
    url_name = "scoring_rule_list_view"
    search_option = False
    navbar_indication = True
    navbar_indication_attrs = {
        "hx-get": reverse_lazy("leads:scoring_rule_view"),
        "hx-target": "#scoring-rule-view",
        "hx-swap": "outerHTML",
        "hx-push-url": "true",
        "hx-select": "#scoring-rule-view",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.request.GET.get("obj")
        if obj_id:
            obj_id_clean = obj_id.split("?")[0].strip()
            try:
                obj_id_int = int(obj_id_clean)
                obj = ScoringRule.objects.filter(pk=obj_id_int).first()
                if obj:
                    self.nav_title = obj.name
                    context["nav_title"] = self.nav_title
            except ValueError:
                logger.error(f"Invalid obj_id parameter: {obj_id}")
        return context

    @cached_property
    def new_button(self):
        model_name = self.request.GET.get("model_name")
        obj = self.request.GET.get("obj")
        if self.request.user.has_perm("leads.add_scoringcriterion"):
            return {
                "url": f"""{ reverse_lazy('leads:scoring_rule_criteria_create_form')}?model_name={model_name}&obj={obj}""",
                "attrs": {"id": "scroring-criteria-create-form"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_scoringcriterion"), name="dispatch"
)
class ScoringCriterionCreateUpdateView(LoginRequiredMixin, HorillaSingleFormView):
    model = ScoringCriterion
    form_class = ScoringCriterionForm
    fields = ["rule", "points", "operation_type"]
    condition_fields = ["field", "operator", "value", "logical_operator"]
    condition_model = ScoringCondition
    condition_related_name = "conditions"
    condition_order_by = ["order"]
    hidden_fields = ["rule"]
    modal_height = False
    form_title = _("Create New Rule Criteria")
    save_and_new = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        model_name = self.request.GET.get("model_name") or self.request.POST.get(
            "model_name"
        )

        if self.object and self.object.rule:
            model_name = self.object.rule.module

        if model_name:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["model_name"] = model_name

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not self.kwargs.get("pk"):
            obj = self.request.GET.get("obj") or self.request.POST.get("obj")
            if obj:
                obj_clean = obj.split("?")[0].strip()
                try:
                    obj_id = int(obj_clean)
                    initial["rule"] = ScoringRule.objects.get(pk=obj_id)
                except (ValueError, ScoringRule.DoesNotExist) as e:
                    logger.error(f"Invalid obj parameter: {obj}, error: {e}")
                    pass
        return initial

    @cached_property
    def form_url(self):
        model_name = self.request.GET.get("model_name")
        obj = self.request.GET.get("obj")
        pk = self.kwargs.get("pk")
        if pk:
            base_url = reverse_lazy(
                "leads:scoring_rule_criteria_edit_form",
                kwargs={"pk": pk} if pk else None,
            )
        else:
            base_url = reverse_lazy("leads:scoring_rule_criteria_create_form")

        if model_name:
            return f"{base_url}?{urlencode({'model_name': model_name,'obj': obj})}"
        return base_url


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.delete_scoringcriterion", modal=True),
    name="dispatch",
)
class ScoringCriteriaDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = ScoringCriterion

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
class ScroringActiveToggleView(LoginRequiredMixin, View):
    """Toggle default dashboard for the current user via HTMX"""

    def post(self, request, *args, **kwargs):
        try:
            rule = ScoringRule.objects.get(pk=kwargs["pk"])
            user = request.user
            if user.has_perm("leads.change_scoringrule"):
                if not rule.is_active:
                    rule.is_active = True
                    messages.success(request, f"{rule.name} activated successfully")
                else:
                    rule.is_active = False
                    messages.success(request, f"{rule.name} deactivated successfully")
                rule.save()
                return HttpResponse("<script>$('#reloadButton').click();</script>")

        except Exception as e:
            messages.error(request, e)
            return HttpResponse(("<script>$('#reloadButton').click();</script>"))
