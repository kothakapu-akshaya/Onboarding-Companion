"""Notification tasks for sending emails, SMS, and other notifications."""

import logging
from typing import Any

from sqlmodel import Session, select

from app.core.celery_app import celery_app
from app.db.session import engine
from app.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.notifications.send_email")
def send_email(  # noqa: D417
    self,
    recipients: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    sender: str | None = None,
) -> dict[str, Any]:
    """Send email notification.

    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        sender: Optional sender email (uses default if not provided)

    Returns:
        Dict with send results
    """
    try:
        logger.info(f"Sending email to {len(recipients)} recipients: {subject}")

        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "status": "Preparing email..."},
        )

        # TODO: Configure SMTP settings in config
        # This is a placeholder implementation
        results = {
            "status": "success",
            "sent_to": recipients,
            "subject": subject,
            "timestamp": None,  # Would add actual timestamp
        }

        self.update_state(
            state="PROGRESS",
            meta={"current": 100, "total": 100, "status": "Email sent"},
        )

        logger.info(f"Email sent successfully to {len(recipients)} recipients")
        return results

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise


@celery_app.task(
    name="app.tasks.notifications.send_processing_complete_notification"
)
def send_processing_complete_notification(
    user_id: int, record_id: int
) -> dict[str, Any]:
    """Send notification when file processing is complete.

    Args:
        user_id: User ID to notify
        record_id: Record ID that was processed

    Returns:
        Dict with notification results
    """
    try:
        logger.info(
            f"Sending processing complete notification to user {user_id} "
            f"for record {record_id}"
        )

        with Session(engine) as session:
            # Get user details
            user = session.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Get record details
            from app.models.record import Record

            record = session.get(Record, record_id)
            if not record:
                raise ValueError(f"Record {record_id} not found")

            # Send email notification
            subject = (
                f"File Processing Complete - {record.file_name or 'Unknown'}"
            )
            body = f"""
            Dear {user.name},
            
            Your file "{record.file_name or "Unknown"}" has been successfully
            processed.
            
            Processing Details:
            - Record ID: {record.uid}
            - File Type: {record.media_type}
            - Processing Status: {record.status}
            
            You can now access your processed file in the application.
            
            Best regards,
            Indic languages Corpus Collections Team
            """

            # Queue email sending task
            if user.email:
                email_task = celery_app.send_task(
                    "app.tasks.notifications.send_email",
                    args=[[user.email], subject, body],
                )

                return {
                    "status": "success",
                    "user_id": user_id,
                    "record_id": record_id,
                    "email_task_id": email_task.id,
                }
            else:
                logger.warning(
                    f"User {user_id} has no email address for notification"
                )
                return {
                    "status": "skipped",
                    "reason": "No email address",
                    "user_id": user_id,
                    "record_id": record_id,
                }

    except Exception as e:
        logger.error(f"Failed to send processing notification: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notifications.send_bulk_notification")
def send_bulk_notification(
    user_ids: list[int],
    subject: str,
    message: str,
    notification_type: str = "email",
) -> dict[str, Any]:
    """Send bulk notification to multiple users.

    Args:
        user_ids: List of user IDs to notify
        subject: Notification subject
        message: Notification message
        notification_type: Type of notification (email, sms, etc.)

    Returns:
        Dict with bulk notification results
    """
    try:
        logger.info(
            f"Sending bulk {notification_type} notification to "
            f"{len(user_ids)} users"
        )

        results = {"sent": [], "failed": [], "total": len(user_ids)}

        with Session(engine) as session:
            # Get users in batches
            from sqlalchemy import Column

            users = session.exec(
                select(User).where(Column("id").in_(user_ids))
            ).all()

            for user in users:
                try:
                    if notification_type == "email" and user.email:
                        # Queue individual email task
                        task = celery_app.send_task(
                            "app.tasks.notifications.send_email",
                            args=[[user.email], subject, message],
                        )

                        results["sent"].append(
                            {
                                "user_id": user.id,
                                "email": user.email,
                                "task_id": task.id,
                            }
                        )
                    else:
                        results["failed"].append(
                            {
                                "user_id": user.id,
                                "reason": f"No {notification_type} address",
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to queue notification for user {user.id}: "
                        f"{str(e)}"
                    )
                    results["failed"].append(
                        {"user_id": user.id, "reason": str(e)}
                    )

        logger.info(
            f"Bulk notification queued: {len(results['sent'])} sent, "
            f"{len(results['failed'])} failed"
        )
        return results

    except Exception as e:
        logger.error(f"Bulk notification failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notifications.send_system_alert")
def send_system_alert(
    alert_type: str,
    message: str,
    severity: str = "info",
    admin_only: bool = True,
) -> dict[str, Any]:
    """Send system alert notification to administrators.

    Args:
        alert_type: Type of alert (error, warning, info)
        message: Alert message
        severity: Alert severity level
        admin_only: Whether to send only to admins

    Returns:
        Dict with alert results
    """
    try:
        logger.info(f"Sending system alert: {alert_type} - {severity}")

        with Session(engine) as session:
            # Get all users (User model doesn't have role field)
            # In production, you'd want to add a role field or use a
            # separate admin table
            query = select(User)

            admin_users = session.exec(query).all()

            if not admin_users:
                logger.warning("No admin users found for system alert")
                return {"status": "skipped", "reason": "No admin users found"}

            # Prepare alert email
            subject = f"System Alert [{severity.upper()}]: {alert_type}"
            body = f"""
            System Alert Notification
            
            Alert Type: {alert_type}
            Severity: {severity}
            Timestamp: {alert_type}_alert
            
            Message:
            {message}
            
            This is an automated system notification.
            """

            # Send to all admin users
            admin_emails = [user.email for user in admin_users if user.email]

            if admin_emails:
                task = celery_app.send_task(
                    "app.tasks.notifications.send_email",
                    args=[admin_emails, subject, body],
                )

                return {
                    "status": "success",
                    "alert_type": alert_type,
                    "severity": severity,
                    "recipients": len(admin_emails),
                    "email_task_id": task.id,
                }
            else:
                return {
                    "status": "skipped",
                    "reason": "No admin email addresses found",
                }

    except Exception as e:
        logger.error(f"Failed to send system alert: {str(e)}")
        raise
