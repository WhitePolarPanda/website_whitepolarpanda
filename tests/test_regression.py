import json
from pathlib import Path
import numpy as np
import pytest
import sympy
from fastapi.testclient import TestClient
from app.main import app
from app.calculation import calculate
from app.solver.safe_sympy import parse_expression,build_lambdify
from app.solver.black_scholes import analytical_surface,implicit_surface,cn_direct_surface,rannacher_surface
from app.solver.heat import solve_heat_equation

@pytest.mark.parametrize('method',['implicit','cn_direct','rannacher'])
@pytest.mark.parametrize('include_analytical',[False,True])
def test_full_comparison(method,include_analytical):
 p=dict(K=100,T=.4,r=-1,sigma=20,n=32,m=20,method=method,compare_analytical=True,include_analytical=include_analytical,error_mode='both')
 result=calculate('black',p)
 assert [v['kind'] for v in result['plots']]==['fd_price']+(['analytical_price'] if include_analytical else [])+['signed_error','absolute_error']
 a,x,t=analytical_surface(100,.4,-.01,.2,32,20)
 v,s,u={'implicit':implicit_surface,'cn_direct':cn_direct_surface,'rannacher':rannacher_surface}[method](100,.4,-.01,.2,32,20)
 np.testing.assert_array_equal(s,x);np.testing.assert_array_equal(u,t)
 np.testing.assert_allclose(v[-1],a[-1],atol=1e-12)
 assert result['summary']['full_grid']['max_abs']==np.max(abs(v-a))
 np.testing.assert_allclose(result['summary']['spatial_interior']['rmse'],np.sqrt(np.mean((v[:,1:-1]-a[:,1:-1])**2)))

@pytest.mark.parametrize('expr',["__import__('os')",'x.__class__','[x]','x[0]','open(x)','exp(1000)','sqrt(-1)','1/0','9**9**9','x'*513])
def test_expression_rejected(expr):
 with pytest.raises(ValueError):build_lambdify(parse_expression(expr,{sympy.Symbol('x')}),['x'])(np.array([0.,1.]))

@pytest.mark.parametrize('method',['explicit','implicit','cn'])
def test_heat_manufactured(method):
 v,x,t=solve_heat_equation(method,dict(f_expr='1',u0_expr='x',ua_expr='t',ub_expr='1+t',a=0,b=1,l=.1,n=16,m=65))
 np.testing.assert_allclose(v,x[None,:]+t[:,None],atol=1e-12)

def test_api_validation_and_content():
 c=TestClient(app);p=dict(K=100,T=1,r=5,sigma=20,n=50,m=50,method='analytical')
 for change in [dict(n=401),dict(m=4001),dict(n=400,m=4000),dict(r='NaN'),dict(error_mode='bad')]:assert c.post('/api/black-scholes',json=p|change).status_code==422
 text=c.get('/').text;copy=json.loads(Path('app/static/copy.json').read_text())
 assert copy['page']['intro'] in text
 assert '{{' not in text
 assert 'placeholder' not in text.lower()
 for path in ['/static/EEG_Figure_4_PRIVATE_REVIEW.png','/_review/assets/eeg','/private-assets/eeg/figure-4-aggregate-owner-review.png']:assert c.get(path).status_code==404


def test_production_figures_and_template():
    with TestClient(app, client=('198.51.100.4', 50000)) as client:
        home = client.get('/')
        assert home.status_code == 200
        assert home.text.count('data-image="/static/eeg.png"') == 2
        assert '{{' not in home.text
        assert 'noindex' not in home.headers.get('x-robots-tag', '')
        assert 'Heat Equation' not in home.text
        assert 'hedging-background' in home.text
        for path in ['/static/eeg.png', '/static/tradeoff.png']:
            image = client.get(path)
            assert image.status_code == 200
            assert image.content.startswith(b'\x89PNG\r\n\x1a\n')
        assert client.get('/static/index.html').text == home.text
        assert client.get('/background').text == home.text
