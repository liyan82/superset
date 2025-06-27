# Superset Bug Fix Log

This document records tricky bugs and their resolutions to serve as a reference for future development and troubleshooting.

## Issue: Resend Activation Link Allows Direct URL Access

**Date:** 2024-08-01

### The Problem

The `resend_activation` endpoint was accessible via a simple `GET` request. This meant a user could repeatedly trigger the resend activation email functionality by simply navigating to the URL (`/register/resend-activation/<user_id>`), which could potentially be abused.

### The Goal

To prevent direct URL access to the `resend_activation` endpoint, ensuring it can only be triggered by the user clicking the "Resend" button on the "Check Your Email" page after a timeout.

### The Solution Journey

#### Attempt 1: Change Endpoint to POST-only

The first step was to change the endpoint to only accept `POST` requests.

- **File:** `superset/security/custom_register.py`
- **Change:** Modified the `@expose` decorator from `@expose("/resend-activation/<int:register_user_id>")` to `@expose("/resend-activation/<int:register_user_id>", methods=["POST"])`.
- **Frontend:** Updated the `<a>` tag to a `<form>` with `method="POST"` in `superset/templates/appbuilder/general/security/check_email_for_activation.html`.

- **Result:** This led to an unexpected redirect to the login page upon clicking the "Resend" button.

#### Attempt 2: Incorrectly Modifying the Redirect Logic

It was assumed the redirect was the problem. The `resend_activation` method was changed to render the `check_email_page` template directly instead of redirecting to it.

- **Result:** This did not solve the problem and the redirect to the login page persisted.

#### Attempt 3: The Real Culprit - Missing CSRF Token

The key insight was that `POST` requests within the Superset/Flask-AppBuilder framework are protected by CSRF (Cross-Site Request Forgery) protection. Without a valid CSRF token, any `POST` request is considered potentially malicious and is rejected, typically by redirecting the user to the login page.

### The Final Fix

The solution required two key changes:

1.  **Inject CSRF Token into the Form:**
    - **File:** `superset/templates/appbuilder/general/security/check_email_for_activation.html`
    - **Change:** A hidden input field was added to the form to include the CSRF token.
      ```html
      <input type="hidden" name="csrf_token" value="{{ csrf_token() if csrf_token else '' }}"/>
      ```

2.  **Restore Redirect Logic:**
    - **File:** `superset/security/custom_register.py`
    - **Change:** The `resend_activation` method's final action was reverted to `redirect(url_for(...))`. This is the correct pattern, as it allows the browser to perform a fresh `GET` request to the `check_email_page`, which can then properly display the flashed success message (e.g., "Activation email resent successfully").

### Key Takeaway

When changing a `GET` endpoint to a `POST` endpoint within Superset (or any Flask-AppBuilder application), always remember to include a `CSRF` token in the corresponding form to satisfy the framework's security requirements. Failure to do so will likely result in unexplained redirects to the login page. 