"""
Email Sender — Gmail SMTP integration for sending research digests.

Uses Python's built-in smtplib + email.mime for zero-dependency email delivery.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from backend.config import EmailConfig

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends HTML research digest emails via SMTP."""

    def __init__(self, config: EmailConfig):
        self.address = config.smtp_user
        self.password = config.smtp_password
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port

        if not self.address or not self.password or not self.smtp_server:
            logger.warning(
                "SMTP credentials not configured. "
                "Email sending will be disabled."
            )

    def send_digest(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        plain_text: str = "",
    ) -> bool:
        """
        Send a digest email to multiple recipients.

        Args:
            to_emails: List of recipient email addresses.
            subject: Email subject line.
            html_body: Full HTML body of the email.
            plain_text: Plain text fallback (auto-generated if empty).

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.address or not self.password or not self.smtp_server:
            logger.error("Cannot send email: SMTP credentials not configured.")
            return False

        if not to_emails:
            logger.warning("No recipients specified. Skipping email.")
            return False

        # Auto-generate plain text if not provided
        if not plain_text:
            plain_text = self._html_to_plain(html_body)

        try:
            # Build multipart message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"Research Paper Summarizer <{self.address}>"
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            # Attach both plain text and HTML versions
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Send via SMTP
            if self.smtp_port == 465:
                # Implicit TLS for port 465
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.address, self.password)
                    server.sendmail(self.address, to_emails, msg.as_string())
            else:
                # STARTTLS for port 587
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.address, self.password)
                    server.sendmail(self.address, to_emails, msg.as_string())

            logger.info(
                f"✅ Email sent successfully to {len(to_emails)} recipients: "
                f"'{subject}'"
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP authentication failed. "
                "Check your SMTP_USER and SMTP_PASSWORD in .env. "
            )
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_test_email(self, to_email: str) -> bool:
        """Send a quick test email to verify SMTP configuration works."""
        return self.send_digest(
            to_emails=[to_email],
            subject="🧪 Research Paper Summarizer — Test Email",
            html_body=(
                "<html><body>"
                "<h2>✅ Email Configuration Working!</h2>"
                "<p>Your SMTP setup is correctly configured. "
                "You will start receiving research digests at this address.</p>"
                "<p style='color: #666; font-size: 12px;'>"
                "— Research Paper Summarizer</p>"
                "</body></html>"
            ),
            plain_text="Email configuration is working! You will receive research digests at this address.",
        )

    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Very basic HTML to plain text conversion."""
        import re
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
