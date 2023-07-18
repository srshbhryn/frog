from frog.types import Pair


def translate_asset_name(pair: Pair) -> str:
    base = pair.base.name
    quote = pair.quote.name
    if quote == 'RLS':
        quote = 'IRT'
    return base + quote
