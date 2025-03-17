import datetime
import json

import stripe
from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.views import ModelView
from flask import redirect, url_for, request, flash, g, current_app, jsonify
from flask_babel import lazy_gettext as _
from sqlalchemy import or_, text

from flask_appbuilder.security.sqla.models import User
from stripe import PaymentIntent

from superset.models.subscription import SubscriptionPlan, UserSubscription, Payment
from superset.utils.payment import PaymentProcessor


class SubscriptionView(BaseView):
    route_base = "/subscription"
    default_view = "index"  # Set the default view to the index method
    payment_processor = None
    calculateTax = False

    def __init__(self):
        super().__init__()
        self.payment_processor = PaymentProcessor(current_app)

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
            flash(_("You already have an active subscription. Manage it below."),
                  "info")
            return redirect(url_for('.manage'))

        plans = self.appbuilder.session.query(SubscriptionPlan).filter_by(
            is_active=True).all()
        return self.render_template('subscription/plans.html',
                                    plans=plans,
                                    user=user)

    @expose('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
    @has_access
    def subscribe(self, plan_id):
        """Process new subscription - redirects to payment page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Please cancel it before subscribing to a new plan."),
                "warning")
            return redirect(url_for('.manage'))

        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for('.plans'))

        # Redirect to payment page with plan_id
        return redirect(url_for('.payment', plan_id=plan_id))

    @expose('/payment/<int:plan_id>', methods=['GET', 'POST'])
    @has_access
    def payment(self, plan_id):
        """Show payment form using Stripe Checkout"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Please cancel it before subscribing to a new plan."),
                "warning")
            return redirect(url_for('.manage'))

        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for('.plans'))

        # Pass the plan and stripe publishable key to the template
        # The client_secret will be fetched via AJAX
        return self.render_template('subscription/payment.html',
                                    plan=plan,
                                    user=user,
                                    plan_id=plan_id,
                                    stripe_publishable_key=current_app.config.get(
                                        'STRIPE_PUBLIC_KEY'))

    @expose('/create-payment-intent', methods=['POST'])
    @has_access
    def create_payment_intent(self):
        try:
            data = json.loads(request.data)
            order_amount = data['orderAmount']

            # Convert to float first (in case it's a string), then to cents as integer
            amount_in_cents = int(float(order_amount) * 100)

            intent: PaymentIntent

            if self.calculateTax:
                tax_calculation = self.payment_processor.calculate_tax(order_amount, "usd")
                intent: PaymentIntent = stripe.PaymentIntent.create(
                    amount=tax_calculation['amount_total'],
                    currency='usd',
                    automatic_payment_methods={
                        'enabled': True,
                    },
                    metadata={
                      'tax_calculation': tax_calculation['id']
                    }
                )
            else:
                intent: PaymentIntent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency='usd',
                    automatic_payment_methods={
                        'enabled': True,
                                              }
                )

            # send payment intent to client
            current_app.logger.info(f'Created payment intent for {intent.amount} {intent.currency} with id: {intent.id} and client_secret: {intent.client_secret}')
            return jsonify({'clientSecret': intent.client_secret})
        except stripe.error.StripeError as e:
            return jsonify({'error': {'message': str(e)}}), 400
        except Exception as e:
            return jsonify({'error': {'message': str(e)}}), 400



    @expose('/create-checkout-session', methods=['POST'])
    @has_access
    def create_checkout_session(self):
        """API endpoint to create a Stripe Checkout Session"""
        # Get a fresh User instance
        user = self._get_user()

        # Get plan_id from the request
        data = json.loads(request.data)
        plan_id = data.get('plan_id')

        if not plan_id:
            return jsonify({"error": "Missing plan_id parameter"}), 400

        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            return jsonify({"error": "Invalid subscription plan"}), 400

        # Create Stripe Checkout Session
        success, session_id, client_secret = self.payment_processor.create_checkout_session(
            plan=plan,
            user=user
        )

        if not success:
            return jsonify({"error": client_secret}), 500
        
        # Log the client secret for debugging (redact in production)
        current_app.logger.info(f"Client secret: {client_secret}")
            
        return jsonify({
            "checkoutSessionClientSecret": client_secret
        })

    @expose('/payment-complete', methods=['POST'])
    @has_access
    def payment_complete(self):
        """Handle successful payment completion via AJAX"""
        # Get a fresh User instance
        user = self._get_user()

        # Get session_id and subscription_id from the request
        data = json.loads(request.data)
        intent_id = data.get('payment_intent_id')
        plan_id = data.get('plan_id')

        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            return jsonify({"error": "Invalid subscription plan"}), 400

        if not intent_id:
            return jsonify({"error": "Payment was no successful because Stripe does not response."}), 400

        # Retrieve the checkout session from Stripe to verify
        intent = self.payment_processor.retrieve_intent(intent_id)
        if not intent:
            return jsonify({"error": "Error retrieving payment information"}), 500

        # Verify the payment was successful
        if intent.status != 'succeeded':
            return jsonify({"error": "Payment not completed successfully"}), 400

        # Create subscription in our database
        end_date = datetime.datetime.now() + self.calc_subscription_period(plan)
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status='active',
            start_date=datetime.datetime.now(),
            end_date=end_date,
            is_auto_renew=True,
            external_subscription_id=intent_id
        )

        # Save the subscription first to get an ID
        self.appbuilder.session.add(subscription)
        self.appbuilder.session.flush()  # Flush to get subscription.id without committing

        # Create payment record with subscription association
        payment = Payment(
            user_id=user.id,
            subscription_id=subscription.id,  # Link payment to subscription
            amount=plan.price,
            payment_method='stripe',
            transaction_id=intent_id,
            status='success'
        )

        # Add payment to session and commit both subscription and payment
        self.appbuilder.session.add(payment)

        # Debug logging
        current_app.logger.info(
            f"Created subscription {subscription.id} with payment from Stripe")
        current_app.logger.info(
            f"Payment details: {payment.amount}, {payment.payment_method}, {payment.status}")

        # Commit subscription and payment
        self.appbuilder.session.commit()

        # Update user paid status using direct SQL (this includes its own commit)
        self.update_user_paid_status(user.id, True)

        return jsonify({
            "success": True,
            "subscription_id": subscription.id
        })

    @expose('/subscription-success')
    @has_access
    def subscription_success(self):
        """Show subscription success page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        # Get current subscription - the one most recently created
        subscription = user.current_subscription

        if not subscription:
            flash(_("No active subscription found"), "danger")
            return redirect(url_for('.plans'))

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
            flash(
                _("You don't have an active subscription. Choose a plan below to subscribe."),
                "info")
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
            current_app.logger.info(
                f"Number of payments from subscription: {len(subscription.payments) if subscription.payments else 0}")

            # If we have payments but they're not showing up in subscription.payments, manually add them
            if payments and (
                not subscription.payments or len(subscription.payments) == 0):
                current_app.logger.info(
                    "Manually setting payments on subscription object")
                subscription.payments = payments

        # Check if user is admin
        is_admin = self.is_admin_user(user)

        return self.render_template('subscription/manage.html',
                                    subscription=subscription,
                                    user=user,
                                    is_admin=is_admin)

    @expose('/cancel', methods=['POST'])
    @has_access
    def cancel(self):
        """Cancel subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        # Get current subscription using the mixin property
        subscription = user.current_subscription

        if subscription:
            # If we have a Stripe subscription ID, cancel in Stripe
            if hasattr(subscription,
                       'stripe_subscription_id') and subscription.stripe_subscription_id:
                success = self.payment_processor.cancel_subscription(
                    subscription.stripe_subscription_id)
                if not success:
                    flash(_("Error cancelling subscription with payment provider"),
                          "danger")
                    return redirect(url_for('.manage'))

            subscription.status = 'cancelled'
            subscription.is_auto_renew = False
            self.appbuilder.session.commit()

            # Update user paid status to False since their subscription is cancelled
            self.update_user_paid_status(user.id, False)

            flash(_("Your subscription has been cancelled"), "success")
        return redirect(url_for('.manage'))

    # Helper methods
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
                    Payment.user_id == self.appbuilder.session.query(
                        UserSubscription.user_id).filter(
                        UserSubscription.id == subscription_id
                    ).scalar_subquery()
                )
            ).all()

            current_app.logger.info(
                f"Found {len(payments)} payments for subscription {subscription_id}")
            return payments
        except Exception as e:
            current_app.logger.error(f"Error checking payments: {str(e)}")
            return []

    def update_user_paid_status(self, user_id, is_paid=True):
        """Update a user's is_paid_user status using direct SQL"""
        try:
            # Create update query
            stmt = text(
                "UPDATE ab_user SET is_paid_user = :is_paid WHERE id = :user_id")

            # Execute the query
            self.appbuilder.session.execute(stmt,
                                            {"is_paid": is_paid, "user_id": user_id})

            # Commit the changes
            self.appbuilder.session.commit()

            current_app.logger.info(
                f"Updated is_paid_user status for user {user_id} to {is_paid}")
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
