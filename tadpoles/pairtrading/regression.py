import numpy as np
from scipy.stats import linregress
from typing import Tuple


def linear_regression(array1: np.ndarray, array2: np.ndarray) -> Tuple[float, float]:
    """
    Perform linear regression between two arrays.

    Parameters:
    - array1 (np.ndarray): First array.
    - array2 (np.ndarray): Second array.

    Returns:
    - Tuple[float, float]: Intercept (alpha) and slope (beta) of the linear regression.
    """
    # Check if arrays have the same shape
    if array1.shape != array2.shape:
        raise ValueError("The two arrays must have the same shape.")

    # Flatten arrays and drop NaN values
    flat_array1 = array1.flatten()
    flat_array2 = array2.flatten()
    mask = ~np.isnan(flat_array1) & ~np.isnan(flat_array2)

    # Perform linear regression
    slope, intercept, _, _, _ = linregress(flat_array1[mask], flat_array2[mask])

    return intercept, slope
