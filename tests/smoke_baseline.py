"""Original API and numerical regression checks. Run from website-baseline/."""
from base64 import b64decode
from pathlib import Path
from os import environ
from fastapi.testclient import TestClient
from app.main import app
from app.solver.black_scholes import analytical_surface, implicit_surface, cn_direct_surface, rannacher_surface
from app.solver.heat import solve_heat_equation
import numpy as np
from scipy.stats import norm
if __name__ == '__main__':
    client = TestClient(app)
    PNG = b'\x89PNG\r\n\x1a\n'
    BS = dict(K=100, T=1, r=5, sigma=20, n=48, m=28)
    HEAT = dict(f_expr='0', u0_expr='sin(pi*x)', ua_expr='0', ub_expr='0', a=0, b=1, l=.1, n=16, m=65)

    def images(response, count):
        assert response.status_code == 200, response.text[:500]
        plots = response.json()['plots']
        assert len(plots) == count, [p['title'] for p in plots]
        imgs = [b64decode(p['image'], validate=True) for p in plots]
        assert all(i.startswith(PNG) and len(i) > 10_000 for i in imgs)
        return imgs

    samples = {}
    for route in ('/', '/background', '/static/app.js'):
        assert client.get(route).status_code == 200, route
    for method in ('analytical','implicit','cn_direct','rannacher'):
        imgs = images(client.post('/api/black-scholes',json=dict(BS,method=method,compare_analytical=True)),1 if method=='analytical' else 2)
        if method == 'analytical': samples['black-scholes-analytic.png'] = imgs[0]
        if method == 'cn_direct':
            samples['black-scholes-cn-direct.png'], samples['black-scholes-cn-signed-error.png'] = imgs
    for method in ('explicit','implicit','cn'):
        imgs = images(client.post('/api/heat',json=dict(HEAT,method=method)),1)
        result,x,t = solve_heat_equation(method, HEAT)
        expected = np.exp(-(np.pi**2)*t[-1])*np.sin(np.pi*x)
        assert np.max(abs(result[-1]-expected)) < .006, method
        if method == 'cn': samples['heat-equation-cn.png'] = imgs[0]
    images(client.post('/api/heat',json=dict(HEAT,method='implicit',f_expr='x+t',u0_expr='x',ua_expr='t',ub_expr='1+t')),1)
    unstable = client.post('/api/heat',json=dict(HEAT,method='explicit',l=.5,m=2))
    assert unstable.status_code == 400 and 'unstable' in unstable.json()['detail'].lower()
    assert client.post('/api/black-scholes',json=dict(BS,method='none')).status_code == 400

    vals,S,t = analytical_surface(100,1,.05,.2,64,40)
    np.testing.assert_allclose(vals[-1],np.maximum(S-100,0),atol=1e-12)
    assert abs(vals[0,16] - (100*norm.cdf(.35)-100*np.exp(-.05)*norm.cdf(.15))) < 1e-11
    assert abs(vals[0,16]-10.450583572)<1e-8
    for fn in (implicit_surface,cn_direct_surface,rannacher_surface):
        w,sx,tx=fn(100,1,.05,.2,64,40)
        assert w.shape == vals.shape and np.isfinite(w).all(), fn.__name__
        np.testing.assert_array_equal(sx,S)
        np.testing.assert_array_equal(tx,t)
        np.testing.assert_allclose(w[-1],vals[-1],atol=1e-12)
        np.testing.assert_allclose(w[:,0],0,atol=1e-12)
        assert abs(w[0,16]-vals[0,16]) < .16, fn.__name__
    if (out := environ.get('BASELINE_SAMPLE_DIR')):
        folder=Path(out); folder.mkdir(parents=True,exist_ok=True)
        for name,content in samples.items(): (folder/name).write_bytes(content)
    print('PASS: routes, 4 Black–Scholes methods, legacy signed compare for 3 FD methods, 3 Heat methods, custom expressions, instability handling, common grids, payoff, and analytical benchmark.')
