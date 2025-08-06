import logging
import time
import uuid
from datetime import datetime
from threading import Thread
from typing import Any

from flask import current_app, request
from flask_appbuilder import permission_name
from flask_appbuilder.api import expose, safe
from flask_appbuilder.security.decorators import has_access
from flask_appbuilder.security.sqla.models import User
from marshmallow import fields, Schema, ValidationError

from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.extensions import db
from superset.superset_typing import FlaskResponse
from superset.utils import json
from superset.utils.core import send_email_smtp
from superset.views.base import json_error_response, json_success
from superset.views.base_api import BaseSupersetApi, statsd_metrics

from .base import BaseSupersetView

logger = logging.getLogger(__name__)


class NewsletterSendSchema(Schema):
    subject = fields.String(required=True)
    recipient_ids = fields.List(fields.Integer(), required=True)
    html_body = fields.String(required=True)


class NewsletterProgressSchema(Schema):
    session_id = fields.String(required=True)


# In-memory store for progress tracking (in production, use Redis)
newsletter_progress = {}


class NewsletterView(BaseSupersetView):
    route_base = "/newsletter"
    class_permission_name = "Newsletter"

    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP

    @expose("/", methods=["GET"])
    @has_access
    @permission_name("read")
    def root(self, **kwargs: Any) -> FlaskResponse:
        """Handles the default Newsletter page."""
        return self.render_app_template()


class NewsletterApi(BaseSupersetApi):
    """API for newsletter operations"""

    route_base = "/api/v1/newsletter"
    class_permission_name = "Newsletter"
    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP
    openapi_spec_tag = "Newsletter"

    def _generate_unsubscribe_link(self, user_id: int, session_id: str) -> str:
        """Generate unsubscribe link with user-specific token"""
        token = f"{user_id}_{session_id}_{uuid.uuid4().hex[:8]}"
        base_url = current_app.config.get(
            "SUPERSET_WEBSERVER_ADDRESS", "http://localhost:8088"
        )
        return f"{base_url}/newsletter/unsubscribe?token={token}"

    def _process_email_template(
        self, html_content: str, user: User, session_id: str
    ) -> str:
        """Process email template with user-specific variables"""
        # Replace user variables
        html_content = html_content.replace(
            "{user_first_name}", user.first_name or ""
        )
        html_content = html_content.replace(
            "{user_last_name}", user.last_name or ""
        )
        html_content = html_content.replace(
            "{user_username}", user.username or ""
        )
        html_content = html_content.replace("{user_email}", user.email or "")

        # Add unsubscribe link
        unsubscribe_link = self._generate_unsubscribe_link(user.id, session_id)
        html_content = html_content.replace(
            "{unsubscribe_link}", unsubscribe_link
        )

        # If no unsubscribe link placeholder exists, add one at the bottom
        if "{unsubscribe_link}" not in html_content:
            unsubscribe_footer = (
                '<div style="margin-top: 40px; padding-top: 20px; '
                'border-top: 1px solid #ccc; font-size: 12px; color: #666;">'
                f'<a href="{unsubscribe_link}">Unsubscribe from newsletters</a>'
                '</div>'
            )
            # Try to add before closing body tag, otherwise append
            if "</body>" in html_content:
                html_content = html_content.replace(
                    "</body>", f"{unsubscribe_footer}</body>"
                )
            else:
                html_content += unsubscribe_footer

        return html_content

    def _send_email_with_retry(self, user: User, subject: str, html_content: str, session_id: str, max_retries: int = 3) -> bool:
        """Send email with retry logic"""
        for attempt in range(max_retries):
            try:
                processed_content = self._process_email_template(html_content, user, session_id)

                # Prepare config with proper SMTP mapping (same as password reset)
                config = current_app.config.copy()
                smtp_config_mapping = {
                    "SMTP_HOST": config.get("MAIL_SERVER", "localhost"),
                    "SMTP_PORT": config.get("MAIL_PORT", 587),
                    "SMTP_STARTTLS": config.get("MAIL_USE_TLS", True),
                    "SMTP_SSL": config.get("MAIL_USE_SSL", False),
                    "SMTP_USER": config.get("MAIL_USERNAME", ""),
                    "SMTP_PASSWORD": config.get("MAIL_PASSWORD", ""),
                    "SMTP_MAIL_FROM": config.get("MAIL_DEFAULT_SENDER", "noreply@localhost"),
                }

                # Update config with mapped values
                config.update(smtp_config_mapping)

                send_email_smtp(
                    to=user.email,
                    subject=subject,
                    html_content=processed_content,
                    config=config,
                    dryrun=False
                )

                logger.info(f"Newsletter sent successfully to {user.email} on attempt {attempt + 1}")
                return True

            except Exception as e:
                logger.warning(f"Failed to send newsletter to {user.email} on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to send newsletter to {user.email} after {max_retries} attempts")

        return False

    @expose("/send", methods=["POST"])
    @safe
    @statsd_metrics
    def send_newsletter(self) -> FlaskResponse:
        """Send newsletter to selected users"""
        try:
            # Parse and validate request data
            json_data = request.get_json()
            if not json_data:
                return json_error_response("No JSON data provided", status=400)

            schema = NewsletterSendSchema()
            try:
                data = schema.load(json_data)
            except ValidationError as e:
                return json_error_response(f"Validation error: {e.messages}", status=400)

            # Get users
            try:
                users = db.session.query(User).filter(
                    User.id.in_(data["recipient_ids"]),
                    User.active.is_(True),
                    User.email.isnot(None)
                ).all()
            except Exception as e:
                logger.error(f"Error fetching users: {str(e)}")
                return json_error_response("Error fetching users", status=500)

            if not users:
                return json_error_response("No valid users found", status=400)

            # Generate session ID for tracking
            session_id = str(uuid.uuid4())

            # Initialize progress tracking
            newsletter_progress[session_id] = {
                "total": len(users),
                "sent": 0,
                "failed": 0,
                "failed_emails": [],
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
                "percentage": 0
            }

            # Capture the app instance before starting the thread
            app = current_app._get_current_object()

            # Start background email sending with Flask context
            def send_emails_background():
                """Background task to send emails with real-time progress updates"""
                # Use the captured app instance to create context in the thread
                with app.app_context():
                    try:
                        for i, user in enumerate(users):
                            if not user.email:
                                newsletter_progress[session_id]["failed"] += 1
                                newsletter_progress[session_id]["failed_emails"].append({"email": "N/A", "reason": "No email address"})
                            else:
                                success = self._send_email_with_retry(
                                    user=user,
                                    subject=data["subject"],
                                    html_content=data["html_body"],
                                    session_id=session_id
                                )

                                if success:
                                    newsletter_progress[session_id]["sent"] += 1
                                else:
                                    newsletter_progress[session_id]["failed"] += 1
                                    newsletter_progress[session_id]["failed_emails"].append({
                                        "email": user.email,
                                        "reason": "SMTP delivery failed after retries"
                                    })

                            # Update progress percentage after each email
                            processed = newsletter_progress[session_id]["sent"] + newsletter_progress[session_id]["failed"]
                            newsletter_progress[session_id]["percentage"] = (processed / newsletter_progress[session_id]["total"]) * 100

                            logger.info(f"Newsletter progress: {processed}/{newsletter_progress[session_id]['total']} emails processed")

                            # Small delay to avoid overwhelming SMTP server
                            time.sleep(0.5)

                        # Mark as completed
                        newsletter_progress[session_id]["status"] = "completed"
                        newsletter_progress[session_id]["completed_at"] = datetime.now().isoformat()

                    except Exception as e:
                        logger.error(f"Background email sending failed: {str(e)}")
                        newsletter_progress[session_id]["status"] = "failed"
                        newsletter_progress[session_id]["error"] = str(e)

            # Start the background thread
            email_thread = Thread(target=send_emails_background)
            email_thread.daemon = True
            email_thread.start()

            # Return immediately with session_id
            return json_success(json.dumps({
                "message": "Newsletter sending started in background",
                "session_id": session_id,
                "status": "started"
            }, default=json.json_int_dttm_ser))

        except Exception as e:
            logger.error(f"Error sending newsletter: {str(e)}")
            return json_error_response("Internal server error", status=500)

    @expose("/progress/<string:session_id>", methods=["GET"])
    @safe
    def get_progress(self, session_id: str) -> FlaskResponse:
        """Get sending progress for a newsletter session"""
        if session_id not in newsletter_progress:
            return json_error_response("Session not found", status=404)

        progress_data = newsletter_progress[session_id].copy()
        # Use stored percentage if available, otherwise calculate it
        if "percentage" not in progress_data:
            progress_data["percentage"] = (
                (progress_data["sent"] + progress_data["failed"]) / progress_data["total"] * 100
                if progress_data["total"] > 0 else 0
            )

        return json_success(json.dumps(progress_data, default=json.json_int_dttm_ser))
