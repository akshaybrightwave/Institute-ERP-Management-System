import os
import sys
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from django.test import Client
from apps.accounts.models import User

c = Client(SERVER_NAME='127.0.0.1')
users = {'SUPER_ADMIN': 'superadmin@gmail.com', 'ADMIN': 'admin@123', 'COUNSELOR': 'counselor@123', 'TELECALLER': 'telecaller@123'}

for role, email in users.items():
    user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
    if user:
        c.force_login(user)
        start = time.time()
        url = '/management/super-admin/dashboard/'
        if role == 'ADMIN': url = '/management/admin/dashboard/'
        if role == 'COUNSELOR': url = '/management/counselor/dashboard/'
        if role == 'TELECALLER': url = '/management/telecaller/dashboard/'
        
        resp = c.get(url)
        end = time.time()
        print(f'{role} ({url}): Status {resp.status_code}, Time: {end - start:.2f}s')
    else:
        print(f'User {email} not found')
