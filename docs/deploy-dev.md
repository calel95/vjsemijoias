# Deploy DEV

Este projeto roda melhor em DEV remoto como um unico Web Service FastAPI:
o backend serve a API em `/api` e tambem entrega o frontend estatico.

## Recomendacao

Para testar de qualquer lugar, use:

- VPS com Dokploy e build por Railpack para a aplicacao FastAPI.
- Postgres gerenciado para o banco, como Neon ou Postgres criado no Dokploy.
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
DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require
PUBLIC_BASE_URL=https://dev.seudominio.com
CORS_ALLOWED_ORIGINS=https://dev.seudominio.com
ADMIN_PASSWORD=uma-senha-dev-forte
SECRET_KEY=uma-chave-longa
JWT_SECRET_KEY=outra-chave-longa
INFINITEPAY_HANDLE=sua_infinite_tag
RATE_LIMIT_ENABLED=true
ADMIN_COOKIE_SECURE=true
ADMIN_COOKIE_SAMESITE=lax
USER_COOKIE_SECURE=true
USER_COOKIE_SAMESITE=lax
CSRF_COOKIE_SECURE=true
```

Use `.env.dev.example` como checklist. Nunca envie `backend/.env` para o Git.

## Dokploy com Railpack

Esse e o caminho recomendado para DEV em VPS. O projeto inclui
`railpack.json`, entao o Dokploy/Railpack deve:

- detectar o projeto como Python por causa do `pyproject.toml`;
- usar Python 3.12;
- instalar dependencias pelo `uv.lock`;
- iniciar com Alembic antes do Uvicorn.

No Dokploy:

- Source: repositorio Git do projeto.
- Branch: `dev`.
- Build Type: Railpack.
- Port: `5000`.
- Healthcheck Path: `/api/ready`.
- Domain: `https://dev.seudominio.com`.

O `railpack.json` define este start command:

```bash
alembic upgrade head && uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-5000}
```

Se voce preferir configurar pelo painel, use a variavel abaixo. Ela tem
prioridade sobre o `railpack.json`:

```dotenv
RAILPACK_START_CMD=alembic upgrade head && uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-5000}
```

Variaveis minimas no Dokploy:

```dotenv
APP_ENV=development
DEBUG=false
PORT=5000
RAILPACK_PYTHON_VERSION=3.12
DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require
PUBLIC_BASE_URL=https://dev.seudominio.com
CORS_ALLOWED_ORIGINS=https://dev.seudominio.com
SECRET_KEY=gere-uma-chave-longa
JWT_SECRET_KEY=gere-outra-chave-longa
ADMIN_PASSWORD=uma-senha-dev-forte
ADMIN_COOKIE_SECURE=true
ADMIN_COOKIE_SAMESITE=lax
USER_TOKEN_EXPIRE_DAYS=7
USER_COOKIE_SECURE=true
USER_COOKIE_SAMESITE=lax
CSRF_COOKIE_SECURE=true
INFINITEPAY_HANDLE=sua_infinite_tag
INFINITEPAY_API_BASE=https://api.checkout.infinitepay.io
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=seu_account_id_cloudflare
R2_BUCKET=vjsemijoias-dev
R2_ACCESS_KEY_ID=sua_access_key_id
R2_SECRET_ACCESS_KEY=sua_secret_access_key
R2_PUBLIC_BASE_URL=https://assets-dev.seudominio.com
RATE_LIMIT_ENABLED=true
```

O arquivo `.dockerignore` tambem e usado pelo Railpack para montar o contexto
de build. Ele exclui `.env`, `backend/.env`, banco local, caches, uploads e
imagens geradas do catalogo.

## Rate limiting

O backend limita apenas rotas `/api`, por IP, e ignora arquivos estaticos,
imagens, `/api/health` e `/api/ready`.

Valores iniciais recomendados para DEV:

```dotenv
RATE_LIMIT_ENABLED=true
RATE_LIMIT_GLOBAL_PER_MINUTE=300
RATE_LIMIT_PUBLIC_PER_MINUTE=180
RATE_LIMIT_AUTH_PER_MINUTE=20
RATE_LIMIT_REGISTER_PER_HOUR=5
RATE_LIMIT_WRITE_PER_MINUTE=60
RATE_LIMIT_EXPENSIVE_PER_MINUTE=5
```

As rotas de importacao de catalogo e geracao de PDF entram no limite
`EXPENSIVE`. Registro de usuarios tem limite proprio por hora para reduzir
criacao automatizada de contas. Em PRD com mais de uma instancia, prefira
reforcar tambem no proxy/edge ou migrar os contadores para Redis.

## Frete externo

Comece em DEV com o provider interno. Ele usa as regras comerciais do admin ou
do ambiente e serve como fallback quando a API externa falhar:

```dotenv
SHIPPING_PROVIDER=internal
SHIPPING_MODE=free
SHIPPING_FIXED_VALUE=0
SHIPPING_FREE_MINIMUM=0
SHIPPING_ESTIMATED_DAYS=5-10
```

Para testar Melhor Envio, habilite o provider externo e informe o token e o CEP
de origem. O backend tenta o Melhor Envio somente quando houver CEP de destino e
pacote calculado pelos itens do carrinho; se a API falhar, volta para o provider
interno.

```dotenv
SHIPPING_PROVIDER=melhor_envio
MELHOR_ENVIO_API_BASE=https://www.melhorenvio.com.br/api/v2
MELHOR_ENVIO_TOKEN=seu_token
MELHOR_ENVIO_FROM_POSTAL_CODE=01001000
# Opcional: restrinja servicos especificos, por exemplo PAC/Sedex conforme sua conta.
MELHOR_ENVIO_SERVICES=1,2
MELHOR_ENVIO_TIMEOUT_SECONDS=6
```
## E-mails transacionais

Em DEV, comece com o backend `console`, que registra os e-mails sem enviar para
clientes reais:

```dotenv
EMAIL_BACKEND=console
EMAIL_FROM_NAME=VJ Semijoias DEV
EMAIL_FROM_ADDRESS=nao-responda@dev.seudominio.com
```

Quando for testar envio real, configure SMTP:

```dotenv
EMAIL_BACKEND=smtp
EMAIL_SMTP_HOST=smtp.seu-provedor.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=usuario
EMAIL_SMTP_PASSWORD=senha
EMAIL_SMTP_USE_TLS=true
```

## Render

O arquivo `render.yaml` continua como alternativa caso voce queira manter ou
comparar o deploy do Render.

Se criar manualmente pelo dashboard:

- Service type: Web Service
- Runtime: Python
- Build Command:

```bash
pip install uv && uv sync --frozen --no-dev
```

- Start Command:

```bash
uv run alembic upgrade head && uv run uvicorn backend.app:app --host 0.0.0.0 --port $PORT
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

O start do Render roda:

```bash
uv run alembic upgrade head
```

Isso cria/atualiza o schema no Postgres DEV antes de iniciar o app. O app tambem tem bootstrap para
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

### Imagens 404 no DEV remoto

Se os logs do deploy mostrarem requisicoes como:

```text
GET /images/catalog/.../img_1.jpeg 404 Not Found
```

o banco esta apontando para caminhos locais do projeto. Em DEV remoto, isso
normalmente significa que o import foi feito com `STORAGE_BACKEND=local` ou que
os produtos ja existiam no banco com caminhos locais.

Corrija assim:

1. Configure no Dokploy ou na plataforma usada:

```dotenv
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=...
R2_BUCKET=vjsemijoias-dev
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_PUBLIC_BASE_URL=https://...
```

2. Redeploy/restart o servico.
3. Importe novamente a mesma pasta do catalogo pelo admin.

A importacao e idempotente: os produtos existentes sao atualizados e as imagens
passam a salvar URLs publicas do R2 no banco.

## Alternativa rapida: tunnel local

Se voce so quer mostrar/testar hoje sem subir infraestrutura, pode manter local
e expor temporariamente com Cloudflare Tunnel ou ngrok. Isso usa seu banco local
e seu computador precisa ficar ligado.

Esse caminho e otimo para validacao rapida, mas nao substitui DEV remoto.
