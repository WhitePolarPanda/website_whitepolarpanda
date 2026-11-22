from io import BytesIO
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.colors import Normalize
from .solver.heat import solve_heat_equation
from .solver.black_scholes import analytical_surface, implicit_surface, cn_direct_surface, rannacher_surface

SOLVERS={'analytical':analytical_surface,'implicit':implicit_surface,'cn_direct':cn_direct_surface,'rannacher':rannacher_surface}
TITLES={'analytical':'Black-Scholes Analytical','implicit':'Black-Scholes Implicit','cn_direct':'Black-Scholes CN Direct','rannacher':'Black-Scholes Rannacher Stepping'}

def plot(x,t,v,kind,zlim=None):
    if not np.isfinite(v).all(): raise ValueError('Choose parameters that produce finite values.')
    ix=np.linspace(0,len(x)-1,min(90,len(x))).astype(int);it=np.linspace(0,len(t)-1,min(90,len(t))).astype(int)
    if kind!='heat': t=(t[-1]-t)[::-1];v=v[::-1]
    X,Y=np.meshgrid(x[ix],t[it]); Z=v[np.ix_(it,ix)]
    fig=Figure(figsize=(7.2,5.2),dpi=150,facecolor='white');ax=fig.add_subplot(111,projection='3d')
    kw={'cmap':'viridis','linewidth':0,'antialiased':True,'rcount':90,'ccount':90}
    if kind=='signed_error':
        lim=max(float(np.max(abs(v))),1e-14);kw.update(cmap='RdBu_r',norm=Normalize(-lim,lim));ax.set_zlim(-lim,lim)
    elif kind=='absolute_error':
        lim=max(float(np.max(v)),1e-14);kw.update(cmap='viridis',norm=Normalize(0,lim));ax.set_zlim(0,lim)
    elif zlim: ax.set_zlim(*zlim);kw['norm']=Normalize(*zlim)
    surf=ax.plot_surface(X,Y,Z,**kw)
    ax.set_xlabel('x' if kind=='heat' else 'Spot S',labelpad=10)
    ax.set_ylabel('t' if kind=='heat' else 'Time to expiry (years)',labelpad=11)
    ax.set_zlabel('u' if kind=='heat' else ('Error (price units)' if kind.endswith('_error') else 'Call price'),labelpad=9)
    ax.tick_params(labelsize=9);ax.view_init(25,-135)
    if kind.endswith('_error'):fig.colorbar(surf,ax=ax,shrink=.5,pad=.10)
    fig.subplots_adjust(left=.15 if kind.endswith('_error') else .04,right=.88,bottom=.10,top=.99)
    buf=BytesIO();fig.savefig(buf,format='png');fig.clear()
    return base64.b64encode(buf.getvalue()).decode()

def calculate(endpoint,p):
    if endpoint=='heat':
        v,x,t=solve_heat_equation(p['method'],p)
        return {'plots':[{'title':{'explicit':'Heat Equation (Explicit)','implicit':'Heat Equation (Implicit)','cn':'Heat Equation (Crank-Nicolson)'}.get(p['method'],'Heat Equation'),'kind':'heat','image':plot(x,t,v,'heat')}]}
    method=p['method']
    if method not in SOLVERS:raise ValueError('Unknown method.')
    if min(p['K'],p['T'],p['sigma'])<=0:raise ValueError('K, T, and sigma must be positive.')
    args=(p['K'],p['T'],p['r']/100,p['sigma']/100,p['n'],p['m'])
    v,x,t=SOLVERS[method](*args)
    compare=method!='analytical' and p['compare_analytical'];a=None
    if compare:
        a,sx,tx=analytical_surface(*args)
        if v.shape!=a.shape or not np.array_equal(x,sx) or not np.array_equal(t,tx):raise ValueError('Comparison grids do not match.')
        if not np.isfinite(a).all():raise ValueError('Choose parameters that produce finite values.')
    lo=min(float(v.min()),float(a.min()) if a is not None else 0);hi=max(float(v.max()),float(a.max()) if a is not None else 0)
    zlim=(lo,hi if hi>lo else lo+1)
    def entry(title,kind,values):return {'title':title,'kind':kind,'image':plot(x,t,values,kind,zlim if 'price' in kind else None)}
    plots=[entry(TITLES[method],'analytical_price' if method=='analytical' else 'fd_price',v)]
    result={'plots':plots}
    if compare:
        signed=v-a
        if p['include_analytical']:plots.append(entry('Black-Scholes Analytical','analytical_price',a))
        modes=['signed','absolute'] if p['error_mode']=='both' else [p['error_mode']]
        for mode in modes:
            title={'implicit':'Implicit','cn_direct':'CN Direct','rannacher':'Rannacher'}[method]+' vs Analytical (Difference)'
            plots.append(entry(title if mode=='signed' else 'Absolute error',mode+'_error',signed if mode=='signed' else abs(signed)))
        def stats(d):return {'max_abs':float(np.max(abs(d))),'rmse':float(np.sqrt(np.mean(d*d)))}
        result['summary']={'full_grid':stats(signed),'spatial_interior':stats(signed[:,1:-1])}
    return result

def worker(connection,endpoint,p):
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise'): result=calculate(endpoint,p)
        connection.send((200,result))
    except (ValueError,FloatingPointError,OverflowError,ZeroDivisionError) as exc:connection.send((400,{'detail':str(exc)}))
    except Exception:connection.send((500,{'detail':'Unable to calculate. Please try again.'}))
    finally:connection.close()
