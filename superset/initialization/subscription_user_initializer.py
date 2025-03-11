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
from flask import Flask, flash, redirect, url_for, request
from flask_appbuilder import AppBuilder, expose, BaseView
from flask_appbuilder.security.decorators import has_access
from flask_babel import lazy_gettext as _
from flask_appbuilder.models.sqla.interface import SQLAInterface
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, select
from flask_appbuilder.forms import DynamicForm
from wtforms import BooleanField, StringField, HiddenField, validators
from flask_appbuilder.security.sqla.models import User

logger = logging.getLogger(__name__)


class SubscriptionForm(DynamicForm):
    """Form for editing user subscription properties"""
    user_id = HiddenField('User ID')
    username = StringField('Username', render_kw={'readonly': True})
    email = StringField('Email', render_kw={'readonly': True})
    is_paid_user = BooleanField('Paid User', description='User has a paid subscription')
    trial_used = BooleanField('Trial Used', description='User has used their trial period')
    stripe_customer_id = StringField('Stripe Customer ID', description='Stripe customer identifier')


class UserSubscriptionManagementView(BaseView):
    """
    View for managing user subscription properties
    """
    route_base = "/user-subscription-management"
    
    @expose('/list/')
    @has_access
    def list(self):
        """List all users with their subscription status"""
        users = self.appbuilder.get_session.query(User).all()
        
        # Fetch subscription data for all users
        for user in users:
            self._fetch_subscription_data(user)
            
        return self.render_template(
            'superset/subscription_management/list.html',
            users=users,
            title="User Subscription Management"
        )
    
    @expose('/edit/<int:user_id>', methods=['GET', 'POST'])
    @has_access
    def edit(self, user_id):
        """Edit subscription details for a specific user"""
        user = self.appbuilder.get_session.query(User).filter_by(id=user_id).first_or_404()
        
        # Fetch current subscription data
        self._fetch_subscription_data(user)
        
        form = SubscriptionForm(request.form if request.method == 'POST' else None)
        
        # Handle form submission
        if request.method == 'POST' and form.validate():
            # Update subscription data in the database
            self._update_subscription_data(user, form)
            flash(_('Subscription information updated successfully'), 'success')
            return redirect(url_for(f"{self.__class__.__name__}.list"))
        
        # Pre-fill the form with existing data
        if request.method == 'GET':
            form.user_id.data = user.id
            form.username.data = user.username
            form.email.data = user.email
            form.is_paid_user.data = getattr(user, 'is_paid_user', False)
            form.trial_used.data = getattr(user, 'trial_used', False)
            form.stripe_customer_id.data = getattr(user, 'stripe_customer_id', '')
            
        return self.render_template(
            'superset/subscription_management/edit.html',
            user=user,
            form=form,
            title=f"Edit Subscription: {user.username}"
        )
    
    def _fetch_subscription_data(self, user):
        """Fetch subscription data for a user from the database"""
        session = self.appbuilder.get_session
        from sqlalchemy import text
        
        # Execute direct SQL to get the subscription fields
        result = session.execute(text(
            "SELECT is_paid_user, trial_used, stripe_customer_id FROM ab_user WHERE id = :id"
        ), {"id": user.id}).fetchone()
        
        if result:
            # Add attributes to the user object
            user.is_paid_user = result[0]
            user.trial_used = result[1]
            user.stripe_customer_id = result[2]
    
    def _update_subscription_data(self, user, form):
        """Update subscription data for a user in the database"""
        session = self.appbuilder.get_session
        
        # Use SQLAlchemy to update the database
        from sqlalchemy import table, column, update
        from sqlalchemy.types import Boolean, String
        
        user_table = table('ab_user',
            column('id', Integer),
            column('is_paid_user', Boolean),
            column('trial_used', Boolean),
            column('stripe_customer_id', String)
        )
        
        # Create update query
        stmt = update(user_table).where(user_table.c.id == user.id).values(
            is_paid_user=form.is_paid_user.data,
            trial_used=form.trial_used.data,
            stripe_customer_id=form.stripe_customer_id.data
        )
        
        # Execute and commit
        session.execute(stmt)
        session.commit()
        
        # Validate paid user has a Stripe ID
        if form.is_paid_user.data and not form.stripe_customer_id.data:
            flash(_('Warning: User marked as paid but no Stripe Customer ID provided'), 'warning')


def init_subscription_user_views(app: Flask, appbuilder: AppBuilder) -> None:
    """
    Initialize the subscription management view.
    
    This function adds a dedicated view for managing user subscription properties
    that works alongside the standard user management.
    """
    # Create necessary template directories
    import os
    template_dir = os.path.join(app.template_folder, 'superset', 'subscription_management')
    os.makedirs(template_dir, exist_ok=True)
    
    # Create list template
    list_template = os.path.join(template_dir, 'list.html')
    if not os.path.exists(list_template):
        with open(list_template, 'w') as f:
            f.write('''
{% extends "appbuilder/base.html" %}

{% block content %}
<div class="container">
    <h2>{{ title }}</h2>
    <div class="table-responsive">
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Paid User</th>
                    <th>Trial Used</th>
                    <th>Stripe Customer ID</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for user in users %}
                <tr>
                    <td>{{ user.username }}</td>
                    <td>{{ user.email }}</td>
                    <td>
                        {% if user.is_paid_user %}
                            <span class="label label-success">Yes</span>
                        {% else %}
                            <span class="label label-default">No</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if user.trial_used %}
                            <span class="label label-warning">Yes</span>
                        {% else %}
                            <span class="label label-default">No</span>
                        {% endif %}
                    </td>
                    <td>{{ user.stripe_customer_id or '—' }}</td>
                    <td>
                        <a href="{{ url_for('UserSubscriptionManagementView.edit', user_id=user.id) }}" 
                           class="btn btn-sm btn-primary">
                            <i class="fa fa-edit"></i> Edit
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
''')
    
    # Create edit template
    edit_template = os.path.join(template_dir, 'edit.html')
    if not os.path.exists(edit_template):
        with open(edit_template, 'w') as f:
            f.write('''
{% extends "appbuilder/base.html" %}
{% import "appbuilder/general/lib.html" as lib %}

{% block content %}
<div class="container">
    <h2>{{ title }}</h2>
    
    <div class="panel panel-primary">
        <div class="panel-heading">
            <h3 class="panel-title">User Information</h3>
        </div>
        <div class="panel-body">
            <p><strong>Username:</strong> {{ user.username }}</p>
            <p><strong>Email:</strong> {{ user.email }}</p>
            <p><strong>First Name:</strong> {{ user.first_name }}</p>
            <p><strong>Last Name:</strong> {{ user.last_name }}</p>
        </div>
    </div>
    
    <div class="panel panel-info">
        <div class="panel-heading">
            <h3 class="panel-title">Subscription Settings</h3>
        </div>
        <div class="panel-body">
            <form method="post" enctype="multipart/form-data">
                {{ form.hidden_tag() }}
                
                {{ lib.render_field(form.is_paid_user) }}
                {{ lib.render_field(form.trial_used) }}
                {{ lib.render_field(form.stripe_customer_id) }}
                
                <div class="form-group">
                    <button type="submit" class="btn btn-primary">Save</button>
                    <a href="{{ url_for('UserSubscriptionManagementView.list') }}" class="btn btn-default">Cancel</a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
''')
    
    # Register the view
    subscription_view = UserSubscriptionManagementView()
    appbuilder.add_view(
        subscription_view,
        "User Subscriptions",
        icon="fa-money",
        category="Security",
        category_icon="fa-cogs"
        # Removed both endpoint and name parameters
    )
    
    logger.info("Successfully registered User Subscription Management view")
