# Auditoria de Midia e Imagens

## Objetivo da auditoria

Esta auditoria documenta o fluxo atual de imagens de produto da VJ Semijoias e prepara a evolucao futura para uma arquitetura de midia mais escalavel, sem implementar Cloudflare R2, sem alterar upload, sem alterar banco, sem alterar APIs e sem modificar o frontend visual nesta sprint.

O foco e tecnico e arquitetural: identificar onde as imagens estao armazenadas, como os produtos referenciam essas imagens, quais pontos consomem os campos atuais, quais riscos existem no crescimento do catalogo e qual caminho seguro seguir em sprints futuras.

## Resumo executivo

O projeto ja possui uma base parcial para gestao de imagens:

- O modelo `Product` possui `image` como imagem principal.
- O modelo `ProductImage` permite galeria ordenada por `position`.
- A API publica retorna `image`, `imagem_url` e `images` no `Product.to_dict()`.
- O importador de catalogo copia imagens para `frontend/images/catalog/` em modo local ou grava em R2 quando `STORAGE_BACKEND=r2` esta ativo.
- O admin legado aceita multiplas imagens por upload/base64 ou URLs em linhas separadas.
- O VJ Admin modular trabalha hoje com campo `Imagem URL` unico, mas o backend transforma essa imagem em galeria de uma imagem.
- O frontend publico usa a imagem principal nos cards e carrinho, e usa `images` na pagina de produto e no SEO/JSON-LD.

A conclusao principal e que o projeto esta pronto para evoluir, mas ainda existe acoplamento relevante entre produto, caminho local estatico e string salva no banco. A proxima sprint deve preparar uma abstracao formal de midia antes de ampliar upload, galeria ou storage externo.

## Estado atual do armazenamento

Hoje as imagens podem vir de cinco origens principais.

| Origem | Como funciona hoje | Observacao |
|---|---|---|
| Seed local | `backend/services/startup.py` cria produtos com imagens em `images/products/*.svg` | Usado quando o banco esta vazio. |
| Catalogo importado local | `backend/import_products.py` copia imagens para `frontend/images/catalog/<produto>/img_N.ext` | `frontend/images/catalog/` esta no `.gitignore`, mas ha arquivos antigos ainda rastreados pelo Git. |
| URLs externas ou caminhos manuais | Admins podem salvar uma string em `image`/`imagem_url` | Pode ser URL absoluta ou caminho relativo servido pelo frontend. |
| Upload admin em data URL | O admin legado envia imagens como data URL; `backend/services/product_media.py` valida e grava localmente ou em R2 | Suporta multiplas imagens no endpoint `/api/products`. |
| R2 configurado | `backend/services/storage.py` grava em Cloudflare R2 quando `STORAGE_BACKEND=r2` | A infraestrutura existe, mas esta auditoria nao ativa nem altera R2. |

Inventario local observado nesta auditoria:

- `frontend/images/products/`: 10 SVGs seed, cerca de 0,02 MB.
- `frontend/images/catalog/`: 235 arquivos locais, cerca de 25,66 MB.
- `frontend/images/`: 247 arquivos no total, cerca de 25,8 MB.
- `frontend/images/catalog/` esta ignorado pelo Git para novas imagens, mas `git ls-files frontend/images/catalog` ainda mostra 79 arquivos rastreados historicamente.

## Mapa dos campos de imagem

| Campo | Local | Papel atual |
|---|---|---|
| `Product.image` | `backend/models/products.py` | Imagem principal do produto. Armazena caminho relativo local ou URL publica. |
| `ProductImage.path` | `backend/models/products.py` | Imagens da galeria, ordenadas por `position`. |
| `Product.gallery_images` | Relacionamento SQLAlchemy | Fonte da lista `images` no `to_dict()`. |
| `image` | API publica/admin | Campo de imagem principal retornado ao frontend. |
| `imagem_url` | API/admin em portugues | Alias de `image`, usado pelo VJ Admin modular. |
| `images` | API publica/admin | Lista derivada de `ProductImage.path`; se a galeria estiver vazia, cai para `[image]`. |
| `icon` | Produto/API/frontend | Fallback visual quando nao ha imagem ou quando a imagem falha. |
| `badge` | Produto/API/frontend | Selo comercial real do produto, sem relacao direta com midia. |

Nao foi identificado campo `image_url` como contrato principal. O contrato real hoje e `image` no publico e `imagem_url` no VJ Admin modular.

## Como as imagens entram no sistema

### Seed/mock inicial

`backend/services/startup.py` popula produtos seed quando o banco esta vazio. Cada produto recebe `image` apontando para `images/products/*.svg` e tambem cria `ProductImage(path=image, position=0)`.

### Importacao de catalogo

`backend/import_products.py` le `manifest.json`, valida imagens declaradas em `images`, copia ou envia cada arquivo para storage e atualiza:

- `product.image` com a primeira imagem.
- `product.gallery_images` com todas as imagens ordenadas.
- `ProductImport` com `source_key`, `source_page` e `source_folder`.

A importacao aceita `.jpg`, `.jpeg`, `.png`, `.webp` e `.gif`, valida conteudo com Pillow via `validate_image_bytes()` e aplica limite de 20 MB por imagem.

A rota `/api/products/import-folder` aceita pasta com exatamente um `manifest.json`, limita arquivo individual a 20 MB e total da importacao a 250 MB.

### Admin legado

`frontend/admin.html` e `frontend/js/admin.js` possuem fluxo mais completo de imagens:

- Campo de arquivo `image-input` com `multiple`.
- Campo `image-url` com uma URL por linha.
- Preview de galeria.
- Payload com `data.images` e `data.image`.

No backend, `/api/products` usa `product_image_list()`, `store_admin_gallery_images()` e `replace_product_gallery()` para validar data URLs, armazenar arquivos e reconstruir a galeria.

### VJ Admin modular

`frontend/vj-admin.html` possui o campo `Imagem URL` (`product-imagem`). `frontend/js/vj-admin/products.js` envia `imagem_url` no payload.

`backend/routers/vj_admin_products.py` cria ou atualiza produto com `product_payload()`. Quando `image` esta presente, chama `store_admin_gallery_images(product, [product.image])` e `replace_product_gallery()`. Na pratica, o VJ Admin modular suporta uma imagem por vez no formulario atual, embora o backend use a mesma estrutura de galeria.

### PDF de catalogo

`backend/routers/catalog_pdf.py` possui fluxo separado para gerar PDF a partir de uploads temporarios. Essas imagens sao validadas e usadas no PDF, mas nao viram imagens persistentes de produto.

## Onde as imagens sao consumidas

| Ponto | Arquivo | Uso atual |
|---|---|---|
| Home | `frontend/index.html` + `createProductCard()` | Exibe produtos em destaque usando `product.image`. |
| Catalogo | `frontend/catalogo.html` + `frontend/js/main.js` | Cards usam `product.image`; se falhar, exibem `icon`. Nao usam galeria. |
| Produto | `frontend/produto.html` | Usa `product.images` como galeria; se vazio, usa `product.image`; imagem principal tem `loading="eager"`, `fetchpriority="high"`, `width` e `height`. |
| Relacionados | `frontend/produto.html` + `createProductCard()` | Reaproveitam card do catalogo e usam `product.image`. |
| Carrinho | `frontend/js/cart.js`, `frontend/carrinho.html` | Ao adicionar, salva `product.image`; ao sincronizar, usa `product.image || product.images?.[0] || item.image`. |
| Checkout | `frontend/checkout.html` | Mostra `item.image` vindo do carrinho. |
| Pedido/pos-compra | `frontend/pedido.html` | Nao consome imagem de produto de forma relevante hoje; foca em status e itens. |
| SEO/JSON-LD | `frontend/js/seo.js` | Usa `product.images` quando existe, senao `product.image`, senao logo padrao. Preenche `Product.image`, Open Graph e Twitter image. |
| Service worker | `frontend/service-worker.js` | Pre-cache dos SVGs seed e cache dinamico limitado das imagens de `/api/products`. |
| PDF catalogo | `backend/catalog_pdf.py` e `backend/routers/catalog_pdf.py` | Usa uploads temporarios independentes do cadastro de produto. |

## Service worker e cache

O service worker atual (`vj-semijoias-v28`) faz:

- Pre-cache de paginas publicas, CSS/JS comuns, logos, SVGs seed e PDF publico.
- Network-first para `/api/products` com fallback de cache.
- Cache automatico de imagens de produto encontradas na resposta de `/api/products`, limitado a 24 URLs e 300 KB por imagem.
- Cache de imagens por `caches.match()` e fallback para rede.
- Ignora imagens externas no pre-cache dinamico de produtos, pois `productImageUrls()` so adiciona imagens da mesma origem.

Esse desenho reduz risco de cache infinito, mas ainda exige cuidado quando o catalogo real crescer ou quando as URLs passarem para CDN/R2 em outro dominio.

## SEO e performance

O SEO do produto esta centralizado em `frontend/js/seo.js`:

- JSON-LD `Product` usa todas as imagens de `product.images` quando disponiveis.
- `applyProductSEO()` usa a primeira imagem para `og:image`, `twitter:image` e preload.
- A pagina de produto prioriza a imagem principal e lazy-load nas miniaturas.

A documentacao de performance existente ja aponta que imagens reais do catalogo sao o maior risco futuro para LCP, cache e peso de pagina. O alvo sugerido em `docs/PERFORMANCE_BASELINE.md` e buscar imagens principais abaixo de 150 KB por variante exibida no mobile.

## Riscos encontrados

### Alto risco

- `Product.image` mistura caminho relativo local e URL absoluta. Isso dificulta migracao, validacao, cache e backup.
- `frontend/images/catalog/` esta ignorado para novas imagens, mas parte do historico ainda esta rastreada; isso pode confundir deploys e revisoes.
- Produtos importados localmente podem salvar caminhos `images/catalog/...` no banco; em ambiente remoto sem esses arquivos, geram 404.
- O VJ Admin modular mostra apenas uma `Imagem URL`, enquanto o backend e o admin legado ja trabalham com galeria. Ha diferenca de capacidade entre interfaces administrativas.
- Cards do catalogo e home usam apenas `product.image`; se a galeria existir mas `image` estiver vazio/inconsistente, o card perde a imagem mesmo que `images` tenha dados.

### Medio risco

- Falta uma entidade/servico de midia com contrato unico para origem, tipo, tamanho, ordem, alt text, status e URL publica.
- Nao ha variantes responsivas (`thumbnail`, `card`, `detail`, `original`) nem conversao WebP/AVIF.
- Nao ha auditoria visual automatica para URLs quebradas em catalogo/produto/carrinho/checkout.
- R2 ja existe como caminho tecnico, mas ainda depende de variaveis de ambiente e reimportacao para corrigir registros antigos.
- Cache de imagens externas futuras precisara de politica clara de CORS, TTL, CDN e service worker.

### Baixo risco

- `icon` e placeholders evitam quebra visual total quando a imagem falha.
- O produto ja tem galeria no backend e no frontend publico de detalhe.
- `validate_image_bytes()` reduz risco de upload invalido em fluxos que passam pelo backend.
- A importacao tem limites por arquivo e por lote.

## Arquitetura recomendada em fases

### Fase 1 — Preparar abstracao de midia

Objetivo: criar contrato interno de midia sem mudar comportamento publico.

Recomendacoes:

- Criar service de leitura/normalizacao de midia, por exemplo `backend/services/media.py` ou evoluir `product_media.py`.
- Padronizar funcao que resolva imagem principal, galeria e fallback.
- Garantir que API sempre retorne `image` como primeira imagem publica e `images` como lista confiavel.
- Documentar diferenca entre URL absoluta, caminho relativo legado e data URL temporaria.
- Adicionar testes de fallback quando `image` esta vazio e `gallery_images` existe.

### Fase 2 — Consolidar storage externo

Objetivo: usar Cloudflare R2 com seguranca, sem quebrar caminhos antigos.

Recomendacoes:

- Manter `STORAGE_BACKEND=local` para desenvolvimento local simples.
- Usar `STORAGE_BACKEND=r2` em DEV/PRD remotos.
- Definir `R2_PUBLIC_BASE_URL` com dominio estavel de assets.
- Criar rotina de validacao de configuracao (`/api/admin/storage/status` ja existe para admin legado).
- Garantir fallback para imagens antigas `images/catalog/...` enquanto a migracao nao termina.

### Fase 3 — Upload pelo VJ Admin modular

Objetivo: trazer a experiencia de upload para o VJ Admin atual.

Recomendacoes:

- Adicionar componente de upload no VJ Admin modular, reutilizando regras de validacao existentes.
- Evitar gravar data URL permanente no banco; data URL deve ser apenas transporte temporario.
- Exibir preview, erro de tamanho/formato e status de upload.
- Manter routers apenas como HTTP e services cuidando de regra/infra.

### Fase 4 — Multiplas imagens por produto

Objetivo: transformar galeria em funcionalidade operacional completa.

Recomendacoes:

- Permitir reordenacao no VJ Admin modular.
- Manter primeira imagem como principal.
- Preparar alt text por imagem em uma sprint futura, se houver necessidade de SEO/acessibilidade avancada.
- Ajustar cards publicos para usarem fallback `product.images?.[0]` quando `product.image` estiver ausente.

### Fase 5 — Migracao gradual das imagens antigas

Objetivo: retirar dependencia de arquivos locais no deploy remoto.

Recomendacoes:

- Criar script idempotente de migracao local/R2 em sprint propria.
- Migrar em lotes, registrar origem e destino, e preservar rollback.
- Revalidar `/api/products`, catalogo, produto, carrinho, checkout, pedido e SEO apos cada lote.
- Remover imagens antigas do Git somente com plano explicito e backup confirmado.

## Arquivos candidatos para futuras alteracoes

### Backend

- `backend/models/products.py`
- `backend/services/product_media.py`
- `backend/services/storage.py`
- `backend/services/validation.py`
- `backend/services/vj_products.py`
- `backend/services/product_payload.py`
- `backend/import_products.py`
- `backend/routers/admin_products.py`
- `backend/routers/vj_admin_products.py`
- `backend/routers/product_imports.py`
- `backend/routers/public_products.py`
- `backend/routers/catalog_pdf.py`
- `backend/catalog_pdf.py`

### Frontend publico

- `frontend/js/main.js`
- `frontend/js/products.js`
- `frontend/js/cart.js`
- `frontend/js/seo.js`
- `frontend/service-worker.js`
- `frontend/index.html`
- `frontend/catalogo.html`
- `frontend/produto.html`
- `frontend/carrinho.html`
- `frontend/checkout.html`
- `frontend/pedido.html`

### Admin

- `frontend/vj-admin.html`
- `frontend/js/vj-admin/products.js`
- `frontend/js/vj-admin/api.js`
- `frontend/admin.html`
- `frontend/js/admin.js`

### Dados, imagens e documentacao

- `frontend/images/products/`
- `frontend/images/catalog/`
- `import_data/`
- `.gitignore`
- `.dockerignore`
- `docs/deploy-dev.md`
- `docs/PERFORMANCE_BASELINE.md`
- `docs/testing.md`

## Testes recomendados para futuras implementacoes

### Unitarios/backend

- Validacao de tipo MIME e extensao real.
- Rejeicao de imagem vazia, imagem acima do limite e conteudo com tipo divergente.
- Geracao correta de URL publica em R2.
- Fallback local quando `STORAGE_BACKEND=local`.
- Falha clara quando `STORAGE_BACKEND=r2` esta incompleto.
- `Product.to_dict()` com `image`, `images` e `imagem_url` consistentes.
- Produto com `image` vazio e `ProductImage` preenchido.
- Produto com galeria vazia e `image` preenchido.

### Integracao/admin

- Criacao de produto com URL externa.
- Criacao de produto com upload de uma imagem.
- Criacao de produto com multiplas imagens.
- Edicao que remove imagem.
- Edicao que reordena imagens.
- Importacao de pasta com manifest e imagens validas.
- Importacao rejeitando caminho invalido, extensao proibida e lote acima do limite.

### Frontend publico

- Catalogo renderiza imagem principal ou fallback.
- Produto renderiza galeria e troca imagem principal.
- Carrinho preserva imagem ao adicionar e sincroniza com dados atualizados.
- Checkout mostra imagem do item sem alterar total/preco/frete.
- Pedido continua funcionando mesmo sem imagens.
- SEO/JSON-LD inclui imagens absolutas corretas.
- Service worker nao cresce cache sem limite.

### Smoke E2E

- `/api/products` retorna produtos com imagens coerentes.
- Home, catalogo, produto, carrinho e checkout carregam sem 404 evidente de imagem.
- Upload/importacao no admin nao quebra autenticacao nem auditoria.
- Fluxo de pedido continua sem mudanca de payload comercial.

## Recomendacao para a proxima sprint

A proxima sprint deve ser a Fase 1: abstracao e contrato de midia.

Escopo recomendado:

- Nao iniciar upload novo ainda.
- Nao migrar imagens ainda.
- Criar uma camada unica para resolver midia de produto.
- Garantir compatibilidade total com `image`, `imagem_url`, `images` e `ProductImage`.
- Adicionar testes de fallback e serializacao.
- Preparar o VJ Admin modular para receber upload em uma sprint posterior.

Essa fase reduz risco antes de ligar Cloudflare R2 como dependencia operacional do catalogo.

## Validacoes desta sprint documental

Como esta sprint nao altera codigo de producao, as validacoes obrigatorias sao:

- `git diff --check`.
- `uv run pytest`, se nao houver impedimento.

`node --check` nao e necessario porque nenhum JavaScript foi alterado. Alembic nao deve ser executado porque nao houve alteracao de schema, banco ou migrations.