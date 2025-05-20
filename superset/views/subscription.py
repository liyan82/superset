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
from sqlalchemy import or_
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

    def _get_db_features_list(self, db_plan: SubscriptionPlan) -> list[str]:
        """Safely load and parse the features JSON from a SubscriptionPlan."""
        if not db_plan.features:
            return []
        try:
            loaded_features = json.loads(db_plan.features)
            if isinstance(loaded_features, list):
                return loaded_features
            return []  # Return empty list if not a list
        except json.JSONDecodeError:
            current_app.logger.warning(
                f"Could not decode features JSON for plan {db_plan.name} "
                f"during update: {db_plan.features}"
            )
            return []

    def _apply_plan_field_updates(
        self, db_plan: SubscriptionPlan, stripe_plan_item: dict[str, Any]
    ) -> bool:
        """Apply updates from a Stripe plan item to a DB plan record.

        Returns True if any fields were updated, False otherwise.
        """
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
        # Stripe Price ID
        stripe_price_id = stripe_plan_item["stripe_price_id"]
        if db_plan.stripe_price_id != stripe_price_id:
            db_plan.stripe_price_id = stripe_price_id
            updated_fields = True
        # Billing Cycle
        if db_plan.billing_cycle != stripe_plan_item["billing_cycle"]:
            db_plan.billing_cycle = stripe_plan_item["billing_cycle"]
            updated_fields = True
        # Features
        stripe_features_list = stripe_plan_item.get("features", [])
        db_features_list = self._get_db_features_list(db_plan)
        if sorted(db_features_list) != sorted(stripe_features_list):
            db_plan.features = json.dumps(stripe_features_list)
            updated_fields = True
        # Is Active
        stripe_is_active = stripe_plan_item.get("active", True)
        if db_plan.is_active != stripe_is_active:
            db_plan.is_active = stripe_is_active
            updated_fields = True
        return updated_fields

    def _create_new_db_plan(self, stripe_plan_item: dict[str, Any]) -> None:
        """Create a new SubscriptionPlan in the database from a Stripe plan item."""
        try:
            new_plan_instance = SubscriptionPlan(
                product_id=stripe_plan_item["id"],
                stripe_price_id=stripe_plan_item["stripe_price_id"],
                name=stripe_plan_item["product"],
                description=stripe_plan_item.get("description"),
                price=float(stripe_plan_item["price"]),
                billing_cycle=stripe_plan_item["billing_cycle"],
                features=json.dumps(stripe_plan_item.get("features", [])),
                is_active=stripe_plan_item.get("active", True),
            )
            self.appbuilder.session.add(new_plan_instance)
            self.appbuilder.session.commit()
            current_app.logger.info(
                f"Created and committed new DB plan: {new_plan_instance.name}"
            )
        except KeyError as e:
            current_app.logger.error(
                f"Missing key when creating SubscriptionPlan from Stripe item: "
                f"{stripe_plan_item}. Error: {e}"
            )
            self.appbuilder.session.rollback()
        except Exception as e:  # pylint: disable=broad-except
            current_app.logger.error(
                f"Error creating SubscriptionPlan from Stripe item: "
                f"{stripe_plan_item}. Error: {e}"
            )
            self.appbuilder.session.rollback()

    def _update_existing_db_plan(
        self, db_plan: SubscriptionPlan, stripe_plan_item: dict[str, Any]
    ) -> None:
        """Update an existing SubscriptionPlan in the database from a Stripe plan item."""  # noqa: E501
        try:
            updated_fields = self._apply_plan_field_updates(db_plan, stripe_plan_item)
            if updated_fields:
                current_app.logger.info(
                    f"Updating DB plan: {db_plan.name} with data from Stripe."
                )
                self.appbuilder.session.add(db_plan)  # Mark for update
                self.appbuilder.session.commit()
                current_app.logger.info(
                    f"Successfully updated and committed DB plan: {db_plan.name}"
                )
            else:
                current_app.logger.info(
                    f"No updates needed for DB plan: {db_plan.name}. "
                    f"Data from Stripe is identical."
                )
        except KeyError as e:
            current_app.logger.error(
                f"Missing key when updating SubscriptionPlan {db_plan.name} "
                f"from Stripe item: {stripe_plan_item}. Error: {e}"
            )
            self.appbuilder.session.rollback()
        except Exception as e:  # pylint: disable=broad-except
            current_app.logger.error(
                f"Error updating SubscriptionPlan {db_plan.name} "
                f"from Stripe item: {stripe_plan_item}. Error: {e}"
            )
            self.appbuilder.session.rollback()

    def _synchronize_plans_from_stripe(self) -> None:
        """Fetch plans from Stripe and synchronize them with the local database."""
        stripe_plans_list = self.payment_processor.get_stripe_plans()
        current_app.logger.info(f"Plans from Stripe: {stripe_plans_list}")

        if not stripe_plans_list:
            return

        for stripe_plan_item in stripe_plans_list:
            current_app.logger.info(f"Processing Stripe plan item: {stripe_plan_item}")
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
                self._create_new_db_plan(stripe_plan_item)
            else:
                self._update_existing_db_plan(db_plan, stripe_plan_item)

    def _sync_and_get_active_plans(self) -> list[SubscriptionPlan]:
        """Synchronize plans from Stripe and return active plans from the database."""
        self._synchronize_plans_from_stripe()
        # Query plans from the database to display on the page.
        # Display only active plans.
        return (
            self.appbuilder.session.query(SubscriptionPlan)
            .filter_by(is_active=True)
            .all()
        )

    @expose("/")
    @expose("/index")
    def index(self) -> Response:
        """Smart entry point that either shows plans or redirects to manage page"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            # Redirect to manage page if they're already subscribed
            return redirect(url_for(".manage"))
        elif (
            not user.has_active_subscription
            and user.current_subscription
            and user.current_subscription.status == "cancelled"
        ):
            flash(
                _(
                    "Your subscription has been cancelled and will expire on "
                    f"{user.current_subscription.end_date.strftime('%Y-%m-%d')}.\n"
                    "Please subscribe to a new plan below."
                ),
                "info",
            )
            active_db_plans = self._sync_and_get_active_plans()
            current_app.logger.info(f"Plans to render from DB: {active_db_plans}")

            return self.render_template(
                "subscription/plans.html", plans=active_db_plans, user=user
            )
        else:
            flash(
                _(
                    "You don't have an active subscription. "
                    "Choose a plan below to subscribe."
                ),
            )
            active_db_plans = self._sync_and_get_active_plans()
            current_app.logger.info(f"Plans to render from DB: {active_db_plans}")

            return self.render_template(
                "subscription/plans.html", plans=active_db_plans, user=user
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
        current_app.logger.info(f"Plans from Stripe: {plans}")
        if not plans:
            flash(
                _("Error loading subscription plans. Please try again later."), "error"
            )
            return redirect(url_for(".index"))

        return self.render_template("subscription/plans.html", plans=plans, user=user)

    @expose("/subscribe/<plan_id>", methods=["GET", "POST"])
    @has_access
    def subscribe(self, plan_id: str) -> Response:
        """Process new subscription - redirects to payment page"""
        current_app.logger.info(f"Subscribing to plan: {plan_id}")
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        current_subscription = user.current_subscription
        current_app.logger.info(f"Current subscription: {json.dumps(current_subscription.__dict__, indent=2, default=str)}")  # noqa: E501
        subscription_plan = self.appbuilder.session.query(SubscriptionPlan).filter_by(id=current_subscription.plan_id).first()  # noqa: E501
        current_app.logger.info(f"Subscription plan: {json.dumps(subscription_plan.__dict__, indent=2, default=str)}")  # noqa: E501
        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Please cancel it before subscribing to a new plan."),  # noqa: E501
                "warning",
            )

            return redirect(url_for(".manage"))
        elif (
            current_subscription.status == "cancelled"
            and current_subscription.end_date > datetime.datetime.now()
            and subscription_plan.product_id == plan_id
        ):
            current_app.logger.info(f"Reviving subscription: {current_subscription.external_subscription_id}")  # noqa: E501
            revive_success = self.payment_processor.revive_subscription(
                current_subscription.external_subscription_id
            )
            if revive_success:
                current_subscription.status = "active"
                current_subscription.is_auto_renew = True
                self.appbuilder.session.commit()
                flash(
                    _("Your subscription has been revived. Subscription billing will resume on the next billing date."),  # noqa: E501
                    "info",
                )

            return redirect(url_for(".manage"))
        else:
            # Find plan by Stripe product ID
            plan = self.payment_processor.get_stripe_plan(plan_id)
            if not plan:
                flash(_("Invalid subscription plan"), "danger")
                return redirect(url_for(".plans"))

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
                )
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
        success, session_id, client_secret = (
            self.payment_processor.create_checkout_session(plan=plan, user=user)
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
        )
        # plan = self.payment_processor.get_stripe_plan(product_id)
        if not plan:
            return make_response(jsonify({"error": "Invalid subscription plan"}), 400)

        # Retrieve the checkout session from Stripe to verify
        intent = self.payment_processor.retrieve_intent(intent_id)
        current_app.logger.info(f"Intent: {intent}")
        if not intent:
            return make_response(
                jsonify({"error": "Error retrieving payment information"}), 500
            )

        # Verify the payment was successful
        if intent.status != "succeeded":
            return make_response(
                jsonify({"error": "Payment not completed successfully"}), 400
            )

        try:
            # Create subscription in our database
            sub_start_date = datetime.datetime.now()
            current_subscription = user.current_subscription
            if (
                current_subscription
                and current_subscription.status == "cancelled"
                and current_subscription.end_date
                and current_subscription.end_date > sub_start_date
            ):
                sub_start_date = current_subscription.end_date

            end_date = sub_start_date + self.calc_subscription_period(plan)
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                start_date=sub_start_date,
                end_date=end_date,
                is_auto_renew=True,
            )

            # Save the subscription first to get an ID
            self.appbuilder.session.add(subscription)
            self.appbuilder.session.flush()  # Flush to get subscription.id without committing  # noqa: E501

            # Create payment record with subscription association
            payment = Payment(
                user_id=user.id,
                subscription_id=subscription.id,  # Link payment to subscription
                amount=plan.price,
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
            )

            current_app.logger.info(
                "Subscription created successfully in DB. Now create Stripe subscription."  # noqa: E501
            )
            stripe_subscription = self.payment_processor.create_stripe_subscription(
                user, plan
            )
            current_app.logger.info(f"Stripe subscription: {stripe_subscription}")  # noqa: E501
            if stripe_subscription:
                subscription.external_subscription_id = stripe_subscription.id
                user.stripe_customer_id = stripe_subscription.customer
                current_app.logger.info(
                    f"Stripe customer ID: {user.stripe_customer_id}"
                )  # noqa: E501
                self.appbuilder.session.commit()

            # Commit subscription and payment
            self.appbuilder.session.commit()

            # Update user paid status using direct SQL (this includes its own commit)
            self.update_user_paid_status(user.id, True)

            return jsonify({"success": True, "subscription_id": subscription.id})
        except StripeError as e:  # More specific catch for StripeErrors
            current_app.logger.error(
                f"StripeError during subscription creation or commit: {str(e)}"
            )
            self.appbuilder.session.rollback()
            return make_response(jsonify({"error": str(e)}), 500)
        except Exception as e:
            current_app.logger.error(
                f"Generic error during subscription creation or commit in payment_complete: {str(e)}",  # noqa: E501
                exc_info=True,
            )
            self.appbuilder.session.rollback()
            return make_response(jsonify({"error": str(e)}), 500)

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
        elif subscription.status == "cancelled":
            flash(
                _(
                    "Your subscription has been cancelled. "
                    "Choose a plan below to subscribe."
                ),
                "info",
            )
            return redirect(url_for(".plans"))
        elif subscription.status == "expired":
            flash(
                _("Your subscription has expired. Choose a plan below to subscribe."),
                "info",
            )
            return redirect(url_for(".plans"))

        # Explicitly load payments
        from sqlalchemy.orm import joinedload

        if subscription.status == "active":
            # Check for payments directly
            payments = self.check_user_payments(user.id)
            subscription.payments = payments

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
            )

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
        current_app.logger.info("Cancelling subscription")
        """Cancel subscription"""
        # Get a fresh User instance with the mixin applied
        subscription_id = request.form.get("subscription_id")
        current_app.logger.info(f"Subscription ID: {subscription_id}")
        user = self._get_user()
        current_app.logger.info(f"User: {user}")

        # Get current subscription using the mixin property
        subscription = user.current_subscription
        current_app.logger.info(f"Subscription: {subscription}")

        if subscription:
            # If we have a Stripe subscription ID, cancel in Stripe
            if (
                hasattr(subscription, "external_subscription_id")
                and subscription.external_subscription_id
            ):
                current_app.logger.info(
                    f"Cancelling subscription {subscription.external_subscription_id} for user {user.id}"  # noqa: E501
                )
                success = self.payment_processor.cancel_subscription(
                    subscription.external_subscription_id
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
            # TODO: Remove paid role from user, but has to be after the subscription is expired  # noqa: E501
            self.update_user_paid_status(user.id, False)

            flash(_("Your subscription has been cancelled"), "success")
        return redirect(url_for(".manage"))

    # Helper methods
    def calc_subscription_period(
        self, plan: SubscriptionPlan | None
    ) -> datetime.timedelta:
        """Calculate subscription end date based on billing cycle"""
        if not plan:
            return datetime.timedelta(days=30)  # Default to monthly if no plan
        if plan.billing_cycle == "month":
            return datetime.timedelta(days=30)
        elif plan.billing_cycle == "quarter":
            return datetime.timedelta(days=90)
        elif plan.billing_cycle == "year":
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

    def check_user_payments(self, user_id: int) -> list[Payment]:
        """Helper function to check if a user has payments"""
        try:
            payments = (
                self.appbuilder.session.query(Payment).filter_by(user_id=user_id).all()
            )
            return payments
        except Exception as e:
            current_app.logger.error(f"Error checking payments: {str(e)}")
            return []

    def update_user_paid_status(self, user_id: int, is_paid: bool = True) -> None:
        """Update a user's is_paid_user status using direct SQL"""
        try:
            if is_paid:
                user = self.appbuilder.session.query(User).get(user_id)
                paid_role = (
                    self.appbuilder.session.query(Role).filter_by(name="Gamma").first()
                )  # noqa: E501
                # Use SQLAlchemy ORM instead of raw SQL for better type handling
                user.is_paid_user = is_paid
                user.changed_on = datetime.datetime.now()

                # Only add role if not already present
                if paid_role and paid_role not in user.roles:
                    user.roles.append(paid_role)

                self.appbuilder.session.commit()
                current_app.logger.info(
                    f"Updated is_paid_user status for user {user_id} to {is_paid}"
                )  # noqa: E501
            else:
                pass  # TODO: Remove paid role from user, but has to be after the subscription is expired  # noqa: E501
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
