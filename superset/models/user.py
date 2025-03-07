from flask_appbuilder.security.sqla.models import User
from sqlalchemy import Column, Boolean


class CustomUser(User):
    """
    Extends the base User model with subscription-related fields
    """
    # You can add direct fields if needed
    is_paid_user = Column(Boolean, default=False)
    trial_used = Column(Boolean, default=False)

    # Use property methods for derived values
    @property
    def has_active_subscription(self):
        for subscription in self.subscriptions:
            if subscription.is_valid():
                return True
        return False

    @property
    def current_subscription(self):
        active_subs = [sub for sub in self.subscriptions if sub.is_valid()]
        if active_subs:
            return active_subs[0]
        return None

    @property
    def subscription_features(self):
        sub = self.current_subscription
        if sub and sub.plan and sub.plan.features:
            import json
            return json.loads(sub.plan.features)
        return {}
