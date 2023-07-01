

def get_nobitex_candle_symbol(symbol):
    return {
        'btc-rls': 'BTCIRT',
        'eth-rls': 'ETHIRT',
    }.get(symbol)
