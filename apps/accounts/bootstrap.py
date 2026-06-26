from django.conf import settings
from django.db import transaction
from django.db.models import Q

from .models import AuthActivityLog, User


def parse_owner_config():
    owner_path = settings.BASE_DIR / 'owner.md'
    if not owner_path.exists():
        return {}

    config = {}
    for raw_line in owner_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        config[key.strip()] = value.strip()
    return config


def bootstrap_default_super_admin():
    config = parse_owner_config()
    email = config.get('SUPER_ADMIN_EMAIL')
    password = config.get('SUPER_ADMIN_PASSWORD')
    owner_name = config.get('OWNER_NAME', 'System Owner')
    role = config.get('ROLE', 'SUPER_ADMIN')

    if role != 'SUPER_ADMIN' or not email or not password:
        return None

    if User.all_objects.filter(role='SUPER_ADMIN').exists():
        return None

    with transaction.atomic():
        user = User.all_objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email)
        ).first()

        if user:
            user.username = email
            user.email = email
            user.first_name = owner_name
            user.role = 'SUPER_ADMIN'
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
        else:
            user = User.all_objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=owner_name,
                role='SUPER_ADMIN',
                is_staff=True,
                is_superuser=True,
            )

        AuthActivityLog.objects.create(
            user=user,
            username=email,
            event_type='BOOTSTRAP_SUPER_ADMIN',
            details='Default Super Admin bootstrapped from owner.md.',
        )
        return user


def bootstrap_super_admin_after_migrate(**kwargs):
    bootstrap_default_super_admin()
