with open('SVEX_APP/templates/SVEX_APP/register.html', 'r') as f:
    content = f.read()

# Replace all the dark mode css with light mode
replacements = {
    'color: #ffffff;': 'color: #0f172a;',
    'color: #e0e0e0;': 'color: #334155;',
    'background: #2a2a2a;': 'background: #ffffff;',
    'border: 1px solid #3a3a3a;': 'border: 1px solid #cbd5e1;',
    'background: #333333;': 'background: #f8fafc;',
    'background: #2a1a1a;': 'background: #fef2f2;',
    'background: #1a2a1a;': 'background: #ecfdf5;',
    'color: #e0e0e0': 'color: #334155'
}

for old, new in replacements.items():
    content = content.replace(old, new)

# add background to register card if it's missing
content = content.replace('.register-card {\n        \n        border-radius: 12px;', '.register-card {\n        background: #ffffff;\n        border-radius: 12px;')

with open('SVEX_APP/templates/SVEX_APP/register.html', 'w') as f:
    f.write(content)
