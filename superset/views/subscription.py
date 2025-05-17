import datetime
import json
from typing import Any

import stripe
from flask import (
    current_app,
    flash,
    g,
    jsonify,
    make_response,
    redirect,
    request,
    url_for,
)
from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.security.sqla.models import Role, User
from flask_babel import lazy_gettext as _
from sqlalchemy import or_, text
from stripe import StripeError
from werkzeug.wrappers import Response

from superset.models.subscription import Payment, SubscriptionPlan, UserSubscription
from superset.utils.payment import PaymentProcessor


class SubscriptionView(BaseView):
    route_base = "/subscription"
    default_view = "index"  # Set the default view to the index method
    payment_processor: PaymentProcessor
    calculate_tax: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.payment_processor = PaymentProcessor(current_app)

    def _get_user(self) -> User:
        """Get a fresh User instance with all extensions applied"""
        from sqlalchemy.orm import joinedload

        # Make sure to eagerly load the subscriptions relationship and payments
        user = (
            self.appbuilder.session.query(User)
            .options(
                joinedload(User.subscriptions).joinedload(UserSubscription.plan),
                joinedload(User.subscriptions).joinedload(UserSubscription.payments),
            )
            .get(g.user.id)
        )

        # Force SQLAlchemy to load the subscriptions
        if hasattr(user, "subscriptions"):
            _ = user.subscriptions
            # Force SQLAlchemy to load payments for each subscription
            for subscription in user.subscriptions:
                if hasattr(subscription, "payments"):
                    _ = subscription.payments

        return user

    @expose("/")
    @expose("/index")
    def index(self) -> Response:  # noqa: C901
        """Smart entry point that either shows plans or redirects to manage page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        current_app.logger.info(f"User: {user}")

        if user.has_active_subscription:
            # Redirect to manage page if they're already subscribed
            return redirect(url_for(".manage"))
        else:
            # Show plans page if they don't have an active subscription
            stripe_plans_list = self.payment_processor.get_stripe_plans()
            current_app.logger.info(f"Plans from Stripe: {stripe_plans_list}")

            if (
                stripe_plans_list
            ):  # Ensure the list is not None and not empty before iterating
                for stripe_plan_item in stripe_plans_list:
                    current_app.logger.info(
                        f"Processing Stripe plan item: {stripe_plan_item}"
                    )
                    if not stripe_plan_item or not stripe_plan_item.get("id"):
                        current_app.logger.warning(
                            f"Skipping invalid stripe plan item: {stripe_plan_item}"
                        )
                        continue

                    db_plan = (
                        self.appbuilder.session.query(SubscriptionPlan)
                        .filter_by(product_id=stripe_plan_item["id"])
                        .first()
                    )
                    if not db_plan:
                        try:
                            new_plan_instance = SubscriptionPlan(
                                product_id=stripe_plan_item["id"],
                                name=stripe_plan_item["product"],
                                description=stripe_plan_item.get("description"),
                                price=float(stripe_plan_item["price"]),
                                billing_cycle=stripe_plan_item["billing_cycle"],
                                features=json.dumps(
                                    stripe_plan_item.get("features", [])
                                ),
                                is_active=stripe_plan_item.get("active", True),
                            )
                            self.appbuilder.session.add(new_plan_instance)
                            self.appbuilder.session.commit()  # Commit after adding new plan  # noqa: E501
                            current_app.logger.info(
                                f"Created and committed new DB plan: {new_plan_instance.name}"  # noqa: E501
                            )
                        except KeyError as e:
                            current_app.logger.error(
                                f"Missing key when creating SubscriptionPlan from Stripe item: {stripe_plan_item}. Error: {e}"  # noqa: E501
                            )
                            self.appbuilder.session.rollback()
                        except Exception as e:
                            current_app.logger.error(
                                f"Error creating SubscriptionPlan from Stripe item: {stripe_plan_item}. Error: {e}"  # noqa: E501
                            )
                            self.appbuilder.session.rollback()
                    else:  # db_plan exists, check for updates
                        try:
                            updated_fields = False
                            # Name
                            if db_plan.name != stripe_plan_item["product"]:
                                db_plan.name = stripe_plan_item["product"]
                                updated_fields = True
                            # Description
                            stripe_desc = stripe_plan_item.get("description")
                            if db_plan.description != stripe_desc:
                                db_plan.description = stripe_desc
                                updated_fields = True
                            # Price
                            stripe_price = float(stripe_plan_item["price"])
                            if db_plan.price != stripe_price:
                                db_plan.price = stripe_price
                                updated_fields = True
                            # Billing Cycle
                            if (
                                db_plan.billing_cycle
                                != stripe_plan_item["billing_cycle"]
                            ):
                                db_plan.billing_cycle = stripe_plan_item[
                                    "billing_cycle"
                                ]
                                updated_fields = True
                            # Features
                            stripe_features_list = stripe_plan_item.get("features", [])
                            db_features_list = []
                            if db_plan.features:
                                try:
                                    db_features_list = json.loads(db_plan.features)
                                    if not isinstance(
                                        db_features_list, list
                                    ):  # Ensure it's a list for comparison
                                        db_features_list = []
                                except json.JSONDecodeError:
                                    current_app.logger.warning(
                                        f"Could not decode features JSON for plan {db_plan.name} during update: {db_plan.features}"  # noqa: E501
                                    )

                            # Compare content of features (e.g., as sorted lists or sets if order doesn't matter)  # noqa: E501
                            # Assuming features are lists of simple, sortable items (like strings or numbers)  # noqa: E501
                            if sorted(db_features_list) != sorted(stripe_features_list):
                                db_plan.features = json.dumps(stripe_features_list)
                                updated_fields = True

                            # Is Active
                            stripe_is_active = stripe_plan_item.get("active", True)
                            if db_plan.is_active != stripe_is_active:
                                db_plan.is_active = stripe_is_active
                                updated_fields = True

                            if updated_fields:
                                current_app.logger.info(
                                    f"Updating DB plan: {db_plan.name} with data from Stripe."  # noqa: E501
                                )
                                self.appbuilder.session.add(db_plan)  # Mark for update
                                self.appbuilder.session.commit()
                                current_app.logger.info(
                                    f"Successfully updated and committed DB plan: {db_plan.name}"  # noqa: E501
                                )
                            else:
                                current_app.logger.info(
                                    f"No updates needed for DB plan: {db_plan.name}. Data from Stripe is identical."  # noqa: E501
                                )
                        except KeyError as e:
                            current_app.logger.error(
                                f"Missing key when updating SubscriptionPlan {db_plan.name} from Stripe item: {stripe_plan_item}. Error: {e}"  # noqa: E501
                            )
                            self.appbuilder.session.rollback()
                        except Exception as e:
                            current_app.logger.error(
                                f"Error updating SubscriptionPlan {db_plan.name} from Stripe item: {stripe_plan_item}. Error: {e}"  # noqa: E501
                            )
                            self.appbuilder.session.rollback()

            # Query plans from the database to display on the page.
            # Display only active plans.
            plans_for_template = (
                self.appbuilder.session.query(SubscriptionPlan)
                .filter_by(is_active=True)
                .all()
            )
            current_app.logger.info(f"Plans to render from DB: {plans_for_template}")

            return self.render_template(
                "subscription/plans.html", plans=plans_for_template, user=user
            )

    @expose("/plans")
    def plans(self) -> Response:
        """Show available subscription plans"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Manage it below."), "info"
            )
            return redirect(url_for(".manage"))

        plans = self.payment_processor.get_stripe_plans()
        if not plans:
            flash(
                _("Error loading subscription plans. Please try again later."), "error"
            )  # noqa: E501
            return redirect(url_for(".index"))

        return self.render_template("subscription/plans.html", plans=plans, user=user)

    @expose("/subscribe/<plan_id>", methods=["GET", "POST"])
    @has_access
    def subscribe(self, plan_id: str) -> Response:
        """Process new subscription - redirects to payment page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _(
                    "You already have an active subscription. "
                    "Please cancel it before subscribing to a new plan."
                ),
                "warning",
            )
            return redirect(url_for(".manage"))

        # Find plan by Stripe product ID
        plan = self.payment_processor.get_stripe_plan(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for(".plans"))

        # Redirect to payment page with plan_id
        return redirect(url_for(".payment", plan_id=plan_id))

    @expose("/payment/<plan_id>", methods=["GET", "POST"])
    @has_access
    def payment(self, plan_id: str) -> Response:
        """Show payment form using Stripe Checkout"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _(
                    "You already have an active subscription. "
                    "Please cancel it before subscribing to a new plan."
                ),
                "warning",
            )
            return redirect(url_for(".manage"))

        # Find plan by Stripe product ID
        plan = self.payment_processor.get_stripe_plan(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for(".plans"))

        # Pass the plan and stripe publishable key to the template
        # The client_secret will be fetched via AJAX
        return self.render_template(
            "subscription/payment.html",
            plan=plan,
            user=user,
            plan_id=plan_id,
            stripe_publishable_key=current_app.config.get("STRIPE_PUBLIC_KEY"),
        )

    @expose("/create-payment-intent", methods=["POST"])
    @has_access
    def create_payment_intent(self) -> Response:
        try:
            data = json.loads(request.data)
            order_amount = data["orderAmount"]

            # Convert to float first (in case it's a string), then to cents as integer
            amount_in_cents = int(float(order_amount) * 100)

            if self.calculate_tax:
                tax_calculation = self.payment_processor.calculate_tax(
                    order_amount, "usd"
                )  # noqa: E501
                intent = stripe.PaymentIntent.create(
                    amount=tax_calculation["amount_total"],
                    currency="usd",
                    automatic_payment_methods={
                        "enabled": True,
                    },
                    metadata={"tax_calculation": tax_calculation["id"]},
                )
            else:
                intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency="usd",
                    automatic_payment_methods={
                        "enabled": True,
                    },
                )

            # send payment intent to client
            current_app.logger.info(
                f"Created payment intent for {intent.amount} {intent.currency} "
                f"with id: {intent.id} and client_secret: {intent.client_secret}"
            )
            return jsonify({"clientSecret": intent.client_secret})
        except StripeError as e:
            return make_response(jsonify({"error": {"message": str(e)}}), 400)
        except Exception as e:
            return make_response(jsonify({"error": {"message": str(e)}}), 400)

    @expose("/create-checkout-session", methods=["POST"])
    @has_access
    def create_checkout_session(self) -> Response:
        """API endpoint to create a Stripe Checkout Session"""
        # Get a fresh User instance
        user = self._get_user()

        # Get plan_id from the request
        data = json.loads(request.data)
        plan_id = data.get("plan_id")

        if not plan_id:
            return make_response(jsonify({"error": "Missing plan_id parameter"}), 400)

        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            return make_response(jsonify({"error": "Invalid subscription plan"}), 400)

        # Create Stripe Checkout Session
        success, client_secret = self.payment_processor.create_checkout_session(
            plan=plan, user=user
        )

        if not success:
            return make_response(jsonify({"error": client_secret}), 500)

        # Log the client secret for debugging (redact in production)
        current_app.logger.info(f"Client secret: {client_secret}")

        return jsonify({"checkoutSessionClientSecret": client_secret})

    @expose("/payment-complete", methods=["POST"])
    @has_access
    def payment_complete(self) -> Response:
        """Handle successful payment completion via AJAX"""
        # Get a fresh User instance
        user = self._get_user()

        # Get session_id and subscription_id from the request
        data = json.loads(request.data)
        intent_id = data.get("payment_intent_id")
        product_id = data.get("plan_id")
        current_app.logger.info(f"Payment complete data: {data}")
        plan = (
            self.appbuilder.session.query(SubscriptionPlan)
            .filter_by(product_id=product_id)
            .first()
        )  # noqa: E501
        # plan = self.payment_processor.get_stripe_plan(product_id)
        if not plan:
            return make_response(jsonify({"error": "Invalid subscription plan"}), 400)

        # Retrieve the checkout session from Stripe to verify
        intent = self.payment_processor.retrieve_intent(intent_id)
        current_app.logger.info(f"Intent: {intent}")
        if not intent:
            return make_response(
                jsonify({"error": "Error retrieving payment information"}), 500
            )  # noqa: E501

        # Verify the payment was successful
        if intent.status != "succeeded":
            return make_response(
                jsonify({"error": "Payment not completed successfully"}), 400
            )  # noqa: E501

        # Create subscription in our database
        end_date = datetime.datetime.now() + self.calc_subscription_period(plan)
        subscription = UserSubscription(
            user_id=user.id,
            product_id=product_id,
            status="active",
            start_date=datetime.datetime.now(),
            end_date=end_date,
            is_auto_renew=True,
            external_subscription_id=intent_id,
        )

        # Save the subscription first to get an ID
        self.appbuilder.session.add(subscription)
        self.appbuilder.session.flush()  # Flush to get subscription.id without committing  # noqa: E501

        # Create payment record with subscription association
        payment = Payment(
            user_id=user.id,
            subscription_id=subscription.id,  # Link payment to subscription
            amount=plan["price"],
            payment_method="stripe",
            transaction_id=intent_id,
            status="success",
        )

        # Add payment to session and commit both subscription and payment
        self.appbuilder.session.add(payment)

        # Debug logging
        current_app.logger.info(
            f"Created subscription {subscription.id} with payment from Stripe"
        )
        current_app.logger.info(
            f"Payment details: {payment.amount}, {payment.payment_method}, {payment.status}"  # noqa: E501
        )  # noqa: E501

        # Commit subscription and payment
        self.appbuilder.session.commit()

        # Update user paid status using direct SQL (this includes its own commit)
        self.update_user_paid_status(user.id, True)

        return jsonify({"success": True, "subscription_id": subscription.id})

    @expose("/subscription-success")
    @has_access
    def subscription_success(self) -> Response:
        """Show subscription success page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        # Get current subscription - the one most recently created
        subscription = user.current_subscription

        if not subscription:
            flash(_("No active subscription found"), "danger")
            return redirect(url_for(".plans"))

        return self.render_template(
            "subscription/success.html", subscription=subscription, user=user
        )

    @expose("/manage")
    @has_access
    def manage(self) -> Response:
        """Manage existing subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        # Get current subscription using the mixin property
        subscription = user.current_subscription

        # If no subscription, redirect to plans page
        if not subscription:
            flash(
                _(
                    "You don't have an active subscription. "
                    "Choose a plan below to subscribe."
                ),
                "info",
            )
            return redirect(url_for(".plans"))

        # Explicitly load payments
        from sqlalchemy.orm import joinedload

        if subscription:
            # Check for payments directly
            payments = self.check_subscription_payments(subscription.id)

            # Reload the subscription with joined payments
            subscription = (
                self.appbuilder.session.query(UserSubscription)
                .options(joinedload(UserSubscription.payments))
                .filter_by(id=subscription.id)
                .first()
            )

            # Debug logging
            current_app.logger.info(f"Subscription ID: {subscription.id}")
            current_app.logger.info(f"Number of payments from helper: {len(payments)}")
            current_app.logger.info(
                f"Number of payments from subscription: {len(subscription.payments) if subscription.payments else 0}"  # noqa: E501
            )  # noqa: E501

            # If we have payments but they're not showing up in subscription.payments, manually add them  # noqa: E501
            if payments and (
                not subscription.payments or len(subscription.payments) == 0
            ):
                current_app.logger.info(
                    "Manually setting payments on subscription object"
                )
                subscription.payments = payments

        # Check if user is admin
        is_admin = self.is_admin_user(user)

        return self.render_template(
            "subscription/manage.html",
            subscription=subscription,
            user=user,
            is_admin=is_admin,
        )

    @expose("/cancel", methods=["POST"])
    @has_access
    def cancel(self) -> Response:
        """Cancel subscription"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        # Get current subscription using the mixin property
        subscription = user.current_subscription

        if subscription:
            # If we have a Stripe subscription ID, cancel in Stripe
            if (
                hasattr(subscription, "stripe_subscription_id")
                and subscription.stripe_subscription_id
            ):  # noqa: E501
                success = self.payment_processor.cancel_subscription(
                    subscription.stripe_subscription_id
                )
                if not success:
                    flash(
                        _("Error cancelling subscription with payment provider"),
                        "danger",
                    )
                    return redirect(url_for(".manage"))

            subscription.status = "cancelled"
            subscription.is_auto_renew = False
            self.appbuilder.session.commit()

            # Update user paid status to False since their subscription is cancelled
            self.update_user_paid_status(user.id, False)

            flash(_("Your subscription has been cancelled"), "success")
        return redirect(url_for(".manage"))

    # Helper methods
    def calc_subscription_period(
        self, plan: dict[str, Any] | None
    ) -> datetime.timedelta:  # noqa: E501
        """Calculate subscription end date based on billing cycle"""
        if not plan:
            return datetime.timedelta(days=30)  # Default to monthly if no plan
        if plan.get("billing_cycle") == "month":
            return datetime.timedelta(days=30)
        elif plan.get("billing_cycle") == "quarter":
            return datetime.timedelta(days=90)
        elif plan.get("billing_cycle") == "year":
            return datetime.timedelta(days=365)
        return datetime.timedelta(days=30)  # Default to monthly

    def check_subscription_payments(self, subscription_id: int) -> list[Payment]:
        """Helper function to check if a subscription has payments"""
        try:
            # Find both directly linked payments and possibly orphaned ones for this subscription  # noqa: E501
            payments = (
                self.appbuilder.session.query(Payment)
                .filter(
                    or_(
                        Payment.subscription_id == subscription_id,
                        Payment.user_id
                        == self.appbuilder.session.query(UserSubscription.user_id)
                        .filter(UserSubscription.id == subscription_id)
                        .scalar_subquery(),
                    )
                )
                .all()
            )

            current_app.logger.info(
                f"Found {len(payments)} payments for subscription {subscription_id}"
            )
            return payments
        except Exception as e:
            current_app.logger.error(f"Error checking payments: {str(e)}")
            return []

    def update_user_paid_status(self, user_id: int, is_paid: bool = True) -> None:
        """Update a user's is_paid_user status using direct SQL"""
        try:
            # self.appbuilder.session.begin()
            user = self.appbuilder.session.query(User).get(user_id)
            paid_role = self.appbuilder.session.query(Role).filter_by(id=4).first()
            stmt = text(
                "UPDATE ab_user SET is_paid_user = :is_paid, changed_on = :changed_on WHERE id = :user_id"  # noqa: E501
            )  # noqa: E501
            self.appbuilder.session.execute(
                stmt,
                {
                    "is_paid": is_paid,
                    "user_id": user_id,
                    "changed_on": datetime.datetime.now(),
                },
            )  # noqa: E501
            user.roles.append(paid_role)
            self.appbuilder.session.commit()

            current_app.logger.info(
                f"Updated is_paid_user status for user {user_id} to {is_paid}"
            )
        except Exception as e:
            current_app.logger.error(f"Error updating user paid status: {str(e)}")
            self.appbuilder.session.rollback()

    def is_admin_user(self, user: User | None = None) -> bool:
        """Helper function to check if a user has the Admin role"""
        if user is None:
            user = g.user

        if not hasattr(user, "roles"):
            return False

        for role in user.roles:
            if role.name == "Admin":
                return True

        return False
