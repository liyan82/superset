import datetime
import logging
import os
from typing import Any, cast

import stripe

# import stripe # Import the stripe library - you'll need to install it: pip install stripe
from sqlalchemy import column, table, text, update

from superset import db
from superset.extensions import celery_app
from superset.models.subscription import UserSubscription  # Import the model

# Assuming User model might not have stripe_customer_id directly or for consistency with subscription_user_view.py
# from superset.models.user import User


logger = logging.getLogger(__name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# --- Placeholder Stripe API Functions ---
# In a real application, these would use the Stripe SDK and API key.
# stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") # Configure Stripe API Key


def get_stripe_customer_by_email(email: str) -> stripe.Customer | None:
    """Placeholder: Retrieve a Stripe customer by email."""
    logger.info(f"[Stripe Mock] Checking for customer with email: {email}")
    try:
        # stripe.Customer.search() returns a SearchListObject containing StripeObject by default.
        # The objects in .data will be Customer objects when searching customers.
        customers_response = stripe.Customer.search(query=f"email:'{email}'")
        logger.info(f"Customers response: {customers_response}")
        if customers_response.data:
            # Cast the StripeObject to stripe.Customer to satisfy the type checker.
            return cast(stripe.Customer, customers_response.data[0])
        else:
            # No customer found with that email.
            return None
    except Exception as e:
        logger.error(f"Error retrieving Stripe customer by email: {e}")
        return None


def get_stripe_customer(stripe_customer_id: str) -> dict[str, Any] | None:
    """Placeholder: Retrieve a Stripe customer by ID."""
    logger.info(f"[Stripe Mock] Getting customer: {stripe_customer_id}")
    if stripe_customer_id == "cus_mockexistingid":  # Simulate an existing customer
        return {
            "id": stripe_customer_id,
            "email": "test@example.com",
            "name": "Test User",
        }
    return None


def create_stripe_customer(email: str, name: str) -> dict[str, Any] | None:
    """Placeholder: Create a Stripe customer."""
    logger.info(f"[Stripe Mock] Creating customer for email: {email}, name: {name}")
    customer = stripe.Customer.create(email=email, name=name)
    # In a real scenario, this would return the Stripe customer object
    return {"id": customer.id, "email": email, "name": name}


def update_stripe_customer(
    stripe_customer_id: str, email: str | None = None, name: str | None = None
) -> dict[str, Any] | None:
    """Placeholder: Update a Stripe customer."""
    logger.info(
        f"[Stripe Mock] Updating customer: {stripe_customer_id} with email: {email}, name: {name}"
    )
    return {"id": stripe_customer_id, "email": email, "name": name}


def create_stripe_subscription(
    stripe_customer_id: str,
    product_id: str,
) -> dict[str, Any] | None:
    """Placeholder: Create a Stripe subscription."""
    logger.info(
        f"[Creating subscription for customer: {stripe_customer_id} with product id: {product_id}"
    )
    # This would return the Stripe subscription object
    return {
        "id": f"sub_mocknew_{stripe_customer_id}",
        "customer": stripe_customer_id,
        "plan": {"product": product_id, "id": product_id},
        "status": "active",
    }


def get_stripe_subscription(stripe_subscription_id: str) -> dict[str, Any] | None:
    """Placeholder: Retrieve a Stripe subscription by ID."""
    logger.info(f"[Stripe Mock] Getting subscription: {stripe_subscription_id}")
    if stripe_subscription_id.startswith(
        "sub_mock_"
    ):  # Simulate an existing subscription
        return {
            "id": stripe_subscription_id,
            "status": "active",
            "plan": {"id": "price_mockplan"},
        }
    return None


# --- End Placeholder Stripe API Functions ---


# Helper to map local plan_type to Stripe Price ID
# This mapping needs to be maintained based on your Stripe setup.
def get_stripe_price_id_for_plan(plan_type: str) -> str | None:
    if plan_type == "premium_monthly":
        return "price_premium_monthly_mock"  # Replace with actual Stripe Price ID
    if plan_type == "premium_yearly":
        return "price_premium_yearly_mock"  # Replace with actual Stripe Price ID
    # Add other plans as needed
    logger.warning(f"No Stripe Price ID found for plan_type: {plan_type}")
    return None


@celery_app.task(name="sync_stripe.sync_stripe_data")
def sync_stripe_data() -> None:
    """
    Synchronizes user data and subscriptions with Stripe.
    - Scans the user table and syncs user info to Stripe customers.
    - Scans the user_subscriptions table and syncs to Stripe subscriptions.
    """
    logger.info("Starting Stripe data synchronization...")

    # Configure Stripe API Key - ideally from config or environment variables
    # Ensure this is set before making any Stripe calls.
    # Example: stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
    # For this task, we are using placeholder functions that don't require a live key.
    # if not os.environ.get("STRIPE_SECRET_KEY"):
    #     logger.error("STRIPE_SECRET_KEY not configured. Skipping Stripe sync.")
    #     return

    try:
        # Part 1: Synchronize Users with Stripe Customers
        logger.info("Synchronizing user data with Stripe customers...")

        users_to_sync = db.session.execute(
            text(
                "SELECT id, email, first_name, last_name, stripe_customer_id FROM ab_user where (stripe_customer_id is null or stripe_customer_id = '') and id > 1"  # noqa: E501
            )
        ).fetchall()

        logger.info(f"Users to sync: {users_to_sync} with number of users: {len(users_to_sync)}")  # noqa: E501
        user_table = table(
            "ab_user",
            column("id"),
            column("stripe_customer_id"),
            # Add other columns if needed for update, though models.User might be better for complex updates  # noqa: E501
        )
        plan_table = table(
            "subscription_plans",
            column("id"),
            column("name"),
            column("product_id"),
        )

        for user_row in users_to_sync:
            user_id, email, first_name, last_name, stripe_customer_id = user_row
            user_full_name = f"{first_name or ''} {last_name or ''}".strip()
            logger.info(f"Processing user {user_id} ({email}) with name: {user_full_name}")  # noqa: E501

            try:
                # Try to find by email first to avoid duplicates if ID was lost
                stripe_customer_by_email = get_stripe_customer_by_email(email)
                logger.info(f"Stripe customer by email: {stripe_customer_by_email}")
                if stripe_customer_by_email:
                    logger.info(
                        f"Found existing Stripe customer by email {email}: {stripe_customer_by_email['id']}. Linking to user {user_id}."  # noqa: E501
                    )
                    new_stripe_id = stripe_customer_by_email["id"]
                else:
                    logger.info(
                        f"User {user_id} ({email}) has no Stripe ID. Creating Stripe customer."  # noqa: E501
                    )
                    new_customer = create_stripe_customer(
                        email=email, name=user_full_name
                    )
                    if new_customer and new_customer.get("id"):
                        new_stripe_id = new_customer["id"]
                        logger.info(
                            f"Created Stripe customer for user {user_id}: {new_stripe_id}"  # noqa: E501
                        )
                    else:
                        logger.error(
                            f"Failed to create Stripe customer for user {user_id} ({email})."  # noqa: E501
                        )
                        continue  # Skip to next user

                    # Update ab_user with the new/found Stripe customer ID
                    stmt = (
                        update(user_table)
                        .where(user_table.c.id == user_id)
                        .values(stripe_customer_id=new_stripe_id)
                    )
                    db.session.execute(stmt)
                    logger.info(
                        f"Updated user {user_id} with Stripe Customer ID: {new_stripe_id}"  # noqa: E501
                    )

            except Exception as user_sync_exc:
                logger.error(
                    f"Error synchronizing user {user_id} ({email}) with Stripe: {user_sync_exc}",  # noqa: E501
                    exc_info=True,
                )
                # Continue with the next user

        db.session.commit()  # Commit user updates
        logger.info("User data synchronization with Stripe customers finished.")

        # Part 2: Synchronize Subscriptions with Stripe
        logger.info("Synchronizing user subscriptions with Stripe...")

        # Fetch active/relevant local subscriptions
        # NOTE: This assumes UserSubscription model has a 'stripe_subscription_id' field.
        # If not, a database migration would be needed to add it.
        local_subscriptions = (
            db.session.query(
                UserSubscription,
                user_table.c.stripe_customer_id.label("stripe_customer_id"),
            )
            .join(user_table, UserSubscription.user_id == user_table.c.id)
            .join(plan_table, UserSubscription.plan_id == plan_table.c.id)
            .filter(
                UserSubscription.status.notin_(
                    ["expired", "cancelled"]
                ),  # Sync active or pending subscriptions
                UserSubscription.end_date
                >= datetime.datetime.now(),  # Or some other logic for active subs
            )
            .filter(UserSubscription.external_subscription_id is not None)
            .all()
        )

        for sub_wrapper in local_subscriptions:
            sub, user_stripe_customer_id = (
                sub_wrapper.UserSubscription,
                sub_wrapper.stripe_customer_id,
            )

            if not user_stripe_customer_id:
                logger.warning(
                    f"User {sub.user_id} for subscription {sub.id} has no Stripe Customer ID. Skipping subscription sync."  # noqa: E501
                )
                continue

            # This is where you'd store Stripe's subscription ID on your local model
            current_stripe_subscription_id = getattr(
                sub, "external_subscription_id", None
            )

            try:
                if not current_stripe_subscription_id:
                    logger.info(
                        f"Local subscription {sub.id} for user {sub.user_id} has no Stripe subscription ID. Creating in Stripe."  # noqa: E501
                    )


                    new_stripe_sub = create_stripe_subscription(
                        stripe_customer_id=user_stripe_customer_id,
                        product_id=sub.plan.product_id,
                    )

                    if new_stripe_sub and new_stripe_sub.get("id"):
                        sub.external_subscription_id = new_stripe_sub[
                            "id"
                        ]  # Update local model
                        db.session.add(sub)  # Add to session for commit
                        logger.info(
                            f"Created Stripe subscription {sub.external_subscription_id} for local sub {sub.id} (User: {sub.user_id})."  # noqa: E501
                        )
                    else:
                        logger.error(
                            f"Failed to create Stripe subscription for local sub {sub.id} (User: {sub.user_id})."  # noqa: E501
                        )

            except Exception as sub_sync_exc:
                logger.error(
                    f"Error synchronizing subscription {sub.id} (User: {sub.user_id}) with Stripe: {sub_sync_exc}",  # noqa: E501
                    exc_info=True,
                )
                # Continue with the next subscription

        db.session.commit()  # Commit subscription updates
        logger.info("User subscription synchronization with Stripe finished.")

        logger.info("Stripe data synchronization finished successfully.")
    except Exception as e:
        logger.error(f"Error during Stripe data synchronization: {e}", exc_info=True)
        db.session.rollback()
    finally:
        db.session.remove()  # Ensure session is cleaned up
        logger.info("Finished Stripe data synchronization task run.")
