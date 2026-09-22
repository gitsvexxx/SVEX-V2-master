import os
import glob
import re

template_dir = 'SVEX_APP/templates/SVEX_APP'
html_files = glob.glob(os.path.join(template_dir, '**/*.html'), recursive=True)

for file in html_files:
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove dark hover events
    content = re.sub(r'onmouseover="this\.style\.backgroundColor=\'#1a1a1a\'"', '', content)
    content = re.sub(r'onmouseout="this\.style\.backgroundColor=\'transparent\'"', '', content)
    content = re.sub(r'onmouseover="this\.style\.background=\'#404040\'"', '', content)
    content = re.sub(r'onmouseout="this\.style\.background=\'#262626\'"', '', content)
    
    # Remove the inline styles completely from the tr and tables to be 100% sure
    # Actually, let's just rip out the main offender: background: #0f0f0f, #1a1a1a, #262626
    content = content.replace('background: #0f0f0f;', '')
    content = content.replace('background: #1a1a1a;', '')
    content = content.replace('background: #262626;', '')
    content = content.replace('background-color: #1a1a1a;', '')
    content = content.replace('background-color: #0f0f0f;', '')
    content = content.replace('background-color: #262626;', '')
    
    with open(file, 'w') as f:
        f.write(content)
        
print("Hover scripts stripped!")
