"""The server-rendered citizen surface (§10).

The citizen portal is HTML from FastAPI, not a single-page app: R24.1's 150 KB
compressed budget and R24.3's throttled first-paint targets rule out shipping a
JavaScript framework (§10.1). Templates and the one service worker that is the whole
JavaScript budget live under this package. :mod:`app.citizen.templating` holds the
Jinja2 environment and the render helper that renders the *gated* payload (§8.2).
"""
