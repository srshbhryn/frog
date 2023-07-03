import dataclasses


@dataclasses.dataclass(slots=True)
class Interpolation:
    alpha: float
    beta: float
    long_price_zero: float
    short_price_zero: float
