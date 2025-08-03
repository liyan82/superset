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
from typing import Any

from flask import request
from flask_appbuilder.api import expose, safe
from marshmallow import fields, Schema, ValidationError

from superset import db
from superset.commands.auth.password_reset import (
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    ValidateResetTokenCommand,
)
from superset.views.base_api import BaseSupersetApi

logger = logging.getLogger(__name__)


class ForgotPasswordSchema(Schema):
    """Schema for forgot password request"""

    email = fields.Email(required=True, description="User's email address")


class ResetPasswordSchema(Schema):
    """Schema for password reset request"""

    token = fields.String(required=True, description="Password reset token")
    new_password = fields.String(
        required=True,
        validate=lambda x: len(x) >= 8,
        description="New password (minimum 8 characters)",
    )
    confirm_password = fields.String(required=True, description="Confirm new password")


class PasswordResetApi(BaseSupersetApi):
    """API endpoints for password reset functionality"""

    resource_name = "auth"
    allow_browser_login = True

    @expose("/forgot-password", methods=["POST"])
    @safe
    def forgot_password(self) -> Any:
        """
        Request a password reset email
        ---
        post:
          summary: Request password reset
          description: Send a password reset link to the user's email
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    email:
                      type: string
                      format: email
                      description: User's email address
          responses:
            200:
              description: Reset email sent (always returns success)
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            400:
              description: Invalid request
        """
        try:
            json_data = request.get_json(force=True)
            schema = ForgotPasswordSchema()
            data = schema.load(json_data)

            command = RequestPasswordResetCommand(data["email"])
            command.run()

            return self.response(
                200,
                message=(
                    "If an account with that email exists, "
                    "we've sent you a password reset link."
                ),
            )

        except ValidationError as ex:
            return self.response_400(message=str(ex.messages))
        except Exception as ex:
            logger.error(f"Forgot password error: {ex}")
            return self.response_500(message="Something went wrong. Please try again.")

    @expose("/reset-password", methods=["POST"])
    @safe
    def reset_password(self) -> Any:
        """
        Reset user password with token
        ---
        post:
          summary: Reset password
          description: Reset user password using a valid token
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    token:
                      type: string
                      description: Password reset token
                    new_password:
                      type: string
                      minLength: 8
                      description: New password
                    confirm_password:
                      type: string
                      description: Confirm new password
          responses:
            200:
              description: Password reset successful
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            400:
              description: Invalid request or token
        """
        try:
            json_data = request.get_json(force=True)
            logger.info(f"Reset password request data: {json_data}")
            schema = ResetPasswordSchema()
            data = schema.load(json_data)
            logger.info(f"Schema validated data: {data}")

            command = ResetPasswordCommand(
                data["token"], data["new_password"], data["confirm_password"]
            )
            logger.info("About to validate command")
            command.validate()
            logger.info("Command validation passed")

            logger.info("About to run command")
            success = command.run()
            logger.info(f"Command run result: {success}")
            if success:
                return self.response(
                    200,
                    message=(
                        "Password updated successfully. "
                        "You can now sign in with your new password."
                    ),
                )
            else:
                error_message = self._get_detailed_error_message(command)
                return self.response_400(message=error_message)

        except ValidationError as ex:
            return self.response_400(message=str(ex.messages))
        except ValueError as ex:
            return self.response_400(message=str(ex))
        except Exception as ex:
            logger.error(f"Reset password error: {ex}")
            return self.response_500(
                message="Failed to reset password. Please try again."
            )

    def _get_detailed_error_message(self, command: Any) -> str:
        """Extract detailed error message for failed password reset"""
        error_message = "Invalid or expired token. Please request a new password reset."
        try:
            # Try to get more specific error details
            token_validation = command._validate_token()
            if token_validation is None:
                # Check if token exists but is expired/used
                user_id = command._extract_user_id_for_error()
                if user_id:
                    import hashlib

                    token_hash = hashlib.sha256(command._token.encode()).hexdigest()
                    from superset.models.password_reset import (
                        PasswordResetToken,
                    )

                    reset_token = (
                        db.session.query(PasswordResetToken)
                        .filter(
                            PasswordResetToken.token_hash == token_hash,
                            PasswordResetToken.user_id == user_id,
                        )
                        .first()
                    )

                    if reset_token:
                        if reset_token.is_used:
                            error_message = (
                                "This password reset link has already been "
                                "used. Please request a new password reset."
                            )
                        elif reset_token.is_expired:
                            error_message = (
                                "This password reset link has expired "
                                "(valid for 1 hour). Please request a new "
                                "password reset."
                            )
        except Exception as ex:
            # Fall back to generic message if specific error detection fails
            logger.debug(f"Error extracting specific error details: {ex}")

        return error_message

    @expose("/validate-reset-token/<token>", methods=["GET"])
    @safe
    def validate_reset_token(self, token: str) -> Any:
        """
        Validate a password reset token
        ---
        get:
          summary: Validate reset token
          description: Check if a password reset token is valid
          parameters:
            - in: path
              name: token
              required: true
              schema:
                type: string
              description: Password reset token
          responses:
            200:
              description: Token validation result
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      valid:
                        type: boolean
                      expires_at:
                        type: string
                        format: date-time
                      error:
                        type: string
        """
        try:
            command = ValidateResetTokenCommand(token)
            result = command.run()
            return self.response(200, **result)

        except Exception as ex:
            logger.error(f"Validate token error: {ex}")
            return self.response(200, valid=False, error="Token validation failed")
