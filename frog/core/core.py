import logging
from ..config import  Config
from ..state import  State, Position


class Core:

    @staticmethod
    def open_long(long_asset_price, short_asset_price):
        logging.info(f'entering long')
        long_asset_amount = Config.long_order_value() / long_asset_price
        short_asset_amount = Config.short_order_value() / short_asset_price
        State.trader.open_long(Config.long_symbol, long_asset_amount, long_asset_price)
        State.trader.open_short(Config.short_symbol, short_asset_amount, short_asset_price)
        State.position = Position.LONG

    @staticmethod
    def open_short(long_asset_price, short_asset_price):
        logging.info(f'entering short')
        long_asset_amount = Config.long_order_value() / long_asset_price
        short_asset_amount = Config.short_order_value() / short_asset_price
        State.trader.open_short(Config.long_symbol, long_asset_amount, long_asset_price)
        State.trader.open_long(Config.short_symbol, short_asset_amount, short_asset_price)
        State.position = Position.SHORT

    @staticmethod
    def close_long(long_asset_price, short_asset_price):
        logging.info('exiting long')
        State.trader.close_all_long(Config.long_symbol, long_asset_price)
        State.trader.close_all_short(Config.short_symbol, short_asset_price)
        State.position = Position.CLOSE

    @staticmethod
    def close_short(long_asset_price, short_asset_price):
        logging.info('exiting short')
        State.trader.close_all_short(Config.long_symbol, long_asset_price)
        State.trader.close_all_long(Config.short_symbol, short_asset_price)
        State.position = Position.CLOSE
