from flask_appbuilder.security.sqla.manager import SecurityManager
from flask import redirect, url_for, flash, g
from flask_babel import gettext as _

from superset.models.user import CustomUser


class SubscriptionSecurityManager(SecurityManager):
    user_model = CustomUser

    def is_subscription_valid_for_route(self, route):
        """Check if the current user's subscription allows access to a route"""
        # Implementation depends on your route protection scheme
        # For example, you could have a mapping of routes to required subscription levels

        # Skip checks for authentication-related routes
        auth_routes = ['/login', '/register', '/subscription']
        if any(route.startswith(auth_path) for auth_path in auth_routes):
            return True

        # Always allow admins full access
        if hasattr(g, 'user') and g.user and self.has_role(g.user, 'Admin'):
            return True

        # Check user's subscription for other routes
        if not hasattr(g, 'user') or not g.user or not g.user.has_active_subscription:
            return False

        # Here you could implement more granular access control based on subscription level
        return True

    def before_request(self):
        """
        Extend base method to check subscription status before allowing access
        """
        super().before_request()

        # If user is authenticated but doesn't have a valid subscription
        # redirect to subscription page for protected routes
        if hasattr(g, 'user') and g.user and g.user.is_authenticated:
            if not self.is_subscription_valid_for_route(request.path):
                flash(_("You need an active subscription to access this page"),
                      "warning")
                return redirect(url_for('SubscriptionView.subscribe'))
