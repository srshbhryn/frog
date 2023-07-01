

class Config:
    alpha_open: float = .0011
    alpha_close: float = -.0001
    long_symbol: str = 'btc-rls'
    short_symbol: str = 'eth-rls'
    beta: float = 1
    usable_total_quote_rate: float = .2
    residual_length = 180


def load():
    pass
