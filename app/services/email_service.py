import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger("app.services.email")


def _render_welcome_html(first_name: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Welcome to Expense Tracker, {first_name}!</h2>
        <p>Your account has been created successfully.</p>
        <p>Start tracking your expenses, set budgets, and gain insights into your spending habits.</p>
        <p>Happy budgeting!</p>
        <p><em>The Expense Tracker Team</em></p>
    </body>
    </html>
    """


def _render_password_reset_html(token: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password.</p>
        <p>Use the following token to reset your password:</p>
        <p style="font-size: 18px; font-weight: bold; background: #f4f4f4; padding: 10px;">{token}</p>
        <p>If you did not request this, please ignore this email.</p>
        <p><em>The Expense Tracker Team</em></p>
    </body>
    </html>
    """


def _render_budget_alert_html(
    first_name: str,
    category_name: str,
    limit_amount: float,
    spent_amount: float,
) -> str:
    percentage = round((spent_amount / limit_amount) * 100, 1) if limit_amount > 0 else 0
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Budget Alert for {first_name}</h2>
        <p>Your spending in <strong>{category_name}</strong> has exceeded your budget threshold.</p>
        <table style="border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 4px 12px 4px 0;">Budget Limit:</td><td>${limit_amount:,.2f}</td></tr>
            <tr><td style="padding: 4px 12px 4px 0;">Amount Spent:</td><td>${spent_amount:,.2f}</td></tr>
            <tr><td style="padding: 4px 12px 4px 0;">Percentage Used:</td><td>{percentage}%</td></tr>
        </table>
        <p>Review your transactions and adjust your spending to stay on track.</p>
        <p><em>The Expense Tracker Team</em></p>
    </body>
    </html>
    """


class EmailService:
    """Helper service to construct and send MIME messages via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM_EMAIL
        self.from_name = from_name or settings.SMTP_FROM_NAME

    def _is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_port)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send an email message. Returns True on success, False on failure."""
        if not self._is_configured():
            logger.warning(
                "SMTP not configured; skipping email delivery",
                to_email=to_email,
                subject=subject,
            )
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info("Email sent successfully", to_email=to_email, subject=subject)
            return True
        except Exception as exc:
            logger.warning(
                "Failed to send email",
                to_email=to_email,
                subject=subject,
                error=str(exc),
                exc_info=True,
            )
            return False

    def send_welcome_email(self, to_email: str, first_name: str) -> bool:
        """Send a welcome email to a newly registered user."""
        html = _render_welcome_html(first_name)
        text = (
            f"Welcome to Expense Tracker, {first_name}!\n\n"
            "Your account has been created successfully.\n"
            "Start tracking your expenses, set budgets, and gain insights into your spending habits."
        )
        return self.send_email(
            to_email=to_email,
            subject="Welcome to Expense Tracker",
            html_body=html,
            text_body=text,
        )

    def send_password_reset_email(self, to_email: str, token: str) -> bool:
        """Send a password reset email containing the reset token."""
        html = _render_password_reset_html(token)
        text = (
            "Password Reset Request\n\n"
            "We received a request to reset your password.\n"
            f"Use the following token to reset your password: {token}\n\n"
            "If you did not request this, please ignore this email."
        )
        return self.send_email(
            to_email=to_email,
            subject="Password Reset - Expense Tracker",
            html_body=html,
            text_body=text,
        )

    def send_budget_alert_email(
        self,
        to_email: str,
        first_name: str,
        category_name: str,
        limit_amount: float,
        spent_amount: float,
    ) -> bool:
        """Send a budget threshold exceeded alert email."""
        html = _render_budget_alert_html(
            first_name=first_name,
            category_name=category_name,
            limit_amount=limit_amount,
            spent_amount=spent_amount,
        )
        text = (
            f"Budget Alert for {first_name}\n\n"
            f"Your spending in {category_name} has exceeded your budget threshold.\n"
            f"Budget Limit: ${limit_amount:,.2f}\n"
            f"Amount Spent: ${spent_amount:,.2f}\n"
        )
        return self.send_email(
            to_email=to_email,
            subject=f"Budget Alert: {category_name}",
            html_body=html,
            text_body=text,
        )
