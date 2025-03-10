from flask_appbuilder.security.sqla.models import User
from sqlalchemy import Column, Boolean, String
from sqlalchemy.ext.declarative import declared_attr
from flask_appbuilder import Model


# Option 1: Add columns to existing User class (recommended)
# This uses SQLAlchemy's declared_attr pattern for extensions

class UserSubscriptionMixin:
    """Mixin that adds subscription fields to the User model"""

    @declared_attr
    def is_paid_user(cls):
        return Column(Boolean, default=False)

    @declared_attr
    def trial_used(cls):
        return Column(Boolean, default=False)

    @declared_attr
    def stripe_customer_id(cls):
        return Column(String(255), nullable=True)

    # Property methods remain unchanged
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


# Apply the mixin to User
User.__bases__ = (UserSubscriptionMixin,) + User.__bases__
