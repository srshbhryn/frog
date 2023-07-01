
from frog.types import Config, State


class Core:
    def __init__(self, state: State, config: Config) -> None:
        self.state = state
        self.config = config

    def open_long(self, long_asset_price, short_asset_price):
        trading_quote = self.state.trader.available_quote() * self.config.usable_total_quote_rate
        long_asset_quote = trading_quote / (1 + self.config.beta)
        short_asset_quote = trading_quote * self.config.beta / (1 + self.config.beta)
        long_asset_amount = long_asset_quote / long_asset_price
        short_asset_amount = short_asset_quote / short_asset_price
        self.state.trader.open_long(self.config.long_symbol, long_asset_amount, long_asset_price)
        self.state.trader.open_short(self.config.short_symbol, short_asset_amount, short_asset_price)

    def open_short(self, long_asset_price, short_asset_price):
        trading_quote = self.state.trader.available_quote() * self.config.usable_total_quote_rate
        long_asset_quote = trading_quote / (1 + self.config.beta)
        short_asset_quote = trading_quote * self.config.beta / (1 + self.config.beta)
        long_asset_amount = long_asset_quote / long_asset_price
        short_asset_amount = short_asset_quote / short_asset_price
        self.state.trader.open_short(self.config.long_symbol, long_asset_amount, long_asset_price)
        self.state.trader.open_long(self.config.short_symbol, short_asset_amount, short_asset_price)

    def close_long(self, long_asset_price, short_asset_price):
        self.state.trader.close_all_long(self.config.long_symbol, long_asset_price)
        self.state.trader.close_all_short(self.config.short_symbol, short_asset_price)

    def close_short(self, long_asset_price, short_asset_price):
        self.state.trader.close_all_short(self.config.long_symbol, long_asset_price)
        self.state.trader.close_all_long(self.config.short_symbol, short_asset_price)
