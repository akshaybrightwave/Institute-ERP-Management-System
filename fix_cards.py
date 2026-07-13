import os
import re

def update_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern to match a column containing a card with a footer link
    # We want to transform:
    # <div class="col">
    #   <div class="erp-card bg-g-xxx h-100">
    #     ...
    #     <a href="URL" class="erp-card-footer ...">
    #       ...
    #     </a>
    #   </div>
    # </div>
    # INTO:
    # <div class="col">
    #   <a href="URL" class="text-decoration-none">
    #   <div class="erp-card bg-g-xxx h-100" style="cursor:pointer;">
    #     ...
    #     <div class="erp-card-footer ...">
    #       ...
    #     </div>
    #   </div>
    #   </a>
    # </div>
    
    # We'll use a regex to capture the parts
    pattern = re.compile(
        r'(<div class="col">\s*)'
        r'(<div class="erp-card[^"]*"[^>]*>\s*'
        r'<div class="erp-card-body">.*?'
        r'</div>\s*)'
        r'<a (href="[^"]*")[^>]*class="(erp-card-footer[^"]*)"[^>]*>(.*?)</a>\s*'
        r'(</div>)',
        re.DOTALL
    )

    def repl(m):
        col_div = m.group(1)
        card_start = m.group(2)
        href = m.group(3)
        footer_class = m.group(4)
        footer_content = m.group(5)
        card_end = m.group(6)
        
        # Make the card a div with pointer cursor
        card_start = card_start.replace('class="erp-card', 'style="cursor:pointer;" class="erp-card')
        
        # Replace date filters for counselor_dashboard links if present
        href = href.replace('?assigned_date={% now \'Y-m-d\' %}', '')
        href = href.replace('&status_date={% now \'Y-m-d\' %}', '')
        
        # Update footer text for counselor_dashboard 
        footer_content = footer_content.replace('View today\'s', 'View all')
        
        return (
            f'{col_div}'
            f'<a {href} class="text-decoration-none">\n'
            f'      {card_start}'
            f'<div class="{footer_class}">{footer_content}</div>\n'
            f'    {card_end}\n'
            f'      </a>'
        )
        
    new_content = pattern.sub(repl, content)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated {file_path}")

base_dir = r"c:\Users\Eco_India\Desktop\Management_System\Institute-ERP-Management-System\apps\management\templates\management"
update_file(os.path.join(base_dir, "counselor_dashboard.html"))
update_file(os.path.join(base_dir, "telecaller_dashboard.html"))
update_file(os.path.join(base_dir, "counselor_telecalling_dashboard.html"))

