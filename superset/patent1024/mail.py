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
"""Helpers for mail that patent1024 sends itself."""

import logging

from flask import current_app

logger = logging.getLogger(__name__)

# Last-resort origin, used only when neither config key is set.
DEFAULT_PUBLIC_BASE_URL = "https://patent1024.com"

# Hosts that are fine for local browsing but unreachable for a mail recipient.
_UNREACHABLE_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")


def public_base_url() -> str:
    """Public origin for links that end up inside an email.

    Deliberately config-driven and never derived from the incoming request:
    building a reset link from the Host header would let an attacker send a
    forged Host, receive a link pointing at their own domain, and harvest the
    victim's reset token.

    ``PASSWORD_RESET_BASE_URL`` wins; ``SUPERSET_WEBSERVER_ADDRESS`` is honoured
    for backwards compatibility, but it gets pointed at localhost for local
    browsing, which silently produces links no recipient can open.
    """
    base_url = (
        current_app.config.get("PASSWORD_RESET_BASE_URL")
        or current_app.config.get("SUPERSET_WEBSERVER_ADDRESS")
        or ""
    ).strip().rstrip("/")

    if not base_url:
        base_url = DEFAULT_PUBLIC_BASE_URL
        logger.error(
            "Neither PASSWORD_RESET_BASE_URL nor SUPERSET_WEBSERVER_ADDRESS is "
            "set; falling back to %s. Set PASSWORD_RESET_BASE_URL explicitly.",
            base_url,
        )
    elif any(host in base_url for host in _UNREACHABLE_HOSTS):
        logger.warning(
            "Outgoing email links are being built against %s, which recipients "
            "cannot reach. Set PASSWORD_RESET_BASE_URL to the public site URL "
            "(e.g. %s) in superset_config.py.",
            base_url,
            DEFAULT_PUBLIC_BASE_URL,
        )

    return base_url


def to_ascii_html(html: str) -> str:
    """Re-express every non-ASCII character as a numeric HTML entity.

    ``superset.utils.core.send_mime_email`` ends in
    ``smtplib.sendmail(..., mime_msg.as_string())``, and smtplib encodes that
    ``str`` as ASCII. Whether non-ASCII survives therefore depends on the MIME
    layer picking a base64/utf-8 body, which does not happen on every Superset
    build. Where it does not, the send dies with::

        UnicodeEncodeError: 'ascii' codec can't encode character '\\U0001f512'
        (LOCK) in position 5735: ordinal not in range(128)

    Both senders here swallow that exception, so the caller is told the mail
    went out and nothing arrives.

    Entities render identically in mail clients and keep the payload ASCII
    however the MIME layer encodes it. This covers emoji in a template or a
    newsletter body, and accented characters in a recipient's name, which fail
    the same way.

    Only for HTML bodies. A ``Subject:`` needs RFC 2047 encoding instead --
    entities would show up literally there.
    """
    return html.encode("ascii", "xmlcharrefreplace").decode("ascii")
