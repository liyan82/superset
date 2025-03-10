from superset.initialization import SupersetAppInitializer


class SubscriptionAppInitializer(SupersetAppInitializer):
    """Custom initializer that adds subscription functionality to Superset."""

    def init_app_in_ctx(self) -> None:
        # First call the parent method to handle standard initialization
        super().init_app_in_ctx()

        # Then add subscription-specific initialization
        self.configure_subscription()

    def configure_subscription(self) -> None:
        """Set up subscription-related functionality."""
        appbuilder = self.superset_app.appbuilder

        # Import your views here to avoid circular imports
        from superset.views.subscription import (
            SubscriptionView,
        )
        from superset.views.admin import (
            SubscriptionPlanAdmin,
            UserSubscriptionAdmin,
            PaymentAdmin
        )

        # Initialize payment processor
        from superset.utils.payment import PaymentProcessor
        payment_processor = PaymentProcessor(self.superset_app)
        self.superset_app.payment_processor = payment_processor

        # Register subscription views
        appbuilder.add_view(
            SubscriptionView,
            "Subscription",
            category="Account"
        )
        appbuilder.add_view(
            SubscriptionPlanAdmin,
            "Subscription Plans",
            category="Admin"
        )
        appbuilder.add_view(
            UserSubscriptionAdmin,
            "User Subscriptions",
            category="Admin"
        )
        appbuilder.add_view(
            PaymentAdmin,
            "Payments",
            category="Admin"
        )
