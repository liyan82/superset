import json
import stripe

from flask import request, jsonify, current_app
from flask_appbuilder import BaseView, expose

from superset.models.subscription import UserSubscription, Payment
from superset.utils.payment import PaymentProcessor


class StripeWebhookView(BaseView):
    route_base = "/stripe-webhook"

    def __init__(self):
        super().__init__()
        self.payment_processor = PaymentProcessor(current_app)

    @expose('/', methods=['POST'])
    def webhook(self):
        """Handle Stripe webhook events"""
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')

        # Verify webhook signature and construct event
        try:
            webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            current_app.logger.error(f"Stripe webhook invalid payload: {str(e)}")
            return jsonify(error=str(e)), 400
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            current_app.logger.error(f"Stripe webhook invalid signature: {str(e)}")
            return jsonify(error=str(e)), 400

        # Handle the event
        try:
            event_type = event['type']
            event_data = event['data']['object']

            current_app.logger.info(f"Processing Stripe webhook event: {event_type}")

            if event_type == 'checkout.session.completed':
                # Payment was successful, handle subscription
                self._handle_checkout_session_completed(event_data)
            elif event_type == 'customer.subscription.updated':
                # Subscription was updated
                self._handle_subscription_updated(event_data)
            elif event_type == 'customer.subscription.deleted':
                # Subscription was cancelled
                self._handle_subscription_deleted(event_data)
            elif event_type == 'invoice.payment_succeeded':
                # Invoice payment succeeded
                self._handle_invoice_payment_succeeded(event_data)
            elif event_type == 'invoice.payment_failed':
                # Invoice payment failed
                self._handle_invoice_payment_failed(event_data)

            return jsonify(success=True)
        except Exception as e:
            current_app.logger.error(f"Error processing Stripe webhook: {str(e)}")
            return jsonify(error=str(e)), 500

    def _handle_checkout_session_completed(self, session):
        """Handle checkout.session.completed event"""
        # This was already handled in the success redirect handler
        # But we include it here for redundancy in case the redirect fails

        # Check if this session has already been processed
        payment = self.appbuilder.session.query(Payment).filter_by(
            transaction_id=session.id
        ).first()

        if payment:
            current_app.logger.info(f"Checkout session {session.id} already processed")
            return

        # Get metadata
        metadata = session.get('metadata', {})
        plan_id = metadata.get('plan_id')
        user_id = metadata.get('user_id')

        if not plan_id or not user_id:
            current_app.logger.error(
                f"Missing metadata in checkout session: {session.id}")
            return

        # Create subscription record (if missing)
        from superset.models.subscription import SubscriptionPlan
        import datetime

        # Get the plan
        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            current_app.logger.error(f"Invalid plan ID in checkout session: {plan_id}")
            return

        # Calculate subscription period
        if plan.billing_cycle == 'monthly':
            period = datetime.timedelta(days=30)
        elif plan.billing_cycle == 'quarterly':
            period = datetime.timedelta(days=90)
        elif plan.billing_cycle == 'yearly':
            period = datetime.timedelta(days=365)
        else:
            period = datetime.timedelta(days=30)

        # Create subscription record
        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            status='active',
            start_date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + period,
            is_auto_renew=True,
            stripe_subscription_id=session.subscription
        )

        # Save subscription
        self.appbuilder.session.add(subscription)
        self.appbuilder.session.flush()

        # Create payment record
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=plan.price,
            payment_method='stripe',
            transaction_id=session.id,
            status='success'
        )

        # Save payment
        self.appbuilder.session.add(payment)
        self.appbuilder.session.commit()

        # Update user paid status
        self._update_user_paid_status(user_id, True)

    def _handle_subscription_updated(self, subscription):
        """Handle customer.subscription.updated event"""
        # Find the subscription in our database
        db_subscription = self.appbuilder.session.query(UserSubscription).filter_by(
            stripe_subscription_id=subscription.id
        ).first()

        if not db_subscription:
            current_app.logger.error(f"Subscription not found: {subscription.id}")
            return

        # Update subscription status
        if subscription.status == 'active':
            db_subscription.status = 'active'
        elif subscription.status == 'canceled':
            db_subscription.status = 'cancelled'
            db_subscription.is_auto_renew = False
        elif subscription.status == 'past_due':
            db_subscription.status = 'past_due'
        elif subscription.status == 'unpaid':
            db_subscription.status = 'unpaid'
        elif subscription.status == 'incomplete':
            db_subscription.status = 'pending'
        elif subscription.status == 'incomplete_expired':
            db_subscription.status = 'expired'
        elif subscription.status == 'trialing':
            db_subscription.status = 'active'

        # Update end date
        if subscription.current_period_end:
            import datetime
            db_subscription.end_date = datetime.datetime.fromtimestamp(
                subscription.current_period_end)

        # Save changes
        self.appbuilder.session.commit()

        # Update user paid status if subscription is not active
        if db_subscription.status != 'active':
            self._update_user_paid_status(db_subscription.user_id, False)

    def _handle_subscription_deleted(self, subscription):
        """Handle customer.subscription.deleted event"""
        # Find the subscription in our database
        db_subscription = self.appbuilder.session.query(UserSubscription).filter_by(
            stripe_subscription_id=subscription.id
        ).first()

        if not db_subscription:
            current_app.logger.error(f"Subscription not found: {subscription.id}")
            return

        # Update subscription status
        db_subscription.status = 'cancelled'
        db_subscription.is_auto_renew = False

        # Save changes
        self.appbuilder.session.commit()

        # Update user paid status
        self._update_user_paid_status(db_subscription.user_id, False)

    def _handle_invoice_payment_succeeded(self, invoice):
        """Handle invoice.payment_succeeded event"""
        # Only handle subscription invoices
        if not invoice.subscription:
            return

        # Find the subscription in our database
        db_subscription = self.appbuilder.session.query(UserSubscription).filter_by(
            stripe_subscription_id=invoice.subscription
        ).first()

        if not db_subscription:
            current_app.logger.error(f"Subscription not found: {invoice.subscription}")
            return

        # Check if payment already exists
        payment = self.appbuilder.session.query(Payment).filter_by(
            transaction_id=invoice.id
        ).first()

        if payment:
            current_app.logger.info(f"Invoice {invoice.id} already processed")
            return

        # Create payment record
        payment = Payment(
            user_id=db_subscription.user_id,
            subscription_id=db_subscription.id,
            amount=invoice.amount_paid / 100.0,  # Convert from cents
            payment_method='stripe',
            transaction_id=invoice.id,
            status='success'
        )

        # Save payment
        self.appbuilder.session.add(payment)

        # Update subscription status
        db_subscription.status = 'active'

        # Update end date
        if hasattr(invoice, 'lines') and invoice.lines.data:
            for line in invoice.lines.data:
                if line.type == 'subscription':
                    import datetime
                    db_subscription.end_date = datetime.datetime.fromtimestamp(
                        line.period.end)
                    break

        # Save changes
        self.appbuilder.session.commit()

        # Update user paid status
        self._update_user_paid_status(db_subscription.user_id, True)

    def _handle_invoice_payment_failed(self, invoice):
        """Handle invoice.payment_failed event"""
        # Only handle subscription invoices
        if not invoice.subscription:
            return

        # Find the subscription in our database
        db_subscription = self.appbuilder.session.query(UserSubscription).filter_by(
            stripe_subscription_id=invoice.subscription
        ).first()

        if not db_subscription:
            current_app.logger.error(f"Subscription not found: {invoice.subscription}")
            return

        # Create payment record
        payment = Payment(
            user_id=db_subscription.user_id,
            subscription_id=db_subscription.id,
            amount=invoice.amount_due / 100.0,  # Convert from cents
            payment_method='stripe',
            transaction_id=invoice.id,
            status='failed'
        )

        # Save payment
        self.appbuilder.session.add(payment)

        # Update subscription status if payment fails too many times
        if invoice.attempt_count >= 3:
            db_subscription.status = 'past_due'

            # Update user paid status
            self._update_user_paid_status(db_subscription.user_id, False)

        # Save changes
        self.appbuilder.session.commit()

    def _update_user_paid_status(self, user_id, is_paid=True):
        """Update a user's is_paid_user status"""
        try:
            from sqlalchemy import text

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
