import decimal

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore


def get_alpha_and_beta(
    first_series: list[decimal.Decimal],
    second_series: list[decimal.Decimal],
) -> tuple[decimal.Decimal, decimal.Decimal]:
    regression = LinearRegression().fit(
        np.array([[1, p] for p in second_series]),
        np.array(first_series),
    )
    alpha = decimal.Decimal(regression.predict([[1, 0]])[0])
    beta = decimal.Decimal(regression.predict([[1, 1]])[0]) - alpha
    return alpha, beta
