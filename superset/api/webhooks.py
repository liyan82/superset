from flask import Blueprint, request, jsonify, current_app
import stripe
from superset.extensions import db
from superset.models.subscription import UserSubscription, Payment
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound

webhook_blueprint = Blueprint('webhook', __name__)


@webhook_blueprint.route('/stripe', methods=['POST'])
def stripe_webhook():
    # Get the webhook signature
    signature = request.headers.get('Stripe-Signature')
    payload = request.data

    try:
        # Verify the webhook signature
        event = stripe.Webhook.construct_event(
            payload, signature, current_app.config.get('STRIPE_WEBHOOK_SECRET')
        )

        # Handle the event based on type
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            handle_successful_payment(payment_intent)
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            handle_successful_invoice(invoice)
        elif event['type'] == 'subscription.created':
            subscription = event['data']['object']
            handle_subscription_created(subscription)
        elif event['type'] == 'subscription.updated':
            subscription = event['data']['object']
            handle_subscription_updated(subscription)
        elif event['type'] == 'subscription.deleted':
            subscription = event['data']['object']
            handle_subscription_cancelled(subscription)

        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


# All handler methods defined in the same file
def handle_successful_payment(payment_intent):
    """
    Handle a successful payment intent from Stripe
    """
    # Extract metadata from the payment intent
    metadata = payment_intent.get('metadata', {})
    user_id = metadata.get('user_id')
    subscription_id = metadata.get('subscription_id')

    if not user_id or not subscription_id:
        current_app.logger.error(
            "Payment intent missing user_id or subscription_id in metadata")
        return

    try:
        # Find the subscription in our database
        subscription = db.session.query(UserSubscription).filter_by(
            id=subscription_id).one()

        # Create a payment record
        payment = Payment(
            subscription_id=subscription_id,
            user_id=user_id,
            amount=payment_intent['amount'] / 100.0,  # Convert from cents
            currency=payment_intent['currency'].upper(),
            payment_method='stripe',
            transaction_id=payment_intent['id'],
            status='success',
            payment_date=datetime.fromtimestamp(payment_intent['created'])
        )

        db.session.add(payment)
        db.session.commit()
        current_app.logger.info(
            f"Recorded successful payment for subscription {subscription_id}")
    except NoResultFound:
        current_app.logger.error(
            f"Subscription {subscription_id} not found for payment {payment_intent['id']}")
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {str(e)}")
        db.session.rollback()


def handle_successful_invoice(invoice):
    """
    Handle a successful invoice payment from Stripe
    """
    # Extract subscription info from the invoice
    stripe_subscription_id = invoice.get('subscription')
    if not stripe_subscription_id:
        return

    try:
        # Find our subscription that matches this Stripe subscription
        subscription = db.session.query(UserSubscription).filter_by(
            external_subscription_id=stripe_subscription_id
        ).one()

        # Update subscription end date based on billing cycle
        subscription.end_date = calculate_new_end_date(subscription)

        # Create payment record
        payment = Payment(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            amount=invoice['amount_paid'] / 100.0,  # Convert from cents
            currency=invoice['currency'].upper(),
            payment_method='stripe',
            transaction_id=invoice['payment_intent'],
            status='success',
            payment_date=datetime.fromtimestamp(invoice['created'])
        )

        db.session.add(payment)
        db.session.commit()
        current_app.logger.info(
            f"Processed invoice payment for subscription {subscription.id}")
    except NoResultFound:
        current_app.logger.error(
            f"No matching subscription found for Stripe subscription {stripe_subscription_id}")
    except Exception as e:
        current_app.logger.error(f"Error processing invoice: {str(e)}")
        db.session.rollback()


def handle_subscription_created(subscription_data):
    """
    Handle a subscription creation event from Stripe
    """
    # Extract customer info to find our user
    stripe_customer_id = subscription_data.get('customer')
    if not stripe_customer_id:
        return

    try:
        # Find user by Stripe customer ID (assuming you store this)
        from superset.models.core import User
        user = db.session.query(User).filter_by(
            stripe_customer_id=stripe_customer_id
        ).one()

        # Create or update subscription record
        subscription = UserSubscription(
            user_id=user.id,
            external_subscription_id=subscription_data['id'],
            status='active',
            start_date=datetime.now(),
            # Set plan_id based on your business logic
            # plan_id=determine_plan_id_from_stripe_data(subscription_data),
            is_auto_renew=True
        )

        db.session.add(subscription)
        db.session.commit()
    except NoResultFound:
        current_app.logger.error(
            f"No user found with Stripe customer ID {stripe_customer_id}")
    except Exception as e:
        current_app.logger.error(f"Error processing subscription creation: {str(e)}")
        db.session.rollback()


def handle_subscription_updated(subscription_data):
    """
    Handle a subscription update event from Stripe
    """
    stripe_subscription_id = subscription_data.get('id')
    if not stripe_subscription_id:
        return

    try:
        # Find subscription by Stripe ID
        subscription = db.session.query(UserSubscription).filter_by(
            external_subscription_id=stripe_subscription_id
        ).one()

        # Update subscription status based on Stripe status
        status_mapping = {
            'active': 'active',
            'past_due': 'past_due',
            'unpaid': 'expired',
            'canceled': 'cancelled',
            'trialing': 'trial'
        }

        new_status = status_mapping.get(subscription_data['status'],
                                        subscription.status)
        subscription.status = new_status

        # Update other details as needed
        db.session.commit()
        current_app.logger.info(
            f"Updated subscription {subscription.id} status to {new_status}")
    except NoResultFound:
        current_app.logger.error(
            f"No matching subscription found for Stripe subscription {stripe_subscription_id}")
    except Exception as e:
        current_app.logger.error(f"Error updating subscription: {str(e)}")
        db.session.rollback()


def handle_subscription_cancelled(subscription_data):
    """
    Handle a subscription cancellation event from Stripe
    """
    stripe_subscription_id = subscription_data.get('id')
    if not stripe_subscription_id:
        return

    try:
        # Find subscription by Stripe ID
        subscription = db.session.query(UserSubscription).filter_by(
            external_subscription_id=stripe_subscription_id
        ).one()

        # Mark as cancelled
        subscription.status = 'cancelled'
        subscription.is_auto_renew = False

        db.session.commit()
        current_app.logger.info(f"Marked subscription {subscription.id} as cancelled")
    except NoResultFound:
        current_app.logger.error(
            f"No matching subscription found for Stripe subscription {stripe_subscription_id}")
    except Exception as e:
        current_app.logger.error(f"Error cancelling subscription: {str(e)}")
        db.session.rollback()


def calculate_new_end_date(subscription):
    """Helper function to calculate new end date based on billing cycle"""
    from datetime import datetime, timedelta

    # Get the billing cycle from the subscription's plan
    billing_cycle = subscription.plan.billing_cycle

    if billing_cycle == 'monthly':
        return datetime.now() + timedelta(days=30)
    elif billing_cycle == 'quarterly':
        return datetime.now() + timedelta(days=90)
    elif billing_cycle == 'yearly':
        return datetime.now() + timedelta(days=365)

    # Default to monthly if unknown
    return datetime.now() + timedelta(days=30)
