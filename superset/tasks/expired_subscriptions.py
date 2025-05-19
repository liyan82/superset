import datetime
import logging

from superset import db  # Import the SQLAlchemy db session
from superset.extensions import celery_app, security_manager
from superset.models.subscription import UserSubscription  # Import the model
from superset.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(name="expired_subscriptions.scan_and_label")
def scan_and_label_expired_subscriptions() -> None:
    logger.info("Starting scan for expired subscriptions...")
    try:
        now = datetime.datetime.now()
        expired_subscriptions = (
            db.session.query(UserSubscription)
            .filter(
                UserSubscription.end_date < now,
                UserSubscription.status
                != "expired",  # Avoid re-processing already expired  # noqa: E501
                UserSubscription.status
                != "cancelled",  # Avoid processing cancelled subscriptions  # noqa: E501
            )
            .all()
        )

        if not expired_subscriptions:
            logger.info("No subscriptions found that need to be marked as expired.")
            return

        updated_count = 0
        for sub in expired_subscriptions:
            logger.info(
                f"Marking subscription ID {sub.id} for user {sub.user_id} as expired. "
                f"End date: {sub.end_date}"
            )
            sub.status = "expired"

            # Remove Gamma role from the user
            user = db.session.query(User).filter(User.id == sub.user_id).first()
            if user:
                gamma_role = security_manager.find_role("Gamma")
                logger.info(f"Gamma role: {gamma_role}")
                if gamma_role in user.roles:
                    user.roles.remove(gamma_role)
                    logger.info(f"Removed Gamma role from user {user.username}")

            updated_count += 1

        db.session.commit()
        logger.info(f"Successfully updated {updated_count} subscriptions to 'expired'.")

    except Exception as e:
        logger.error(f"Error during expired subscription scan: {e}", exc_info=True)
        db.session.rollback()  # Rollback in case of error
    finally:
        db.session.remove()  # Ensure session is cleaned up
    logger.info("Finished scanning and labeling expired subscriptions.")
