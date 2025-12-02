"""
Signal handlers for leads in Horilla CRM.
Handles automatic updates when company-related events occur, e.g., currency change.
"""

from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django.http import HttpResponse
from django.urls import reverse_lazy

from horilla_core.models import HorillaUser
from horilla_core.signals import company_created, company_currency_changed
from horilla_crm.leads.models import Lead
from horilla_keys.models import ShortcutKey

lead_stage_created = Signal()


@receiver(company_created)
def handle_company_created(sender, instance, request, view, is_new, **kwargs):
    """Inject lead stages loading after company creation"""
    if is_new:  # Only for new companies
        return HttpResponse(
            """
            <script>
                closeModal();
                $('#reloadButton').click();
                openContentModal();
                var div = document.createElement('div');
                div.setAttribute('hx-get', '%s');
                div.setAttribute('hx-target', '#contentModalBox');
                div.setAttribute('hx-trigger', 'load');
                div.setAttribute('hx-swap', 'innerHTML');
                document.body.appendChild(div);
                htmx.process(div);
            </script>
            """
            % reverse_lazy(
                "leads:load_lead_stages", kwargs={"company_id": instance.id}
            ),
            headers={"X-Debug": "Modal transition in progress"},
        )
    return None


@receiver(company_currency_changed)
def update_crm_on_currency_change(sender, **kwargs):
    """
    Updates Lead amounts when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    leads_to_update = []
    leads = (
        Lead.objects.filter(company=company)
        .select_related()
        .only("id", "annual_revenue")
    )

    for lead in leads:
        if lead.annual_revenue is not None:
            lead.annual_revenue = lead.annual_revenue * conversion_rate
            leads_to_update.append(lead)

    if leads_to_update:
        Lead.objects.bulk_update(leads_to_update, ["annual_revenue"], batch_size=1000)


@receiver(post_save, sender=HorillaUser)
def create_leads_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/leads/leads-view/", "key": "E", "command": "alt"},
    ]

    for item in predefined:
        if not ShortcutKey.objects.filter(user=instance, page=item["page"]).exists():
            ShortcutKey.objects.create(
                user=instance,
                page=item["page"],
                key=item["key"],
                command=item["command"],
                company=instance.company,
            )
