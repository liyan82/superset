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

        # Initialize payment processor
        from superset.utils.payment import PaymentProcessor
        payment_processor = PaymentProcessor(self.superset_app)
        self.superset_app.payment_processor = payment_processor

        # Replace the default user model view with our subscription-enhanced version
        # init_subscription_user_views(self.superset_app, appbuilder)
