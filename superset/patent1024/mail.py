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
