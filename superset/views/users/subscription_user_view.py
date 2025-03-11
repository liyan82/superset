
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
from flask_appbuilder.security.views import UserDBModelView
from flask_babel import lazy_gettext as _
from flask import flash, request
from wtforms.fields import BooleanField, StringField


class SubscriptionUserModelView(UserDBModelView):
    """
    Extended User Model View that includes subscription-related fields
    This view accesses the subscription fields that exist in the ab_user table
    but are not defined in the SQLAlchemy model.
    """
    # Use a distinct route name
    route_base = "/subscription-users"
    
    # Define label
    list_title = "Subscription Users"
    
    # Add form fields directly using extra_fields
    add_form_extra_fields = {
        "is_paid_user": BooleanField(_("Paid User"), description=_("User has a paid subscription")),
        "trial_used": BooleanField(_("Trial Used"), description=_("User has used their trial period")),
        "stripe_customer_id": StringField(_("Stripe Customer ID"), description=_("Stripe customer identifier")),
    }
    
    # Same for edit form
    edit_form_extra_fields = {
        "is_paid_user": BooleanField(_("Paid User"), description=_("User has a paid subscription")),
        "trial_used": BooleanField(_("Trial Used"), description=_("User has used their trial period")),
        "stripe_customer_id": StringField(_("Stripe Customer ID"), description=_("Stripe customer identifier")),
    }
    
    # Process form submission to save subscription fields
    def process_form(self, form, is_created):
        # Process the standard fields first
        form = super().process_form(form, is_created)
        
        # Extract subscription fields from the form
        form.is_paid_user = form.is_paid_user.data if hasattr(form, 'is_paid_user') else False
        form.trial_used = form.trial_used.data if hasattr(form, 'trial_used') else False
        form.stripe_customer_id = form.stripe_customer_id.data if hasattr(form, 'stripe_customer_id') else None
        
        return form
    
    # When displaying a user, fetch subscription fields from the database
    def pre_show(self, item):
        self._fetch_subscription_fields(item)
        return super().pre_show(item)
    
    # Before editing, fetch subscription fields
    def pre_update(self, item):
        self._fetch_subscription_fields(item)
        return super().pre_update(item)
    
    def _fetch_subscription_fields(self, item):
        """
        Fetch subscription fields from the database
        """
        # Use the session to query for subscription fields
        session = self.datamodel.session
        from sqlalchemy import text
        
        # Execute direct SQL to get subscription fields
        result = session.execute(text(
            "SELECT is_paid_user, trial_used, stripe_customer_id FROM ab_user WHERE id = :id"
        ), {"id": item.id}).fetchone()
        
        if result:
            # Set the subscription fields on the item
            item.is_paid_user = result[0]
            item.trial_used = result[1]
            item.stripe_customer_id = result[2]
    
    # After adding a user, save subscription fields
    def post_add(self, item):
        self._save_subscription_fields(item)
        super().post_add(item)
    
    # After updating a user, save subscription fields
    def post_update(self, item):
        self._save_subscription_fields(item)
        super().post_update(item)
    
    def _save_subscription_fields(self, item):
        """
        Save subscription fields to the database
        """
        # Get values from the item (which should have been set by process_form)
        is_paid_user = getattr(item, 'is_paid_user', False)
        trial_used = getattr(item, 'trial_used', False)
        stripe_customer_id = getattr(item, 'stripe_customer_id', None)
        
        # Use SQLAlchemy to update the database
        session = self.datamodel.session
        from sqlalchemy import table, column, update
        from sqlalchemy.types import Boolean, String

        user_table = table('ab_user',
            column('id'),
            column('is_paid_user', Boolean),
            column('trial_used', Boolean),
            column('stripe_customer_id', String)
        )
        
        # Create update query
        stmt = update(user_table).where(user_table.c.id == item.id).values(
            is_paid_user=is_paid_user,
            trial_used=trial_used,
            stripe_customer_id=stripe_customer_id
        )
        
        # Execute and commit
        session.execute(stmt)
        session.commit()
        
        # Provide feedback
        if is_paid_user and not stripe_customer_id:
            flash(_("Warning: User marked as paid but no Stripe Customer ID provided"), "warning")
        else:
            flash(_("Subscription information saved successfully"), "success")
