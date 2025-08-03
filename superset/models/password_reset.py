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

from datetime import datetime, timedelta
from uuid import uuid4

from flask_appbuilder import Model
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class PasswordResetToken(Model):
    """Model for storing password reset tokens"""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("ab_user.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="password_reset_tokens")

    def __init__(self, user_id: int, token_hash: str, expires_in_hours: int = 1):
        self.user_id = user_id
        self.token_hash = token_hash
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=expires_in_hours)

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired

    def mark_as_used(self) -> None:
        """Mark the token as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()

    @classmethod
    def cleanup_expired_tokens(cls) -> int:
        """Remove expired tokens from the database"""
        from superset import db

        expired_tokens = db.session.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        )
        count = expired_tokens.count()
        expired_tokens.delete()
        db.session.commit()
        return count

    def __repr__(self) -> str:
        return f"<PasswordResetToken {self.id} for user {self.user_id}>"
