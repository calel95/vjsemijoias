# Testes

## Suite rapida

```powershell
$env:APP_ENV='test'
$env:DATABASE_URL='sqlite+pysqlite:///./ci.db'
uv --cache-dir .uv-cache run pytest -q
```

## Cobertura

```powershell
$env:APP_ENV='test'
$env:DATABASE_URL='sqlite+pysqlite:///./ci.db'
uv --cache-dir .uv-cache run pytest --cov=backend --cov-report=term-missing
```

A configuracao atual exige pelo menos 80% de cobertura do backend quando o
relatorio de cobertura e executado.

## Smoke E2E

```powershell
$env:APP_ENV='test'
$env:DATABASE_URL='sqlite+pysqlite:///./ci.db'
uv --cache-dir .uv-cache run python tools\e2e_smoke.py
```

Use o smoke depois de mudancas em checkout, admin, pagamento, produtos ou
configuracao de loja. Ele valida os fluxos principais com `TestClient` e mocks
dos provedores externos.
