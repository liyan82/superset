from flask_appbuilder.security.views import AuthDBView
from flask_babel import lazy_gettext


class CustomAuthDBView(AuthDBView):
    """
    Custom AuthDBView to use a custom login template.
    """

    login_template = "login.html"
    title = lazy_gettext("Sign In to Superset") 