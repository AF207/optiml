import pytest

from optimization.optimization_function import quad1, quad2, Rosenbrock
from optimization.unconstrained.line_search.steepest_gradient_descent import *
from optimization.unconstrained.stochastic.stochastic_gradient_descent import StochasticGradientDescent


def test_QuadraticSteepestGradientDescent():
    assert np.allclose(QuadraticSteepestGradientDescent(quad1).minimize()[0], quad1.x_star())
    assert np.allclose(QuadraticSteepestGradientDescent(quad2).minimize()[0], quad2.x_star())


def test_SteepestGradientDescent_quadratic():
    assert np.allclose(SteepestGradientDescent(quad1).minimize()[0], quad1.x_star())
    assert np.allclose(SteepestGradientDescent(quad2).minimize()[0], quad2.x_star())


def test_SteepestGradientDescent_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(SteepestGradientDescent(obj).minimize()[0], obj.x_star())


def test_GradientDescent_quadratic():
    assert np.allclose(StochasticGradientDescent(quad1).minimize()[0], quad1.x_star())
    assert np.allclose(StochasticGradientDescent(quad2).minimize()[0], quad2.x_star())


def test_GradientDescent_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(StochasticGradientDescent(obj).minimize()[0], obj.x_star(), rtol=0.1)


def test_GradientDescent_standard_momentum_quadratic():
    assert np.allclose(StochasticGradientDescent(quad1, momentum_type='standard').minimize()[0], quad1.x_star())
    assert np.allclose(StochasticGradientDescent(quad2, momentum_type='standard').minimize()[0], quad2.x_star())


def test_GradientDescent_standard_momentum_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(StochasticGradientDescent(obj, momentum_type='standard').minimize()[0], obj.x_star())


def test_GradientDescent_Nesterov_momentum_quadratic():
    assert np.allclose(StochasticGradientDescent(quad1, momentum_type='nesterov').minimize()[0], quad1.x_star())
    assert np.allclose(StochasticGradientDescent(quad2, momentum_type='nesterov').minimize()[0], quad2.x_star())


def test_GradientDescent_Nesterov_momentum_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(StochasticGradientDescent(obj, momentum_type='nesterov').minimize()[0], obj.x_star())


if __name__ == "__main__":
    pytest.main()
