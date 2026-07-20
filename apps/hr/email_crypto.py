import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class EmailPasswordCryptoError(Exception):
    pass


def normalize_app_password(raw_password):
    return ''.join((raw_password or '').split())


def _fernet():
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_app_password(raw_password):
    normalized_password = normalize_app_password(raw_password)
    if not normalized_password:
        raise EmailPasswordCryptoError('Google App Password is required.')
    return _fernet().encrypt(normalized_password.encode('utf-8')).decode('utf-8')


def decrypt_app_password(encrypted_password):
    if not encrypted_password:
        raise EmailPasswordCryptoError('Google App Password is missing.')
    try:
        return _fernet().decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    except InvalidToken as exc:
        raise EmailPasswordCryptoError('Stored Google App Password could not be decrypted.') from exc
