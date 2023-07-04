import decimal


class Config:
    alpha_open: float = .004
    alpha_close: float = .001
    long_symbol: str = 'btc-rls'
    short_symbol: str = 'eth-rls'
    beta: float = 1
    trading_quote: float = 500_000_0
    residual_length = 180

    @classmethod
    def long_order_value(cls):
        return decimal.Decimal(cls.trading_quote / (1 + cls.beta))

    @classmethod
    def short_order_value(cls):
        return decimal.Decimal(cls.trading_quote * cls.beta / (1 + cls.beta))


def load():
    pass
