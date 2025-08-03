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

import base64
import hashlib
import hmac
import secrets
import time
from typing import Optional, Tuple

from flask import current_app


class PasswordResetTokenManager:
    """Secure token generation and validation for password reset functionality"""

    @staticmethod
    def generate_token(user_id: int, expires_in_hours: int = 1) -> Tuple[str, str]:
        """
        Generate a secure password reset token.

        Returns:
            Tuple of (token, token_hash) where:
            - token: The token to send to the user (base64 encoded)
            - token_hash: The hash to store in the database
        """
        # Generate random salt (32 bytes = 256 bits)
        salt = secrets.token_bytes(32)

        # Calculate expiry timestamp
        expiry = int(time.time()) + (expires_in_hours * 3600)

        # Create payload: user_id + expiry + salt
        payload = f"{user_id}:{expiry}:{salt.hex()}"

        # Generate HMAC signature
        secret_key = current_app.config["SECRET_KEY"].encode()
        signature = hmac.new(secret_key, payload.encode(), hashlib.sha256).hexdigest()

        # Combine payload and signature
        token_data = f"{payload}:{signature}"

        # Base64 encode for URL safety
        token = base64.urlsafe_b64encode(token_data.encode()).decode()

        # Create hash for database storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        return token, token_hash

    @staticmethod
    def validate_token(token: str, stored_token_hash: str, user_id: int) -> bool:
        """
        Validate a password reset token.

        Args:
            token: The token from the user request
            stored_token_hash: The hash stored in the database
            user_id: Expected user ID

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Verify token hash matches stored hash (prevents tampering)
            calculated_hash = hashlib.sha256(token.encode()).hexdigest()
            if not hmac.compare_digest(calculated_hash, stored_token_hash):
                return False

            # Decode token
            token_data = base64.urlsafe_b64decode(token.encode()).decode()

            # Split components
            parts = token_data.split(":")
            if len(parts) != 4:
                return False

            payload_user_id, expiry_str, salt_hex, signature = parts

            # Verify user ID matches
            if int(payload_user_id) != user_id:
                return False

            # Verify token hasn't expired
            if int(expiry_str) < time.time():
                return False

            # Verify HMAC signature
            payload = f"{payload_user_id}:{expiry_str}:{salt_hex}"
            secret_key = current_app.config["SECRET_KEY"].encode()
            expected_signature = hmac.new(
                secret_key, payload.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, TypeError, UnicodeDecodeError):
            return False

    @staticmethod
    def extract_user_id(token: str) -> Optional[int]:
        """
        Extract user ID from token without full validation.
        Used for database lookups.

        Returns:
            User ID if token format is valid, None otherwise
        """
        try:
            token_data = base64.urlsafe_b64decode(token.encode()).decode()
            parts = token_data.split(":")
            if len(parts) >= 1:
                return int(parts[0])
        except (ValueError, TypeError, UnicodeDecodeError):
            pass
        return None
