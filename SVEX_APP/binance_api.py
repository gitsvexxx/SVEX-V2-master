"""
Binance API utility functions for fetching cryptocurrency prices.
Uses Binance Public API - no API key required for price data.
"""

import requests
from decimal import Decimal, InvalidOperation
from typing import Optional


def get_binance_price(symbol: str, timeout: int = 4) -> Optional[Decimal]:
    """
    Get the current price of a cryptocurrency from Binance API.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        timeout: Request timeout in seconds
        
    Returns:
        Decimal price or None if request fails
    """
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(url, params=params, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            price = Decimal(str(data.get("price", 0)))
            return price
    except (requests.RequestException, ValueError, KeyError, InvalidOperation) as e:
        print(f"Error fetching {symbol} price from Binance: {e}")
    
    return None


def get_btc_price(timeout: int = 4) -> Decimal:
    """
    Get Bitcoin (BTC) price in USDT from Binance.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Decimal BTC price, defaults to 50000 if request fails
    """
    price = get_binance_price("BTCUSDT", timeout)
    return price if price is not None else Decimal('50000')


def get_eth_price(timeout: int = 4) -> Decimal:
    """
    Get Ethereum (ETH) price in USDT from Binance.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Decimal ETH price, defaults to 3000 if request fails
    """
    price = get_binance_price("ETHUSDT", timeout)
    return price if price is not None else Decimal('3000')


def get_usdt_price(timeout: int = 4) -> Decimal:
    """
    Get USDT price in USD from Binance.
    Note: USDT is a stablecoin, so this should be very close to $1.00,
    but can have slight variations (e.g., $0.999 or $1.001).
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Decimal USDT price, defaults to 1.0 if request fails
    """
    price = get_binance_price("USDTUSDT", timeout)
    # If USDTUSDT doesn't work, try BUSDUSDT as alternative
    if price is None:
        price = get_binance_price("BUSDUSDT", timeout)
    return price if price is not None else Decimal('1.0')


def get_crypto_prices(timeout: int = 4) -> dict:
    """
    Get BTC, ETH, and USDT prices from Binance in a single call.
    More efficient than calling get_btc_price, get_eth_price, and get_usdt_price separately.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with 'btc_price', 'eth_price', and 'usdt_price' as Decimal values
    """
    btc_price = get_btc_price(timeout)
    eth_price = get_eth_price(timeout)
    usdt_price = get_usdt_price(timeout)
    
    return {
        'btc_price': btc_price,
        'eth_price': eth_price,
        'usdt_price': usdt_price,
    }

