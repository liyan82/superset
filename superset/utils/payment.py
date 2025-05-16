from typing import Any, Literal, Optional, Tuple

import stripe
from flask import current_app, Flask, request

# Assuming User and SubscriptionPlan are defined elsewhere and can be imported
# from superset.models import User  # Example, adjust path as necessary
# from superset.models.subscription import SubscriptionPlan # Example

# Forward declaration for type hinting if direct import is complex
User = Any 
SubscriptionPlan = Any


class PaymentProcessor:
    def __init__(self, app: Optional[Flask] = None) -> None:
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        self.app = app
        stripe.api_key = app.config.get("STRIPE_SECRET_KEY")
        # Enable beta headers for Custom Checkout (correct format)
        stripe.api_version = "2025-01-27.acacia; custom_checkout_beta=v1;"
        # Stripe API version is still in beta for Custom Checkout
        # We set this directly when calling Session.create

    def calculate_tax(self, order_amount: int, currency: str) -> stripe.tax.Calculation:
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
                    "amount": order_amount,  # Amount in cents
                    "reference": "ProductRef",
                    "tax_behavior": "exclusive",
                    "tax_code": "txcd_30011000"
                }
            ],
            shipping_cost={"amount": 300}
        )

        return tax_calculation

    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        current_app.logger.info(f"Creating payment intent for {amount} {currency}")
        """Create a payment intent in Stripe"""
        try:
            params: dict[str, Any] = {
                "amount": int(amount * 100),  # Convert to cents
                "currency": currency,
                "confirm": True if payment_method else False,
            }
            if customer:
                params["customer"] = customer
            if payment_method:
                params["payment_method"] = payment_method

            intent = stripe.PaymentIntent.create(**params)
            current_app.logger.info(
                f"Created payment intent for {amount} {currency} "
                f"with id: {intent.id} and client_secret: {intent.client_secret}"
            )
            return True, intent.id, intent.client_secret
        except stripe.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return False, None, str(e)

    def create_customer(self, email: str, name: Optional[str] = None) -> Optional[str]:
        """Create a customer in Stripe"""
        try:
            params: dict[str, Any] = {"email": email}
            if name:
                params["name"] = name
            customer = stripe.Customer.create(**params)
            return customer.id
        except stripe.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return None

    def create_subscription(self, customer_id: str, price_id: str) -> Optional[stripe.Subscription]:  # noqa: E501
        """Create a subscription in Stripe"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                expand=["latest_invoice.payment_intent"],
            )
            return subscription
        except stripe.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return None

    def create_checkout_session(self, plan: SubscriptionPlan, user: User) -> Tuple[bool, Optional[str], Optional[str]]:  # noqa: E501
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
            interval: Literal["day", "month", "week", "year"] = "month"  # Default to monthly
            interval_count: int = 1

            if plan.billing_cycle == "quarterly":
                interval = "month"
                interval_count = 3
            elif plan.billing_cycle == "yearly":
                interval = "year"
                interval_count = 1

            # Check if a price_id exists in Stripe for this plan
            # If not, create a new price in Stripe
            if not hasattr(plan, "stripe_price_id") or not plan.stripe_price_id:
                # Create a product first if needed
                product_id: str
                if not hasattr(plan, "stripe_product_id") or not plan.stripe_product_id:
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
                    currency="usd",
                    recurring={
                        "interval": interval,
                        "interval_count": interval_count
                    }
                )
                # In a real implementation, you'd save this back to the plan model
                price_id = price.id
            else:
                price_id = plan.stripe_price_id

            # Create a checkout session - note no success_url or cancel_url for custom checkout
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                ui_mode="embedded",  # Use 'embedded' or 'hosted'
                customer_email=user.email,
                metadata={
                    "plan_id": str(plan.id),
                    "user_id": str(user.id)
                },
                # Include Stripe headers for the beta separately as recommended in the docs  # noqa: E501
                stripe_version="2025-01-27.acacia; custom_checkout_beta=v1;",
                stripe_account=None
            )

            # Log the session details for debugging (redact in production)
            current_app.logger.info(f"Session created with id: {session.id}")
            current_app.logger.info(f"Session client_secret: {session.client_secret}")

            return True, session.id, session.client_secret
        except stripe.StripeError as e:
            current_app.logger.error(
                f"Stripe error creating checkout session: {str(e)}")
            return False, None, str(e)

    def retrieve_intent(self, intent_id: str) -> Optional[stripe.PaymentIntent]:
        """
        Retrieve a Stripe Payment Intent

        Args:
            intent_id: The Stripe Payment Intent ID

        Returns:
            The PaymentIntent object or None if error
        """
        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)

            return intent
        except stripe.StripeError as e:
            current_app.logger.error(
                f"Stripe error retrieving payment intent: {str(e)}")
            return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a Stripe subscription

        Args:
            subscription_id: The Stripe Subscription ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Cancelling immediately, or at period end.
            # stripe.Subscription.delete(subscription_id) # Immediate
            stripe.Subscription.modify( # At period end
                subscription_id,
                cancel_at_period_end=True
            )
            return True
        except stripe.StripeError as e:
            current_app.logger.error(f"Stripe error canceling subscription: {str(e)}")
            return False
