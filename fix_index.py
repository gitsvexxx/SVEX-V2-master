import re

with open('SVEX_APP/templates/SVEX_APP/wallets/index.html', 'r') as f:
    content = f.read()

# Extract EUR block
eur_block_match = re.search(r'([ \t]*<!-- Spot Bitcoin -> EUR Account -->.*?</a>\n)', content, re.DOTALL)
if eur_block_match:
    eur_block = eur_block_match.group(1)
    # Remove from original location
    content = content.replace(eur_block, '')
    
    # Insert before Bitcoin (BTC)
    content = content.replace('<!-- Bitcoin (BTC) -->', eur_block + '\n        <!-- Bitcoin (BTC) -->')

with open('SVEX_APP/templates/SVEX_APP/wallets/index.html', 'w') as f:
    f.write(content)
