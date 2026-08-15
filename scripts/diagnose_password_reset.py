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
"""Pinpoint why a password reset email is not arriving.

The reset path swallows every failure: _render_email_template falls back to
plain HTML, _send_reset_email catches everything, and the command always
returns True so the API cannot leak whether an account exists. The result is
that a broken reset looks identical to a working one from the outside. This
script walks the same path with the exception handling removed, so the first
real error surfaces.

Nothing is sent: send_email_smtp is replaced with a capture stub, and no
password is modified.

Usage, from the directory holding docker-compose.yml:

    docker compose exec -T superset python - <someone@example.com> \\
        < scripts/diagnose_password_reset.py
"""

import sys
import traceback


def main() -> None:
    email = (sys.argv[1] if len(sys.argv) > 1 else "").strip()

    from superset.app import create_app

    app = create_app()

    captured: dict[str, object] = {}

    import superset.utils.core as core

    def _capture(to, subject, html_content, config, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(
            to=to, subject=subject, html=html_content, host=config.get("SMTP_HOST")
        )

    core.send_email_smtp = _capture

    with app.app_context():
        from flask_appbuilder.security.sqla.models import User
        from sqlalchemy import inspect as sa_inspect

        from superset import db
        from superset.commands.auth.password_reset import RequestPasswordResetCommand

        cfg = app.config
        print("== configuration ==")
        for key in (
            "MAIL_SERVER",
            "MAIL_PORT",
            "MAIL_USERNAME",
            "MAIL_DEFAULT_SENDER",
            "MAIL_USE_TLS",
            "SUPERSET_WEBSERVER_ADDRESS",
            "PASSWORD_RESET_BASE_URL",
            "RESET_PASSWORD_TOKEN_EXPIRY_HOURS",
        ):
            value = cfg.get(key)
            if key == "MAIL_PASSWORD":
                value = "<set>" if value else None
            print(f"   {key} = {value!r}")

        print("\n== schema ==")
        tables = sa_inspect(db.engine).get_table_names()
        present = "password_reset_tokens" in tables
        print(f"   password_reset_tokens table present: {present}")
        if not present:
            print("   -> the table is missing; run 'superset db upgrade'")
            return
        version = db.session.execute(
            db.text("SELECT version_num FROM alembic_version")
        ).scalar()
        print(f"   alembic_version = {version}")

        if not email:
            print("\nPass an account email as an argument to exercise the full path.")
            return

        print("\n== reset path ==")
        user = (
            db.session.query(User)
            .filter(User.email == email.lower(), User.active)
            .first()
        )
        if not user:
            print(f"   no ACTIVE user with email {email!r}")
            print("   -> the request silently no-ops; nothing is ever sent")
            return
        print(f"   user: {user.username} (id={user.id}, active={user.active})")

        command = RequestPasswordResetCommand(email)

        # Deliberately not wrapped: let the first real failure raise.
        token = command._create_reset_token(user)
        print("   token created")

        url = command._build_reset_url(token._token)
        print(f"   reset url: {url}")
        if any(h in url for h in ("localhost", "127.0.0.1", "0.0.0.0")):
            print("   -> recipients cannot open this host")

        html = command._render_email_template(user, url)
        styled = "cta-button" in html
        print(f"   template rendered: {'branded' if styled else 'PLAIN FALLBACK'}")
        if not styled:
            print("   -> email/password_reset.html failed to render; see log above")

        command._send_reset_email(user, token)
        if captured:
            print(f"   send reached SMTP host {captured.get('host')!r}")
            print(f"   subject: {captured.get('subject')!r}")
            print("\nAll stages completed. If mail still does not arrive, the")
            print("failure is in SMTP delivery itself; check the app log for")
            print("'Exception during email send'.")
        else:
            print("   send_email_smtp was never reached -- see traceback above")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - the whole point is to surface it
        print("\n*** FAILED — this is the error the app was swallowing ***\n")
        traceback.print_exc()
