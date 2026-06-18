# Deploy DEV

Este projeto roda melhor em DEV remoto como um unico Web Service FastAPI:
o backend serve a API em `/api` e tambem entrega o frontend estatico.

## Recomendacao

Para testar de qualquer lugar, use:

- Render Web Service para a aplicacao FastAPI.
- Postgres gerenciado para o banco, como Neon ou Render Postgres.
- `PUBLIC_BASE_URL` apontando para a URL publica do ambiente DEV.
- Cloudflare R2 para imagens de catalogo e uploads do painel admin.

Evite SQLite em deploy remoto. O arquivo local `instance/vjsemijoias.db` funciona
bem no computador, mas em plataformas com filesystem efemero ele pode sumir ou
ficar diferente entre deploys/restarts.

## Antes do deploy

1. Confirme que os testes passam:

```powershell
uv --cache-dir .uv-cache run pytest -q
uv --cache-dir .uv-cache run python tools\e2e_smoke.py
```

2. Crie um banco Postgres DEV e copie a connection string.

3. Use variaveis diferentes do ambiente local:

```dotenv
APP_ENV=development
DEBUG=false
DATABASE_URL=postgresql://usuario:senha@host/neondb?sslmode=require&channel_binding=require
PUBLIC_BASE_URL=https://seu-servico-dev.onrender.com
CORS_ALLOWED_ORIGINS=https://seu-servico-dev.onrender.com
ADMIN_PASSWORD=uma-senha-dev-forte
SECRET_KEY=uma-chave-longa
JWT_SECRET_KEY=outra-chave-longa
INFINITEPAY_HANDLE=sua_infinite_tag
```

Use `.env.dev.example` como checklist. Nunca envie `backend/.env` para o Git.

## Render

O arquivo `render.yaml` ja deixa uma configuracao inicial pronta.

Se criar manualmente pelo dashboard:

- Service type: Web Service
- Runtime: Python
- Build Command:

```bash
pip install uv && uv sync --frozen --no-dev && uv run alembic upgrade head
```

- Start Command:

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

- Health Check Path:

```text
/api/ready
```

Depois do primeiro deploy, acesse:

```text
https://seu-servico-dev.onrender.com/api/health
https://seu-servico-dev.onrender.com/api/ready
https://seu-servico-dev.onrender.com/admin
```

## Banco e migrations

O build do Render roda:

```bash
uv run alembic upgrade head
```

Isso cria/atualiza o schema no Postgres DEV. O app tambem tem bootstrap para
popular produtos seed quando o banco esta vazio, mas o catalogo real precisa
ser importado no ambiente DEV.

## Catalogo e imagens

Atencao: os produtos importados podem referenciar imagens em
`frontend/images/catalog/`, e essa pasta nao esta versionada no Git. Para DEV,
o caminho recomendado e usar Cloudflare R2.

Crie um bucket R2, por exemplo:

```text
vjsemijoias-dev
```

Depois crie um token S3/R2 com permissao de escrita nesse bucket e configure:

```dotenv
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=seu_account_id_cloudflare
R2_BUCKET=vjsemijoias-dev
R2_ACCESS_KEY_ID=sua_access_key_id
R2_SECRET_ACCESS_KEY=sua_secret_access_key
R2_PUBLIC_BASE_URL=https://seu-bucket-publico.r2.dev
```

Para testes, `r2.dev` funciona. Para um ambiente mais estavel, prefira um
subdominio proprio como `https://assets-dev.seudominio.com`.

Com `STORAGE_BACKEND=r2`, imagens enviadas pelo painel admin e imagens
importadas pelo catalogo sao gravadas no R2, e o banco salva a URL publica.

Se `STORAGE_BACKEND` ficar vazio ou `local`, o app volta ao comportamento local
e salva em `frontend/images/catalog/`.

## Alternativa rapida: tunnel local

Se voce so quer mostrar/testar hoje sem subir infraestrutura, pode manter local
e expor temporariamente com Cloudflare Tunnel ou ngrok. Isso usa seu banco local
e seu computador precisa ficar ligado.

Esse caminho e otimo para validacao rapida, mas nao substitui DEV remoto.
