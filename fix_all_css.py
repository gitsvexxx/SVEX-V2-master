import os
import glob
import re

template_dir = 'SVEX_APP/templates/SVEX_APP'
html_files = glob.glob(os.path.join(template_dir, '**/*.html'), recursive=True)

# Replace all common dark CSS colors with light Tailwind colors
replacements = {
    # Backgrounds
    'background: #2a2a2a': 'background: #ffffff',
    'background-color: #2a2a2a': 'background-color: #ffffff',
    'background: #1a1a1a': 'background: #ffffff',
    'background-color: #1a1a1a': 'background-color: #ffffff',
    'background: #0f0f0f': 'background: #f8fafc',
    'background-color: #0f0f0f': 'background-color: #f8fafc',
    'background: #262626': 'background: #f1f5f9',
    'background-color: #262626': 'background-color: #f1f5f9',
    'background: #333333': 'background: #f8fafc',
    'background-color: #333333': 'background-color: #f8fafc',
    'background: #3a3a3a': 'background: #e2e8f0',
    'background-color: #3a3a3a': 'background-color: #e2e8f0',
    'background: #404040': 'background: #e2e8f0',
    'background-color: #404040': 'background-color: #e2e8f0',
    
    # Text colors
    'color: #ffffff': 'color: #0f172a',
    'color: #e5e5e5': 'color: #1e293b',
    'color: #e0e0e0': 'color: #334155',
    'color: #d4d4d4': 'color: #334155',
    'color: #a3a3a3': 'color: #475569',
    'color: #888888': 'color: #64748b',
    'color: #737373': 'color: #64748b',
    'color: white': 'color: #0f172a',
    
    # Borders
    'border: 1px solid #3a3a3a': 'border: 1px solid #cbd5e1',
    'border: 1px solid #404040': 'border: 1px solid #cbd5e1',
    'border: 1px solid #333333': 'border: 1px solid #e2e8f0',
    'border-color: #3a3a3a': 'border-color: #cbd5e1',
    'border-bottom: 2px solid #3a3a3a': 'border-bottom: 2px solid #cbd5e1',
    'border-bottom: 1px solid #2a2a2a': 'border-bottom: 1px solid #e2e8f0',
    
    # Forms
    'color: #fff;': 'color: #0f172a;',
}

for file in html_files:
    # Don't touch the dark sidebar styles in base_manager
    if 'base_manager.html' in file:
        continue
        
    with open(file, 'r') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    # Also fix some regex patterns
    content = re.sub(r'background:\s*#1a1a1a;?', 'background: #ffffff;', content)
    
    with open(file, 'w') as f:
        f.write(content)
        
print("All templates converted to light mode.")
