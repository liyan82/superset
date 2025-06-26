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
from typing import cast, Optional
import re

from flask import (
    current_app,
    flash,
    redirect,
    request,
    Response,
    url_for,
)
from flask_appbuilder import expose
from flask_appbuilder.security.forms import RegisterUserDBForm
from flask_appbuilder.security.registerviews import RegisterUserDBView
from flask_appbuilder.security.sqla.models import RegisterUser
from flask_babel import lazy_gettext

logger = logging.getLogger(__name__)


class SupersetRegisterUserDBView(RegisterUserDBView):
    """
    Custom Register User DB View for Superset to override
    templates and redirection behavior.
    """

    # Redirect to the login page after successful registration and email activation.
    # You might want to change this to a specific welcome page if you have one.
    redirect_url = "/login/"

    # Custom email template for the registration confirmation email.
    email_template = "appbuilder/general/security/register_mail.html"

    # Custom template for the user registration page.
    # This allows for a dedicated design different from the generic edit.html.
    form_template = "appbuilder/general/security/register_user.html"

    # Override the form title for the registration page.
    form_title = lazy_gettext("Create Your Account")

    # Override the message shown after the registration form is submitted.
    message = lazy_gettext(
        "Registration successful! Please check your email to activate your account."
    )

    # You can also override other properties as needed:
    # email_subject = lazy_gettext("Activate Your Superset Account")
    # activation_template = "superset/profile/activation.html" # Template shown after successful activation  # noqa: E501
    # error_message = lazy_gettext("Registration failed. Please try again or contact support.")  # noqa: E501
    # false_error_message = lazy_gettext("Invalid activation link or your account may already be active.")  # noqa: E501

    # If you have a custom registration form (e.g., with additional fields or different validation),  # noqa: E501
    # you would define it in superset/security/forms.py and set it here:
    # from superset.security.forms import CustomRegisterUserDBForm
    # form = CustomRegisterUserDBForm

    # Override the methods that handle GET and POST requests to
    # ensure they always render our custom template with the 'form' object.
    @expose("/form", methods=["GET"])
    def this_form_get(self) -> Response:
        self._init_vars()
        form = self.form()
        return self.render_template(
            self.form_template,
            title=self.form_title,
            form=form,
            appbuilder=self.appbuilder,
        )

    @expose("/form", methods=["POST"])
    def this_form_post(self) -> Response:
        self._init_vars()
        form = self.form()
        self.add_form_unique_validations(form)
        if form.validate_on_submit():
            response = self.form_post(form)
            if response is not None:
                return response
        
        return self.render_template(
            self.form_template,
            title=self.form_title,
            form=form,
            appbuilder=self.appbuilder,
        )

    def form_get(self, form: RegisterUserDBForm) -> None:
        """
        Called when the registration form is displayed (GET request).
        You can add custom logic here if needed.
        """
        super().form_get(form)

    def form_post(self, form: RegisterUserDBForm) -> Optional[Response]:
        """
        Called when the registration form is submitted (POST request).
        Handles the registration process and redirects upon successful submission
        (prior to email activation).
        """
        # Password policy validation
        password = form.password.data or ""
        errors = []
        if len(password) < 8:
            errors.append(lazy_gettext("Password must be at least 8 characters long."))
        if not re.search("[a-z]", password):
            errors.append(lazy_gettext("Password must contain a lowercase letter."))
        if not re.search("[A-Z]", password):
            errors.append(lazy_gettext("Password must contain an uppercase letter."))
        if not re.search("[0-9]", password):
            errors.append(lazy_gettext("Password must contain a number."))

        if errors:
            # Add errors to the form field and return to the form
            form.password.errors.extend(errors)
            return None

        if current_app.config.get("ENABLE_REGISTRATION_EMAIL_DOMAIN_VALIDATION"):
            email_domain = form.email.data.split('@')[1]
            blacklist = current_app.config.get("REGISTRATION_EMAIL_DOMAIN_BLACKLIST", set())
            if email_domain.lower() in blacklist:
                form.email.errors.append(lazy_gettext(
                    "Our registration policy requires a business email. Public domains are not accepted."
                ))
                return None
                
        # This method is on BaseRegisterUser. It handles:
        # 1. Creating the RegisterUser entry in the database.
        # 2. Sending the activation email.
        # 3. Flashing 'self.message' (e.g., "Registration successful! Please check your email...") on success.  # noqa: E501
        # 4. Flashing 'self.error_message' on failure.
        # It returns the created register_user object on success, or None on failure.
        register_user = self.add_registration(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data,
        )

        if register_user:
            # Registration process initiated successfully.
            # The success message (self.message) has already been flashed by add_registration.  # noqa: E501
            # Redirect to the "check your email" page.
            return cast(
                Response,
                redirect(
                    url_for(
                        "SupersetRegisterUserDBView.check_email_page",
                        register_user_id=register_user.id,
                        email=register_user.email,
                    )
                ),
            )
        else:
            # Registration failed (e.g., email could not be sent, database issue, duplicate user).  # noqa: E501
            # An error message (self.error_message) has already been flashed by add_registration.  # noqa: E501
            # Returning None will let Flask-AppBuilder handle the response,
            # which typically means re-rendering the registration form.
            # The form will display any validation errors and the flashed error message.
            return None

    @expose("/check-email/")
    def check_email_page(self) -> Response:
        """
        Displays a page instructing the user to check their email for activation.
        """
        register_user_id = request.args.get("register_user_id")
        email = request.args.get("email")
        if not register_user_id or not email:
            flash(self.false_error_message, "danger")
            return cast(Response, redirect(self.appbuilder.get_url_for_login))

        return cast(
            Response,
            self.render_template(
                "appbuilder/general/security/check_email_for_activation.html",
                title=lazy_gettext("Check Your Email"),
                appbuilder=self.appbuilder,
                register_user_id=register_user_id,
                email=email,
            ),
        )

    @expose("/resend-activation/<int:register_user_id>")
    def resend_activation(self, register_user_id: int) -> Response:
        """
        Resends the activation email to the user.
        """
        register_user = (
            self.appbuilder.sm.get_session.query(RegisterUser)
            .filter_by(id=register_user_id)
            .first()
        )

        if not register_user:
            flash(self.false_error_message, "danger")
            return cast(Response, redirect(self.appbuilder.get_url_for_login))

        try:
            # Use the inherited send_email method from BaseRegisterUser
            if not self.send_email(register_user):
                # This method returns True on success, False on failure
                # (and logs errors internally if Flask-Mail is not set up or fails)
                raise Exception("self.send_email failed")

            flash(
                lazy_gettext(
                    "Activation email resent successfully. Please check your email."
                ),
                "info",
            )

        except Exception as e:
            logger.error(f"Error resending activation email: {e}", exc_info=True)
            flash(self.error_message, "danger")

        return cast(
            Response,
            redirect(
                url_for(
                    "SupersetRegisterUserDBView.check_email_page",
                    register_user_id=register_user.id,
                    email=register_user.email,
                )
            ),
        )
