from decimal import Decimal
from .binance_api import get_crypto_prices


def crypto_prices(request):
    """
    Context processor to provide BTC and ETH prices from Binance API.
    Available in all templates as 'btc_price' and 'eth_price'.
    """
    prices = get_crypto_prices(timeout=4)
    return prices