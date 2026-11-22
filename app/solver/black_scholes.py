import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from scipy.stats import norm


def analytical_surface(K, T, r, sigma, n, m):
    s_max = 4 * K
    s_grid = np.linspace(0, s_max, n + 1)
    t_grid = np.linspace(0, T, m + 1)

    values = np.zeros((m + 1, n + 1))

    tau = (T - t_grid[:-1])[:, None]
    spots = s_grid[None, 1:]
    d1 = (np.log(spots / K) + (r + 0.5 * sigma ** 2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)
    values[:-1, 1:] = spots * norm.cdf(d1) - K * np.exp(-r * tau) * norm.cdf(d2)
    values[-1] = np.maximum(s_grid - K, 0)

    return values, s_grid, t_grid


def implicit_surface(K, T, r, sigma, n, m):
    s_max = 4 * K
    h = s_max / n
    s_grid = np.linspace(0, s_max, n + 1)
    s_interior = s_grid[1:n]

    k = T / m
    t_grid = np.linspace(0, T, m + 1)

    N = n - 1

    a_imp = -k * (0.5 * sigma ** 2 * s_interior ** 2 / h ** 2 - r * s_interior / (2 * h))
    b_imp = 1 + k * r + k * sigma ** 2 * s_interior ** 2 / h ** 2
    c_imp = -k * (0.5 * sigma ** 2 * s_interior ** 2 / h ** 2 + r * s_interior / (2 * h))

    A = diags([a_imp[1:], b_imp, c_imp[:-1]], [-1, 0, 1], shape=(N, N), format='csc')

    c_prev = np.maximum(s_grid - K, 0)
    C = np.zeros((m + 1, n + 1))
    C[m, :] = c_prev

    for j in range(m - 1, -1, -1):
        t_j = t_grid[j]
        rhs = c_prev[1:n].copy()

        c_left = 0.0
        c_right = s_max - K * np.exp(-r * (T - t_j))

        rhs[0] -= a_imp[0] * c_left
        rhs[-1] -= c_imp[-1] * c_right

        c_next_int = spsolve(A, rhs)
        c_next = np.zeros(n + 1)
        c_next[0] = c_left
        c_next[-1] = c_right
        c_next[1:n] = c_next_int

        C[j, :] = c_next
        c_prev = c_next

    return C, s_grid, t_grid


def cn_direct_surface(K, T, r, sigma, n, m):
    s_max = 4 * K
    h = s_max / n
    s_grid = np.linspace(0, s_max, n + 1)
    s_interior = s_grid[1:n]

    k = T / m
    t_grid = np.linspace(0, T, m + 1)

    N = n - 1

    a_lhs = (sigma ** 2 * s_interior ** 2) / (4 * h ** 2) - (r * s_interior) / (4 * h)
    b_lhs = -1 / k - (sigma ** 2 * s_interior ** 2) / (2 * h ** 2) - r / 2
    c_lhs = (sigma ** 2 * s_interior ** 2) / (4 * h ** 2) + (r * s_interior) / (4 * h)

    A = diags([a_lhs[1:], b_lhs, c_lhs[:-1]], [-1, 0, 1], shape=(N, N), format='csc')

    a_rhs = -a_lhs
    b_rhs = -1 / k + (sigma ** 2 * s_interior ** 2) / (2 * h ** 2) + r / 2
    c_rhs = -c_lhs

    c_prev = np.maximum(s_grid - K, 0)
    C = np.zeros((m + 1, n + 1))
    C[m, :] = c_prev

    for j in range(m - 1, -1, -1):
        t_j = t_grid[j]
        c_left = 0.0
        c_right = s_max - K * np.exp(-r * (T - t_j))

        rhs = (
            a_rhs * c_prev[0:N]
            + b_rhs * c_prev[1:N + 1]
            + c_rhs * c_prev[2:N + 2]
        )

        rhs[0] -= a_lhs[0] * c_left
        rhs[-1] -= c_lhs[-1] * c_right

        c_next_int = spsolve(A, rhs)
        c_next = np.zeros(n + 1)
        c_next[0] = c_left
        c_next[-1] = c_right
        c_next[1:n] = c_next_int

        C[j, :] = c_next
        c_prev = c_next

    return C, s_grid, t_grid


def rannacher_surface(K, T, r, sigma, n, m, q=4):
    s_max = 4 * K
    h = s_max / n
    s_grid = np.linspace(0, s_max, n + 1)
    s_interior = s_grid[1:n]
    N = n - 1

    k = T / m
    t_grid = np.linspace(0, T, m + 1)

    c_prev = np.maximum(s_grid - K, 0.0)
    C = np.zeros((m + 1, n + 1))
    C[m, :] = c_prev

    k_sub = k / q

    a_imp = -k_sub * (0.5 * sigma ** 2 * s_interior ** 2 / h ** 2 - r * s_interior / (2 * h))
    b_imp = 1 + k_sub * r + k_sub * sigma ** 2 * s_interior ** 2 / h ** 2
    c_imp = -k_sub * (0.5 * sigma ** 2 * s_interior ** 2 / h ** 2 + r * s_interior / (2 * h))

    A_impl = diags([a_imp[1:], b_imp, c_imp[:-1]], [-1, 0, 1], shape=(N, N), format='csc')

    a_lhs = (sigma ** 2 * s_interior ** 2) / (4 * h ** 2) - (r * s_interior) / (4 * h)
    b_lhs = -1 / k - (sigma ** 2 * s_interior ** 2) / (2 * h ** 2) - r / 2
    c_lhs = (sigma ** 2 * s_interior ** 2) / (4 * h ** 2) + (r * s_interior) / (4 * h)

    A_cn = diags([a_lhs[1:], b_lhs, c_lhs[:-1]], [-1, 0, 1], shape=(N, N), format='csc')

    a_rhs = -a_lhs
    b_rhs = -1 / k + (sigma ** 2 * s_interior ** 2) / (2 * h ** 2) + r / 2
    c_rhs = -c_lhs

    t_current = T
    c_next = np.zeros(n + 1)
    for _ in range(q):
        t_next = t_current - k_sub
        tau_next = T - t_next
        c_left = 0.0
        c_right = s_max - K * np.exp(-r * tau_next)

        rhs = c_prev[1:n].copy()
        rhs[0] -= a_imp[0] * c_left
        rhs[-1] -= c_imp[-1] * c_right

        c_next_int = spsolve(A_impl, rhs)
        c_next[0] = c_left
        c_next[-1] = c_right
        c_next[1:n] = c_next_int

        c_prev = c_next.copy()
        t_current = t_next

    C[m - 1, :] = c_prev

    for j in range(m - 2, -1, -1):
        t_j = t_grid[j]
        tau = T - t_j

        c_left = 0.0
        c_right = s_max - K * np.exp(-r * tau)

        rhs = (
            a_rhs * c_prev[0:N]
            + b_rhs * c_prev[1:N + 1]
            + c_rhs * c_prev[2:N + 2]
        )

        rhs[0] -= a_lhs[0] * c_left
        rhs[-1] -= c_lhs[-1] * c_right

        c_next_int = spsolve(A_cn, rhs)
        c_next = np.zeros(n + 1)
        c_next[0] = c_left
        c_next[-1] = c_right
        c_next[1:n] = c_next_int

        C[j, :] = c_next
        c_prev = c_next

    return C, s_grid, t_grid