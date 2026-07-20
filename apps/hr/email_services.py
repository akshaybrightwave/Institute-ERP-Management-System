import logging
import smtplib
import socket
from email.utils import formataddr

from django.core.mail import EmailMessage, get_connection

from .email_crypto import EmailPasswordCryptoError, decrypt_app_password, normalize_app_password
from .models import EmailConfiguration

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when a configured SMTP send cannot be completed."""


class EmailConfigurationService:
    @staticmethod
    def active_configuration():
        return EmailConfiguration.active()

    @staticmethod
    def configuration_error():
        if not EmailConfigurationService.active_configuration():
            return 'No active email configuration found. Please configure Settings > Email Configuration.'
        return ''

    @staticmethod
    def send_mail(subject, body, recipients, attachments=None):
        config = EmailConfigurationService.active_configuration()
        if not config:
            raise EmailDeliveryError('No active email configuration found. Please configure Settings > Email Configuration.')

        recipients = [email for email in (recipients or []) if email]
        if not recipients:
            raise EmailDeliveryError('No recipient email address was provided.')

        try:
            app_password = normalize_app_password(decrypt_app_password(config.google_app_password))
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=config.smtp_host,
                port=config.smtp_port,
                username=config.email_address,
                password=app_password,
                use_tls=config.use_tls,
                timeout=20,
                fail_silently=False,
            )
            from_email = formataddr((config.from_name or config.email_address, config.email_address))
            message = EmailMessage(subject, body, from_email, recipients, connection=connection)
            for attachment in attachments or []:
                try:
                    message.attach_file(attachment)
                except OSError as exc:
                    logger.exception('Email attachment could not be read.')
                    raise EmailDeliveryError(f'Could not attach file: {attachment}') from exc
            return message.send(fail_silently=False)
        except EmailPasswordCryptoError as exc:
            logger.exception('Configured email password could not be decrypted.')
            raise EmailDeliveryError(str(exc)) from exc
        except EmailDeliveryError:
            raise
        except smtplib.SMTPAuthenticationError as exc:
            logger.exception('SMTP authentication failed for configured email account.')
            raise EmailDeliveryError('Gmail rejected the login. Use the exact Google account email that generated the 16-character App Password, then save and test again.') from exc
        except smtplib.SMTPRecipientsRefused as exc:
            logger.exception('SMTP refused all recipients.')
            raise EmailDeliveryError('SMTP refused the recipient email address.') from exc
        except smtplib.SMTPSenderRefused as exc:
            logger.exception('SMTP refused configured sender address.')
            raise EmailDeliveryError('SMTP refused the configured sender email address.') from exc
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, smtplib.SMTPHeloError, socket.timeout, TimeoutError, OSError) as exc:
            logger.exception('SMTP connection failed for configured email account.')
            raise EmailDeliveryError('Could not connect to Gmail SMTP. Check host, port, TLS and network connectivity.') from exc
        except Exception as exc:
            logger.exception('Unexpected email delivery failure.')
            raise EmailDeliveryError(f'Email sending failed: {exc}') from exc
