# horilla_core/registry.py

import logging
from collections import defaultdict

from django.apps import apps

logger = logging.getLogger(__name__)

FEATURE_REGISTRY = defaultdict(list)

# Track models registered with all=True and their exclude lists
# Format: {model_class: set(excluded_features)}
ALL_FEATURES_MODELS = {}

# Track models that tried to use features before they were registered
# Format: {feature_name: [model_class, ...]}
PENDING_FEATURE_MODELS = defaultdict(list)

# Feature configuration mapping: feature_name -> registry_key
# Core features are defined here, but apps can register additional features
# using register_feature() without modifying this file
FEATURE_CONFIG = {
    "import_data": "import_models",
    "export_data": "export_models",
    "global_search": "global_search_models",
}


def register_feature(feature_name, registry_key=None):
    """
    Register a new feature dynamically from any app.

    Args:
        feature_name: Feature name (e.g., "workflow", "notification")
        registry_key: Registry key in FEATURE_REGISTRY (defaults to "{feature_name}_models")

    Example:
        register_feature("workflow")
        register_feature("notification", "notification_models")

    Returns:
        bool: True if registered, False if already exists
    """
    if registry_key is None:
        registry_key = f"{feature_name}_models"

    if feature_name in FEATURE_CONFIG:
        logger.warning(
            f"Feature '{feature_name}' is already registered. "
            f"Overwriting registry key from '{FEATURE_CONFIG[feature_name]}' to '{registry_key}'"
        )
        FEATURE_CONFIG[feature_name] = registry_key
        return False
    else:
        FEATURE_CONFIG[feature_name] = registry_key
        logger.info(f"Registered new feature '{feature_name}' -> '{registry_key}'")

        # Register this new feature for all models that were registered with all=True
        # (unless they excluded this feature)
        for model_class, excluded_features in ALL_FEATURES_MODELS.items():
            if feature_name not in excluded_features:
                if model_class not in FEATURE_REGISTRY[registry_key]:
                    FEATURE_REGISTRY[registry_key].append(model_class)
                    logger.debug(
                        f"Auto-registered model {model_class.__name__} for new feature '{feature_name}' "
                        f"(was registered with all=True)"
                    )

        # Register models that tried to use this feature before it was registered
        if feature_name in PENDING_FEATURE_MODELS:
            for model_class in PENDING_FEATURE_MODELS[feature_name]:
                if model_class not in FEATURE_REGISTRY[registry_key]:
                    FEATURE_REGISTRY[registry_key].append(model_class)
                    logger.debug(
                        f"Registered model {model_class.__name__} for feature '{feature_name}' "
                        f"(was pending before feature registration)"
                    )
            # Clear pending list for this feature
            del PENDING_FEATURE_MODELS[feature_name]

        return True


def register_model_for_feature(
    model_class=None,
    app_label=None,
    model_name=None,
    features=None,
    all=False,
    exclude=None,
    **kwargs,
):
    """
    Register an existing model for specific features without modifying the model file.

    Args:
        model_class: Model class (optional if app_label/model_name provided)
        app_label: App label (e.g., "horilla_core")
        model_name: Model name (e.g., "User")
        features: Feature name(s) as list or string
        all: Enable all features if True
        exclude: Features to exclude when all=True
        **kwargs: Legacy boolean flags (global_search=True, etc.)

    Example:
        register_model_for_feature(
            app_label="horilla_core",
            model_name="User",
            features=["global_search"]
        )
        register_model_for_feature(
            app_label="horilla_calendar",
            model_name="Event",
            all=True
        )

    Returns:
        bool: True if registered, False otherwise
    """
    # Determine which model to register
    if model_class is None:
        if app_label is None or model_name is None:
            logger.error(
                "register_model_for_feature: Must provide either model_class or both "
                "app_label and model_name"
            )
            return False

        try:
            model_class = apps.get_model(app_label, model_name)
        except LookupError as e:
            logger.error(
                f"register_model_for_feature: Model '{app_label}.{model_name}' not found: {e}"
            )
            return False
    else:
        # Use model class directly
        app_label = model_class._meta.app_label
        model_name = model_class.__name__

    # Determine which features to enable
    enabled_features = set()
    exclude_set = set()

    # Handle 'all' flag - enable all features
    if all:
        # Track this model in ALL_FEATURES_MODELS for future feature auto-registration
        if exclude is not None:
            exclude_list = [exclude] if isinstance(exclude, str) else exclude
            exclude_set = set(exclude_list)
        ALL_FEATURES_MODELS[model_class] = exclude_set

        # Enable all currently registered features
        enabled_features.update(FEATURE_CONFIG.keys())

    # New way: using features parameter
    if features is not None:
        if isinstance(features, str):
            features = [features]
        enabled_features.update(features)

    # Legacy way: check boolean keyword arguments
    legacy_features = {
        "import_data": kwargs.get("import_data", False),
        "export_data": kwargs.get("export_data", False),
        "global_search": kwargs.get("global_search", False),
    }

    for feature_name, enabled in legacy_features.items():
        if enabled:
            enabled_features.add(feature_name)

    # Check kwargs for any dynamically registered features
    for feature_name, enabled in kwargs.items():
        if enabled and isinstance(enabled, bool) and enabled:
            if feature_name in FEATURE_CONFIG:
                enabled_features.add(feature_name)

    # Apply exclusions
    if exclude is not None:
        if isinstance(exclude, str):
            exclude = [exclude]
        enabled_features -= set(exclude)

    if not enabled_features:
        logger.warning(
            f"register_model_for_feature: No features specified for model "
            f"{app_label}.{model_name}"
        )
        # Even if no features to register now, return True if all=True (for tracking)
        return all

    # Register model for each enabled feature
    registered = False
    for feature_name in enabled_features:
        if feature_name in FEATURE_CONFIG:
            registry_key = FEATURE_CONFIG[feature_name]
            if model_class not in FEATURE_REGISTRY[registry_key]:
                FEATURE_REGISTRY[registry_key].append(model_class)
                registered = True
                logger.info(
                    f"Registered model {app_label}.{model_name} for feature '{feature_name}'"
                )
            else:
                logger.debug(
                    f"Model {app_label}.{model_name} already registered for feature '{feature_name}'"
                )
        else:
            logger.warning(
                f"Unknown feature '{feature_name}' for model {app_label}.{model_name}. "
                f"Make sure to register it using register_feature('{feature_name}')"
            )

    return registered


def register_models_for_feature(
    models, features=None, all=False, exclude=None, **kwargs
):
    """
    Register multiple models at once with the same features.

    Args:
        models: List of models as tuples [("app_label", "model_name")],
                model classes, or dicts [{"app_label": "...", "model_name": "..."}]
        features: Feature name(s) as list or string
        all: Enable all features if True
        exclude: Features to exclude when all=True
        **kwargs: Legacy boolean flags

    Example:
        register_models_for_feature(
            models=[
                ("horilla_core", "User"),
                ("horilla_activity", "Activity"),
                ("horilla_calendar", "Event"),
            ],
            features=["global_search", "import_data"]
        )
        register_models_for_feature(
            models=[("horilla_core", "User"), ("horilla_activity", "Activity")],
            all=True,
            exclude=["export_data"]
        )

    Returns:
        dict: Summary with "registered", "failed", and "total" keys
    """
    registered_models = []
    failed_models = []

    # Normalize models list
    normalized_models = []
    for model in models:
        if isinstance(model, tuple) and len(model) == 2:
            # Tuple format: (app_label, model_name)
            normalized_models.append({"app_label": model[0], "model_name": model[1]})
        elif isinstance(model, dict):
            # Dict format: {"app_label": "...", "model_name": "..."}
            normalized_models.append(model)
        else:
            # Assume it's a model class
            try:
                normalized_models.append({"model_class": model})
            except Exception:
                failed_models.append(str(model))
                logger.error(
                    f"register_models_for_feature: Invalid model format: {model}"
                )
                continue

    # Register each model
    for model_info in normalized_models:
        try:
            if "model_class" in model_info:
                # Use model class directly
                result = register_model_for_feature(
                    model_class=model_info["model_class"],
                    features=features,
                    all=all,
                    exclude=exclude,
                    **kwargs,
                )
                model_identifier = f"{model_info['model_class']._meta.app_label}.{model_info['model_class'].__name__}"
            else:
                # Use app_label and model_name
                result = register_model_for_feature(
                    app_label=model_info["app_label"],
                    model_name=model_info["model_name"],
                    features=features,
                    all=all,
                    exclude=exclude,
                    **kwargs,
                )
                model_identifier = (
                    f"{model_info['app_label']}.{model_info['model_name']}"
                )

            if result:
                registered_models.append(model_identifier)
            else:
                failed_models.append(model_identifier)

        except Exception as e:
            model_identifier = str(model_info)
            failed_models.append(model_identifier)
            logger.error(
                f"register_models_for_feature: Failed to register {model_identifier}: {e}"
            )

    result_summary = {
        "registered": registered_models,
        "failed": failed_models,
        "total": len(normalized_models),
    }

    logger.info(
        f"register_models_for_feature: Registered {len(registered_models)}/{len(normalized_models)} models"
    )

    return result_summary


def feature_enabled(
    *,
    all=False,
    features=None,
    exclude=None,
    import_data=False,
    export_data=False,
    global_search=False,
    **kwargs,
):
    """
    Decorator to register models for specific features.

    Supports both core features and dynamically registered features.

    Example:
        @feature_enabled(features=["import_data", "export_data"])
        @feature_enabled(all=True, exclude=["import_data"])
        @feature_enabled(global_search=True)
        @feature_enabled(global_search=True, dashboard_component=True)  # Works for dynamically registered features
        @feature_enabled(mail_template=True, activity_related=True)  # Works for dynamically registered features
    """

    def decorator(model_class):
        # Determine which features to enable
        enabled_features = set()

        # Track exclude list for all=True models
        exclude_set = set()

        # New way: using features parameter (list of strings)
        if features is not None:
            features_list = [features] if isinstance(features, str) else features
            enabled_features.update(features_list)

        # Backward compatibility: check old keyword arguments
        legacy_features = {
            "import_data": import_data,
            "export_data": export_data,
            "global_search": global_search,
        }

        # If any legacy features are explicitly set, add them
        for feature_name, enabled in legacy_features.items():
            if enabled:
                enabled_features.add(feature_name)

        # Check kwargs for any dynamically registered features
        # Any kwargs that are True and exist in FEATURE_CONFIG are treated as feature flags
        for feature_name, enabled in kwargs.items():
            if enabled and isinstance(enabled, bool) and enabled:
                # Check if this is a registered feature
                if feature_name in FEATURE_CONFIG:
                    enabled_features.add(feature_name)
                else:
                    # Feature not registered yet - track it for later registration
                    if model_class not in PENDING_FEATURE_MODELS[feature_name]:
                        PENDING_FEATURE_MODELS[feature_name].append(model_class)
                    logger.debug(
                        f"Feature '{feature_name}' not yet registered for model {model_class.__name__}. "
                        f"Will register when feature is registered."
                    )

        # Handle 'all' flag
        if all:
            # Track this model for future feature registrations
            exclude_list = []
            if exclude is not None:
                exclude_list = [exclude] if isinstance(exclude, str) else exclude
            exclude_set = set(exclude_list)
            ALL_FEATURES_MODELS[model_class] = exclude_set

            enabled_features.update(FEATURE_CONFIG.keys())

        # Apply exclusions
        enabled_features -= exclude_set

        # Register model for each enabled feature
        for feature_name in enabled_features:
            if feature_name in FEATURE_CONFIG:
                registry_key = FEATURE_CONFIG[feature_name]
                if model_class not in FEATURE_REGISTRY[registry_key]:
                    FEATURE_REGISTRY[registry_key].append(model_class)
            else:
                logger.warning(
                    f"Unknown feature '{feature_name}' for model {model_class.__name__}. "
                    f"Make sure to register it using register_feature('{feature_name}') "
                    f"in your app's ready() method or models.py"
                )

        return model_class

    return decorator
