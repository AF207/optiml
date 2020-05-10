import numpy as np
import pytest

from yase.optimization.optimizer import quad1, quad2, Rosenbrock
from yase.optimization.unconstrained.line_search import Newton


def test_quadratic():
    assert np.allclose(Newton(f=quad1, x=np.random.uniform(size=2)).minimize()[0], quad1.x_star())
    assert np.allclose(Newton(f=quad2, x=np.random.uniform(size=2)).minimize()[0], quad2.x_star())


def test_Rosenbrock():
    rosen = Rosenbrock()
    assert np.allclose(Newton(f=rosen, x=np.random.uniform(size=2)).minimize()[0], rosen.x_star())


if __name__ == "__main__":
    pytest.main()