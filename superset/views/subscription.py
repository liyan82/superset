import datetime

from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.views import ModelView
from flask import redirect, url_for, request, flash, g, current_app
from flask_babel import lazy_gettext as _
from sqlalchemy import or_, text

from flask_appbuilder.security.sqla.models import User
from superset.models.subscription import SubscriptionPlan, UserSubscription, Payment


class SubscriptionView(BaseView):
    route_base = "/subscription"
    default_view = "index"  # Set the default view to the index method

    def _get_user(self):
        """Get a fresh User instance with all extensions applied"""
        from sqlalchemy.orm import joinedload
        # Make sure to eagerly load the subscriptions relationship and payments
        user = self.appbuilder.session.query(User).options(
            joinedload(User.subscriptions).joinedload(UserSubscription.plan),
            joinedload(User.subscriptions).joinedload(UserSubscription.payments)
        ).get(g.user.id)

        # Force SQLAlchemy to load the subscriptions
        if hasattr(user, 'subscriptions'):
            _ = user.subscriptions
            # Force SQLAlchemy to load payments for each subscription
            for subscription in user.subscriptions:
                if hasattr(subscription, 'payments'):
                    _ = subscription.payments

        return user

    @expose('/')
    @expose('/index')
    def index(self):
        """Smart entry point that either shows plans or redirects to manage page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        if user.has_active_subscription:
            # Redirect to manage page if they're already subscribed
            return redirect(url_for('.manage'))
        else:
            # Show plans page if they don't have an active subscription
            return self.plans()
    
    @expose('/plans')
    def plans(self):
        """Show available subscription plans"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        if user.has_active_subscription:
            flash(_("You already have an active subscription. Manage it below."), "info")
            return redirect(url_for('.manage'))
            
        plans = self.appbuilder.session.query(SubscriptionPlan).filter_by(
            is_active=True).all()
        return self.render_template('subscription/plans.html',
                                    plans=plans,
                                    user=user)

    @expose('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
    @has_access
    def subscribe(self, plan_id):
        """Process new subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        if user.has_active_subscription:
            flash(_("You already have an active subscription. Please cancel it before subscribing to a new plan."), "warning")
            return redirect(url_for('.manage'))
            
        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for('.plans'))

        if request.method == 'POST':
            # Process payment form data
            payment_method = request.form.get('payment_method')
            
            # Get credit card details
            card_number = request.form.get('card_number')
            expiration = request.form.get('expiration')
            cvv = request.form.get('cvv')
            
            # Validate credit card details
            if not (card_number and expiration and cvv):
                flash(_("Please fill in all credit card details"), "danger")
                return self.render_template('subscription/payment.html',
                                          plan=plan,
                                          user=user)

            # Integrate with payment processor (simplified)
            success, transaction_id = self.process_payment(
                plan, 
                payment_method, 
                {
                    'card_number': card_number,
                    'expiration': expiration,
                    'cvv': cvv
                }
            )

            if success:
                # Create subscription
                end_date = datetime.datetime.now() + self.calc_subscription_period(plan)
                subscription = UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status='active',
                    start_date=datetime.datetime.now(),
                    end_date=end_date,
                    is_auto_renew=True
                )

                # Save the subscription first to get an ID
                self.appbuilder.session.add(subscription)
                self.appbuilder.session.flush()  # Flush to get subscription.id without committing

                # Create payment record with subscription association
                payment = Payment(
                    user_id=user.id,
                    subscription_id=subscription.id,  # Link payment to subscription
                    amount=plan.price,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    status='success'
                )

                # Add payment to session and commit both subscription and payment
                self.appbuilder.session.add(payment)
                
                # Debug logging
                current_app.logger.info(f"Created subscription {subscription.id} with payment")
                current_app.logger.info(f"Payment details: {payment.amount}, {payment.payment_method}, {payment.status}")

                # Commit subscription and payment
                self.appbuilder.session.commit()
                
                # Update user paid status using direct SQL (this includes its own commit)
                self.update_user_paid_status(user.id, True)

                flash(_("Subscription activated successfully!"), "success")
                # Redirect to success page instead of index
                return redirect(url_for('.subscription_success', subscription_id=subscription.id))
            else:
                flash(_("Payment processing failed"), "danger")

        # GET request - show payment form
        return self.render_template('subscription/payment.html',
                                    plan=plan,
                                    user=user)

    @expose('/success/<int:subscription_id>')
    @has_access
    def subscription_success(self, subscription_id):
        """Show subscription success page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        subscription = self.appbuilder.session.query(UserSubscription).get(subscription_id)
        if not subscription or subscription.user_id != user.id:
            flash(_("Invalid subscription"), "danger")
            return redirect(url_for('SupersetIndexView.index'))
            
        return self.render_template('subscription/success.html',
                                    subscription=subscription,
                                    user=user)

    @expose('/manage')
    @has_access
    def manage(self):
        """Manage existing subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        # Get current subscription using the mixin property
        subscription = user.current_subscription
        
        # If no subscription, redirect to plans page
        if not subscription:
            flash(_("You don't have an active subscription. Choose a plan below to subscribe."), "info")
            return redirect(url_for('.plans'))
        
        # Explicitly load payments
        from sqlalchemy.orm import joinedload
        if subscription:
            # Check for payments directly
            payments = self.check_subscription_payments(subscription.id)
            
            # Reload the subscription with joined payments
            subscription = self.appbuilder.session.query(UserSubscription).options(
                joinedload(UserSubscription.payments)
            ).filter_by(id=subscription.id).first()
            
            # Debug logging
            current_app.logger.info(f"Subscription ID: {subscription.id}")
            current_app.logger.info(f"Number of payments from helper: {len(payments)}")
            current_app.logger.info(f"Number of payments from subscription: {len(subscription.payments) if subscription.payments else 0}")
            
            # If we have payments but they're not showing up in subscription.payments, manually add them
            if payments and (not subscription.payments or len(subscription.payments) == 0):
                current_app.logger.info("Manually setting payments on subscription object")
                subscription.payments = payments
            
        # Check if user is admin
        is_admin = self.is_admin_user(user)
        
        return self.render_template('subscription/manage.html',
                                    subscription=subscription,
                                    user=user,
                                    is_admin=is_admin)

    @expose('/fix_missing_payment_links', methods=['GET'])
    @has_access
    def fix_missing_payment_links(self):
        """Administrative endpoint to fix payments without subscription_id"""
        # Check if user is admin
        if not self.is_admin_user():
            flash(_("You need to be an administrator to use this feature"), "warning")
            return redirect(url_for('SupersetIndexView.index'))
            
        try:
            # Find payments without subscription_id
            orphaned_payments = self.appbuilder.session.query(Payment).filter(
                Payment.subscription_id.is_(None)
            ).all()
            
            fixed_count = 0
            for payment in orphaned_payments:
                # Look for subscription from the same user
                subscription = self.appbuilder.session.query(UserSubscription).filter_by(
                    user_id=payment.user_id
                ).first()
                
                if subscription:
                    # Associate payment with subscription
                    payment.subscription_id = subscription.id
                    fixed_count += 1
            
            # Commit changes if any were made
            if fixed_count > 0:
                self.appbuilder.session.commit()
                flash(_(f"Successfully linked {fixed_count} orphaned payments to subscriptions"), "success")
            else:
                flash(_("No orphaned payments found"), "info")
                
        except Exception as e:
            current_app.logger.error(f"Error fixing orphaned payments: {str(e)}")
            flash(_("An error occurred while fixing orphaned payments"), "danger")
            self.appbuilder.session.rollback()
            
        return redirect(url_for('.manage'))
        
    @expose('/link_all_user_payments', methods=['GET'])
    @has_access
    def link_all_user_payments(self):
        """Link current user's payments to their active subscription"""
        user = self._get_user()
        subscription = user.current_subscription
        
        if not subscription:
            flash(_("You don't have an active subscription."), "warning")
            return redirect(url_for('.plans'))
            
        try:
            # Find payments for this user without subscription_id
            orphaned_payments = self.appbuilder.session.query(Payment).filter(
                Payment.user_id == user.id,
                Payment.subscription_id.is_(None)
            ).all()
            
            if orphaned_payments:
                # Link them to the current subscription
                for payment in orphaned_payments:
                    payment.subscription_id = subscription.id
                
                self.appbuilder.session.commit()
                flash(_(f"Successfully linked {len(orphaned_payments)} payment records to your subscription"), "success")
            else:
                flash(_("No unlinked payment records found"), "info")
                
        except Exception as e:
            current_app.logger.error(f"Error linking user payments: {str(e)}")
            flash(_("An error occurred while linking payments"), "danger")
            self.appbuilder.session.rollback()
            
        return redirect(url_for('.manage'))

    @expose('/cancel', methods=['POST'])
    @has_access
    def cancel(self):
        """Cancel subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        
        # Get current subscription using the mixin property
        subscription = user.current_subscription
        
        if subscription:
            subscription.status = 'cancelled'
            subscription.is_auto_renew = False
            self.appbuilder.session.commit()
            
            # Update user paid status to False since their subscription is cancelled
            self.update_user_paid_status(user.id, False)
            
            flash(_("Your subscription has been cancelled"), "success")
        return redirect(url_for('.manage'))

    # Helper methods
    def process_payment(self, plan, payment_method, payment_details=None):
        """
        Integrate with payment processor (Stripe, PayPal, etc.)
        Returns (success, transaction_id)
        """
        # Implement actual payment processing here
        # This is where you'd integrate with Stripe, PayPal, etc.
        if payment_method == 'credit_card' and payment_details:
            # Here you would use the payment_details to process the credit card payment
            # For example, using Stripe API
            pass
            
        return True, f"TRANS-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    def calc_subscription_period(self, plan):
        """Calculate subscription end date based on billing cycle"""
        if plan.billing_cycle == 'monthly':
            return datetime.timedelta(days=30)
        elif plan.billing_cycle == 'quarterly':
            return datetime.timedelta(days=90)
        elif plan.billing_cycle == 'yearly':
            return datetime.timedelta(days=365)
        return datetime.timedelta(days=30)  # Default to monthly
        
    def check_subscription_payments(self, subscription_id):
        """Helper function to check if a subscription has payments"""
        try:
            # Find both directly linked payments and possibly orphaned ones for this subscription
            payments = self.appbuilder.session.query(Payment).filter(
                or_(
                    Payment.subscription_id == subscription_id,
                    Payment.user_id == self.appbuilder.session.query(UserSubscription.user_id).filter(
                        UserSubscription.id == subscription_id
                    ).scalar_subquery()
                )
            ).all()
            
            current_app.logger.info(f"Found {len(payments)} payments for subscription {subscription_id}")
            return payments
        except Exception as e:
            current_app.logger.error(f"Error checking payments: {str(e)}")
            return []
            
    def update_user_paid_status(self, user_id, is_paid=True):
        """Update a user's is_paid_user status using direct SQL"""
        try:
            # Create update query
            stmt = text("UPDATE ab_user SET is_paid_user = :is_paid WHERE id = :user_id")
            
            # Execute the query
            self.appbuilder.session.execute(stmt, {"is_paid": is_paid, "user_id": user_id})
            
            # Commit the changes
            self.appbuilder.session.commit()
            
            current_app.logger.info(f"Updated is_paid_user status for user {user_id} to {is_paid}")
        except Exception as e:
            current_app.logger.error(f"Error updating user paid status: {str(e)}")
            self.appbuilder.session.rollback()
            
    def is_admin_user(self, user=None):
        """Helper function to check if a user has the Admin role"""
        if user is None:
            user = g.user
            
        if not hasattr(user, 'roles'):
            return False
            
        for role in user.roles:
            if role.name == 'Admin':
                return True
                
        return False
