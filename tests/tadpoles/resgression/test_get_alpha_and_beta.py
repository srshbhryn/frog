import numpy as np

from tadpoles.pairtrading.regression import linear_regression


def test_regression():
    alpha, beta = linear_regression(np.array([1, 2, 3]), np.array([8, 13, 18]))
    assert beta == 5 and alpha == 3
