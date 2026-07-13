import os
import glob

# Paths to search
search_apps = [
    'categories', 'courses', 'batches', 'centers', 'fees', 
    'attendance', 'certificates', 'reports', 'exams'
]

# We also need to include specific accounts templates that are part of the ERP (e.g. user_list)
# but maybe we should just replace across the listed apps first.

base_dir = r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal\apps'

count = 0

for app in search_apps:
    app_dir = os.path.join(base_dir, app, 'templates')
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if it extends base.html
                if "{% extends 'accounts/base.html' %}" in content:
                    # Update inheritance
                    content = content.replace("{% extends 'accounts/base.html' %}", "{% extends 'accounts/admin_dashboard.html' %}")
                    
                    # Update content block to erp_content
                    # We have to be careful with block content
                    # We'll replace the exact string to avoid issues, or use regex
                    content = content.replace("{% block content %}", "{% block erp_content %}")
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"Updated {file_path}")
                    count += 1

print(f"Total files updated: {count}")
