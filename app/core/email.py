"""Email service - handles sending system emails (auth, alerts, notifications)"""

import logging
from typing import List, Optional
from pydantic import EmailStr

logger = logging.getLogger(__name__)

class EmailService:
    """
    Service for sending emails.
    Currently implements console logging for development.
    Can be easily swapped for SendGrid, AWS SES, or SMTP.
    """

    @staticmethod
    async def send_email(
        to_email: EmailStr,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email to a single recipient.
        
        PRODUCTION READY:
        - In production, this should use a background task (e.g., Celery or FastAPI background tasks)
        - Use a robust provider like AWS SES or SendGrid
        """
        logger.info(f" SENDING EMAIL TO: {to_email}")
        logger.info(f"   SUBJECT: {subject}")
        logger.info(f"   BODY: {body}")
        
        # MOCK SUCCESS
        return True

    @staticmethod
    async def send_password_reset_email(email: str, token: str):
        """Send password reset link to user"""
        reset_link = f"https://graphmind.ai/reset-password?token={token}"
        
        subject = "GraphMind - Reset Your Password"
        body = f"Click the link below to reset your password. This link expires in 1 hour.\n\n{reset_link}"
        
        await EmailService.send_email(to_email=email, subject=subject, body=body)
