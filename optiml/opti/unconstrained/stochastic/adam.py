import warnings

import numpy as np

from . import StochasticMomentumOptimizer


class Adam(StochasticMomentumOptimizer):

    def __init__(self,
                 f,
                 x=None,
                 batch_size=None,
                 eps=1e-6,
                 epochs=1000,
                 step_size=0.001,
                 momentum_type='none',
                 momentum=0.9,
                 beta1=0.9,
                 beta2=0.999,
                 offset=1e-8,
                 callback=None,
                 callback_args=(),
                 shuffle=True,
                 random_state=None,
                 verbose=False):
        super().__init__(f=f,
                         x=x,
                         step_size=step_size,
                         momentum_type=momentum_type,
                         momentum=momentum,
                         batch_size=batch_size,
                         eps=eps,
                         epochs=epochs,
                         callback=callback,
                         callback_args=callback_args,
                         shuffle=shuffle,
                         random_state=random_state,
                         verbose=verbose)
        if not 0 <= beta1 < 1:
            raise ValueError('beta1 has to lie in [0, 1)')
        self.beta1 = beta1
        self.est_mom1 = 0  # initialize 1st moment vector
        if not 0 <= beta2 < 1:
            raise ValueError('beta2 has to lie in [0, 1)')
        self.beta2 = beta2
        self.est_mom2 = 0  # initialize 2nd moment vector
        if not self.beta1 < np.sqrt(self.beta2):
            warnings.warn('constraint from convergence analysis for adam not satisfied')
        if not offset > 0:
            raise ValueError('offset must be > 0')
        self.offset = offset

    def minimize(self):

        self._print_header()

        for batch in self.batches:

            self.f_x = self.f.function(self.x, *batch)

            self._print_info()

            try:
                self.callback(batch)
            except StopIteration:
                break

            if self.is_batch_end():
                self.epoch += 1

            if self.epoch >= self.epochs:
                self.status = 'stopped'
                break

            t = self.iter + 1

            if self.momentum_type == 'nesterov':
                step_m1 = self.step
                step1 = self.momentum * step_m1
                self.x += step1

            self.g_x = self.f.jacobian(self.x, *batch)

            # compute search direction
            d = -self.g_x

            est_mom1_m1 = self.est_mom1
            est_mom2_m1 = self.est_mom2

            # update biased 1st moment estimate
            self.est_mom1 = self.beta1 * est_mom1_m1 + (1. - self.beta1) * d
            # update biased 2nd raw moment estimate
            self.est_mom2 = self.beta2 * est_mom2_m1 + (1. - self.beta2) * self.g_x ** 2

            est_mom1_crt = self.est_mom1 / (1. - self.beta1 ** t)  # compute bias-corrected 1st moment estimate
            est_mom2_crt = self.est_mom2 / (1. - self.beta2 ** t)  # compute bias-corrected 2nd raw moment estimate

            step2 = self.step_size * est_mom1_crt / (np.sqrt(est_mom2_crt) + self.offset)

            if self.momentum_type == 'standard':

                step_m1 = self.step
                self.step = self.momentum * step_m1 + step2
                self.x += self.step

            elif self.momentum_type == 'nesterov':

                self.x += step2
                self.step = step1 + step2

            elif self.momentum_type == 'none':

                self.step = step2
                self.x += self.step

            self.iter += 1

        if self.verbose:
            print('\n')

        return self
