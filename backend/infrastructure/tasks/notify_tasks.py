"""
Celery tasks for alert notification dispatch.

dispatch_pending_alerts: called by beat every 2 minutes.
  Fetches all PENDING alerts and enqueues one send_alert_notification task each.

send_alert_notification: called per alert.
  Instantiates SendAlertNotification with real adapters and executes it.
"""

import logging

from backend.application.commands import SendAlertNotificationCommand
from backend.application.exceptions import NotificationFailedError
from backend.application.use_cases.send_alert_notification import SendAlertNotification
from backend.infrastructure.notifications.composite_service import CompositeNotificationService
from backend.infrastructure.notifications.sendgrid_service import SendGridNotificationService
from backend.infrastructure.notifications.twilio_service import TwilioWhatsAppService
from backend.infrastructure.persistence.alert_repository import PostgresAlertRepository
from backend.infrastructure.persistence.database import SessionLocal
from backend.infrastructure.persistence.search_repository import PostgresSearchRepository
from backend.infrastructure.persistence.user_repository import PostgresUserRepository
from backend.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.infrastructure.tasks.notify_tasks.dispatch_pending_alerts")
def dispatch_pending_alerts() -> dict:
    """
    Fan out one send_alert_notification task per PENDING alert.

    Returns:
        Dict with count of enqueued notification tasks.
    """
    with SessionLocal() as session:
        repo = PostgresAlertRepository(session)
        pending = repo.find_pending()

    for alert in pending:
        send_alert_notification.delay(str(alert.id))

    logger.info("Enqueued %d notification tasks.", len(pending))
    return {"enqueued": len(pending)}


@celery_app.task(
    name="backend.infrastructure.tasks.notify_tasks.send_alert_notification",
    autoretry_for=(NotificationFailedError,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def send_alert_notification(alert_id: str) -> dict:
    """
    Dispatch the notification for a single PENDING Alert.

    Args:
        alert_id: String UUID of the Alert to notify.

    Returns:
        Dict with alert_id and success status.
    """
    from uuid import UUID

    with SessionLocal() as session:
        alerts = PostgresAlertRepository(session)
        searches = PostgresSearchRepository(session)
        users = PostgresUserRepository(session)
        notification = CompositeNotificationService([
            SendGridNotificationService(),
            TwilioWhatsAppService(),
        ])

        use_case = SendAlertNotification(
            alerts=alerts,
            searches=searches,
            users=users,
            notification=notification,
        )

        try:
            use_case.execute(SendAlertNotificationCommand(alert_id=UUID(alert_id)))
            session.commit()
            logger.info("Alert %s notified successfully.", alert_id)
            return {"alert_id": alert_id, "success": True}
        except NotificationFailedError:
            session.commit()  # status=FAILED was already saved
            logger.error("All channels failed for alert %s — will retry.", alert_id)
            raise
        except Exception:
            session.rollback()
            logger.exception("Unexpected error notifying alert %s.", alert_id)
            raise
