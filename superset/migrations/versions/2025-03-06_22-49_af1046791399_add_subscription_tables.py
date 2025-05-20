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
"""Add subscription tables

Revision ID: af1046791399
Revises: 74ad1125881c
Create Date: 2025-03-06 22:49:31.268363

"""

import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "af1046791399"
down_revision = "74ad1125881c"


def upgrade():
    # Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=False, unique=True),
        sa.Column("stripe_price_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("billing_cycle", sa.String(20), nullable=False),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_on", sa.DateTime(), default=datetime.datetime.now),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False, default=datetime.datetime.now),  # noqa: E501
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("is_auto_renew", sa.Boolean(), default=True),
        sa.Column("external_subscription_id", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["ab_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("payment_date", sa.DateTime(), default=datetime.datetime.now),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["ab_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create payment_methods table
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("method_type", sa.String(50), nullable=False),
        sa.Column("token", sa.String(255), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("last_digits", sa.String(4), nullable=True),
        sa.Column("expiry_date", sa.String(7), nullable=True),
        sa.Column("created_on", sa.DateTime(), default=datetime.datetime.now),
        sa.ForeignKeyConstraint(["user_id"], ["ab_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add subscription fields to user model
    op.add_column(
        "ab_user", sa.Column("is_paid_user", sa.Boolean(), server_default="0")
    )
    op.add_column("ab_user", sa.Column("trial_used", sa.Boolean(), server_default="0"))
    op.add_column(
        "ab_user", sa.Column("stripe_customer_id", sa.String(255), nullable=True)
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_column("ab_user", "stripe_customer_id")
    op.drop_column("ab_user", "trial_used")
    op.drop_column("ab_user", "is_paid_user")
    op.drop_table("payment_methods")
    op.drop_table("payments")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
