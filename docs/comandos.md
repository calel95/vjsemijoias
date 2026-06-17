# 📋 Dicionário de Comandos — VJ Semijoias

Referência rápida de todos os comandos disponíveis no terminal para desenvolvimento,
manutenção e operação do projeto. Execute a partir da raiz do projeto (`vjsemijoias/`).

---

## ⚡ Ambiente e Dependências

| Comando | Descrição |
|---------|-----------|
| `Copy-Item .env.example .env` | Criar arquivo `.env` a partir do modelo (Windows PowerShell) |
| `cp .env.example .env` | Criar arquivo `.env` a partir do modelo (Linux/macOS) |
| `uv --cache-dir .uv-cache sync` | Instalar todas as dependências do projeto |
| `uv --cache-dir .uv-cache sync --group dev` | Instalar dependências de desenvolvimento também |

---

## 🚀 Subir a Aplicação

| Comando | Descrição |
|---------|-----------|
| `uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000` | Iniciar servidor em produção (sem reload) |
| `uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000 --reload` | Iniciar servidor em desenvolvimento (recarrega ao alterar arquivos) |

**Nota:** Em alguns ambientes Windows, `--reload` pode falhar por permissão de processo. Nesse caso, execute sem `--reload`.

Após iniciar, acesse:

- Site: `http://localhost:5000`
- Swagger (documentação da API): `http://localhost:5000/docs`

---

## 🗄️ Banco de Dados e Migrations (Alembic)

| Comando | Descrição |
|---------|-----------|
| `uv --cache-dir .uv-cache run alembic upgrade head` | Aplicar todas as migrations pendentes (cria tabelas num banco novo) |
| `uv --cache-dir .uv-cache run alembic stamp 20260617_0001` | Marcar migration base como já aplicada (para bancos pré-existentes) |
| `uv --cache-dir .uv-cache run alembic revision --autogenerate -m "descricao da alteracao"` | Criar nova migration automaticamente a partir das mudanças nos modelos |
| `uv --cache-dir .uv-cache run alembic downgrade -1` | Reverter a última migration |
| `uv --cache-dir .uv-cache run alembic current` | Verificar qual migration está atualmente aplicada |
| `uv --cache-dir .uv-cache run alembic history` | Listar histórico de migrations |

**Fluxo típico ao alterar `backend/models.py`:**

```powershell
uv --cache-dir .uv-cache run alembic revision --autogenerate -m "descricao da alteracao"
uv --cache-dir .uv-cache run alembic upgrade head
```

---

## 📦 Importação do Catálogo de Produtos

### A partir do catálogo extraído (`import_data/catalogo_extraido/`)

| Comando | Descrição |
|---------|-----------|
| `uv run python -m backend.import_products --dry-run` | Simular importação do catálogo extraído (não altera o banco) |
| `uv run python -m backend.import_products` | Importar/atualizar catálogo extraído no banco |

### A partir do catálogo manual (`import_data/catalogo_manual/`)

| Comando | Descrição |
|---------|-----------|
| `uv run python tools/generate_manual_manifest.py import_data/catalogo_manual` | Gerar manifest inicial para catálogo manual |
| `uv run python -m backend.import_products import_data/catalogo_manual --dry-run` | Simular importação do catálogo manual |
| `uv run python -m backend.import_products import_data/catalogo_manual` | Importar/atualizar catálogo manual no banco |

### Importação pelo painel admin (interface web)

1. Acessar `http://localhost:5000/admin`
2. Fazer login com a senha administrativa
3. Clicar em **Importar Pasta de Produtos**
4. Selecionar a pasta completa (`catalogo_extraido/` ou `catalogo_manual/`)

---

## 🧪 Testes

| Comando | Descrição |
|---------|-----------|
| `uv run pytest` | Executar todos os testes automatizados |
| `uv run pytest -v` | Executar testes com output verboso (mostra nome de cada teste) |
| `uv run pytest tests/test_api.py` | Executar apenas os testes da API |
| `uv run pytest -k "nome_do_teste"` | Executar testes que contenham o termo no nome |
| `uv run python tools/e2e_smoke.py` | Executar smoke test ponta a ponta (não afeta banco real nem InfinitePay) |

---

## 🛠️ Ferramentas Auxiliares

| Comando | Descrição |
|---------|-----------|
| `uv run python tools/generate_pdf.py` | Gerar o catálogo PDF oficial da loja |
| `uv run python tools/generate_placeholders.py` | Gerar imagens placeholder para desenvolvimento |
| `uv run python tools/process_logo.py` | Processar/redimensionar o logo da loja |
| `uv run python tools/organize_project.py` | Organizar arquivos do projeto |

---

## 🔐 Comandos de Produção / Deploy

| Comando | Descrição |
|---------|-----------|
| `uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000` | Iniciar em produção |
| `uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000 --workers 4` | Iniciar com 4 workers (para produção com múltiplos CPUs) |

---

## 📝 Resumo Rápido do Dia a Dia

```powershell
# 1. Instalar dependências (primeira vez ou após alterações)
uv --cache-dir .uv-cache sync

# 2. Subir a aplicação em desenvolvimento
uv --cache-dir .uv-cache run uvicorn backend.app:app --host 0.0.0.0 --port 5000 --reload

# 3. Aplicar migrations (após alterar modelos)
uv --cache-dir .uv-cache run alembic upgrade head

# 4. Rodar testes
uv run pytest

# 5. Simular importação de catálogo
uv run python -m backend.import_products --dry-run

# 6. Importar catálogo para o banco
uv run python -m backend.import_products

# 7. Gerar catálogo PDF
uv run python tools/generate_pdf.py