import numpy as np
import sympy
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

from .safe_sympy import parse_expression, build_lambdify


def _evaluate_expression(expr, symbols, values):
    func = build_lambdify(expr, symbols)
    return func(*values)


def _init_condition(u0_expr, x_grid):
    x = sympy.Symbol('x')
    func = build_lambdify(u0_expr, [x])
    values = func(x_grid)
    if np.isscalar(values):
        values = np.full_like(x_grid, float(values))
    if np.any(~np.isfinite(values)):
        values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    return values


def solve_heat_equation(method, inputs):
    x = sympy.Symbol('x')
    t = sympy.Symbol('t')

    f_expr = parse_expression(inputs['f_expr'], {x, t})
    u0_expr = parse_expression(inputs['u0_expr'], {x})
    ua_expr = parse_expression(inputs['ua_expr'], {t})
    ub_expr = parse_expression(inputs['ub_expr'], {t})

    a = float(inputs['a'])
    b = float(inputs['b'])
    l = float(inputs['l'])
    n = int(inputs['n'])
    m = int(inputs['m'])

    if not (a < b):
        raise ValueError('a must be less than b.')
    if l <= 0:
        raise ValueError('l must be positive.')
    if n < 2 or m < 1:
        raise ValueError('n must be >= 2 and m must be >= 1.')

    h = (b - a) / n
    k = l / m
    r = k / (h ** 2)

    x_grid = np.linspace(a, b, n + 1)
    t_grid = np.linspace(0, l, m + 1)

    u = np.zeros((m + 1, n + 1))
    u[0, :] = _init_condition(u0_expr, x_grid)

    ua_func = build_lambdify(ua_expr, [t])
    ub_func = build_lambdify(ub_expr, [t])

    u[:, 0] = ua_func(t_grid)
    u[:, -1] = ub_func(t_grid)

    f_func = build_lambdify(f_expr, [x, t])

    if method == 'explicit':
        if r > 0.5:
            raise ValueError(f'Explicit method unstable for r={r:.4f}; increase m or decrease n.')

        for j in range(m):
            t_j = t_grid[j]
            f_vals = np.asarray(f_func(x_grid, t_j))
            if f_vals.shape == ():
                f_vals = np.full_like(x_grid, float(f_vals))
            u[j + 1, 1:-1] = (
                u[j, 1:-1]
                + r * (u[j, :-2] - 2 * u[j, 1:-1] + u[j, 2:])
                + k * f_vals[1:-1]
            )
            u[j + 1, 0] = ua_func(t_grid[j + 1])
            u[j + 1, -1] = ub_func(t_grid[j + 1])

    elif method == 'implicit':
        diag = np.full(n - 1, 1 + 2 * r)
        off = np.full(n - 2, -r)
        A = diags([off, diag, off], [-1, 0, 1], format='csc')

        for j in range(m):
            t_next = t_grid[j + 1]
            f_vals = np.asarray(f_func(x_grid, t_next))
            if f_vals.shape == ():
                f_vals = np.full_like(x_grid, float(f_vals))

            rhs = u[j, 1:-1] + k * f_vals[1:-1]
            rhs[0] += r * ua_func(t_next)
            rhs[-1] += r * ub_func(t_next)

            u_next_interior = spsolve(A, rhs)
            u[j + 1, 1:-1] = u_next_interior
            u[j + 1, 0] = ua_func(t_next)
            u[j + 1, -1] = ub_func(t_next)

    elif method == 'cn':
        diag = np.full(n - 1, 1 + r)
        off = np.full(n - 2, -r / 2)
        A = diags([off, diag, off], [-1, 0, 1], format='csc')

        diag_b = np.full(n - 1, 1 - r)
        off_b = np.full(n - 2, r / 2)
        B = diags([off_b, diag_b, off_b], [-1, 0, 1], format='csc')

        for j in range(m):
            t_j = t_grid[j]
            t_next = t_grid[j + 1]
            f_j = np.asarray(f_func(x_grid, t_j))
            f_next = np.asarray(f_func(x_grid, t_next))
            if f_j.shape == ():
                f_j = np.full_like(x_grid, float(f_j))
            if f_next.shape == ():
                f_next = np.full_like(x_grid, float(f_next))

            rhs = B.dot(u[j, 1:-1]) + (k / 2) * (f_j[1:-1] + f_next[1:-1])
            rhs[0] += (r / 2) * (ua_func(t_j) + ua_func(t_next))
            rhs[-1] += (r / 2) * (ub_func(t_j) + ub_func(t_next))

            u_next_interior = spsolve(A, rhs)
            u[j + 1, 1:-1] = u_next_interior
            u[j + 1, 0] = ua_func(t_next)
            u[j + 1, -1] = ub_func(t_next)

    else:
        raise ValueError('Unknown method.')

    return u, x_grid, t_grid
