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

## Sprint 013 — Abstracao e contrato de midia

Status: concluida.

Decisao tecnica implementada:

- `backend/services/product_media.py` passou a centralizar a resolucao de midia publica de produto.
- `Product.to_dict()` passou a usar `serialize_product_media(product)` para preencher `image`, `imagem_url` e `images`.
- O contrato publico foi preservado: os mesmos campos continuam sendo retornados pelas APIs existentes.
- Nenhum caminho local foi alterado e nenhuma URL absoluta nova foi montada.
- Nenhum schema, migration, endpoint, frontend visual, carrinho, checkout, pedido, estoque, preco, frete ou pagamento foi alterado.

Regra de resolucao adotada:

1. Se `Product.gallery_images` possuir imagens validas, `images` vem da galeria ordenada por `position` e sem duplicidade.
2. Quando a galeria existe, `image` e `imagem_url` passam a ser a primeira imagem valida da galeria.
3. Se a galeria estiver vazia e `Product.image` existir, `image` e `imagem_url` usam `Product.image`, e `images` retorna uma lista com esse valor.
4. Se nao houver imagem valida, `image` e `imagem_url` ficam `None`, `images` retorna lista vazia e `icon` continua como fallback visual do frontend.

Impacto arquitetural:

- A logica de compatibilidade entre `image`, `imagem_url`, `images` e `ProductImage` deixou de ficar embutida diretamente no modelo.
- Produtos antigos com apenas `Product.image` continuam funcionando.
- Produtos com galeria passam a ter origem de midia previsivel, evitando divergencia entre imagem principal e primeira imagem da galeria.
- Entradas duplicadas de galeria sao normalizadas antes de serializar e antes de substituir a galeria em fluxos admin existentes.

Cobertura adicionada:

- Produto com apenas `Product.image`.
- Produto com `Product.image` e galeria.
- Produto com galeria e `Product.image` vazio.
- Produto sem imagem.
- Consistencia entre `image`, `imagem_url` e `images`.
- Galeria ordenada por `position`.
- Ausencia de duplicidade quando a mesma imagem aparece mais de uma vez.
- Compatibilidade com `icon` como fallback visual.

## Sprint 014 — Preparacao e validacao de storage externo R2

Status: concluida.

Decisao tecnica implementada:

- `backend/services/storage.py` passou a validar explicitamente `STORAGE_BACKEND` como `local` ou `r2`.
- `local` segue como padrao quando `STORAGE_BACKEND` esta vazio ou ausente.
- `r2` exige configuracao completa antes de operacoes que dependem de storage externo.
- `storage_status()` passou a retornar um diagnostico administrativo seguro, com backend ativo, prontidao, pendencias e booleans de configuracao.
- O endpoint existente `/api/admin/storage/status` continua sendo reutilizado, sem novo endpoint e sem exposicao de credenciais sensiveis.
- `store_public_file()` continua recusando gravacao externa quando R2 nao esta habilitado, sem tentar upload em modo local.

Regra de configuracao adotada:

| Cenario | Resultado |
|---|---|
| `STORAGE_BACKEND` vazio ou ausente | Usa `local`, pronto, sem exigir variaveis R2. |
| `STORAGE_BACKEND=local` | Mantem gravacao local nos fluxos existentes. |
| `STORAGE_BACKEND=r2` completo | R2 fica habilitado e pronto para operacoes futuras. |
| `STORAGE_BACKEND=r2` incompleto | Status aponta pendencias por nome de variavel, sem exibir valores. |
| `STORAGE_BACKEND` invalido | Status retorna erro claro e operacoes levantam `RuntimeError`. |

Variaveis esperadas para R2:

- `STORAGE_BACKEND=r2`.
- `R2_ACCOUNT_ID`.
- `R2_BUCKET`.
- `R2_ACCESS_KEY_ID`.
- `R2_SECRET_ACCESS_KEY`.
- `R2_PUBLIC_BASE_URL`.

Compatibilidade preservada:

- Nenhum upload novo foi criado.
- Nenhuma migracao de imagem antiga foi executada.
- Nenhum endpoint novo foi criado.
- Nenhum schema, migration, frontend publico, carrinho, checkout, pedido, pagamento, estoque, preco ou frete foi alterado.
- R2 nao se tornou dependencia obrigatoria do sistema.

Cobertura adicionada:

- Storage local como padrao.
- R2 desativado quando o backend e local.
- R2 completo com status pronto.
- R2 incompleto com erro seguro.
- `STORAGE_BACKEND` invalido com erro claro.
- `storage_status()` sem exposicao de `R2_ACCESS_KEY_ID` ou `R2_SECRET_ACCESS_KEY`.
- `store_public_file()` sem tentativa de upload quando R2 nao esta habilitado.
- `public_asset_url()` preservando caminho relativo local ou montando URL publica codificada.

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

## Sprint 015 — Upload de imagens no VJ Admin modular

Status: concluida.

Decisao tecnica implementada:

- O VJ Admin modular passou a oferecer upload de imagem de produto no formulario de criacao/edicao, reutilizando os services de midia e storage existentes.
- O campo `Imagem URL` foi mantido por compatibilidade. O usuario pode usar URL manual ou upload de arquivo.
- O upload usa `FileReader` apenas para gerar uma data URL temporaria como transporte no payload. A data URL nunca e persistida no banco.
- O backend reutiliza `product_payload()`, `store_admin_gallery_images()`, `replace_product_gallery()` e `validate_image_bytes()` para validar, armazenar e reconstruir a galeria.
- O preview da imagem e exibido no formulario, tanto para imagem cadastrada quanto para imagem selecionada antes de salvar.
- O botao "Remover imagem" permite limpar a selecao antes de salvar. Na edicao, enviar `imagem_url` vazio remove a imagem e limpa a galeria.
- A validacao frontend verifica extensao, tipo MIME e tamanho antes de enviar, mas o backend continua validando com Pillow e rejeitando formatos nao suportados (incluindo SVG).
- Nenhum schema, migration, endpoint novo, site publico, carrinho, checkout, pedido, pagamento, estoque, preco ou frete foi alterado.
- R2 nao se tornou obrigatorio. O modo local continua funcionando com `STORAGE_BACKEND=local`.
- R2 incompleto gera erro 500 sem expor credenciais.

Fluxo de upload no VJ Admin modular:

1. Usuario seleciona arquivo via input `product-imagem-file`.
2. Frontend valida extensao (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`), tipo MIME e tamanho (ate 8 MB).
3. `FileReader.readAsDataURL()` gera data URL temporaria para preview e transporte.
4. Ao salvar, o payload envia `imagem_url` com a data URL (ou URL manual, se nao houver arquivo).
5. Backend detecta data URL em `save_admin_image()`, valida com Pillow, armazena localmente ou em R2, e retorna caminho/URL final.
6. `replace_product_gallery()` reconstrui a galeria com a imagem final.
7. A resposta retorna `image`, `imagem_url` e `images` com o caminho final, nunca com data URL.

Compatibilidade com URL manual:

- Se o usuario digitar uma URL manual e nao selecionar arquivo, o payload envia a URL diretamente.
- Se o usuario selecionar arquivo, o campo de URL e limpo e a data URL tem prioridade no payload.
- Se o usuario comecar a digitar uma URL apos selecionar arquivo, a selecao de arquivo e descartada e a URL manual passa a ser usada.

Comportamento local/R2:

| Cenario | Resultado |
|---|---|
| `STORAGE_BACKEND=local` (padrao) | Imagem e gravada em `frontend/images/catalog/admin/<id>-<slug>/img_N.ext` |
| `STORAGE_BACKEND=r2` completo | Imagem e enviada para R2 e URL publica e retornada |
| `STORAGE_BACKEND=r2` incompleto | Erro 500 sem expor secrets |
| Sem `STORAGE_BACKEND` | Usa local por padrao |

Restricoes preservadas:

- Nenhum site publico, carrinho, checkout, pedido, pagamento, estoque, preco ou frete foi alterado.
- Nenhuma migration ou alteracao de schema foi executada.
- `Product.to_dict()` nao foi alterado.
- O contrato publico `image`/`imagem_url`/`images` foi preservado.
- Nenhuma imagem antiga foi migrada.
- Nenhuma imagem local foi removida.
- R2 nao foi ativado automaticamente.
- Nenhuma dependencia nova foi instalada.
- SVG e arquivos nao-imagem continuam rejeitados pelo backend.

Cobertura adicionada:

- Criacao de produto com URL manual continua funcionando.
- Criacao de produto com imagem data URL valida.
- Edicao de produto alterando imagem (URL manual para upload).
- Edicao de produto removendo imagem (envio de `imagem_url` vazio).
- Imagem invalida (SVG) gera erro 400 claro.
- Imagem com tipo MIME divergente gera erro 400 claro.
- `ProductImage` e criado corretamente com `path` e `position`.
- `product.image`, `imagem_url` e `images` continuam consistentes.
- Modo local nao exige R2.
- R2 incompleto gera erro 500 sem expor `R2_ACCESS_KEY_ID` ou `R2_SECRET_ACCESS_KEY`.

Arquivos alterados:

- `frontend/vj-admin.html`: adicionado input de arquivo, preview, hint e botao remover.
- `frontend/css/vj-admin.css`: adicionados estilos para area de upload e preview.
- `frontend/js/vj-admin/products.js`: adicionada logica de selecao, validacao, preview e transporte de imagem.
- `tests/test_vj_admin.py`: adicionados testes de upload, edicao, remocao, formato invalido, tipo divergente, consistencia, local e R2 incompleto.
- `docs/AUDIT_MEDIA_IMAGES.md`: atualizado com Sprint 015.

## Recomendacao para a proxima sprint

A proxima sprint recomendada e a Sprint 016 — Multiplas imagens/galeria no VJ Admin modular.

Motivo:

- O upload de imagem unica ja esta operacional no VJ Admin modular desde a Sprint 015.
- O backend ja suporta galeria com `ProductImage` ordenada por `position`.
- O admin legado ja trabalha com multiplas imagens, mas o VJ Admin modular ainda envia uma imagem por vez.
- A migracao gradual de imagens antigas para R2 pode ser feita em sprint posterior sem bloquear a evolucao da galeria.

Escopo recomendado:

- Permitir selecao e preview de multiplas imagens no VJ Admin modular.
- Reordenar imagens da galeria no formulario.
- Manter primeira imagem como principal.
- Reutilizar `store_admin_gallery_images()` e `replace_product_gallery()` com lista de imagens.
- Preservar compatibilidade com `image`, `imagem_url`, `images` e `ProductImage`.
- Deixar migracao gradual de imagens antigas para uma sprint posterior.

## Validacoes da Sprint 015

Validacoes obrigatorias desta sprint:

- `uv run pytest`.
- `uv run python tools/e2e_smoke.py`.
- `node --check` em `frontend/js/vj-admin/products.js` e `frontend/js/vj-admin/api.js`.
- `git diff --check`.

Alembic nao deve ser executado porque nao houve alteracao de schema, banco ou migrations.
