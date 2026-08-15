# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""App initializer and index view for patent1024.

Both customizations hang off documented upstream hooks rather than edits to
upstream modules, so syncing with apache/superset stays a mechanical merge:

* ``APP_INITIALIZER`` is read by ``superset.app.create_app``.
* ``FAB_INDEX_VIEW`` is read by Flask-AppBuilder's ``AppBuilder.init_app`` and
  takes precedence over the ``appbuilder.indexview`` that Superset sets.

Wire both up from ``superset_config.py``::

    from superset.patent1024.initializer import Patent1024AppInitializer

    APP_INITIALIZER = Patent1024AppInitializer
    FAB_INDEX_VIEW = "superset.patent1024.initializer.Patent1024IndexView"
"""

import logging
import os
from typing import Any

from flask import (
    abort,
    current_app,
    g,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_appbuilder import expose

# lazy_gettext: initialization happens before the request scope exists.
from flask_babel import lazy_gettext as _

from superset.extensions import appbuilder, csrf
from superset.initialization import SupersetAppInitializer, SupersetIndexView
from superset.superset_typing import FlaskResponse

logger = logging.getLogger(__name__)

# Slug -> metadata for the marketing blog. ``template`` resolves under
# ``superset/templates/superset/``.
BLOG_POSTS: dict[str, dict[str, str]] = {
    "patent-filing-trends-2024": {
        "title": "USPTO Patent Filing Trends & Statistics for 2024",
        "date": "2025-01-15",
        "excerpt": (
            "Comprehensive analysis of 2024 patent filing patterns, technology "
            "trends, and USPTO statistics revealing key insights for IP "
            "professionals."
        ),
        "template": "blog_patent_trends.html",
    },
    "top-patent-law-firms-rankings": {
        "title": "Top Patent Law Firms Rankings: Performance Analysis 2024",
        "date": "2025-01-15",
        "excerpt": (
            "Data-driven analysis of leading patent law firms, success rates, "
            "and prosecution strategies based on USPTO filing data."
        ),
        "template": "blog_law_firm_rankings.html",
    },
    "ai-technology-patent-landscape": {
        "title": "AI Technology Patent Landscape: Innovation Trends & Key Players",
        "date": "2025-01-15",
        "excerpt": (
            "Deep dive into artificial intelligence patent filings, major "
            "companies, and emerging technology trends shaping the IP landscape."
        ),
        "template": "blog_ai_patents.html",
    },
}


def _spa_response(view: Any) -> FlaskResponse:
    """Render the React SPA shell with the standard bootstrap payload.

    Builds the context through get_spa_template_context rather than assembling
    it by hand: spa.html also needs theme_tokens, spinner_svg, default_title and
    the language-pack vars, and rendering without them raises UndefinedError.
    """
    from superset.views.base import get_spa_template_context

    context = get_spa_template_context("spa")
    return view.render_template("superset/spa.html", **context)


class Patent1024IndexView(SupersetIndexView):
    """Public marketing homepage plus the SEO and password-reset routes.

    Upstream's index redirects straight to ``Superset.welcome``; anonymous
    visitors should land on the marketing page instead.
    """

    @expose("/")
    def index(self) -> FlaskResponse:
        if g.user is not None and g.user.is_authenticated:
            return redirect(url_for("Superset.welcome"))
        return render_template("superset/public_index.html")

    # -- Password reset (rendered by the SPA) --------------------------------

    @expose("/forgot-password/")
    def forgot_password(self) -> FlaskResponse:
        return _spa_response(self)

    @expose("/reset-password/")
    def reset_password(self) -> FlaskResponse:
        return _spa_response(self)

    # -- Marketing / SEO landing pages ---------------------------------------

    @expose("/patent-analytics-software/")
    def patent_analytics_software(self) -> FlaskResponse:
        return render_template("superset/patent_analytics_software.html")

    @expose("/uspto-data-analysis/")
    def uspto_data_analysis(self) -> FlaskResponse:
        return render_template("superset/uspto_data_analysis.html")

    @expose("/patent-portfolio-intelligence/")
    def patent_portfolio_intelligence(self) -> FlaskResponse:
        return render_template("superset/patent_portfolio_intelligence.html")

    @expose("/ai-patent-search/")
    def ai_patent_search(self) -> FlaskResponse:
        return render_template("superset/ai_patent_search.html")

    @expose("/free-patent-analytics-report/")
    def patent_report(self) -> FlaskResponse:
        return render_template("superset/report_landing.html")

    @expose("/blog/")
    def blog_index(self) -> FlaskResponse:
        return render_template("superset/blog_index.html")

    @expose("/blog/<string:slug>/")
    def blog_post(self, slug: str) -> FlaskResponse:
        post = BLOG_POSTS.get(slug)
        if post is None:
            abort(404)

        # Some posts are listed before their template has been written. Treat a
        # missing template as "not published yet" rather than a 500 on a page
        # that search engines crawl.
        template = f"superset/{post['template']}"
        try:
            current_app.jinja_env.get_template(template)
        except Exception:  # noqa: BLE001 - jinja2.TemplateNotFound and friends
            logger.warning("Blog post %s has no template %s", slug, template)
            abort(404)

        return render_template(template, post=post, slug=slug)

    # -- Crawler files -------------------------------------------------------

    @expose("/robots.txt")
    def robots_txt(self) -> FlaskResponse:
        static_dir = os.path.join(current_app.root_path, "static")
        return send_from_directory(static_dir, "robots.txt", mimetype="text/plain")

    @expose("/sitemap.xml")
    def sitemap_xml(self) -> FlaskResponse:
        static_dir = os.path.join(current_app.root_path, "static")
        return send_from_directory(
            static_dir, "sitemap.xml", mimetype="application/xml"
        )


class Patent1024AppInitializer(SupersetAppInitializer):
    """Register the patent1024 views, APIs and menu links on top of upstream."""

    def init_views(self) -> None:
        super().init_views()

        from superset.views.ai_query import AIQueryView
        from superset.views.attorneys import AttorneysView
        from superset.views.newsletter import NewsletterApi, NewsletterView
        from superset.views.password_reset_api import PasswordResetApi
        from superset.views.stripe_webhook import StripeWebhookView

        app_root = self.config["APPLICATION_ROOT"].rstrip("/")

        appbuilder.add_api(NewsletterApi)
        appbuilder.add_api(PasswordResetApi)

        self._init_subscription_views()

        appbuilder.add_view_no_menu(AIQueryView)
        appbuilder.add_view_no_menu(NewsletterView)
        appbuilder.add_view_no_menu(AttorneysView)
        # Registered regardless of ENABLE_SUBSCRIPTIONS: Stripe retries webhooks
        # for days, so unregistering the endpoint would drop events for any
        # subscription that is still live on the Stripe side.
        appbuilder.add_view_no_menu(StripeWebhookView)

        appbuilder.add_link(
            "AI Query",
            label=_("AI Query"),
            href=f"{app_root}/ai-query/",
            icon="fa-robot",
        )
        appbuilder.add_link(
            "Newsletter",
            label=_("Newsletter"),
            href=f"{app_root}/newsletter/",
            icon="fa-newspaper",
        )

    def _init_subscription_views(self) -> None:
        """Register the Stripe subscription views, when the feature is enabled.

        Gated on ENABLE_SUBSCRIPTIONS. Leaving the views unregistered is what
        keeps the menu entries hidden AND keeps Flask-AppBuilder from
        (re)creating their permissions, so they cannot be granted to a role.
        Existing grants from earlier boots have to be cleared separately --
        see `superset fab security-cleanup`.
        """
        if not self.config.get("ENABLE_SUBSCRIPTIONS", False):
            logger.info("ENABLE_SUBSCRIPTIONS is off; skipping subscription views")
            return

        from superset.views.admin import (
            PaymentAdmin,
            SubscriptionPlanAdmin,
            UserSubscriptionAdmin,
        )
        from superset.views.subscription import SubscriptionView

        appbuilder.add_view(SubscriptionView, "Subscription", category="Account")
        appbuilder.add_view(
            SubscriptionPlanAdmin, "Subscription Plans", category="Admin"
        )
        appbuilder.add_view(
            UserSubscriptionAdmin, "User Subscriptions", category="Admin"
        )
        appbuilder.add_view(PaymentAdmin, "Payments", category="Admin")

    def configure_wtf(self) -> None:
        super().configure_wtf()
        if self.config["WTF_CSRF_ENABLED"]:
            # Stripe signs its webhooks itself; a CSRF token cannot be supplied.
            csrf.exempt("/stripe-webhook/")
