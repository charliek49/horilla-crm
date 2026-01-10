"""
Feature registration for Horilla Core app.
"""

from horilla.registry.feature import register_models_for_feature

register_models_for_feature(
    models=[
        ("horilla_core", "Company"),
        ("horilla_core", "Department"),
        ("horilla_core", "Role"),
        ("horilla_core", "HorillaUser"),
    ],
    all=True,
    exclude=["dashboard_component", "report_choices"]
)

