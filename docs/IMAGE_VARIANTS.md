# Variantes de imagem

Este documento descreve a base de variantes de imagem criada na Sprint 018.

A sprint prepara a geracao de arquivos otimizados, mas ainda nao ativa o uso das variantes no site publico e nao muda o contrato `image`/`imagem_url`/`images`.

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

## Como validar

Antes de usar variantes em producao:

1. Rodar dry-run e revisar erros.
2. Rodar apply em lote pequeno.
3. Conferir arquivos em `frontend/images/variants`.
4. Validar dimensoes e qualidade visual.
5. Rodar `uv run pytest` e smoke E2E.
6. So em sprint futura alterar catalogo/produto para consumir variantes.

## O que nao fazer

- Nao apontar o site publico para variantes nesta sprint.
- Nao apagar originais.
- Nao mover arquivos antigos.
- Nao alterar `Product.to_dict()` para retornar variantes ainda.
- Nao salvar variantes no banco nesta sprint.
- Nao gerar variantes fora de `frontend/images`.

## Proximos passos

A proxima sprint recomendada e usar variantes no catalogo publico, porque os cards/listagens tendem a multiplicar o impacto de peso de imagem.

Depois disso, avaliar uso na pagina de produto e, por ultimo, gerar variantes automaticamente no upload do VJ Admin modular.