import numpy as np
from sklearn.linear_model import LinearRegression


def get_residual(long_prices, short_prices) -> float:
    long_returns = [p / long_prices[0] for p in long_prices]
    short_returns = [p / short_prices[0] for p in short_prices]
    reg = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    return long_returns[-1] - reg.predict([[1, short_returns[-1]]])[0]
