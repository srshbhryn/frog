from tadpoles.pairtrading.regression import get_alpha_and_beta


def test_regression():
    alpha, beta = get_alpha_and_beta([8, 13, 18], [1, 2, 3])
    assert abs(alpha - 3) < 1e-8, abs(beta - 5) < 1e-8
