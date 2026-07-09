import os
import re

def fix_syntax_errors(root_dir):
    pattern = re.compile(r'\.not course\.assignments\.filter\(center=request\.user\.center, is_active=True\)\.exists\(\) and request\.user\.center != request\.user\.center')
    pattern2 = re.compile(r'\.not course\.assignments\.filter\(center=request\.user\.center, is_active=True\)\.exists\(\) and request\.user\.center != center')
    pattern3 = re.compile(r'\.not course\.assignments\.filter\(center=request\.user\.center, is_active=True\)\.exists\(\) and request\.user\.center != self\.user\.center')
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = pattern.sub('.center != request.user.center', content)
                new_content = pattern2.sub('.center != center', new_content)
                new_content = pattern3.sub('.center != self.user.center', new_content)

                if content != new_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed syntax errors in {filepath}")

fix_syntax_errors('c:/Users/Akshay/Desktop/Akshay/Django/Online-Examination-Portal/apps')
