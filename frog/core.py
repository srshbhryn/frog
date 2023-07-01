import logging
from .config import  Config
from .state import  State


class Core:

    @staticmethod
    def open_long(long_asset_price, short_asset_price):
        logging.info(f'entering long')
        trading_quote = State.trader.available_quote() * Config.usable_total_quote_rate
        long_asset_quote = trading_quote / (1 + Config.beta)
        short_asset_quote = trading_quote * Config.beta / (1 + Config.beta)
        long_asset_amount = long_asset_quote / long_asset_price
        short_asset_amount = short_asset_quote / short_asset_price
        State.trader.open_long(Config.long_symbol, long_asset_amount, long_asset_price)
        State.trader.open_short(Config.short_symbol, short_asset_amount, short_asset_price)

    @staticmethod
    def open_short(long_asset_price, short_asset_price):
        logging.info(f'entering short')
        trading_quote = State.trader.available_quote() * Config.usable_total_quote_rate
        long_asset_quote = trading_quote / (1 + Config.beta)
        short_asset_quote = trading_quote * Config.beta / (1 + Config.beta)
        long_asset_amount = long_asset_quote / long_asset_price
        short_asset_amount = short_asset_quote / short_asset_price
        State.trader.open_short(Config.long_symbol, long_asset_amount, long_asset_price)
        State.trader.open_long(Config.short_symbol, short_asset_amount, short_asset_price)

    @staticmethod
    def close_long(long_asset_price, short_asset_price):
        logging.info('exiting long')
        State.trader.close_all_long(Config.long_symbol, long_asset_price)
        State.trader.close_all_short(Config.short_symbol, short_asset_price)

    @staticmethod
    def close_short(long_asset_price, short_asset_price):
        logging.info('exiting short')
        State.trader.close_all_short(Config.long_symbol, long_asset_price)
        State.trader.close_all_long(Config.short_symbol, short_asset_price)
