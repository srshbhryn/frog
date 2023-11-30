import typing
import datetime

from frog.tradestore._django_setup import setup

if typing.TYPE_CHECKING:
    from frog.tradestore.db.models import Trade as FT

from tadpoles.prices.models import Trade
from tadpoles.timescaledb import db


def get_frog_trade_model():
    setup()
    from frog.tradestore.db.models import Trade

    return Trade


def convert(frog_trade: 'FT'):
    if frog_trade.pair[-4:] == 'usdt':
        base_asset = frog_trade.pair[:-4]
        quote_asset = 'usdt'
    else:
        base_asset = frog_trade.pair[:-3]
        quote_asset = 'rls'

    return Trade(
        base_asset=base_asset,
        quote_asset=quote_asset,
        exchange='nobitex',
        timestamp=datetime.datetime.fromtimestamp(
            frog_trade.time,
            tz=datetime.timezone(datetime.timedelta()),
        ),
        is_buyer_maker=frog_trade.is_buyer_maker,
        price=frog_trade.price,
        amount=frog_trade.amount,
    )


def main():
    frog_trade_model = get_frog_trade_model()
    batch_size = 10_000
    number_of_batches = int(frog_trade_model.objects.count() / batch_size) + 1
    for batch_number in range(number_of_batches):
        print(f'{datetime.datetime.now().isoformat()}\t{batch_number}\t{number_of_batches}')
        db.add_all(
            [
                convert(frog_trade)
                for frog_trade in frog_trade_model.objects.order_by('id')[
                    batch_number * batch_size : (batch_number + 1) * batch_size
                ]
            ]
        )
        db.commit()


if __name__ == '__main__':
    main()
