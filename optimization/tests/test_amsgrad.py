import numpy as np
import pytest

from optimization.optimization_function import quad1, quad2, quad5, Rosenbrock
from optimization.unconstrained.amsgrad import AMSGrad


def test_AMSGrad_quadratic():
    x, _ = AMSGrad(quad1).minimize()
    np.allclose(x, quad1.x_star())

    x, _ = AMSGrad(quad2).minimize()
    np.allclose(x, quad2.x_star())

    x, _ = AMSGrad(quad5).minimize()
    np.allclose(x, quad5.x_star())


def test_AMSGrad_Rosenbrock():
    obj = Rosenbrock()
    x, _ = AMSGrad(obj, nesterov_momentum=True).minimize()
    assert np.allclose(x, obj.x_star(), rtol=0.1)


if __name__ == "__main__":
    pytest.main()