FROM python:3.12-slim

WORKDIR /app

# uv: fast, deterministic installs from pyproject.toml + uv.lock (no requirements.txt)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

# Railway/PaaS inject $PORT; default to 8000 for local/compose.
ENV PORT=8000
EXPOSE 8000

# Run migrations, then serve. --proxy-headers so the HTTPS scheme is honored behind a proxy.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
