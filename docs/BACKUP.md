# Backup e exportacao operacional

Este documento cobre os cuidados minimos antes de usar o VJ Admin em piloto ou producao.

## Backup PostgreSQL com pg_dump

Use `pg_dump` contra a `DATABASE_URL` do ambiente de producao. Gere o arquivo em um local seguro, fora do servidor da aplicacao.

```powershell
$env:DATABASE_URL="postgresql://usuario:senha@host/banco?sslmode=require"
pg_dump $env:DATABASE_URL --format=custom --file backup-vjsemijoias-$(Get-Date -Format yyyyMMdd-HHmm).dump
```

Para um dump SQL texto, use:

```powershell
pg_dump $env:DATABASE_URL --file backup-vjsemijoias-$(Get-Date -Format yyyyMMdd-HHmm).sql
```

## Restaurar com psql ou pg_restore

Para arquivo `.dump` em formato custom:

```powershell
pg_restore --clean --if-exists --dbname $env:DATABASE_URL backup-vjsemijoias-YYYYMMDD-HHMM.dump
```

Para arquivo `.sql`:

```powershell
psql $env:DATABASE_URL --file backup-vjsemijoias-YYYYMMDD-HHMM.sql
```

Antes de restaurar em producao, teste a restauracao em um banco temporario.

## Frequencia recomendada

- Piloto: backup diario automatico e backup manual antes de deploy.
- Producao: backup automatico diario, retencao minima de 7 a 30 dias e backup manual antes de migrations.
- Antes de qualquer `alembic upgrade head` em producao, gere um backup novo e confirme que o arquivo foi criado.

## Exports CSV disponiveis

Todos exigem login administrativo.

- `GET /api/vj-admin/produtos/export.csv`
- `GET /api/vj-admin/clientes/export.csv`
- `GET /api/vj-admin/pedidos/export.csv`
- `GET /api/vj-admin/financeiro/despesas/export.csv`
- `GET /api/vj-admin/financeiro/resumo/export.csv`

Os CSVs sao complementares ao backup do banco. Eles ajudam em conferencia operacional, mas nao substituem `pg_dump`.

## Cuidados antes de deploy

1. Gerar backup do banco atual.
2. Rodar `uv --cache-dir .uv-cache run alembic upgrade head`.
3. Rodar `uv --cache-dir .uv-cache run alembic check`.
4. Conferir variaveis `DATABASE_URL`, `ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `SECRET_KEY`, `PUBLIC_BASE_URL` e credenciais InfinitePay.
5. Confirmar que `USER_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` estao adequados para HTTPS.
6. Testar login admin, cadastro de produto, movimentacao de estoque, pedido, financeiro e dashboard.
7. Conferir `/api/vj-admin/auditoria` apos executar acoes criticas.