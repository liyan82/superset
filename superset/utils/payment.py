import datetime
import time
from typing import Any, cast, Literal, Optional, Tuple

import stripe
from flask import current_app, Flask

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
                    "tax_code": "txcd_30011000",
                }
            ],
            shipping_cost={"amount": 300},
        )

        return tax_calculation

    def create_payment_intent(
        self, amount: float, currency: str = "usd", customer: Optional[str] = None, payment_method: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        self.log_payment(f"Creating payment intent for {amount} {currency}", level="info")
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
            self.log_payment(
                f"Created payment intent for {amount} {currency} "
                f"with id: {intent.id} and client_secret: {intent.client_secret}",
                level="info",
            )
            return True, intent.id, intent.client_secret
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error: {str(e)}", level="error")
            return False, None, str(e)

    def create_customer(self, user: User) -> Optional[stripe.Customer]:
        """Create a customer in Stripe"""
        try:
            customer = stripe.Customer.search(query=f"email:'{user.email}'")
            if customer.data:
                return cast(stripe.Customer, customer.data[0])

            params: dict[str, Any] = {"email": user.email}
            params["metadata"] = {"integration_id": user.id}
            if user.first_name and user.last_name:
                params["name"] = f"{user.first_name} {user.last_name}"
            new_customer = stripe.Customer.create(**params)
            return new_customer
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error: {str(e)}", level="error")
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
            self.log_payment(f"Stripe error: {str(e)}", level="error")
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
                    product = stripe.Product.create(name=plan.name, description=plan.description)
                    # In a real implementation, you'd save this back to the plan model
                    product_id = product.id
                else:
                    product_id = plan.stripe_product_id

                # Create a price
                price = stripe.Price.create(
                    product=product_id,
                    unit_amount=int(plan.price * 100),  # Convert to cents
                    currency="usd",
                    recurring={"interval": interval, "interval_count": interval_count},
                )
                # In a real implementation, you'd save this back to the plan model
                price_id = price.id
            else:
                price_id = plan.stripe_price_id

            # Create a checkout session - note no success_url or cancel_url for custom checkout
            session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                ui_mode="embedded",  # Use 'embedded' or 'hosted'
                customer_email=user.email,
                metadata={"product_id": str(plan.stripe_product_id), "user_id": str(user.id)},
                # Include Stripe headers for the beta separately as recommended in the docs  # noqa: E501
                stripe_version="2025-01-27.acacia; custom_checkout_beta=v1;",
                stripe_account=None,
            )

            # Log the entire session details for debugging (redact in production)
            self.log_payment(f"Session details: {session}", level="info")

            return True, session.id, session.client_secret
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error creating checkout session: {str(e)}", level="error")
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
            self.log_payment(f"Stripe error retrieving payment intent: {str(e)}", level="error")
            return None

    def revive_subscription(self, subscription_id: str) -> bool:
        """
        Revive a Stripe subscription

        Args:
            subscription_id: The Stripe Subscription ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Revive a Stripe subscription
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
            return True
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error reviving subscription: {str(e)}", level="error")
            return False

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
            stripe.Subscription.modify(  # At period end
                subscription_id, cancel_at_period_end=True
            )
            return True
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error canceling subscription: {str(e)}", level="error")
            return False

    def get_stripe_plans(self) -> list[dict[str, Any]]:
        """
        Fetch and format all active subscription plans from Stripe.

        Returns:
            list[dict]: List of plans with their details including prices
        """
        try:
            # Fetch all active products with their prices
            products = stripe.Product.list(active=True)
            plans = []

            for product in products.data:
                # Get the default price for this product
                prices = stripe.Price.list(product=product.id, active=True, limit=1)

                if prices.data:
                    price = prices.data[0]
                    self.log_payment(f"Price: {price}", level="info")
                    plans.append(
                        {
                            "id": product.id,
                            "product": product.name,
                            "description": product.description or "",
                            "price": price.unit_amount / 100 if price.unit_amount is not None else 0,
                            "billing_cycle": "month"
                            if price.recurring and price.recurring.interval == "month"
                            else "year",
                            "features": product.metadata.get("features", ""),
                            "stripe_price_id": price.id,
                            "stripe_product_id": product.id,
                        }
                    )

            return plans
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error fetching plans: {str(e)}", level="error")
            return []

    def get_stripe_plan(self, product_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch a single subscription plan from Stripe by its product ID.

        Args:
            product_id: The Stripe Product ID

        Returns:
            Optional[dict]: Plan details if found, None otherwise
        """
        try:
            # Fetch the product
            product = stripe.Product.retrieve(product_id)
            if not product.active:
                return None

            # Get the default price for this product
            prices = stripe.Price.list(product=product.id, active=True, limit=1)

            if not prices.data:
                return None

            price = prices.data[0]
            return {
                "id": product.id,
                "product": product.name,
                "description": product.description or "",
                "price": price.unit_amount / 100 if price.unit_amount is not None else 0,
                "billing_cycle": "month"
                if price.recurring and getattr(price.recurring, "interval", "") == "month"
                else "year",
                "features": product.metadata.get("features", ""),
                "stripe_price_id": price.id,
                "stripe_product_id": product.id,
            }
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error fetching plan {product_id}: {str(e)}", level="error")
            return None

    def create_stripe_customer(self, email: str, name: str) -> Optional[str]:
        """Create a Stripe customer."""
        try:
            # Query Stripe for existing customer
            search_result = stripe.Customer.search(query=f"email:'{email}'")
            if search_result.data:
                self.log_payment(f"Found existing customer {search_result}", level="info")
                # Explicitly cast to stripe.Customer to help the linter
                customer_object = cast(stripe.Customer, search_result.data[0])
                return customer_object.id
            else:
                self.log_payment(f"No existing customer found for {email}", level="info")
                new_customer = stripe.Customer.create(email=email, name=name)
                return new_customer.id
        except stripe.StripeError as e:
            self.log_payment(f"Stripe error creating customer: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log_payment(f"General error creating customer: {str(e)}", level="error")
            raise

    def create_stripe_subscription(
        self, customer: stripe.Customer, plan: SubscriptionPlan, sub_start_date: datetime.datetime
    ) -> Optional[stripe.Subscription]:  # noqa: E501
        """Create a Stripe subscription for a user"""
        self.log_payment(
            f"Starting create_stripe_subscription: "
            f"customer_id={customer.id}, "
            f"plan_id={plan.id}, "
            f"start_date={sub_start_date}",
            level="info",
        )
        try:
            if plan.stripe_price_id is None or plan.stripe_price_id == "":
                self.log_payment(f"Plan {plan.id} has no Stripe price ID", level="error")
                return None

            self.log_payment(f"Using stripe_price_id: {plan.stripe_price_id}", level="info")

            # check if subscription already exists
            self.log_payment(
                f"Checking for existing subscriptions for customer={customer.id}, price={plan.stripe_price_id}",
                level="info",
            )
            subscriptions = stripe.Subscription.list(customer=customer.id, price=plan.stripe_price_id)

            self.log_payment(f"Found {len(subscriptions.data)} existing subscriptions", level="info")

            if subscriptions.data:
                self.log_payment(
                    f"Existing subscription found: "
                    f"id={subscriptions.data[0].id}, "
                    f"status={subscriptions.data[0].status}",
                    level="info",
                )
                # if the subscription was cancelled and the end_date is in the future, we need to revive it
                if subscriptions.data[0].status == "canceled" and subscriptions.data[0].current_period_end > int(
                    time.time()
                ):
                    self.log_payment(
                        f"Reviving canceled subscription: "
                        f"id={subscriptions.data[0].id}, "
                        f"end_date={datetime.datetime.fromtimestamp(subscriptions.data[0].current_period_end)}",
                        level="info",
                    )
                    self.revive_subscription(subscriptions.data[0].id)
                    return subscriptions.data[0]

                # if the subscription is active, we need to return it
                if subscriptions.data[0].status == "active" or subscriptions.data[0].status == "incomplete":
                    self.log_payment(
                        f"Using existing subscription: "
                        f"id={subscriptions.data[0].id}, "
                        f"status={subscriptions.data[0].status}",
                        level="info",
                    )
                    return subscriptions.data[0]

            current_time = datetime.datetime.now()
            self.log_payment(
                f"Creating new subscription: "
                f"start_date={sub_start_date}, "
                f"current_time={current_time}, "
                f"charge_later={sub_start_date > current_time}",
                level="info",
            )

            if sub_start_date.date() > current_time.date():  # charge later
                self.log_payment(
                    f"Setting up future subscription with billing_cycle_anchor={int(sub_start_date.timestamp())}",
                    level="info",
                )
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{"price": plan.stripe_price_id}],
                    payment_behavior="default_incomplete",
                    collection_method="charge_automatically",
                    proration_behavior="none",
                    billing_cycle_anchor=int(sub_start_date.timestamp()),
                    payment_settings={"save_default_payment_method": "on_subscription"},
                    expand=["latest_invoice.payment_intent"],
                )
            else:  # charge now
                self.log_payment("Setting up immediate subscription with charge", level="info")
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{"price": plan.stripe_price_id}],
                    # Attempt the first charge right away:
                    payment_behavior="default_incomplete",
                    collection_method="charge_automatically",
                    # Vault whatever card they use for future cycles:
                    payment_settings={"save_default_payment_method": "on_subscription"},
                    # (optional) give you back the PaymentIntent so you can handle SCA:
                    expand=["latest_invoice.payment_intent"],
                )

            self.log_payment(
                f"Successfully created subscription: "
                f"id={subscription.id}, "
                f"status={subscription.status}, "
                f"current_period_start={datetime.datetime.fromtimestamp(subscription.current_period_start)}, "
                f"current_period_end={datetime.datetime.fromtimestamp(subscription.current_period_end)}",
                level="info",
            )
            return subscription

        except stripe.StripeError as e:
            self.log_payment(f"Stripe error creating subscription: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log_payment(f"General error creating subscription: {str(e)}", level="error")
            raise

    def log_payment(self, message: str, level: str = "info") -> None:
        """Log payment-related messages with special formatting"""
        logger_method = getattr(current_app.logger, level)
        logger_method(message, extra={"payment": True})
