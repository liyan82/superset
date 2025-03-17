import stripe
from flask import current_app, request


class PaymentProcessor:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
        # Enable beta headers for Custom Checkout (correct format)
        stripe.api_version = "2025-01-27.acacia; custom_checkout_beta=v1;"
        # Stripe API version is still in beta for Custom Checkout
        # We set this directly when calling Session.create

    def calculate_tax(orderAmount: int, currency: str):
        tax_calculation = stripe.tax.Calculation.create(
            currency=currency,
            customer_details={
                "address": {
                    "line1": "10709 Cleary Blvd",
                    "city": "Plantation",
                    "state": "FL",
                    "postal_code": "33324",
                    "country": "US",
                },
                "address_source": "shipping",
            },
            line_items=[
                {
                    "amount": orderAmount,  # Amount in cents
                    "reference": "ProductRef",
                    "tax_behavior": "exclusive",
                    "tax_code": "txcd_30011000"
                }
            ],
            shipping_cost={"amount": 300}
        )

        return tax_calculation

    def create_payment_intent(self, amount, currency='usd', customer=None,
                              payment_method=None):
        current_app.logger.info(f"Creating payment intent for {amount} {currency}")
        """Create a payment intent in Stripe"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer,
                payment_method=payment_method,
                confirm=True if payment_method else False,
            )
            current_app.logger.info(f"Created payment intent for {amount} {currency} with id: {intent.id} and client_secret: {intent.client_secret}")
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

    def create_checkout_session(self, plan, user):
        """
        Create a Stripe Checkout Session for a subscription plan

        Args:
            plan: The SubscriptionPlan model instance
            user: The User model instance

        Returns:
            tuple: (success, session_id, client_secret or error message)
        """
        try:
            # Determine the billing interval based on the plan's billing_cycle
            interval = 'month'  # Default to monthly
            interval_count = 1

            if plan.billing_cycle == 'quarterly':
                interval = 'month'
                interval_count = 3
            elif plan.billing_cycle == 'yearly':
                interval = 'year'
                interval_count = 1

            # Check if a price_id exists in Stripe for this plan
            # If not, create a new price in Stripe
            if not hasattr(plan, 'stripe_price_id') or not plan.stripe_price_id:
                # Create a product first if needed
                if not hasattr(plan, 'stripe_product_id') or not plan.stripe_product_id:
                    product = stripe.Product.create(
                        name=plan.name,
                        description=plan.description
                    )
                    # In a real implementation, you'd save this back to the plan model
                    product_id = product.id
                else:
                    product_id = plan.stripe_product_id

                # Create a price
                price = stripe.Price.create(
                    product=product_id,
                    unit_amount=int(plan.price * 100),  # Convert to cents
                    currency='usd',
                    recurring={
                        'interval': interval,
                        'interval_count': interval_count
                    }
                )
                # In a real implementation, you'd save this back to the plan model
                price_id = price.id
            else:
                price_id = plan.stripe_price_id

            # Create a checkout session - note no success_url or cancel_url for custom checkout
            session = stripe.checkout.Session.create(
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                ui_mode='custom',  # Use custom UI mode for embedded components
                customer_email=user.email,
                metadata={
                    'plan_id': str(plan.id),
                    'user_id': str(user.id)
                },
                # Include Stripe headers for the beta separately as recommended in the docs
                stripe_version="2025-01-27.acacia; custom_checkout_beta=v1;",
                stripe_account=None
            )

            # Log the session details for debugging (redact in production)
            current_app.logger.info(f"Session created with id: {session.id}")
            current_app.logger.info(f"Session client_secret: {session.client_secret}")
            
            return True, session.id, session.client_secret
        except stripe.error.StripeError as e:
            current_app.logger.error(
                f"Stripe error creating checkout session: {str(e)}")
            return False, None, str(e)

    def retrieve_intent(self, intent_id):
        """
        Retrieve a Stripe Checkout Session

        Args:
            session_id: The Stripe Checkout Session ID

        Returns:
            The Checkout Session object or None if error
        """
        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)

            return intent
        except stripe.error.StripeError as e:
            current_app.logger.error(
                f"Stripe error retrieving checkout session: {str(e)}")
            return None

    def cancel_subscription(self, subscription_id):
        """
        Cancel a Stripe subscription

        Args:
            subscription_id: The Stripe Subscription ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return True
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error canceling subscription: {str(e)}")
            return False
