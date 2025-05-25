from superset.initialization import SupersetAppInitializer


class SubscriptionAppInitializer(SupersetAppInitializer):
    """Custom initializer that adds subscription functionality to Superset."""

    def init_app_in_ctx(self) -> None:
        # First call the parent method to handle standard initialization
        super().init_app_in_ctx()

        # Then add subscription-specific initialization
        self.configure_subscription()

    def configure_subscription(self) -> None:
        pass
