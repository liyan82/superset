import datetime
import logging

from flask import current_app

from superset import db  # Import the SQLAlchemy db session
from superset.extensions import celery_app, security_manager
from superset.models.subscription import UserSubscription  # Import the model
from superset.models.user import User

logger = logging.getLogger(__name__)


def _process_expired_subscriptions(now: datetime.datetime) -> None:
    """Scans for and updates expired subscriptions."""
    logger.info("Scanning for expired subscriptions...")
    expired_subscriptions = (
        db.session.query(UserSubscription)
        .filter(
            UserSubscription.end_date < now,
            UserSubscription.status != "expired",
            UserSubscription.status != "cancelled",
        )
        .all()
    )

    if not expired_subscriptions:
        logger.info("No subscriptions found that need to be marked as expired.")
        return

    updated_subs_count = 0
    for sub in expired_subscriptions:
        logger.info(
            "Marking subscription ID %s for user %s as expired. End date: %s",
            sub.id,
            sub.user_id,
            sub.end_date,
        )
        sub.status = "expired"

        user = db.session.query(User).filter(User.id == sub.user_id).first()
        if user:
            expired_role_name = current_app.config.get("TRIAL_EXPIRED_ROLE")
            if expired_role_name:
                expired_role = security_manager.find_role(expired_role_name)
                if expired_role:
                    user.roles = [expired_role]
                    logger.info(
                        "Set user %s role to %s",
                        user.username,
                        expired_role_name,
                    )
                else:
                    logger.warning(
                        "Role '%s' not found. Not updating roles for user %s",
                        expired_role_name,
                        user.username,
                    )
            else:
                logger.warning(
                    "TRIAL_EXPIRED_ROLE not set. Not updating roles for user %s",
                    user.username,
                )
        updated_subs_count += 1

    if updated_subs_count > 0:
        logger.info("Marked %s subscriptions as 'expired'.", updated_subs_count)


def _process_expired_trials(now: datetime.datetime) -> None:
    """Scans for and updates expired trial users."""
    logger.info("Scanning for expired trial users...")
    trial_period_days = current_app.config.get("TRIAL_PERIOD_DAYS")
    trial_role_name = current_app.config.get("AUTH_USER_REGISTRATION_ROLE")
    expired_role_name = current_app.config.get("TRIAL_EXPIRED_ROLE")

    if not all([trial_period_days, trial_role_name, expired_role_name]):
        logger.warning(
            "Skipping trial user expiration scan because one or more required "
            "settings (TRIAL_PERIOD_DAYS, AUTH_USER_REGISTRATION_ROLE, "
            "TRIAL_EXPIRED_ROLE) are not configured."
        )
        return

    trial_role = security_manager.find_role(trial_role_name)
    expired_role = security_manager.find_role(expired_role_name)

    if not trial_role:
        logger.warning(
            "Trial role '%s' not found. Cannot process expired trial users.",
            trial_role_name,
        )
    elif not expired_role:
        logger.warning(
            "Expired trial role '%s' not found. Cannot process expired trial users.",
            expired_role_name,
        )
    else:
        if isinstance(trial_period_days, int):
            expiration_delta = datetime.timedelta(days=trial_period_days)
            trial_users = (
                db.session.query(User).filter(User.roles.contains(trial_role)).all()
            )

            updated_users_count = 0
            for user in trial_users:
                if user.created_on and (now > user.created_on + expiration_delta):
                    logger.info(
                        "User %s's trial has expired (created on %s).",
                        user.username,
                        user.created_on,
                    )
                    user.roles = [expired_role]
                    logger.info(
                        "Set user %s role to %s",
                        user.username,
                        expired_role_name,
                    )
                    updated_users_count += 1

            if updated_users_count > 0:
                logger.info(
                    "Successfully updated %s expired trial users.",
                    updated_users_count,
                )


@celery_app.task(name="expired_subscriptions.process_expirations")
def process_expirations() -> None:
    """
    Celery task to process expired subscriptions and user trials.
    """
    logger.info("Starting processing of expired subscriptions and trials...")
    try:
        now = datetime.datetime.now()
        _process_expired_subscriptions(now)
        _process_expired_trials(now)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error during expirations processing: {e}", exc_info=True)
        db.session.rollback()  # Rollback in case of error
    finally:
        db.session.remove()  # Ensure session is cleaned up
    logger.info("Finished processing expired subscriptions and trials.")
