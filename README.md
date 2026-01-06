# White Panda Labs Portfolio

Portfolio site with a live Python backend that runs heat equation and Black-Scholes solvers and returns Matplotlib plots.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

## Notes
- The solvers accept symbolic inputs for the heat equation using SymPy syntax (e.g., `sin(pi*x)` or `exp(-t)`).
- Black-Scholes inputs for `r` and `sigma` are percentages per year.