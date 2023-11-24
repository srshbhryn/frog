from datetime import datetime
from typing import Optional

from frog.types import Pair, Price


class Oracle:
    def get_price(self, asset: Pair, timestamp: datetime) -> Optional[Price]:
        raise NotImplementedError
