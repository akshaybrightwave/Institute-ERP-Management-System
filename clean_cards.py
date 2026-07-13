import os

def clean_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Revert accidental replacements
    content = content.replace('style="cursor:pointer;" class="erp-card-', 'class="erp-card-')

    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Cleaned {file_path}")

base_dir = r"c:\Users\Eco_India\Desktop\Management_System\Institute-ERP-Management-System\apps\management\templates\management"
clean_file(os.path.join(base_dir, "counselor_dashboard.html"))
clean_file(os.path.join(base_dir, "telecaller_dashboard.html"))
clean_file(os.path.join(base_dir, "counselor_telecalling_dashboard.html"))

