"""Module-level ASGI app for the `fastapi` CLI: `fastapi dev app/asgi.py`.

Tests import `create_app` from `app.main` instead, so nothing is created at import time there.
"""

from .main import create_app

app = create_app()
