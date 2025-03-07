import stripe
from flask import current_app


class PaymentProcessor:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        stripe.api_key = app.config.get('STRIPE_SECRET_KEY')

    def create_payment_intent(self, amount, currency='usd', customer=None,
                              payment_method=None):
        """Create a payment intent in Stripe"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer,
                payment_method=payment_method,
                confirm=True if payment_method else False,
            )
            return True, intent.id, intent.client_secret
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return False, None, str(e)

    def create_customer(self, email, name=None):
        """Create a customer in Stripe"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return customer.id
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return None

    def create_subscription(self, customer_id, price_id):
        """Create a subscription in Stripe"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                expand=['latest_invoice.payment_intent'],
            )
            return subscription
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return None
