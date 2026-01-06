const qs = (selector, scope = document) => scope.querySelector(selector);
const qsa = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

const reveal = () => {
  const elements = qsa('[data-reveal]');
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );

  elements.forEach((el) => observer.observe(el));
};

const setupTabs = () => {
  const tabs = qsa('.tab');
  if (!tabs.length) return;

  const panels = qsa('.solver-panel');

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((item) => item.classList.remove('active'));
      tab.classList.add('active');

      const target = tab.dataset.target;
      panels.forEach((panel) => {
        panel.classList.toggle('active', panel.dataset.panel === target);
      });
    });
  });
};

const setStatus = (el, message, isError = false) => {
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? '#b23d3d' : '';
};

const renderResults = (plots) => {
  const grid = qs('#results-grid');
  if (!grid) return;
  grid.innerHTML = '';

  plots.forEach((plot) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const title = document.createElement('strong');
    title.textContent = plot.title;
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${plot.image}`;
    img.alt = plot.title;
    card.appendChild(title);
    card.appendChild(img);
    grid.appendChild(card);
  });
};

const buildPayload = (form) => {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (value === '') continue;
    if (['n', 'm'].includes(key)) {
      payload[key] = Number(value);
    } else if (['a', 'b', 'l', 'K', 'T', 'r', 'sigma'].includes(key)) {
      payload[key] = Number(value);
    } else if (key === 'compare_analytical') {
      payload[key] = value === 'on';
    } else {
      payload[key] = value;
    }
  }

  const compareInput = form.querySelector('#compare-analytical');
  if (compareInput) {
    payload.compare_analytical = compareInput.checked;
  }

  return payload;
};

const setupHeatForm = () => {
  const form = qs('#heat-form');
  if (!form) return;
  const status = qs('#heat-status');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus(status, 'Running solver...');

    const payload = buildPayload(form);

    try {
      const response = await fetch('/api/heat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to run solver.');
      }

      renderResults(data.plots);
      setStatus(status, 'Done.');
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });
};

const setupBlackForm = () => {
  const form = qs('#black-form');
  if (!form) return;
  const status = qs('#black-status');
  const methodSelect = qs('#black-method');
  const compareToggle = qs('#compare-analytical');

  const syncCompare = () => {
    if (!compareToggle) return;
    const disabled = methodSelect.value === 'analytical';
    compareToggle.disabled = disabled;
    if (disabled) {
      compareToggle.checked = false;
    }
  };

  methodSelect.addEventListener('change', syncCompare);
  syncCompare();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus(status, 'Running solver...');

    const payload = buildPayload(form);

    try {
      const response = await fetch('/api/black-scholes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to run solver.');
      }

      renderResults(data.plots);
      setStatus(status, 'Done.');
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });
};

document.addEventListener('DOMContentLoaded', () => {
  reveal();
  setupTabs();
  setupHeatForm();
  setupBlackForm();
});
