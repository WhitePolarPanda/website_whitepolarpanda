# White Panda Labs

FastAPI portfolio with interactive Black–Scholes pricing and a discrete hedging study. The heat-equation solver remains available through the API.

## Local preview

Python 3.12 is recommended.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
./scripts/dev.sh
```

Open http://127.0.0.1:8000. Set `PORT` to use another local port.

## Tests

```sh
PYTHONPATH=. .venv/bin/python tests/smoke_baseline.py
PYTHONPATH=. .venv/bin/pytest -q
node --check app/static/app.js
```

`app/static/copy.json` contains the approved production copy. The homepage template resolves these fields on the server. Solver responses retain the original `plots` contract; optional `include_analytical` and `error_mode` extend FD comparisons. Rates and volatility remain percentage inputs.

The application uses a bounded calculation subprocess with a 30-second deadline. Matplotlib renders PNG surfaces; no numerical matrices are sent to the browser. Original finite-difference boundary conditions are preserved.

Production and local preview use the same bundled EEG and hedging figures. The EEG panels crop the original image in CSS; either panel opens the full image. No external ZIP or review environment variables are required.

Render deploys `main` using `render.yaml`. Polar Station copy follows the supplied CMU MSML CV.
