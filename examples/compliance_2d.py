#!/usr/bin/env python3

import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
import nlopt
import numpy as np
from jax.scipy.signal import convolve

from tofea.fea2d import FEA2D_K


def simp_parametrization(shape, ks, vmin, vmax, penalty=3.0):
    xy = jnp.linspace(-1, 1, ks)
    xx, yy = jnp.meshgrid(xy, xy)
    k = np.sqrt(2) - jnp.sqrt(xx**2 + yy**2)
    k /= jnp.sum(k)

    @jax.jit
    def _parametrization(x):
        x = np.reshape(x, shape)
        x = jnp.pad(x, ks // 2, mode="edge")
        x = convolve(x, k, mode="valid")
        x = vmin + (vmax - vmin) * x**penalty
        return x

    return _parametrization


def main():
    max_its = 50
    volfrac = 0.3
    kernel_size = 5
    shape = (120, 60)
    nelx, nely = shape
    emin, emax = 1e-6, 1

    dofs = np.arange(2 * (nelx + 1) * (nely + 1)).reshape(nelx + 1, nely + 1, 2)
    fixed = np.zeros_like(dofs, dtype="?")
    load = np.zeros_like(dofs)

    fixed[0, :, :] = 1
    load[-1, -1, 1] = 1

    fem = FEA2D_K(fixed)
    parametrization = simp_parametrization(shape, kernel_size, emin, emax)
    x0 = jnp.full(shape, volfrac)

    plt.ion()
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    im = ax.imshow(parametrization(x0).T, cmap="gray_r", vmin=emin, vmax=emax)

    @jax.value_and_grad
    def objective(x):
        x = parametrization(x)
        d = fem.displacement(x, load)
        c = fem.compliance(x, d)
        return c

    @jax.jit
    @jax.value_and_grad
    def volume(x):
        return jnp.mean(x)

    def volume_constraint(x, gd):
        v, g = volume(x)
        if gd.size > 0:
            gd[:] = g.ravel()
        return v.item() - volfrac

    def nlopt_obj(x, gd):
        v, g = objective(x)

        if gd.size > 0:
            gd[:] = g.ravel()

        im.set_data(parametrization(x).T)
        plt.pause(0.01)

        return v.item()

    opt = nlopt.opt(nlopt.LD_MMA, x0.size)
    opt.add_inequality_constraint(volume_constraint)
    opt.set_min_objective(nlopt_obj)
    opt.set_lower_bounds(0)
    opt.set_upper_bounds(1)
    opt.set_maxeval(max_its)
    opt.optimize(x0.ravel())

    plt.show(block=True)


if __name__ == "__main__":
    main()
