import datetime
import json
import traceback
from typing import Any

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
            self.log_subscription(
                f"Could not decode features JSON for plan {db_plan.name} during update: {db_plan.features}",
                level="warning",
            )
            return []

    def _apply_plan_field_updates(self, db_plan: SubscriptionPlan, stripe_plan_item: dict[str, Any]) -> bool:
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
            self.log_subscription(f"Created and committed new DB plan: {new_plan_instance.name}", level="info")
        except KeyError as e:
            self.log_subscription(
                f"Missing key when creating SubscriptionPlan from Stripe item: {stripe_plan_item}. Error: {e}",
                level="error",
            )
            self.appbuilder.session.rollback()
        except Exception as e:  # pylint: disable=broad-except
            self.log_subscription(
                f"Error creating SubscriptionPlan from Stripe item: {stripe_plan_item}. Error: {e}", level="error"
            )
            self.appbuilder.session.rollback()

    def _update_existing_db_plan(self, db_plan: SubscriptionPlan, stripe_plan_item: dict[str, Any]) -> None:
        """Update an existing SubscriptionPlan in the database from a Stripe plan item."""  # noqa: E501
        try:
            updated_fields = self._apply_plan_field_updates(db_plan, stripe_plan_item)
            if updated_fields:
                self.log_subscription(f"Updating DB plan: {db_plan.name} with data from Stripe.", level="info")
                self.appbuilder.session.add(db_plan)  # Mark for update
                self.appbuilder.session.commit()
                self.log_subscription(f"Successfully updated and committed DB plan: {db_plan.name}", level="info")
            else:
                self.log_subscription(
                    f"No updates needed for DB plan: {db_plan.name}. Data from Stripe is identical.", level="info"
                )
        except KeyError as e:
            self.log_subscription(
                f"Missing key when updating SubscriptionPlan {db_plan.name} "
                f"from Stripe item: {stripe_plan_item}. Error: {e}",
                level="error",
            )
            self.appbuilder.session.rollback()
        except Exception as e:  # pylint: disable=broad-except
            self.log_subscription(
                f"Error updating SubscriptionPlan {db_plan.name} from Stripe item: {stripe_plan_item}. Error: {e}",
                level="error",
            )
            self.appbuilder.session.rollback()

    def _synchronize_plans_from_stripe(self) -> None:
        """Fetch plans from Stripe and synchronize them with the local database."""
        stripe_plans_list = self.payment_processor.get_stripe_plans()
        self.log_subscription(f"Plans from Stripe: {stripe_plans_list}", level="info")

        if not stripe_plans_list:
            return

        for stripe_plan_item in stripe_plans_list:
            self.log_subscription(f"Processing Stripe plan item: {stripe_plan_item}", level="info")
            if not stripe_plan_item or not stripe_plan_item.get("id"):
                self.log_subscription(f"Skipping invalid stripe plan item: {stripe_plan_item}", level="warning")
                continue

            db_plan = (
                self.appbuilder.session.query(SubscriptionPlan).filter_by(product_id=stripe_plan_item["id"]).first()
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
        return self.appbuilder.session.query(SubscriptionPlan).filter_by(is_active=True).all()

    @expose("/")
    @expose("/index")
    def index(self) -> Response:
        """Smart entry point that either shows plans or redirects to manage page"""
        self.log_subscription("=== Starting index method ===", level="info")

        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        self.log_subscription(f"Retrieved user with ID: {user.id}", level="info")

        if user.has_active_subscription:
            self.log_subscription(f"User {user.id} has active subscription, redirecting to manage page", level="info")
            # Redirect to manage page if they're already subscribed
            return redirect(url_for(".manage"))
        elif (
            not user.has_active_subscription
            and user.current_subscription
            and user.current_subscription.status == "cancelled"
        ):
            self.log_subscription(
                f"User {user.id} has cancelled subscription ending on "
                f"{user.current_subscription.end_date.strftime('%Y-%m-%d')}",
                level="info",
            )
            flash(
                _(
                    "Your subscription has been cancelled and will expire on "
                    f"{user.current_subscription.end_date.strftime('%Y-%m-%d')}.\n"
                    "Please subscribe to a new plan below."
                ),
                "info",
            )
            active_db_plans = self._sync_and_get_active_plans()
            self.log_subscription(f"Retrieved {len(active_db_plans)} active plans from DB", level="info")
            self.log_subscription(f"Plans to render from DB: {active_db_plans}", level="info")

            return self.render_template("subscription/plans.html", plans=active_db_plans, user=user)
        elif user.current_subscription and user.current_subscription.status == "incomplete":
            self.log_subscription(
                f"User {user.id} has incomplete subscription, redirecting to manage page to pay the first invoice",
                level="info",
            )
            return redirect(url_for(".manage"))
        else:
            self.log_subscription(f"User {user.id} has no active subscription, showing plans page", level="info")
            flash(
                _("You don't have an active subscription. Choose a plan below to subscribe."),
            )
            active_db_plans = self._sync_and_get_active_plans()
            self.log_subscription(f"Retrieved {len(active_db_plans)} active plans from DB", level="info")
            self.log_subscription(f"Plans to render from DB: {active_db_plans}", level="info")

            self.log_subscription("=== Completed index method successfully ===", level="info")
            return self.render_template("subscription/plans.html", plans=active_db_plans, user=user)

    @expose("/plans")
    def plans(self) -> Response:
        """Show available subscription plans"""
        self.log_subscription("=== Starting plans method ===", level="info")

        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        self.log_subscription(f"Retrieved user with ID: {user.id}", level="info")

        if user.has_active_subscription:
            self.log_subscription(f"User {user.id} has active subscription, redirecting to manage page", level="info")
            flash(_("You already have an active subscription. Manage it below."), "info")
            return redirect(url_for(".manage"))

        plans = self.payment_processor.get_stripe_plans()
        self.log_subscription(f"Retrieved {len(plans) if plans else 0} plans from Stripe", level="info")
        self.log_subscription(f"Plans from Stripe: {plans}", level="info")

        if not plans:
            self.log_subscription("No plans retrieved from Stripe, redirecting to index", level="warning")
            flash(_("Error loading subscription plans. Please try again later."), "error")
            return redirect(url_for(".index"))

        self.log_subscription("=== Completed plans method successfully ===", level="info")
        return self.render_template("subscription/plans.html", plans=plans, user=user)

    @expose("/subscribe/<plan_id>", methods=["GET", "POST"])
    @has_access
    def subscribe(self, plan_id: str) -> Response:
        """Process new subscription - redirects to payment page"""
        self.log_subscription(f"Subscribe method called with plan_id: {plan_id}", level="info")
        self.log_subscription(f"Subscribing to plan: {plan_id}", level="info")
        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        self.log_subscription(f"User obtained: {user.username if user else 'None'}", level="info")

        current_subscription = user.current_subscription
        if current_subscription:
            self.log_subscription(
                f"Current subscription: {json.dumps(current_subscription.__dict__, indent=2, default=str)}",
                level="info",
            )
            subscription_plan = (
                self.appbuilder.session.query(SubscriptionPlan).filter_by(id=current_subscription.plan_id).first()
            )
            self.log_subscription(
                f"Subscription plan: {json.dumps(subscription_plan.__dict__, indent=2, default=str)}", level="info"
            )

        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Please cancel it before subscribing to a new plan."),
                "warning",
            )
            self.log_subscription(
                f"User {user.username} already has an active subscription. Redirecting to manage page.", level="info"
            )
            return redirect(url_for(".manage"))
        elif (
            current_subscription
            and current_subscription.status == "cancelled"
            and current_subscription.end_date > datetime.datetime.now()
            and subscription_plan.product_id == plan_id
        ):
            self.log_subscription(
                f"Attempting to revive subscription for user {user.username}, "
                f"external_subscription_id: {current_subscription.external_subscription_id}",
                level="info",
            )
            revive_success = self.payment_processor.revive_subscription(current_subscription.external_subscription_id)
            if revive_success:
                current_subscription.status = "active"
                current_subscription.is_auto_renew = True
                self.appbuilder.session.commit()
                flash(
                    _("Your subscription has been revived. Subscription billing will resume on the next billing date."),
                    "info",
                )
                self.log_subscription(
                    f"Subscription revived successfully for user {user.username}. Redirecting to manage page.",
                    level="info",
                )
            else:
                self.log_subscription(
                    f"Failed to revive subscription for user {user.username}. Redirecting to manage page.",
                    level="warning",
                )
            return redirect(url_for(".manage"))
        else:
            # Find plan by Stripe product ID
            self.log_subscription(
                f"No active or revivable subscription found for user {user.username}. "
                f"Proceeding to fetch plan details for plan_id: {plan_id}",
                level="info",
            )
            plan = self.payment_processor.get_stripe_plan(plan_id)
            if not plan:
                flash(_("Invalid subscription plan"), "danger")
                self.log_subscription(
                    f"Invalid subscription plan_id: {plan_id}. Redirecting to plans page.", level="warning"
                )
                return redirect(url_for(".plans"))

            self.log_subscription(
                f"Plan found: {plan.get('product') if plan else 'None'}. "
                f"Redirecting user {user.username} to payment page for plan_id: {plan_id}",
                level="info",
            )
            return redirect(url_for(".payment", plan_id=plan_id))

    @expose("/payment/<plan_id>", methods=["GET", "POST"])
    @has_access
    def payment(self, plan_id: str) -> Response:
        """Show payment form using Stripe Checkout"""
        # Get a fresh User instance with the mixin applied
        user = self._get_user()

        if user.has_active_subscription:
            flash(
                _("You already have an active subscription. Please cancel it before subscribing to a new plan."),
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
    def create_payment_intent(self) -> Response:  # noqa: C901
        self.log_subscription("=== Starting create_payment_intent method ===", level="info")
        data = json.loads(request.data)
        self.log_subscription(f"Request data received: {data}", level="info")
        if not data:
            self.log_subscription("No data provided in request", level="error")
            return make_response(jsonify({"error": "No data provided"}), 400)

        order_amount = data["orderAmount"]
        self.log_subscription(f"Order amount from request: {order_amount}", level="info")
        try:
            float(order_amount)
        except ValueError:
            self.log_subscription(f"Invalid order amount value: {order_amount}", level="error")
            return make_response(jsonify({"error": "Order amount must be a number"}), 400)

        # Convert to float first (in case it's a string), then to cents as integer
        amount_in_cents = int(float(order_amount) * 100)
        self.log_subscription(f"Amount converted to cents: {amount_in_cents}", level="info")
        if amount_in_cents <= 0:
            self.log_subscription(
                f"Order amount must be greater than 0, received: {amount_in_cents} cents", level="error"
            )
            return make_response(jsonify({"error": "Order amount must be greater than 0"}), 400)

        product_id = data["product_id"]
        self.log_subscription(f"Product ID from request: {product_id}", level="info")
        if not product_id:
            self.log_subscription("No product_id provided in request", level="error")
            return make_response(jsonify({"error": "A Subscription ID is required"}), 400)

        plan = self.appbuilder.session.query(SubscriptionPlan).filter_by(product_id=product_id).first()
        self.log_subscription(f"Subscription plan retrieved: {plan.name if plan else 'None'}", level="info")
        if not plan:
            self.log_subscription(f"Invalid subscription plan with product_id: {product_id}", level="error")
            return make_response(jsonify({"error": "Invalid subscription plan"}), 400)

        try:
            user = self._get_user()
            self.log_subscription(f"User retrieved: {user.id if user else 'None'}", level="info")
            if not user:
                self.log_subscription("User not found", level="error")
                return make_response(jsonify({"error": "User not found"}), 400)

            sub_start_date = datetime.datetime.now()
            self.log_subscription(f"Initial subscription start date: {sub_start_date}", level="info")
            current_subscription = user.current_subscription
            self.log_subscription(
                f"Current subscription: {current_subscription.id if current_subscription else 'None'}"
            )
            if (  # should be useless after adding revive_subscription
                current_subscription
                and current_subscription.status == "cancelled"
                and current_subscription.end_date
                and current_subscription.end_date > sub_start_date
            ):
                sub_start_date = current_subscription.end_date
                self.log_subscription(f"Adjusted subscription start date to: {sub_start_date}", level="info")

            end_date = sub_start_date + self.calc_subscription_period(plan)
            self.log_subscription(f"Calculated subscription end date: {end_date}", level="info")
            subscription = (
                self.appbuilder.session.query(UserSubscription)
                .filter_by(
                    user_id=user.id,
                    status="incomplete",
                )
                .first()
            )
            if not subscription:
                self.log_subscription(f"No incomplete subscription found for user {user.id}", level="info")
                subscription = UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status="incomplete",
                    start_date=sub_start_date,
                    end_date=end_date,
                    is_auto_renew=True,
                )
                self.log_subscription(f"Created subscription object with plan_id: {plan.id}", level="info")
            else:
                self.log_subscription(
                    f"Incomplete subscription found for user {user.id}: {subscription.id}",
                    level="info",
                )

            payment = (
                self.appbuilder.session.query(Payment)
                .filter_by(
                    user_id=user.id,
                    status="incomplete",
                )
                .first()
            )
            if not payment:
                payment = Payment(
                    user_id=user.id,
                    subscription_id=subscription.id,  # Link payment to subscription
                    amount=plan.price,
                    payment_method="stripe",
                    status="incomplete",
                )
                self.log_subscription(f"Created payment object with amount: {plan.price}", level="info")

            self.log_subscription(f"Creating Stripe customer for user: {user.id}", level="info")
            stripe_customer = self.payment_processor.create_customer(user)
            if not stripe_customer:
                self.log_subscription(f"Failed to create Stripe customer for user: {user.id}", level="error")
                return make_response(jsonify({"error": "Failed to create Stripe customer"}), 500)
            self.log_subscription(f"Created Stripe customer with ID: {stripe_customer.id}", level="info")

            # create subscription in stripe
            self.log_subscription(
                f"Creating Stripe subscription for customer: {stripe_customer.id}, plan: {plan.id}", level="info"
            )
            stripe_subscription = self.payment_processor.create_stripe_subscription(
                stripe_customer, plan, sub_start_date
            )
            if not stripe_subscription:
                self.log_subscription(
                    f"Failed to create Stripe subscription for customer: {stripe_customer.id}", level="error"
                )
                return make_response(jsonify({"error": "Failed to create Stripe subscription"}), 500)
            self.log_subscription(f"Created Stripe subscription with ID: {stripe_subscription.id}", level="info")

            self.log_subscription("Retrieving latest invoice and payment intent", level="info")
            first_invoice = stripe_subscription.latest_invoice
            self.log_subscription(
                f"Latest invoice: {getattr(first_invoice, 'id', first_invoice) if first_invoice else 'None'}",
                level="info",
            )
            self.log_subscription(
                f"Latest invoice details: {first_invoice if first_invoice else 'None'}",
                level="info",
            )
            redirect_to_payment_complete = False
            if first_invoice:
                intent = getattr(first_invoice, "payment_intent", None)
                if intent:
                    payment.transaction_id = getattr(intent, "id", None)
                    # send payment intent to client
                    self.log_subscription(
                        f"Created payment intent for "
                        f"{getattr(intent, 'amount', 'N/A')} "
                        f"{getattr(intent, 'currency', 'N/A')} "
                        f"with id: {getattr(intent, 'id', 'N/A')} "
                        f"and client_secret: {getattr(intent, 'client_secret', 'N/A')}",
                        level="info",
                    )
                    redirect_to_payment_complete = True
                else:
                    intent = self.payment_processor.retrieve_intent_from_invoice(
                        first_invoice if isinstance(first_invoice, str) else ""
                    )
                    if intent:
                        payment.transaction_id = getattr(intent, "id", None)
                        self.log_subscription(
                            f"Payment intent retrieved: {getattr(intent, 'id', intent) if intent else 'None'}",
                            level="info",
                        )
                        redirect_to_payment_complete = True
                    else:
                        self.log_subscription(
                            f"Failed to retrieve payment intent from invoice "
                            f"{getattr(first_invoice, 'id', first_invoice)}",
                            level="error",
                        )

                self.log_subscription(
                    f"Payment intent retrieved: {getattr(intent, 'id', intent) if intent else 'None'}", level="info"
                )
            else:
                # subscription.status = "active"
                self.log_subscription(
                    "No invoice found for subscription because it's a new type of "
                    "subscription based on a previous subscription",
                    level="warning",
                )
                self.log_subscription(
                    "The invoice will be created in the next billing cycle after the current one expires",
                    level="info",
                )

            self.log_subscription(f"Updated payment transaction_id: {payment.transaction_id}", level="info")
            subscription.external_subscription_id = stripe_subscription.id
            self.log_subscription(
                f"Updated subscription external_subscription_id: {subscription.external_subscription_id}", level="info"
            )

            subscription, payment = self.sync_with_stripe(user, subscription, payment, stripe_customer.id)
            self.log_subscription(
                f"Syncing with Stripe: "
                f"user={user.id}, "
                f"subscription={subscription.id}, "
                f"payment={payment.id}, "
                f"customer={stripe_customer.id}"
            )
            self.log_subscription("Successfully synced with Stripe", level="info")

            self.log_subscription("=== Completed create_payment_intent method successfully ===", level="info")
            if redirect_to_payment_complete:
                return jsonify(
                    {
                        "clientSecret": getattr(intent, "client_secret", "N/A"),
                        "customer_id": stripe_customer.id,
                        "subscription_id": subscription.id,
                        "payment_id": payment.id,
                    }
                )
            else:
                flash(
                    _(
                        "Your subscription has been created. "
                        "The invoice will be created in the next billing cycle "
                        "after the current one expires."
                    ),
                    "info",
                )
                return jsonify(
                    {
                        "redirect_url": "/subscription/index",
                    }
                )
        except StripeError as e:
            self.log_subscription(f"Stripe error in create_payment_intent: {str(e)}", level="error")
            return make_response(jsonify({"error": {"message": str(e)}}), 400)
        except Exception as e:
            self.log_subscription(f"Unexpected error in create_payment_intent: {str(e)}", level="error")
            self.log_subscription(f"Error traceback: {traceback.format_exc()}", level="error")
            return make_response(jsonify({"error": {"message": str(e)}}), 400)

    @expose("/payment-complete", methods=["POST"])
    @has_access
    def payment_complete(self) -> Response:
        """Handle successful payment completion via AJAX"""
        # Get session_id and subscription_id from the request
        data = json.loads(request.data)
        intent_id = data.get("payment_intent_id")
        subscription_id = data.get("subscription_id")
        payment_id = data.get("payment_id")

        # Retrieve the checkout session from Stripe to verify
        intent = self.payment_processor.retrieve_intent(intent_id)
        if not intent:
            return make_response(jsonify({"error": "Error retrieving payment information"}), 500)

        # Verify the payment was successful
        if intent.status != "succeeded":
            return make_response(jsonify({"error": "Payment not completed successfully"}), 400)
        else:
            try:
                subscription = self.appbuilder.session.query(UserSubscription).filter_by(id=subscription_id).first()
                payment = self.appbuilder.session.query(Payment).filter_by(id=payment_id).first()
                if not subscription or not payment:
                    return make_response(jsonify({"error": "Subscription or payment not found"}), 400)

                subscription.status = "active"
                payment.status = "success"

                user = self._get_user()
                db_user = self.appbuilder.session.query(User).get(user.id)
                paid_role = self.appbuilder.session.query(Role).filter_by(name="Gamma").first()
                db_user.changed_on = datetime.datetime.now()
                if paid_role and paid_role not in db_user.roles:
                    db_user.roles.append(paid_role)
                self.appbuilder.session.commit()

                return make_response(jsonify({"success": True}), 200)
            except Exception as e:
                self.log_subscription(f"Error in payment_complete: {str(e)}", level="error")
                return make_response(jsonify({"error": {"message": str(e)}}), 400)

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

        return self.render_template("subscription/success.html", subscription=subscription, user=user)

    @expose("/manage")
    @has_access
    def manage(self) -> Response:
        """Manage existing subscription"""
        self.log_subscription("=== Starting manage method ===", level="info")

        # Get a fresh User instance with the mixin applied
        user = self._get_user()
        self.log_subscription(f"Retrieved user with ID: {user.id}", level="info")

        # Get current subscription using the mixin property
        subscription = user.current_subscription
        self.log_subscription(f"Current subscription: {subscription.id if subscription else 'None'}", level="info")

        # If no subscription, redirect to plans page
        if not subscription:
            self.log_subscription("No subscription found, redirecting to plans page", level="info")
            flash(
                _("You don't have an active subscription. Choose a plan below to subscribe."),
                "info",
            )
            return redirect(url_for(".plans"))
        elif subscription.status == "cancelled":
            self.log_subscription(
                f"Subscription {subscription.id} is cancelled, redirecting to plans page", level="info"
            )
            flash(
                _("Your subscription has been cancelled. Choose a plan below to subscribe."),
                "info",
            )
            return redirect(url_for(".plans"))
        elif subscription.status == "expired":
            self.log_subscription(f"Subscription {subscription.id} is expired, redirecting to plans page", level="info")
            flash(
                _("Your subscription has expired. Choose a plan below to subscribe."),
                "info",
            )
            return redirect(url_for(".plans"))

        if subscription.status == "active":
            self.log_subscription(f"Processing active subscription {subscription.id}", level="info")
            # Check for payments directly
            payments = self.check_user_payments(user.id)
            self.log_subscription(f"Found {len(payments)} payments for user {user.id}", level="info")

            # Debug logging
            self.log_subscription(f"Subscription ID: {subscription.id}", level="info")
            self.log_subscription(f"Number of payments from helper: {len(payments)}", level="info")
            self.log_subscription(
                f"Number of payments from subscription: {len(subscription.payments) if subscription.payments else 0}",
                level="info",
            )
        elif subscription.status == "incomplete":
            self.log_subscription(
                f"Subscription {subscription.id} is incomplete, redirecting to manage page to pay the first invoice",
                level="info",
            )

        # Check if user is admin
        is_admin = self.is_admin_user(user)
        self.log_subscription(f"User {user.id} admin status: {is_admin}", level="info")

        self.log_subscription("=== Completed manage method successfully ===", level="info")
        return self.render_template(
            "subscription/manage.html",
            subscription=subscription,
            user=user,
            is_admin=is_admin,
        )

    @expose("/resume-payment", methods=["POST"])
    @has_access
    def resume_payment(self) -> Response:
        """Resume payment process for an incomplete subscription."""
        self.log_subscription("=== Starting resume_payment method ===", level="info")
        subscription_id = request.form.get("subscription_id")

        if not subscription_id:
            flash(_("Subscription ID is missing."), "danger")
            self.log_subscription("Subscription ID missing in form data.", level="warning")
            return redirect(url_for(".manage"))

        user = self._get_user()
        subscription = self.appbuilder.session.query(UserSubscription).filter_by(id=subscription_id).first()

        if not subscription:
            flash(_("Subscription not found."), "danger")
            self.log_subscription(f"Subscription not found for ID: {subscription_id}, user: {user.id}", level="warning")
            return redirect(url_for(".manage"))

        self.log_subscription(f"Attempting to resume payment for subscription ID: {subscription.id}", level="info")
        plan_id = subscription.plan.product_id

        if not plan_id:
            flash(_("Could not determine the plan for this subscription."), "danger")
            self.log_subscription(f"Could not determine plan_id for subscription {subscription.id}", level="error")
            return redirect(url_for(".manage"))

        flash(_("Just one small payment away from data visualization nirvana!"), "info")
        self.log_subscription(
            f"Redirecting user to payment page for subscription {subscription.id}, plan {plan_id}", level="info"
        )
        return redirect(url_for(".payment", plan_id=plan_id))

    @expose("/cancel", methods=["POST"])
    @has_access
    def cancel(self) -> Response:
        self.log_subscription("Cancelling subscription", level="info")
        """Cancel subscription"""
        # Get a fresh User instance with the mixin applied
        subscription_id = request.form.get("subscription_id")
        self.log_subscription(f"Subscription ID: {subscription_id}", level="info")
        user = self._get_user()
        self.log_subscription(f"User: {user}", level="info")

        # Get current subscription using the mixin property
        subscription = user.current_subscription
        self.log_subscription(f"Subscription: {subscription}", level="info")

        if subscription:
            # If we have a Stripe subscription ID, cancel in Stripe
            if hasattr(subscription, "external_subscription_id") and subscription.external_subscription_id:
                self.log_subscription(
                    f"Cancelling subscription {subscription.external_subscription_id} for user {user.id}"  # noqa: E501
                )
                success = self.payment_processor.cancel_subscription(subscription.external_subscription_id)
                if not success:
                    flash(
                        _("Error cancelling subscription with payment provider"),
                        "danger",
                    )
                    return redirect(url_for(".manage"))

            subscription.status = "cancelled"
            subscription.is_auto_renew = False
            self.appbuilder.session.commit()
            flash(_("Your subscription has been cancelled"), "success")

        return redirect(url_for(".manage"))

    # Helper methods
    def calc_subscription_period(self, plan: SubscriptionPlan | None) -> datetime.timedelta:
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

            self.log_subscription(f"Found {len(payments)} payments for subscription {subscription_id}", level="info")
            return payments
        except Exception as e:
            self.log_subscription(f"Error checking payments: {str(e)}", level="error")
            return []

    def check_user_payments(self, user_id: int) -> list[Payment]:
        """Helper function to check if a user has payments"""
        try:
            payments = self.appbuilder.session.query(Payment).filter_by(user_id=user_id).all()
            return payments
        except Exception as e:
            self.log_subscription(f"Error checking payments: {str(e)}", level="error")
            return []

    def sync_with_stripe(
        self,
        user: User,
        subscription: UserSubscription,
        payment: Payment,
        customer_id: str | None = None,
    ) -> tuple[UserSubscription, Payment]:
        """Sync the subscription and payment with Stripe"""
        if not subscription.id:
            self.appbuilder.session.add(subscription)
        if not payment.id:
            self.appbuilder.session.add(payment)
        subscription.payments.append(payment)
        self.appbuilder.session.flush()
        self.appbuilder.session.execute(
            text(
                "UPDATE ab_user SET stripe_customer_id = :stripe_customer_id, is_paid_user = :is_paid_user WHERE id = :user_id"  # noqa: E501
            ),
            {
                "stripe_customer_id": customer_id,
                "is_paid_user": True,
                "user_id": user.id,
            },
        )
        self.appbuilder.session.commit()

        return subscription, payment

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

    def log_subscription(self, message: str, level: str = "info") -> None:
        """Log subscription-related messages with special formatting"""
        logger_method = getattr(current_app.logger, level)
        logger_method(message, extra={"subscription": True})
