from flask_appbuilder import BaseView, expose
from superset.superset_typing import FlaskResponse


class AttorneysView(BaseView):
    route_base = "/rankings"
    default_view = "attorneys"  # Set the default view to the index method

    @expose("/")
    @expose("/attorneys")
    def attorneys(self) -> FlaskResponse:
        return self.render_template("superset/top_attorneys.html") 

    @expose("/firms")
    def firms(self) -> FlaskResponse:
        return self.render_template("superset/top_firms.html")

    @expose("/companies")
    def companies(self) -> FlaskResponse:
        return self.render_template("superset/top_companies.html")
