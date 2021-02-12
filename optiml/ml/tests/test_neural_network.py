import numpy as np
import pytest
from sklearn.datasets import load_iris, load_boston
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder

from optiml.ml.neural_network import NeuralNetworkRegressor, NeuralNetworkClassifier
from optiml.ml.neural_network.activations import sigmoid, softmax, linear, relu
from optiml.ml.neural_network.layers import FullyConnected
from optiml.ml.neural_network.losses import mean_squared_error, mean_absolute_error, categorical_cross_entropy
from optiml.ml.neural_network.regularizers import L2
from optiml.opti.unconstrained import ProximalBundle
from optiml.opti.unconstrained.line_search import BFGS
from optiml.opti.unconstrained.stochastic import Adam


def test_perceptron_regressor_with_line_search_optimizer():
    # aka linear regression
    X, y = load_boston(return_X_y=True)
    net = NeuralNetworkRegressor((FullyConnected(13, 1, linear, fit_intercept=False),),
                                 loss=mean_squared_error, optimizer=BFGS).fit(X, y)
    assert np.allclose(net.coefs_[0].ravel(), np.linalg.inv(X.T.dot(X)).dot(X.T).dot(y))


def test_perceptron_ridge_regressor_with_line_search_optimizer():
    # aka ridge regression
    X, y = load_boston(return_X_y=True)
    lmbda = 0.1
    net = NeuralNetworkRegressor((FullyConnected(13, 1, linear, coef_reg=L2(lmbda), fit_intercept=False),),
                                 loss=mean_squared_error, optimizer=BFGS).fit(X, y)
    assert np.allclose(net.coefs_[0].ravel(),
                       np.linalg.inv(X.T.dot(X) + np.identity(net.loss.ndim) * lmbda).dot(X.T).dot(y))


def test_neural_network_regressor_with_stochastic_optimizer():
    X, y = load_boston(return_X_y=True)
    X_scaled = StandardScaler().fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, train_size=0.75, random_state=1)
    net = NeuralNetworkRegressor((FullyConnected(13, 13, sigmoid),
                                  FullyConnected(13, 13, sigmoid),
                                  FullyConnected(13, 1, linear)),
                                 loss=mean_squared_error, optimizer=Adam, learning_rate=0.02)
    net.fit(X_train, y_train)
    assert net.score(X_test, y_test) >= 0.85


def test_neural_network_regressor_with_proximal_bundle_optimizer():
    X, y = load_boston(return_X_y=True)
    X_scaled = StandardScaler().fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, train_size=0.75, random_state=1)
    net = NeuralNetworkRegressor((FullyConnected(13, 13, relu),
                                  FullyConnected(13, 13, relu),
                                  FullyConnected(13, 1, linear)),
                                 loss=mean_absolute_error, optimizer=ProximalBundle, max_iter=100)
    net.fit(X_train, y_train)
    assert net.score(X_test, y_test) >= 0.85


def test_neural_network_classifier_with_stochastic_optimizer():
    X, y = load_iris(return_X_y=True)
    X_scaled = MinMaxScaler().fit_transform(X)
    ohe = OneHotEncoder(sparse=False).fit(y.reshape(-1, 1))
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, train_size=0.75, random_state=1)
    net = NeuralNetworkClassifier((FullyConnected(4, 4, sigmoid),
                                   FullyConnected(4, 4, sigmoid),
                                   FullyConnected(4, 3, softmax)),
                                  loss=categorical_cross_entropy, optimizer=Adam, learning_rate=0.01)
    net.fit(X_train, ohe.transform(y_train.reshape(-1, 1)))
    assert net.score(X_test, ohe.transform(y_test.reshape(-1, 1))) >= 0.95


def test_neural_network_classifier_with_proximal_bundle_optimizer():
    X, y = load_iris(return_X_y=True)
    X_scaled = MinMaxScaler().fit_transform(X)
    ohe = OneHotEncoder(sparse=False).fit(y.reshape(-1, 1))
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, train_size=0.75, random_state=1)
    net = NeuralNetworkClassifier((FullyConnected(4, 4, relu),
                                   FullyConnected(4, 4, relu),
                                   FullyConnected(4, 3, softmax)),
                                  loss=categorical_cross_entropy, optimizer=ProximalBundle, max_iter=100)
    net.fit(X_train, ohe.transform(y_train.reshape(-1, 1)))
    assert net.score(X_test, ohe.transform(y_test.reshape(-1, 1))) >= 0.95


if __name__ == "__main__":
    pytest.main()
