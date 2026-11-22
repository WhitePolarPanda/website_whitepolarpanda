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

Polar Station copy follows the supplied CMU MSML CV.

## Production deployment

Cloudflare proxies both domains to the RackNerd VPS `racknerd261106`.
Caddy forwards requests to FastAPI on `127.0.0.1:8000`. The infrastructure
repository manages Caddy and the `whitepolarpanda.service` systemd unit.

| Cloudflare DNS name | Type | Target | Proxy | TTL |
| --- | --- | --- | --- | --- |
| `@` | `A` | `72.11.133.240` | Proxied | Auto |
| `www` | `A` | `72.11.133.240` | Proxied | Auto |

Once the intended release is on GitHub's `main` branch, connect with
`ssh racknerd261106` and run the update as a user with root privileges:

```sh
cd /srv/whitepolarpanda &&
  runuser -u www-data -- git pull --ff-only origin main &&
  runuser -u www-data -- .venv/bin/python -m pip install -r requirements.txt &&
  systemctl restart whitepolarpanda.service
```

Check the service and recent logs on the VPS, then verify both public URLs:

```sh
systemctl is-active whitepolarpanda.service
journalctl -u whitepolarpanda.service -n 50 --no-pager
curl -fsS -o /dev/null -w '%{http_code}\n' https://whitepolarpanda.com/
curl -fsS -o /dev/null -w '%{http_code}\n' https://www.whitepolarpanda.com/
```

The service should report `active` and both URLs should return `200`.
