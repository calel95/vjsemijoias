# VJ Semijoias

Loja virtual de semijoias com vitrine responsiva, carrinho, checkout, login,
catálogo administrável, pagamentos InfinitePay e backend Python com FastAPI.

## Tecnologias

- Frontend: HTML, CSS e JavaScript
- Backend: Python 3.12, FastAPI e SQLAlchemy 2
- Banco: SQLite
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
uv sync
uv run uvicorn backend.app:app --host 0.0.0.0 --port 5000 --reload
```

5. Acesse `http://localhost:5000`.

O FastAPI serve tanto a API em `/api` quanto os arquivos do site. Não é
necessário abrir outro servidor para o frontend.

A documentação interativa fica disponível em `http://localhost:5000/docs`.

No grupo **Admin - Catálogo PDF**, o endpoint `POST /api/admin/catalog-pdf`
permite enviar imagens e gerar o catálogo final diretamente pelo Swagger. Faça
login administrativo, use o token no botão **Authorize** e envie os metadados
opcionais separados por `|`, respeitando a ordem das imagens.

As páginas também possuem URLs sem extensão, como `/admin`, `/catalogo`,
`/produto` e `/checkout`. Os endereços antigos com `.html` continuam válidos.

## Estrutura do projeto

```text
backend/        API FastAPI, banco e importacao de produtos
frontend/       HTML, CSS, JavaScript, imagens, PWA e PDFs publicos
import_data/    arquivos-fonte usados nas importacoes
tests/          testes automatizados
tools/          scripts de geracao e manutencao
.agent/skills/  skills locais para extrair e gerar catalogos
```

Mantenha na raiz apenas arquivos de configuracao e documentacao do projeto.

## Testes

```powershell
uv run pytest
```

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
