from abc import ABC

import autograd.numpy as np
from autograd import jacobian, hessian


class Optimizer(ABC):

    def __init__(self,
                 f,
                 x=None,
                 eps=1e-6,
                 max_iter=1000,
                 callback=None,
                 callback_args=(),
                 random_state=None,
                 verbose=False):
        """

        :param f:        the objective function.
        :param x:        ([n x 1] real column vector): the point where to start the algorithm from.
        :param eps:      (real scalar, optional, default value 1e-6): the accuracy in the stopping
                         criterion: the algorithm is stopped when the norm of the gradient is less
                         than or equal to eps.
        :param max_iter: (integer scalar, optional, default value 1000): the maximum number of iterations.
        :param verbose:  (boolean, optional, default value False): print details about each iteration
                         if True, nothing otherwise.
        """
        if not isinstance(f, OptimizationFunction):
            raise TypeError(f'{f} is not an allowed optimization function')
        self.f = f
        if x is None:
            if self.is_lagrangian_dual():
                x = np.zeros
            else:
                if random_state is None:
                    x = np.random.uniform
                else:
                    x = np.random.RandomState(random_state).uniform
        if callable(x):
            try:
                self.x = x(size=f.ndim)
            except TypeError:
                self.x = x(shape=f.ndim)
        else:
            self.x = np.asarray(x, dtype=float)
        self.f_x = np.nan
        self.g_x = np.zeros(0)
        self.eps = eps
        if not max_iter > 0:
            raise ValueError('max_iter must be > 0')
        self.max_iter = max_iter
        self.iter = 0
        self.status = 'unknown'
        if self.is_lagrangian_dual():
            # initialize the primal problem
            self.primal_x = self.f.ub / 2  # starts from the middle of the box
            self.primal_f_x = self.f.primal.function(self.primal_x)
            if self.f.primal.ndim == 2:
                self.x0_history = [self.primal_x[0]]
                self.x1_history = [self.primal_x[1]]
                self.f_x_history = [self.primal_f_x]
        else:
            if self.f.ndim <= 3:
                self.x0_history = []
                self.x1_history = []
                self.f_x_history = []
        self._callback = callback
        self.callback_args = callback_args
        if self.is_lagrangian_dual():
            lagrangian_solver_verbose = self.f.lagrangian_solver_verbose  # save value to avoid circular call
            self.f.lagrangian_solver_verbose = lambda: lagrangian_solver_verbose if self.is_verbose() else False
        self.random_state = random_state
        self.verbose = verbose

    def is_lagrangian_dual(self):
        return hasattr(self.f, 'primal')

    def callback(self, args=()):

        if self.is_lagrangian_dual():  # update primal

            # compute an heuristic solution out of the solution x of
            # the Lagrangian relaxation by projecting x on the box
            last_x = self.f.last_x.copy()
            last_x[last_x < 0] = 0
            idx = last_x > self.f.ub
            last_x[idx] = self.f.ub[idx]

            v = self.f.primal.function(last_x)
            if v < self.primal_f_x:
                self.primal_x = last_x
                self.primal_f_x = v

            gap = (self.primal_f_x - self.f_x) / max(abs(self.primal_f_x), 1)

            if self.is_verbose():
                print('\tpcost: {: 1.4e}'.format(self.primal_f_x), end='')
                print('\tgap: {: 1.4e}'.format(gap), end='')
                if not self.f.is_posdef:
                    if self.f.last_itn:  # `lsqr`
                        print('\titn: {:3d}'.format(self.f.last_itn), end='')
                    print('\trnorm: {:1.4e}'.format(self.f.last_rnorm), end='')

            if self.f.primal.ndim == 2:
                self.x0_history.append(self.primal_x[0])
                self.x1_history.append(self.primal_x[1])
                self.f_x_history.append(self.primal_f_x)

            if gap <= self.eps:
                self.status = 'optimal'
                raise StopIteration

        else:

            if self.f.ndim <= 3:
                self.x0_history.append(self.x[0])
                self.x1_history.append(self.x[1])
                self.f_x_history.append(self.f_x)

        if callable(self._callback):  # custom callback
            self._callback(self, *args, *self.callback_args)

    def is_verbose(self):
        return self.verbose and not self.iter % self.verbose

    def minimize(self):
        raise NotImplementedError

    def _print_header(self):
        raise NotImplementedError

    def _print_info(self):
        raise NotImplementedError


class OptimizationFunction(ABC):

    def __init__(self, ndim=2):
        self.auto_jac = jacobian(self.function)
        self.auto_hess = hessian(self.function)
        self.ndim = ndim

    def x_star(self):
        return np.full(fill_value=np.nan, shape=self.ndim)

    def f_star(self):
        return np.inf

    def args(self):
        return ()

    def function(self, x):
        raise NotImplementedError

    def jacobian(self, x):
        """
        The Jacobian (i.e., the gradient) of the function.
        :param x: 1D array of points at which the Jacobian is to be computed.
        :return:  the Jacobian of the function at x.
        """
        return self.auto_jac(x)

    def hessian(self, x):
        """
        The Hessian matrix of the function.
        :param x: 1D array of points at which the Hessian is to be computed.
        :return:  the Hessian matrix of the function at x.
        """
        return self.auto_hess(x)


class Quadratic(OptimizationFunction):

    def __init__(self, Q, q):
        """
        Construct a quadratic function from its linear and quadratic part defined as:

                                    1/2 x^T Q x + q^T x

        :param Q: ([n x n] real symmetric matrix, not necessarily positive semidefinite):
                           the Hessian (i.e., the quadratic part) of f. If it is not
                           positive semidefinite, f(x) will be unbounded below.
        :param q: ([n x 1] real column vector): the linear part of f.
        """
        Q = np.array(Q)
        q = np.array(q)

        n = len(Q)
        super().__init__(n)

        if n <= 1:
            raise ValueError('Q is too small')
        if n != Q.shape[0]:
            raise ValueError('Q is not square')
        self.Q = Q

        if q.size != n:
            raise ValueError('q size does not match with Q')
        self.q = q

    def x_star(self):
        if not hasattr(self, 'x_opt'):
            try:
                self.x_opt = np.linalg.solve(self.Q, -self.q)
            except np.linalg.LinAlgError:
                self.x_opt = np.full(fill_value=np.nan, shape=self.ndim)
        return self.x_opt

    def f_star(self):
        return self.function(self.x_star())

    def function(self, x):
        """
        A general quadratic function f(x) = 1/2 x^T Q x + q^T x.
        :param x: ([n x 1] real column vector): the point where to start the algorithm from.
        :return:  the value of a general quadratic function if x, the optimal solution of a
                  linear system Qx = q (=> x = Q^-1 q) which has a complexity of O(n^3) otherwise.
        """
        return 0.5 * x.dot(self.Q).dot(x) + self.q.dot(x)

    def jacobian(self, x):
        """
        The Jacobian (i.e., the gradient) of a general quadratic function J f(x) = Q x + q.
        :param x: ([n x 1] real column vector): the point where to start the algorithm from.
        :return:  the Jacobian of a general quadratic function.
        """
        return self.Q.dot(x) + self.q

    def hessian(self, x):
        """
        The Hessian matrix of a general quadratic function H f(x) = Q.
        :param x: 1D array of points at which the Hessian is to be computed.
        :return:  the Hessian matrix (i.e., the the quadratic part) of a general quadratic function at x.
        """
        return self.Q


# 2x2 quadratic function with nicely conditioned Hessian
quad1 = Quadratic(Q=[[6, -2], [-2, 6]], q=[10, 5])
# 2x2 quadratic function with less nicely conditioned Hessian
quad2 = Quadratic(Q=[[5, -3], [-3, 5]], q=[10, 5])
# 2x2 quadratic function with Hessian having one zero eigenvalue (singular matrix)
quad3 = Quadratic(Q=[[4, -4], [-4, 4]], q=[10, 5])
# 2x2 quadratic function with indefinite Hessian (one positive and one negative eigenvalue)
quad4 = Quadratic(Q=[[3, -5], [-5, 3]], q=[10, 5])
# 2x2 quadratic function with "very elongated" Hessian
# (a very small positive minimum eigenvalue, the other much larger)
quad5 = Quadratic(Q=[[101, -99], [-99, 101]], q=[10, 5])
