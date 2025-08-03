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

import logging
from datetime import datetime
from typing import Any, Optional

from flask import current_app
from flask_appbuilder.security.sqla.models import User
from werkzeug.security import generate_password_hash

from superset import db
from superset.commands.base import BaseCommand
from superset.models.password_reset import PasswordResetToken
from superset.utils.password_reset import PasswordResetTokenManager

logger = logging.getLogger(__name__)


class RequestPasswordResetCommand(BaseCommand):
    """Command to handle password reset requests"""

    def __init__(self, email: str):
        self._email = email.lower().strip()

    def run(self) -> bool:
        """
        Process password reset request.
        Always returns True to prevent email enumeration.
        """
        try:
            logger.info(f"Processing password reset request for email: {self._email}")

            user = self._get_user_by_email(self._email)
            if user:
                logger.info(
                    f"Found user for email {self._email}: {user.username} "
                    f"(ID: {user.id})"
                )

                reset_token = self._create_reset_token(user)
                logger.info(f"Created reset token for user {user.username}")

                self._send_reset_email(user, reset_token)
                logger.info(f"Completed email send process for user {user.username}")
            else:
                logger.info(f"No user found for email: {self._email}")

            # Always return True to prevent email enumeration
            return True

        except Exception as ex:
            logger.error(
                f"Error processing password reset request: {ex}", exc_info=True
            )
            # Still return True to prevent information leakage
            return True

    def validate(self) -> None:
        """Validate the command input"""
        if not self._email:
            raise ValueError("Email is required")

        # Basic email format validation
        if "@" not in self._email or "." not in self._email:
            raise ValueError("Invalid email format")

    def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return (
            db.session.query(User)
            .filter(
                User.email == email,
                User.active,  # Only active users can reset passwords
            )
            .first()
        )

    def _create_reset_token(self, user: User) -> PasswordResetToken:
        """Create a new password reset token"""
        # Invalidate any existing tokens for this user
        existing_tokens = (
            db.session.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user.id, ~PasswordResetToken.is_used)
            .all()
        )

        for token in existing_tokens:
            token.mark_as_used()

        # Generate new token
        token, token_hash = PasswordResetTokenManager.generate_token(
            user.id, current_app.config.get("RESET_PASSWORD_TOKEN_EXPIRY_HOURS", 1)
        )

        # Store token in database
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_in_hours=current_app.config.get(
                "RESET_PASSWORD_TOKEN_EXPIRY_HOURS", 1
            ),
        )

        db.session.add(reset_token)
        db.session.commit()

        # Store the actual token for email sending
        reset_token._token = token
        return reset_token

    def _send_reset_email(self, user: User, reset_token: PasswordResetToken) -> None:
        """Send password reset email using Superset's core email utility"""
        try:
            from superset.utils.core import send_email_smtp

            logger.info(f"Starting email send process for user: {user.email}")

            reset_url = self._build_reset_url(reset_token._token)
            logger.info(f"Generated reset URL: {reset_url}")

            email_content = self._render_email_template(user, reset_url)
            logger.info(f"Email content length: {len(email_content)} characters")

            # Ensure we have the correct email configuration
            config = current_app.config.copy()

            # Map Flask-Mail config to what send_email_smtp expects
            smtp_config_mapping = {
                "SMTP_HOST": config.get("MAIL_SERVER", "localhost"),
                "SMTP_PORT": config.get("MAIL_PORT", 587),
                "SMTP_STARTTLS": config.get("MAIL_USE_TLS", True),
                "SMTP_SSL": config.get("MAIL_USE_SSL", False),
                "SMTP_USER": config.get("MAIL_USERNAME", ""),
                "SMTP_PASSWORD": config.get("MAIL_PASSWORD", ""),
                "SMTP_MAIL_FROM": config.get(
                    "MAIL_DEFAULT_SENDER", "noreply@localhost"
                ),
            }

            # Update config with mapped values
            config.update(smtp_config_mapping)

            logger.info(f"Using SMTP config: {smtp_config_mapping}")

            # Send email
            send_email_smtp(
                to=user.email,
                subject="Reset your Superset password",
                html_content=email_content,
                config=config,
            )

            logger.info(f"Password reset email sent successfully to {user.email}")

        except Exception as ex:
            logger.error(f"Exception during email send: {ex}", exc_info=True)

    def _build_reset_url(self, token: str) -> str:
        """Build the password reset URL"""
        # Use the correct base URL for the nginx proxy setup
        base_url = "http://localhost"  # nginx serves on port 80
        return f"{base_url}/reset-password/?token={token}"

    def _render_email_template(self, user: User, reset_url: str) -> str:
        """Render the email template"""
        from flask import render_template

        expiry_hours = current_app.config.get("RESET_PASSWORD_TOKEN_EXPIRY_HOURS", 1)
        base_url = current_app.config.get(
            "SUPERSET_WEBSERVER_ADDRESS", "http://localhost:8088"
        )
        logo_url = f"{base_url}/static/assets/images/patent-1024.png"

        try:
            return render_template(
                "email/password_reset.html",
                user_name=user.first_name or user.username,
                reset_url=reset_url,
                expiry_hours=expiry_hours,
                logo_url=logo_url,
            )
        except Exception as ex:
            logger.warning(f"Failed to render email template, using fallback: {ex}")
            # Fallback to simple HTML if template rendering fails
            return (
                "<html><body style='font-family: Arial, sans-serif;'>"
                f"<h2>Reset Your Password</h2>"
                f"<p>Hello {user.first_name or user.username},</p>"
                f"<p>Click <a href='{reset_url}'>here</a> to reset your password.</p>"
                f"<p>This link expires in {expiry_hours} hour(s).</p>"
                "</body></html>"
            )


class ResetPasswordCommand(BaseCommand):
    """Command to handle password reset completion"""

    def __init__(self, token: str, new_password: str, confirm_password: str):
        self._token = token
        self._new_password = new_password
        self._confirm_password = confirm_password

    def run(self) -> bool:
        """Process password reset"""
        try:
            # Find and validate token
            reset_token = self._validate_token()
            if not reset_token:
                return False

            # Update user password
            user = reset_token.user
            user.password = generate_password_hash(self._new_password)

            # Mark token as used
            reset_token.mark_as_used()

            # Invalidate all other tokens for this user
            other_tokens = (
                db.session.query(PasswordResetToken)
                .filter(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.id != reset_token.id,
                    ~PasswordResetToken.is_used,
                )
                .all()
            )

            for token in other_tokens:
                token.mark_as_used()

            db.session.commit()
            logger.info(f"Password reset successful for user {user.id}")
            return True

        except Exception as ex:
            logger.error(f"Error resetting password: {ex}")
            db.session.rollback()
            return False

    def validate(self) -> None:
        """Validate the command input"""
        logger.info(f"Validating token: {bool(self._token)}")
        if not self._token:
            raise ValueError("Token is required")

        logger.info(f"Validating new password: {bool(self._new_password)}")
        if not self._new_password:
            raise ValueError("New password is required")

        logger.info(f"Password length: {len(self._new_password)}")
        if len(self._new_password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        logger.info(f"Passwords match: {self._new_password == self._confirm_password}")
        if self._new_password != self._confirm_password:
            raise ValueError("Passwords do not match")

    def _validate_token(self) -> Optional[PasswordResetToken]:
        """Validate and return the reset token"""
        logger.info(f"Validating token: {self._token[:20]}...")

        # Extract user ID from token
        user_id = PasswordResetTokenManager.extract_user_id(self._token)
        logger.info(f"Extracted user ID: {user_id}")
        if not user_id:
            logger.error("Failed to extract user ID from token")
            return None

        # Find token in database
        import hashlib

        token_hash = hashlib.sha256(self._token.encode()).hexdigest()
        logger.info(f"Token hash: {token_hash[:20]}...")

        reset_token = (
            db.session.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.user_id == user_id,
            )
            .first()
        )

        if not reset_token:
            logger.error(f"No reset token found in database for user {user_id}")
            return None

        logger.info(f"Found reset token: {reset_token.id}")
        logger.info(f"Token is_used: {reset_token.is_used}")
        logger.info(f"Token is_expired: {reset_token.is_expired}")
        logger.info(f"Token expires_at: {reset_token.expires_at}")
        logger.info(f"Current time: {datetime.utcnow()}")
        logger.info(f"Token is_valid: {reset_token.is_valid}")

        # Check if token is valid
        if not reset_token.is_valid:
            if reset_token.is_used:
                logger.error("Token has already been used")
            if reset_token.is_expired:
                logger.error("Token has expired")
            return None

        # Validate token signature and expiry
        token_valid = PasswordResetTokenManager.validate_token(
            self._token, reset_token.token_hash, user_id
        )
        logger.info(f"Token signature validation: {token_valid}")

        if not token_valid:
            logger.error("Token signature validation failed")
            return None

        logger.info("Token validation successful")
        return reset_token

    def _extract_user_id_for_error(self) -> Optional[int]:
        """Extract user ID from token for error reporting purposes"""
        try:
            return PasswordResetTokenManager.extract_user_id(self._token)
        except Exception:
            return None


class ValidateResetTokenCommand(BaseCommand):
    """Command to validate a reset token without using it"""

    def __init__(self, token: str):
        self._token = token

    def validate(self) -> None:
        """Validate the command input"""
        if not self._token:
            raise ValueError("Token is required")

    def run(self) -> dict[str, Any]:
        """Validate token and return status"""
        try:
            # Extract user ID from token
            user_id = PasswordResetTokenManager.extract_user_id(self._token)
            if not user_id:
                return {"valid": False, "error": "Invalid token format"}

            # Find token in database
            import hashlib

            token_hash = hashlib.sha256(self._token.encode()).hexdigest()
            reset_token = (
                db.session.query(PasswordResetToken)
                .filter(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.user_id == user_id,
                )
                .first()
            )

            if not reset_token:
                return {"valid": False, "error": "Token not found"}

            # Check if token is valid
            if not reset_token.is_valid:
                return {"valid": False, "error": "Token expired or used"}

            # Validate token signature
            if not PasswordResetTokenManager.validate_token(
                self._token, reset_token.token_hash, user_id
            ):
                return {"valid": False, "error": "Invalid token signature"}

            return {
                "valid": True,
                "expires_at": reset_token.expires_at.isoformat(),
                "user_id": user_id,
            }

        except Exception as ex:
            logger.error(f"Error validating token: {ex}")
            return {"valid": False, "error": "Validation failed"}
