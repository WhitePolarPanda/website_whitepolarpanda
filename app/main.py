import asyncio
import html
import json
import multiprocessing as mp
import re
import time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, FiniteFloat, model_validator
from .calculation import worker

STATIC_DIR=Path(__file__).resolve().parent/'static'
app=FastAPI()
@app.get('/static/index.html', include_in_schema=False)
def static_index():
    return RedirectResponse('/', status_code=307)

app.mount('/static',StaticFiles(directory=STATIC_DIR),name='static')
busy=False
class GridRequest(BaseModel):
    n:int
    m:int
    @model_validator(mode='after')
    def budget(self):
        if not 2<=self.n<=400 or not 1<=self.m<=4000 or (self.n+1)*(self.m+1)>250000:raise ValueError('Use n=2–400, m=1–4000 and at most 250000 grid points.')
        return self
class HeatRequest(GridRequest):
    method:str
    f_expr:str
    u0_expr:str
    ua_expr:str
    ub_expr:str
    a:FiniteFloat
    b:FiniteFloat
    l:FiniteFloat
class BlackScholesRequest(GridRequest):
    method:str
    K:FiniteFloat
    T:FiniteFloat
    r:FiniteFloat
    sigma:FiniteFloat
    compare_analytical:bool=False
    include_analytical:bool=False
    error_mode:Literal['signed','absolute','both']='signed'
def render_page():
    copy = json.loads((STATIC_DIR / 'copy.json').read_text())
    alt = html.escape(copy['eeg']['figure_alt'], quote=True)
    caption = html.escape(copy['eeg']['figure_caption'], quote=True)
    panels = ''.join(
        f'<div class="eeg-panel"><h3>{label}</h3>'
        f'<button type="button" class="figure-button eeg-crop eeg-crop-{label.lower()}" '
        f'data-image="/static/eeg.png" aria-label="Enlarge full EEG figure: {label}">'
        '<img src="/static/eeg.png" width="913" height="1536" '
        f'loading="lazy" alt="{alt}"></button></div>'
        for label in ('N1', 'P300')
    )
    figure = (
        f'<figure class="eeg-figure"><div class="eeg-panels">{panels}</div>'
        f'<figcaption>{caption}</figcaption></figure>'
    )

    def replace(match):
        if match[1] == 'eeg_figure':
            return figure
        value = copy
        for key in match[1].split('.'):
            value = value[key]
        return html.escape(value, quote=True)

    page = re.sub(r'\{\{([\w.]+)\}\}', replace, (STATIC_DIR / 'index.html').read_text())
    headers = {'Cache-Control': 'no-store'}
    return HTMLResponse(page, headers=headers)


@app.get('/', response_class=HTMLResponse)
@app.get('/background', response_class=HTMLResponse)
def index(request: Request):
    return render_page()


async def execute(endpoint,payload,request):
    global busy
    # A short wait allows a cancelled request to release its worker.
    deadline=time.monotonic()+1
    while busy and time.monotonic()<deadline:await asyncio.sleep(.05)
    if busy:raise HTTPException(429,'A calculation is running. Try again shortly.')
    busy=True;process=None;parent=None;child=None
    try:
        ctx=mp.get_context('spawn');parent,child=ctx.Pipe(duplex=False)
        process=ctx.Process(target=worker,args=(child,endpoint,payload.model_dump()),daemon=True);process.start();child.close()
        deadline=time.monotonic()+30
        while not parent.poll():
            if await request.is_disconnected():raise HTTPException(499,'Request cancelled.')
            if time.monotonic()>deadline:raise HTTPException(422,'Reduce the grid size and try again.')
            if not process.is_alive():raise HTTPException(500,'Unable to calculate. Please try again.')
            await asyncio.sleep(.05)
        status,data=parent.recv();return JSONResponse(data,status_code=status)
    finally:
        if process is not None and process.pid is not None:
            if process.is_alive():process.terminate()
            process.join(timeout=2)
            if process.is_alive():process.kill();process.join()
        if parent is not None:parent.close()
        if child is not None:child.close()
        busy=False
@app.post('/api/heat')
async def heat_solver(payload:HeatRequest,request:Request):return await execute('heat',payload,request)
@app.post('/api/black-scholes')
async def black_scholes_solver(payload:BlackScholesRequest,request:Request):return await execute('black',payload,request)

from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def invalid_request(request,exc):
    # Do not echo invalid non-finite values into a JSON error response.
    return JSONResponse({'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in exc.errors()]},status_code=422)
