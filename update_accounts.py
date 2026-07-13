import os

files = [
    r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal\apps\accounts\templates\accounts\user_list.html',
    r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal\apps\accounts\templates\accounts\user_add.html',
    r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal\apps\accounts\templates\accounts\user_edit.html'
]

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace("{% extends 'accounts/base.html' %}", "{% extends 'accounts/admin_dashboard.html' %}")
    content = content.replace("{% block content %}", "{% block erp_content %}")
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f'Updated {f}')
