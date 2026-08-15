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

"""add password reset tokens table

Revision ID: eb095c5d054f
Revises: af1046791399
Create Date: 2025-08-02 21:33:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from superset.migrations.shared.utils import (
    create_index,
    create_table,
    drop_index,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "eb095c5d054f"
down_revision = "af1046791399"


def upgrade():
    create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["ab_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    # Create indexes for performance
    create_index(
        "password_reset_tokens",
        "ix_password_reset_tokens_token_hash",
        ["token_hash"],
        unique=True,
    )
    create_index(
        "password_reset_tokens",
        "ix_password_reset_tokens_user_id",
        ["user_id"],
    )
    create_index(
        "password_reset_tokens",
        "ix_password_reset_tokens_expires_at",
        ["expires_at"],
    )


def downgrade():
    drop_index("password_reset_tokens", "ix_password_reset_tokens_expires_at")
    drop_index("password_reset_tokens", "ix_password_reset_tokens_user_id")
    drop_index("password_reset_tokens", "ix_password_reset_tokens_token_hash")
    drop_table("password_reset_tokens")
