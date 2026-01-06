from io import BytesIO
import base64
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .solver.heat import solve_heat_equation
from .solver.black_scholes import (
    analytical_surface,
    implicit_surface,
    cn_direct_surface,
    rannacher_surface,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'

app = FastAPI()
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


class HeatRequest(BaseModel):
    method: str
    f_expr: str
    u0_expr: str
    ua_expr: str
    ub_expr: str
    a: float
    b: float
    l: float
    n: int
    m: int


class BlackScholesRequest(BaseModel):
    method: str
    K: float
    T: float
    r: float
    sigma: float
    n: int
    m: int
    compare_analytical: bool = False


@app.get('/')
def index():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/background')
def background():
    return FileResponse(STATIC_DIR / 'background.html')


def _downsample(values, x_grid, t_grid, max_points=90):
    x_count = min(max_points, len(x_grid))
    t_count = min(max_points, len(t_grid))

    x_idx = np.linspace(0, len(x_grid) - 1, x_count).astype(int)
    t_idx = np.linspace(0, len(t_grid) - 1, t_count).astype(int)

    return values[np.ix_(t_idx, x_idx)], x_grid[x_idx], t_grid[t_idx]


def _surface_plot(x_grid, t_grid, values, title, cmap):
    values_ds, x_ds, t_ds = _downsample(values, x_grid, t_grid)
    X, T = np.meshgrid(x_ds, t_ds)

    fig = plt.figure(figsize=(9, 6), dpi=120)
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(X, T, values_ds, cmap=cmap, linewidth=0, antialiased=True)
    ax.set_xlabel('x / s')
    ax.set_ylabel('t')
    ax.set_zlabel('value')
    ax.set_title(title)
    ax.view_init(25, -135)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('ascii')


def _difference_plot(x_grid, t_grid, values, title):
    values_ds, x_ds, t_ds = _downsample(values, x_grid, t_grid)
    X, T = np.meshgrid(x_ds, t_ds)

    fig = plt.figure(figsize=(9, 6), dpi=120)
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(X, T, values_ds, cmap='coolwarm', linewidth=0, antialiased=True)
    ax.set_xlabel('x / s')
    ax.set_ylabel('t')
    ax.set_zlabel('difference')
    ax.set_title(title)
    ax.view_init(25, -135)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('ascii')


@app.post('/api/heat')
def heat_solver(payload: HeatRequest):
    try:
        values, x_grid, t_grid = solve_heat_equation(payload.method, payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    method_title = {
        'explicit': 'Heat Equation (Explicit)',
        'implicit': 'Heat Equation (Implicit)',
        'cn': 'Heat Equation (Crank-Nicolson)',
    }.get(payload.method, 'Heat Equation')

    plot = _surface_plot(x_grid, t_grid, values, method_title, 'viridis')
    return {
        'plots': [
            {
                'title': method_title,
                'image': plot,
            }
        ]
    }


@app.post('/api/black-scholes')
def black_scholes_solver(payload: BlackScholesRequest):
    K = float(payload.K)
    T = float(payload.T)
    r = float(payload.r) / 100.0
    sigma = float(payload.sigma) / 100.0
    n = int(payload.n)
    m = int(payload.m)

    if K <= 0 or T <= 0 or sigma <= 0:
        raise HTTPException(status_code=400, detail='K, T, and sigma must be positive.')
    if n < 2 or m < 1:
        raise HTTPException(status_code=400, detail='n must be >= 2 and m must be >= 1.')

    plots = []

    if payload.method == 'analytical':
        values, s_grid, t_grid = analytical_surface(K, T, r, sigma, n, m)
        plots.append({
            'title': 'Black-Scholes Analytical',
            'image': _surface_plot(s_grid, t_grid, values, 'Black-Scholes Analytical', 'plasma'),
        })

    elif payload.method == 'implicit':
        values, s_grid, t_grid = implicit_surface(K, T, r, sigma, n, m)
        plots.append({
            'title': 'Black-Scholes Implicit',
            'image': _surface_plot(s_grid, t_grid, values, 'Black-Scholes Implicit', 'cividis'),
        })

        if payload.compare_analytical:
            analytical, _, _ = analytical_surface(K, T, r, sigma, n, m)
            diff = values - analytical
            plots.append({
                'title': 'Implicit vs Analytical (Difference)',
                'image': _difference_plot(s_grid, t_grid, diff, 'Implicit - Analytical'),
            })

    elif payload.method == 'cn_direct':
        values, s_grid, t_grid = cn_direct_surface(K, T, r, sigma, n, m)
        plots.append({
            'title': 'Black-Scholes CN Direct',
            'image': _surface_plot(s_grid, t_grid, values, 'Black-Scholes CN Direct', 'coolwarm'),
        })

        if payload.compare_analytical:
            analytical, _, _ = analytical_surface(K, T, r, sigma, n, m)
            diff = values - analytical
            plots.append({
                'title': 'CN Direct vs Analytical (Difference)',
                'image': _difference_plot(s_grid, t_grid, diff, 'CN Direct - Analytical'),
            })

    elif payload.method == 'rannacher':
        values, s_grid, t_grid = rannacher_surface(K, T, r, sigma, n, m)
        plots.append({
            'title': 'Black-Scholes Rannacher Stepping',
            'image': _surface_plot(s_grid, t_grid, values, 'Black-Scholes Rannacher', 'magma'),
        })

        if payload.compare_analytical:
            analytical, _, _ = analytical_surface(K, T, r, sigma, n, m)
            diff = values - analytical
            plots.append({
                'title': 'Rannacher vs Analytical (Difference)',
                'image': _difference_plot(s_grid, t_grid, diff, 'Rannacher - Analytical'),
            })

    else:
        raise HTTPException(status_code=400, detail='Unknown method.')

    return {'plots': plots}
