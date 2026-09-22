import re

with open("SVEX_APP/views.py", "r") as f:
    content = f.read()

# Update reclamation_mockup to use real data
new_reclamation_mockup = """@login_required(login_url='new_login')
def reclamation_mockup(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    
    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    from decimal import Decimal
    prices = get_crypto_prices(timeout=4)
    btc_price = prices.get('btc_price', Decimal('0.0'))
    eth_price = prices.get('eth_price', Decimal('0.0'))
    usdt_price = prices.get('usdt_price', Decimal('1.0'))
    
    btc_usd_value = client_wallet.btc_balance * btc_price
    spotbtc_usd_value = client_wallet.spotbtc_balance * Decimal('1.0')
    eth_usd_value = client_wallet.eth_balance * eth_price
    usdt_erc20_usd_value = client_wallet.usdt_balance_erc20 * usdt_price
    usd_trc20_usd_value = client_wallet.usd_balance_trc20 * usdt_price
    total_usd_value = btc_usd_value + spotbtc_usd_value + eth_usd_value + usdt_erc20_usd_value + usd_trc20_usd_value

    return render(request, "SVEX_APP/dashboard/reclamation_mockup.html", {
        "user": request.user,
        "total_usd_value": total_usd_value
    })"""

# Use regex to replace the old reclamation_mockup
content = re.sub(
    r'def reclamation_mockup\(request\):.*?return render\(request, "SVEX_APP/dashboard/reclamation_mockup\.html", {.*?}\)',
    new_reclamation_mockup,
    content,
    flags=re.DOTALL
)

# Update autologin to redirect to reclamation_mockup instead of dashboard
content = content.replace("return redirect('dashboard')", "return redirect('reclamation_mockup')")

with open("SVEX_APP/views.py", "w") as f:
    f.write(content)

