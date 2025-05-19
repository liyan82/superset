from datetime import datetime
from typing import Any, Optional

from flask_appbuilder.security.sqla.models import User
from sqlalchemy import Boolean, Column, String
from sqlalchemy.ext.declarative import declared_attr


class UserSubscriptionMixin:
    """Mixin that adds subscription fields to the User model"""

    @declared_attr
    def is_paid_user(self) -> Column:
        return Column(Boolean, default=False)

    @declared_attr
    def trial_used(self) -> Column:
        return Column(Boolean, default=False)

    @declared_attr
    def stripe_customer_id(self) -> Column:
        return Column(String(255), nullable=True)

    @property
    def has_active_subscription(self) -> bool:
        for subscription in self.subscriptions:  # type: ignore
            if subscription.is_valid():
                return True
        return False

    @property
    def current_subscription(self) -> Optional[Any]:
        active_subs = [
            sub
            for sub in self.subscriptions
            if sub.end_date and sub.end_date > datetime.now()
        ]
        if active_subs:
            # Sort by end_date in descending order and return the latest one
            active_subs.sort(key=lambda x: x.end_date, reverse=True)
            return active_subs[0]
        return None

    @property
    def subscription_features(self) -> dict[str, Any]:
        sub = self.current_subscription
        if sub and sub.plan and sub.plan.features:
            import json

            return json.loads(sub.plan.features)
        return {}


# Apply the mixin to User
User.__bases__ = (UserSubscriptionMixin,) + User.__bases__
