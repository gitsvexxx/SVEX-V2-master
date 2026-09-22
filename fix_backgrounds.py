import os
import glob

template_dir = 'SVEX_APP/templates/SVEX_APP'
html_files = glob.glob(os.path.join(template_dir, '**/*.html'), recursive=True)

for file in html_files:
    if 'reclamation_mockup' in file or 'base_manager.html' in file:
        continue
        
    with open(file, 'r') as f:
        content = f.read()
        
    # ONLY revert accidental background and border replacements
    content = content.replace('background-color: #0f172a', 'background-color: #ffffff')
    content = content.replace('background: #0f172a', 'background: #ffffff')
    content = content.replace('border-color: #0f172a', 'border-color: #ffffff')
    content = content.replace('border: 1px solid #0f172a', 'border: 1px solid #ffffff')
    
    with open(file, 'w') as f:
        f.write(content)
        
print("Accidental backgrounds fixed properly.")
