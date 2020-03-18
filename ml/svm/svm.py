import numpy as np
import qpsolvers
from qpsolvers import solve_qp
from scipy.optimize import minimize

from ml.learning import Learner
from ml.svm.kernels import rbf_kernel, linear_kernel, polynomial_kernel, sigmoid_kernel
from optimization.optimization_function import Lagrangian


def scipy_solve_qp(f, G, h, max_iter, verbose):
    return minimize(fun=f.function, jac=f.jacobian, x0=np.random.rand(f.n),
                    constraints=({'type': 'ineq',
                                  'fun': lambda x: h - np.dot(G, x),
                                  'jac': lambda x: -G}),
                    options={'maxiter': max_iter,
                             'disp': verbose}).x


class SVM(Learner):
    def __init__(self, kernel=rbf_kernel, degree=3., gamma='scale', C=1.):
        if kernel not in (linear_kernel, polynomial_kernel, rbf_kernel, sigmoid_kernel):
            raise ValueError('unknown kernel function {}'.format(kernel))
        self.kernel = kernel
        self.degree = degree
        if gamma not in ('scale', 'auto'):
            raise ValueError('unknown gamma type {}'.format(gamma))
        self.gamma = gamma
        self.C = C
        self.n_sv = -1
        self.sv_idx = np.zeros(0)
        self.sv = np.zeros(0)
        self.w = None
        self.b = 0.

    def fit(self, X, y, optimizer=solve_qp, max_iter=1000):
        raise NotImplementedError


class SVC(SVM):
    def __init__(self, kernel=rbf_kernel, degree=3., gamma='scale', C=1.):
        super().__init__(kernel, degree, gamma, C)
        self.sv_y = np.zeros(0)
        self.alphas = np.zeros(0)

    def fit(self, X, y, optimizer=solve_qp, max_iter=1000, verbose=False):
        """
        Trains the model by solving a constrained quadratic programming problem.
        :param X: array of size [n_samples, n_features] holding the training samples
        :param y: array of size [n_samples] holding the class labels
        :param optimizer:
        :param max_iter:
        :param verbose:
        """
        self.labels = np.unique(y)
        y = np.where(y == self.labels[0], -1, 1)

        m = len(y)  # m = n_samples
        K = (self.kernel(X, X, self.C, self.degree)
             if self.kernel is polynomial_kernel else
             self.kernel(X, X, self.gamma)
             if self.kernel is rbf_kernel else
             self.kernel(X, X, self.C, self.gamma)
             if self.kernel is sigmoid_kernel else
             self.kernel(X, X))  # linear kernel
        P = K * np.outer(y, y)
        P = (P + P.T) / 2  # ensure P is symmetric
        q = -np.ones(m)

        G = np.vstack((-np.identity(m), np.identity(m)))  # inequality matrix
        lb = np.zeros(m)  # lower bounds
        ub = np.ones(m) * self.C  # upper bounds
        h = np.hstack((lb, ub))  # inequality vector

        A = y.astype(np.float)  # equality matrix
        b = np.zeros(1)  # equality vector

        # we'd like to minimize the negative of the Lagrangian dual function subject to linear constraints:
        # inequalities Gx <= h (A is m x n, where m = 2n is the number of inequalities
        # (n box constraints, 2 inequalities each)
        # equalities Ax = b (these's only one equality constraint, i.e. y.T.dot(x) = 0)
        obj = Lagrangian(P, np.ones_like(q), A, b.item())
        if optimizer is solve_qp:
            qpsolvers.cvxopt_.options['show_progress'] = verbose
        self.alphas = (scipy_solve_qp(obj, G, h, max_iter, verbose) if optimizer is scipy_solve_qp else
                       solve_qp(P, q, G, h, A, b, solver='cvxopt') if optimizer is solve_qp else
                       optimizer(obj, max_iter=max_iter, verbose=verbose).minimize(ub)[0])

        self.sv_idx = np.argwhere(self.alphas > 1e-5).ravel()
        self.sv, self.sv_y, self.alphas = X[self.sv_idx], y[self.sv_idx], self.alphas[self.sv_idx]
        self.n_sv = len(self.alphas)

        if self.kernel is linear_kernel:
            self.w = np.dot(self.alphas * self.sv_y, self.sv)

        self.b = np.mean(self.sv_y - np.dot(self.alphas * self.sv_y,
                                            self.kernel(self.sv, self.sv, self.C, self.degree)
                                            if self.kernel is polynomial_kernel else
                                            self.kernel(self.sv, self.sv, self.gamma)
                                            if self.kernel is rbf_kernel else
                                            self.kernel(self.sv, self.sv, self.C, self.gamma)
                                            if self.kernel is sigmoid_kernel else
                                            self.kernel(self.sv, self.sv)))  # linear kernel
        return self

    def predict_score(self, X):
        """
        Predicts the score for a given example.
        """
        if self.kernel is not linear_kernel:
            return np.dot(self.alphas * self.sv_y,
                          self.kernel(self.sv, X, self.C, self.degree)
                          if self.kernel is polynomial_kernel else
                          self.kernel(self.sv, X, self.gamma)
                          if self.kernel is rbf_kernel else
                          self.kernel(self.sv, X, self.C, self.gamma)) + self.b  # sigmoid kernel
        return np.dot(X, self.w) + self.b

    def predict(self, X):
        """
        Predicts the class of a given example.
        """
        return np.where(self.predict_score(X) >= 0, self.labels[1], self.labels[0])


class SVR(SVM):
    def __init__(self, kernel=rbf_kernel, degree=3., gamma='scale', C=1., eps=0.1):
        super().__init__(kernel, degree, gamma, C)
        self.eps = eps
        self.alphas_p = np.zeros(0)
        self.alphas_n = np.zeros(0)

    def fit(self, X, y, optimizer=solve_qp, max_iter=1000, verbose=False):
        """
        Trains the model by solving a constrained quadratic programming problem.
        :param X: array of size [n_samples, n_features] holding the training samples
        :param y: array of size [n_samples] holding the class labels
        :param optimizer:
        :param max_iter:
        :param verbose:
        """
        m = len(y)  # m = n_samples
        K = (self.kernel(X, X, self.C, self.degree)
             if self.kernel is polynomial_kernel else
             self.kernel(X, X, self.gamma)
             if self.kernel is rbf_kernel else
             self.kernel(X, X, self.C, self.gamma)
             if self.kernel is sigmoid_kernel else
             self.kernel(X, X))  # linear kernel
        P = np.vstack((np.hstack((K, -K)),  # alphas_p, alphas_n
                       np.hstack((-K, K))))  # alphas_n, alphas_p
        P = (P + P.T) / 2  # ensure P is symmetric
        q = np.hstack((-y, y)) + self.eps

        G = np.vstack((-np.identity(2 * m), np.identity(2 * m)))  # inequality matrix
        lb = np.zeros(2 * m)  # lower bounds
        ub = np.ones(2 * m) * self.C  # upper bounds
        h = np.hstack((lb, ub))  # inequality vector

        A = np.hstack((np.ones(m), -np.ones(m)))  # equality matrix
        b = np.zeros(1)  # equality vector

        # we'd like to minimize the negative of the Lagrangian dual function subject to linear constraints:
        # inequalities Gx <= h (A is m x n, where m = 2n is the number of inequalities
        # (n box constraints, 2 inequalities each)
        # equalities Ax = b (these's only one equality constraint, i.e. x.T.dot(x) = 0)
        obj = Lagrangian(P, np.ones_like(q), A, b.item())
        if optimizer is solve_qp:
            qpsolvers.cvxopt_.options['show_progress'] = verbose
        alphas = (scipy_solve_qp(obj, G, h, max_iter, verbose) if optimizer is scipy_solve_qp else
                  solve_qp(P, q, G, h, A, b, solver='cvxopt') if optimizer is solve_qp else
                  optimizer(obj, max_iter=max_iter, verbose=verbose).minimize(ub)[0])
        self.alphas_p = alphas[:m]
        self.alphas_n = alphas[m:]

        self.sv_idx = np.argwhere(alphas > 1e-5).ravel()
        self.sv, alphas = X, alphas[self.sv_idx]
        self.n_sv = len(alphas)

        if self.kernel is linear_kernel:
            self.w = np.dot(self.alphas_p - self.alphas_n, X)

        self.b = np.mean(y - self.eps - np.dot(self.alphas_p - self.alphas_n,
                                               self.kernel(self.sv, X, self.C, self.degree)
                                               if self.kernel is polynomial_kernel else
                                               self.kernel(self.sv, X, self.gamma)
                                               if self.kernel is rbf_kernel else
                                               self.kernel(self.sv, X, self.C, self.gamma)
                                               if self.kernel is sigmoid_kernel else
                                               self.kernel(self.sv, X)))  # linear kernel
        return self

    def predict(self, X):
        """
        Predicts the score of a given example.
        """
        if self.kernel is not linear_kernel:
            return np.dot(self.alphas_p - self.alphas_n,
                          self.kernel(self.sv, X, self.C, self.degree)
                          if self.kernel is polynomial_kernel else
                          self.kernel(self.sv, X, self.gamma)
                          if self.kernel is rbf_kernel else
                          self.kernel(self.sv, X, self.C, self.gamma)) + self.b  # sigmoid kernel

        return np.dot(X, self.w) + self.b
