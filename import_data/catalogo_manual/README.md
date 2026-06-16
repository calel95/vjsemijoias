# Catalogo manual

Use esta pasta quando voce quiser importar produtos sem extrair de um PDF.

## Estrutura

```text
catalogo_manual/
  manifest.json
  products/
    colar-coracao-personalizado/
      img_1.jpeg
      img_2.jpeg
    pulseira-nome-personalizado/
      foto-frente.jpeg
      foto-detalhe.jpeg
```

Cada pasta dentro de `products/` representa um produto. Coloque dentro dela
todas as fotos daquele produto.

## Criar manifest inicial

Depois de criar as pastas e adicionar as imagens:

```powershell
uv run python tools/generate_manual_manifest.py import_data/catalogo_manual
```

O script cria `manifest.json` com os produtos e imagens encontrados. Depois,
edite o arquivo para preencher `category`, `price`, `description` e `features`.

Se o `manifest.json` ja existir, o script nao sobrescreve. Para recriar:

```powershell
uv run python tools/generate_manual_manifest.py import_data/catalogo_manual --force
```

## Testar e importar

Confira sem alterar o banco:

```powershell
uv run python -m backend.import_products import_data/catalogo_manual --dry-run
```

Importe para o catalogo do site:

```powershell
uv run python -m backend.import_products import_data/catalogo_manual
```

Tambem funciona pelo painel admin em **Importar Pasta de Produtos**: selecione a
pasta completa `catalogo_manual`.
