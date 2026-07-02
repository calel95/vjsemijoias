# Migracao gradual de imagens para R2

Este documento descreve o processo seguro para migrar imagens locais antigas de produtos para Cloudflare R2.

O processo nao roda automaticamente, nao apaga arquivos locais, nao altera schema e nao deve ser usado sem dry-run previo.

## Pre-requisitos

- Banco apontando para o ambiente correto.
- Backup recente do banco antes de qualquer `--apply`.
- Variaveis R2 configuradas somente no ambiente em que a migracao real sera executada.
- Permissao administrativa/operacional para atualizar referencias de imagens no banco.
- Validacao previa do relatorio em dry-run.

## Variaveis R2

Para executar `--apply`, o ambiente deve ter:

- `STORAGE_BACKEND=r2`
- `R2_ACCOUNT_ID`
- `R2_BUCKET`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_PUBLIC_BASE_URL`

O script nao imprime secrets e o relatorio nao inclui valores de credenciais.

## Dry-run

O dry-run e o modo padrao. Ele lista candidatos, valida arquivos locais, simula a chave R2 final e pode gerar relatorio JSON.

```powershell
uv run python tools/migrate_product_images_to_r2.py --dry-run --report-path output/media-r2-dry-run.json
```

Tambem e possivel limitar a execucao:

```powershell
uv run python tools/migrate_product_images_to_r2.py --dry-run --limit 20 --report-path output/media-r2-lote-001.json
```

Ou analisar um produto especifico:

```powershell
uv run python tools/migrate_product_images_to_r2.py --dry-run --product-id 123 --report-path output/media-r2-produto-123.json
```

## Apply

O apply faz upload para R2 e atualiza o banco somente depois de processar o lote com sucesso.

Ele exige `STORAGE_BACKEND=r2`, configuracao R2 valida e confirmacao explicita com `--yes`.

```powershell
uv run python tools/migrate_product_images_to_r2.py --apply --yes --limit 20 --report-path output/media-r2-apply-lote-001.json
```

Para um produto especifico:

```powershell
uv run python tools/migrate_product_images_to_r2.py --apply --yes --product-id 123 --report-path output/media-r2-apply-produto-123.json
```

## Relatorio

O relatorio JSON contem:

- `modo`: `dry-run` ou `apply`.
- `total_produtos_analisados`.
- `total_imagens_candidatas`.
- `total_migrar_ou_migradas`.
- `total_ignoradas`.
- `total_problemas`.
- `problemas` com produto, campo, caminho e motivo.
- `produtos` com imagens atuais, imagens previstas e status por imagem.

Status possiveis por imagem:

- `migrar`: imagem local valida que seria enviada no dry-run.
- `migrado`: imagem local enviada no apply.
- `ignorar`: URL absoluta, caminho vazio ou item que nao deve ser migrado.
- `erro`: arquivo inexistente, path traversal, data URL ou caminho fora de `frontend/images`.

## Rollback logico

O script faz rollback do banco se houver falha durante o lote antes do commit.

Se um apply ja tiver sido commitado e for necessario voltar, o rollback logico deve ser feito a partir do backup do banco ou de um relatorio salvo antes/depois da execucao.

Os arquivos locais nao sao apagados, entao as imagens antigas continuam disponiveis para rollback manual de referencias.

## Checklist antes do apply

- Rodar dry-run no mesmo ambiente alvo.
- Revisar `total_problemas`.
- Confirmar que imagens externas foram ignoradas.
- Confirmar que os caminhos locais existem em `frontend/images`.
- Confirmar `R2_PUBLIC_BASE_URL` correto.
- Fazer backup do banco.
- Executar apply em lote pequeno primeiro.

## Checklist depois do apply

- Revisar relatorio do apply.
- Conferir produto migrado no admin/publico.
- Rodar smoke E2E.
- Monitorar 404 de assets no ambiente.
- Manter imagens locais ate validacao completa.

## O que nao fazer

- Nao executar `--apply` sem `--yes` e sem backup.
- Nao remover imagens locais como parte desta sprint.
- Nao migrar URLs externas.
- Nao migrar data URLs; elas devem ser corrigidas no cadastro.
- Nao executar migration de banco, pois o schema nao muda.
- Nao ativar R2 automaticamente em desenvolvimento local.