# Variantes de imagem

Este documento descreve a base de variantes de imagem criada na Sprint 018.

A Sprint 018 preparou a geracao de arquivos otimizados. A Sprint 019 ativou o uso de `card` no catalogo publico e a Sprint 020 ativou `detail`/`thumbnail` na pagina publica de produto, sempre sem mudar o contrato `image`/`imagem_url`/`images`.

## Objetivo

Reduzir peso futuro de imagens em catalogo e pagina de produto por meio de variantes locais geradas de forma segura e idempotente.

## Variantes definidas

| Variante | Largura maxima | Uso futuro esperado |
|---|---:|---|
| `thumbnail` | 160 px | Miniaturas e previews administrativos. |
| `card` | 480 px | Cards de catalogo/home. |
| `detail` | 960 px | Imagem principal da pagina de produto. |
| `original` | Sem alteracao | Arquivo fonte preservado. |

A geracao prefere WebP quando suportado pelo ambiente Pillow. Caso WebP nao esteja disponivel, usa formato raster compativel com a imagem original.

## Comando dry-run

O dry-run e o modo padrao e nao cria arquivos.

```powershell
uv run python tools/generate_image_variants.py --dry-run --report-path output/image-variants-dry-run.json
```

Para uma imagem especifica:

```powershell
uv run python tools/generate_image_variants.py --dry-run --image images/catalog/produto/img_1.jpg --report-path output/image-variants-produto.json
```

Para um produto especifico:

```powershell
uv run python tools/generate_image_variants.py --dry-run --product-id 123 --report-path output/image-variants-produto-123.json
```

## Comando apply

O apply cria arquivos de variantes e exige confirmacao explicita com `--yes`.

```powershell
uv run python tools/generate_image_variants.py --apply --yes --limit 20 --report-path output/image-variants-apply-lote-001.json
```

Para definir outro destino seguro dentro de `frontend/images`:

```powershell
uv run python tools/generate_image_variants.py --apply --yes --output-root frontend/images/variants --report-path output/image-variants-apply.json
```

## Politica de seguranca

O gerador:

- Aceita apenas imagens locais dentro de `frontend/images`.
- Bloqueia path traversal.
- Nao cria arquivos fora do `output-root` permitido.
- Nao remove arquivos.
- Nao sobrescreve imagens originais.
- Nao altera banco.
- Nao chama R2.
- Ignora URL externa.
- Reporta data URL como problema.
- Ignora SVG nesta sprint.
- Ignora GIF animado para evitar quebra de animacao.

## Relatorio

O relatorio JSON contem:

- `modo`: `dry-run` ou `apply`.
- `output_root`.
- totais de imagens, variantes planejadas, geradas, existentes, ignoradas e com erro.
- lista de imagens com fonte, produto quando houver, status e variantes.

Status comuns:

- `planejado`: variante seria criada no dry-run.
- `gerado`: variante criada no apply.
- `existente`: variante ja existia e foi preservada.
- `mantido`: original preservado.
- `ignorar`: item fora do escopo, como URL externa ou SVG.
- `erro`: problema que exige correcao, como arquivo inexistente ou path traversal.

## Uso no catalogo publico

Desde a Sprint 019, os cards do catalogo publico tentam usar a variante `card` quando a imagem principal e um arquivo local raster.

Exemplo:

- Original: `images/catalog/produto/img_1.jpg`
- Variante tentada: `images/variants/catalog/produto/img_1-card.webp`

O catalogo nao faz `fetch` ou `HEAD` para verificar existencia. Ele define a variante como `src` e guarda a imagem original em `data-original-src`.

Se a variante nao existir ou falhar, o `onerror` troca a imagem para a original. Se a original tambem falhar, o placeholder visual do card continua funcionando.

Fontes que nao tentam variante:

- URL externa `http/https`.
- SVG.
- Data URL.
- Caminho vazio.
- Formato local fora de `.jpg`, `.jpeg`, `.png` ou `.webp`.

Para preparar variantes antes de testar o catalogo:

```powershell
uv run python tools/generate_image_variants.py --apply --yes --limit 20 --report-path output/image-variants-apply-lote-001.json
```

## Uso na pagina publica de produto

Desde a Sprint 020, a pagina publica de produto tenta usar variantes quando a imagem original e local raster:

- imagem principal: variante `detail`;
- miniaturas da galeria: variante `thumbnail`.

Exemplos:

- Original: `images/catalog/produto/img_1.jpg`
- Principal tentada: `images/variants/catalog/produto/img_1-detail.webp`
- Miniatura tentada: `images/variants/catalog/produto/img_1-thumbnail.webp`

A pagina de produto nao faz `fetch` ou `HEAD` para verificar existencia. Ela define a variante como `src` e guarda a imagem original em `data-original-src`.

Se a variante nao existir ou falhar, o `onerror` troca a imagem para a original uma unica vez. Se a original tambem falhar, o fallback visual existente continua funcionando.

A imagem principal preserva os atributos de performance da pagina de produto: `loading="eager"`, `fetchpriority="high"`, `decoding="async"`, largura e altura explicitas. As miniaturas preservam `loading="lazy"` e `decoding="async"`.

Fontes que nao tentam variante:

- URL externa `http/https`.
- SVG.
- Data URL.
- Caminho vazio.
- Formato local fora de `.jpg`, `.jpeg`, `.png` ou `.webp`.

O SEO dinamico e o JSON-LD continuam usando o contrato publico original do produto.

## Como validar

Antes de usar variantes em producao:

1. Rodar dry-run e revisar erros.
2. Rodar apply em lote pequeno.
3. Conferir arquivos em `frontend/images/variants`.
4. Validar dimensoes e qualidade visual.
5. Rodar `uv run pytest` e smoke E2E.
6. Validar catalogo e pagina de produto, que consomem variantes de forma opcional com fallback para original.

## O que nao fazer

- Nao tornar variantes obrigatorias no site publico.
- Nao apagar originais.
- Nao mover arquivos antigos.
- Nao alterar `Product.to_dict()` para retornar variantes ainda.
- Nao salvar variantes no banco nesta sprint.
- Nao gerar variantes fora de `frontend/images`.

## Proximos passos

Avaliar geracao automatica de variantes no upload do VJ Admin modular e revisar cache/CDN antes de producao. Antes de lotes maiores, rodar dry-run, aplicar em lote pequeno, conferir qualidade visual e validar catalogo/produto com fallback para original.