import datetime

from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.views import ModelView
from flask import redirect, url_for, request, flash, g
from flask_babel import lazy_gettext as _

from flask_appbuilder.security.sqla.models import User
from superset.models.subscription import SubscriptionPlan, UserSubscription, Payment


class SubscriptionView(BaseView):
    route_base = "/subscription"
    default_view = "index"  # Set the default view to the index method

    def _get_user(self):
        """Get a fresh User instance with all extensions applied"""
        from sqlalchemy.orm import joinedload
        # Make sure to eagerly load the subscriptions relationship
        user = self.appbuilder.session.query(User).options(
            joinedload(User.subscriptions).joinedload(UserSubscription.plan)
        ).get(g.user.id)

        # Force SQLAlchemy to load the subscriptions
        if hasattr(user, 'subscriptions'):
            _ = user.subscriptions

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

                # Create payment record
                payment = Payment(
                    user_id=user.id,
                    amount=plan.price,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    status='success'
                )

                # Update user status - this should now work with the extended model
                user.is_paid_user = True

                # Save to database
                self.appbuilder.session.add(subscription)
                self.appbuilder.session.add(payment)
                self.appbuilder.session.commit()

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
            
        return self.render_template('subscription/manage.html',
                                    subscription=subscription,
                                    user=user)

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
