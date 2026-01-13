from horilla.registry.feature import register_feature, register_model_for_feature

register_feature("activity_related", "activity_related_models")

register_model_for_feature(
    app_label="horilla_activity",
    model_name="Activity",
    features=["global_search", "dashboard_component"],
)
