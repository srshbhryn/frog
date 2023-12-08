import decimal

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore


def get_alpha_and_beta(
    first_series: list[float],
    second_series: list[float],
) -> tuple[float, float]:
    regression = LinearRegression().fit(
        np.array([[1, p] for p in second_series]),
        np.array(first_series),
    )
    alpha = regression.predict([[1, 0]])[0]
    beta = regression.predict([[1, 1]])[0] - alpha
    return alpha, beta
