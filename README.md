# VJ Semijoias

Loja virtual de semijoias com vitrine responsiva, carrinho, checkout, login,
catálogo administrável, pagamentos InfinitePay e backend Python com FastAPI.

## Tecnologias

- Frontend: HTML, CSS e JavaScript
- Backend: Python 3.12, FastAPI e SQLAlchemy 2
- Banco: SQLite ou PostgreSQL
- Dependências e ambiente: `uv`
- Autenticação: JWT
- Pagamentos: InfinitePay Checkout Integrado
- PWA: manifest e service worker

## Executar

1. Crie a configuração local:

```powershell
Copy-Item .env.example .env
```

2. Troque `SECRET_KEY`, `JWT_SECRET_KEY` e `ADMIN_PASSWORD` no `.env`.

3. Informe sua InfiniteTag, sem o símbolo `$`, e o endereço público da loja:

```dotenv
INFINITEPAY_HANDLE=sua_infinite_tag
PUBLIC_BASE_URL=https://seu-dominio.com
```

4. Instale as dependências e inicie a aplicação:

```powershell
uv --cache-dir .uv-cache sync
uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000
```

5. Acesse `http://localhost:5000`.

O FastAPI serve tanto a API em `/api` quanto os arquivos do site. Não é
necessário abrir outro servidor para o frontend.

Se quiser recarregamento automatico em desenvolvimento, adicione `--reload`.
Em alguns ambientes Windows ele pode falhar por permissao de processo; nesse
caso rode sem `--reload`.

A documentação interativa fica disponível em `http://localhost:5000/docs`.

No grupo **Admin - Catálogo PDF**, o endpoint `POST /api/admin/catalog-pdf`
permite enviar imagens e gerar o catálogo final diretamente pelo Swagger. Faça
login administrativo, use o token no botão **Authorize** e envie os metadados
opcionais separados por `|`, respeitando a ordem das imagens.

As páginas também possuem URLs sem extensão, como `/admin`, `/catalogo`,
`/produto` e `/checkout`. Os endereços antigos com `.html` continuam válidos.

## Banco e migrations

O projeto usa Alembic para versionar alteracoes no banco. Depois de configurar
`DATABASE_URL`, aplique as migrations:

```powershell
uv --cache-dir .uv-cache run alembic upgrade head
```

Para um banco novo, esse comando cria todas as tabelas atuais.

O app nao cria nem altera schema no startup; em DEV/PRD rode sempre as
migrations antes de iniciar o servidor.

Se o banco ja existe porque foi criado antes pelo app, marque a migration base
como aplicada e depois rode as proximas:

```powershell
uv --cache-dir .uv-cache run alembic stamp 20260617_0001
uv --cache-dir .uv-cache run alembic upgrade head
```

Quando alterar modelos em `backend/models.py`, crie uma nova migration:

```powershell
uv --cache-dir .uv-cache run alembic revision --autogenerate -m "descricao da alteracao"
uv --cache-dir .uv-cache run alembic upgrade head
```

## Deploy DEV

Para publicar um ambiente DEV acessivel fora do seu computador, veja
[docs/deploy-dev.md](docs/deploy-dev.md). O caminho recomendado agora e
Dokploy com Railpack, Postgres remoto e Cloudflare R2, evitando SQLite em
ambiente remoto.

## Seguranca do admin

O painel administrativo usa um token proprio, emitido somente por
`POST /api/auth/admin/login`. Esse token fica no `sessionStorage` do navegador,
ou seja, expira ao fechar a aba/janela, e tambem tem validade curta configuravel:

```env
ADMIN_TOKEN_EXPIRE_MINUTES=120
ADMIN_LOGIN_MAX_ATTEMPTS=5
ADMIN_LOGIN_LOCKOUT_SECONDS=300
```

Tokens comuns de usuario, mesmo de um usuario marcado como admin no banco, nao
acessam rotas administrativas. Para producao, use uma `ADMIN_PASSWORD` forte e
uma `JWT_SECRET_KEY` longa e aleatoria.

O login de clientes tambem usa cookie `HttpOnly`, configuravel por:

```env
USER_TOKEN_EXPIRE_DAYS=7
USER_COOKIE_NAME=vj_user_token
USER_COOKIE_SECURE=true
USER_COOKIE_SAMESITE=lax
CSRF_COOKIE_SECURE=true
```

Quando a autenticacao acontece por cookie, rotas autenticadas de escrita exigem
o header `X-CSRF-Token`, preenchido automaticamente pelo frontend a partir do
cookie `vj_csrf_token`.

## Estrutura do projeto

```text
backend/app.py       cria o FastAPI, registra middlewares, routers e arquivos estaticos
backend/routers/     endpoints FastAPI separados por dominio
backend/services/    regras reutilizaveis de pedido, pagamento, imagens e startup
backend/models.py    modelos SQLAlchemy
backend/database.py  engine, sessao e dependencia de banco
frontend/            HTML, CSS, JavaScript, imagens, PWA e PDFs publicos
import_data/         arquivos-fonte usados nas importacoes
tests/               testes automatizados
tools/               scripts de geracao e manutencao
.agent/skills/       skills locais para extrair e gerar catalogos
```

Ao criar novas funcionalidades, prefira adicionar o endpoint em
`backend/routers/` e deixar regras de negocio compartilhadas em
`backend/services/`. O `backend/app.py` deve continuar pequeno e focado apenas
na montagem da aplicacao.

Mantenha na raiz apenas arquivos de configuracao e documentacao do projeto.

## Testes

```powershell
uv run pytest
```

Para medir cobertura dos testes em `backend/` e `tools/`:

```powershell
uv run pytest --cov --cov-report=term-missing
```

Para validar os principais fluxos ponta a ponta sem tocar no banco real nem na
InfinitePay, rode o smoke test isolado:

```powershell
uv run python tools/e2e_smoke.py
```

Ele cobre paginas publicas, catalogo, login admin, protecao das rotas admin,
CRUD de produtos, checkout InfinitePay simulado, confirmacao de pagamento e
pedidos no painel.

## Importar catálogo

### A partir do PDF extraído

Coloque o catálogo extraído em `import_data/catalogo_extraido` com esta
estrutura:

```text
manifest.json
products.csv
products/<produto>/info.json
products/<produto>/img_1.jpeg
```

Confira a importação sem alterar o banco:

```powershell
uv run python -m backend.import_products --dry-run
```

Importe ou atualize o catálogo:

```powershell
uv run python -m backend.import_products
```

O processo é idempotente: a página e a pasta de origem identificam o produto,
portanto executar novamente atualiza os registros sem duplicá-los. As imagens
são copiadas para `frontend/images/catalog/` e produtos com várias fotos recebem uma
galeria na página de detalhes.

Também é possível importar pelo painel administrativo:

1. Acesse `/admin` e faça login.
2. Clique em **Importar Pasta de Produtos**.
3. Selecione a pasta completa `catalogo_extraido`.

Essa pasta deve conter `manifest.json` e a pasta `products/` com todas as
imagens referenciadas. O arquivo `products.csv` e os arquivos `info.json` podem
estar presentes, mas são opcionais para a importação.

### Catálogo manual por pastas

Quando você quiser montar o catálogo manualmente, use
`import_data/catalogo_manual`:

```text
import_data/catalogo_manual/
  manifest.json
  products/
    colar-coracao-personalizado/
      img_1.jpeg
      img_2.jpeg
```

Crie uma pasta para cada produto dentro de `products/` e coloque as fotos
dentro dela. Depois gere um manifest inicial com as imagens já preenchidas:

```powershell
uv run python tools/generate_manual_manifest.py import_data/catalogo_manual
```

Edite `import_data/catalogo_manual/manifest.json` e preencha nome, categoria,
preço, descrição e detalhes. Um exemplo fica em
`import_data/catalogo_manual/manifest.example.json`.

Confira sem alterar o banco:

```powershell
uv run python -m backend.import_products import_data/catalogo_manual --dry-run
```

Importe:

```powershell
uv run python -m backend.import_products import_data/catalogo_manual
```

Esse formato manual também pode ser enviado pelo admin em **Importar Pasta de
Produtos**, selecionando a pasta completa `catalogo_manual`.

## Rotas principais

- `GET /api/health`: estado da API
- `GET /api/products`: catálogo
- `POST /api/products/import-folder`: importa a pasta do catálogo
- `POST /api/auth/register`: cadastro
- `POST /api/auth/login`: login
- `POST /api/orders`: cria um pedido
- `GET /api/payments/config`: configuração pública do checkout
- `GET /api/store/config`: configuração pública de frete e cupom
- `POST /api/payments/infinitepay/checkout`: cria o link de pagamento
- `POST /api/payments/infinitepay/confirm`: valida o retorno do checkout
- `GET /api/payments/<pedido>/status`: consulta segura do pagamento
- `POST /api/payments/webhook/infinitepay`: confirmação da InfinitePay
- `POST /api/auth/admin/login`: login administrativo
- `POST|PUT|DELETE /api/products`: administração do catálogo

## Regras importantes

- O servidor recalcula preços, desconto e frete ao receber o pedido.
- Dados completos do cartão nunca passam pelo site; o pagamento acontece no
  checkout seguro hospedado pela InfinitePay.
- Valores, descontos e frete são recalculados no servidor antes da cobrança.
- Pix e cartão em até 12x são escolhidos no checkout da InfinitePay.
- O backend envia automaticamente este webhook ao criar o link:

```text
https://seu-dominio.com/api/payments/webhook/infinitepay
```

- O webhook exige HTTPS em produção. Antes de aprovar o pedido, o backend
  consulta `payment_check` na InfinitePay e confere o valor pago.
- O catálogo continua disponível offline, mas login, cadastro, admin e checkout
  exigem conexão com o backend.
- Imagens enviadas pelo admin são salvas em `frontend/images/catalog/admin/`
  e o banco armazena apenas os caminhos. Para produção com múltiplas instâncias,
  prefira armazenamento de objetos, como S3 ou Cloudflare R2.

## Configuracoes da loja

As configuracoes de marca, contato e catalogo ficam separadas das variaveis
tecnicas:

```env
STORE_NAME=VJ Semijoias
STORE_SHORT_NAME=VJ
STORE_TAGLINE=SEMIJOIAS
STORE_DESCRIPTION=Semijoias finas banhadas a ouro 18k.
STORE_SLOGAN=Brilhe em cada momento
STORE_LOGO_PATH=images/logo.png
STORE_EMAIL=contato@vjsemijoias.com
STORE_PHONE=(51) 98211-0842
STORE_WHATSAPP=51 982110842
STORE_INSTAGRAM=vj_semijoias
STORE_WEBSITE=www.vjsemijoias.com
STORE_CNPJ=
STORE_CATALOG_TITLE=CATALOGO VJ SEMIJOIAS
STORE_CATALOG_COLLECTION=Colecao Banhada a Ouro 18k
STORE_CATALOG_FILENAME=catalogo-vj-semijoias.pdf
```

O endpoint `GET /api/store/config` expõe a configuracao publica da loja para o
frontend: marca, contato, catalogo, frete e cupom.

## Frete e desconto por ambiente

Configure no `.env` local ou nas variaveis de ambiente do deploy:

```env
SHIPPING_MODE=free
SHIPPING_FIXED_VALUE=0
SHIPPING_FREE_MINIMUM=0
SHIPPING_ESTIMATED_DAYS=5-10

COUPONS_ENABLED=true
COUPON_CODE=VJ10
COUPON_DISCOUNT_PERCENT=10
COUPON_USAGE_LIMIT=100
```

Modos de frete:

- `free`: frete gratis.
- `fixed`: usa sempre `SHIPPING_FIXED_VALUE`.
- `threshold`: usa `SHIPPING_FIXED_VALUE`, mas zera o frete quando o subtotal for maior ou igual a `SHIPPING_FREE_MINIMUM`.

Exemplo para producao sem desconto e com frete fixo:

```env
SHIPPING_MODE=fixed
SHIPPING_FIXED_VALUE=19.90
SHIPPING_ESTIMATED_DAYS=5-10
COUPONS_ENABLED=false
```
