# =============================================================================
# VJ Semijoias — Dockerfile Multi-stage
# Base: python:3.12-slim (~120MB final image)
# =============================================================================

# ---------- Stage 1: Builder (install dependencies) ----------
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy only dependency files first (melhor aproveitamento de cache)
COPY pyproject.toml uv.lock ./

# Install production dependencies only (sem dev)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN groupadd -r vj && useradd -r -g vj -d /app -s /bin/false vj

WORKDIR /app

# Copiar do estágio builder
COPY --from=builder /app /app
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/.venv /app/.venv

# Garantir permissões corretas
RUN chown -R vj:vj /app

# Variáveis de ambiente padrão (sobrescritas em produção)
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=5000

# Expor a porta da aplicação
EXPOSE 5000

# Usar usuário não-root
USER vj

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/api/ready')" || exit 1

# Comando de inicialização
CMD ["sh", "-c", "uv run alembic upgrade head && uvicorn backend.app:app --host 0.0.0.0 --port $PORT --workers 2"]