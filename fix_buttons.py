import os
import glob
import re

template_dir = 'SVEX_APP/templates/SVEX_APP'
html_files = glob.glob(os.path.join(template_dir, '**/*.html'), recursive=True)

for file in html_files:
    if 'base_manager.html' in file:
        continue
    with open(file, 'r') as f:
        content = f.read()
        
    # Revert color for btn-primary and similar buttons where it makes sense
    content = re.sub(r'(\.btn-primary\s*{[^}]*?color:\s*)#0f172a(.*?})', r'\1#ffffff\2', content, flags=re.DOTALL)
    content = re.sub(r'(background:\s*#3b82f6.*?color:\s*)#0f172a', r'\1#ffffff', content)
    content = re.sub(r'(background:\s*#4a9eff.*?color:\s*)#0f172a', r'\1#ffffff', content)
    content = re.sub(r'(background-color:\s*#3b82f6.*?color:\s*)#0f172a', r'\1#ffffff', content)

    with open(file, 'w') as f:
        f.write(content)
