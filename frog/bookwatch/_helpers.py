import typing

from frog.types import Pair

from .types import Book


BookHash = typing.NewType('BookHash', tuple[int, int])

def translate_asset_name(pair: Pair) -> str:
    base = pair.base.name
    quote = pair.quote.name
    if quote == 'RLS':
        quote = 'IRT'
    return base + quote


class BookStore:
    def __init__(self) -> None:
        self._pair_to_hash_map: dict[Pair, BookHash] = {}

    def is_a_new_book(self, pair: Pair, book: Book) -> bool:
        old_book_hash = self._pair_to_hash_map.get(pair)
        new_book_hash = self._get_book_hash(book)
        if old_book_hash == new_book_hash:
            return False
        self._pair_to_hash_map[pair] = new_book_hash
        return True

    def _get_book_hash(self, book: Book) -> BookHash:
        return BookHash((hash(tuple(book.asks)), hash(tuple(book.bids))))
