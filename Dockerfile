FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH"
WORKDIR /srv

# Dependencies first for layer caching. --locked fails the build if uv.lock is stale.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

RUN useradd --system --uid 10001 --home /srv sher \
 && mkdir -p /data/storage && chown -R sher /data
COPY app ./app
USER sher

ENV SHER_STORAGE_DIR=/data/storage
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"
CMD ["fastapi", "run", "app/asgi.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
