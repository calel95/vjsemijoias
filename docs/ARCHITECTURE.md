# Arquitetura do backend

Este backend FastAPI separa rotas, servicos e modelos por dominio. `backend.models` e um pacote modular, mas continua funcionando como fachada publica para imports existentes como `from backend.models import Product`.

## Dominios

### Dominio publico

O dominio publico atende vitrine, cadastro, checkout e consulta segura de pedidos. Ele usa `Order`, `OrderEvent`, `Payment`, `Newsletter`, `Coupon` e `CouponRedemption`, alem dos servicos de pedidos publicos, cupons, frete, email e pagamento.

O checkout publico nao depende dos pedidos internos do VJ Admin. Valores, frete e descontos continuam recalculados no servidor antes da criacao ou confirmacao de cobranca.

### Dominio VJ Admin

O dominio VJ Admin concentra operacoes internas do painel: catalogo, fornecedores, clientes, pedidos internos, estoque, dashboard executivo, financeiro simples, auditoria e configuracoes. Os modelos principais sao `Product`, `ProductImage`, `ProductImport`, `Supplier`, `Customer`, `VJAdminOrder`, `VJAdminOrderItem`, `StockMovement`, `Expense`, `AdminAuditLog`, `User` e `StoreSetting`.

As rotas do VJ Admin ficam em routers por area (`vj_admin_products`, `vj_admin_orders`, `vj_admin_stock`, `vj_admin_suppliers`, `vj_admin_customers`, `vj_admin_finance`) e devem delegar regras para services.

### Clientes / CRM

Clientes do admin usam `Customer`. Pedidos internos podem apontar para `customer_id` ou manter os campos avulsos `cliente_nome` e `cliente_whatsapp` para preservar pedidos antigos e vendas sem cadastro.

Cliente inativo nao deve ser selecionavel em novo pedido, mas pedidos ja confirmados continuam no historico e nas metricas. WhatsApp, e-mail, CPF e Instagram sao normalizados nos services.

### Estoque

Estoque fica separado em `backend.models.stock` e nos servicos de estoque. `Product.stock_quantity` guarda o saldo atual e `StockMovement` registra entradas, saidas e ajustes com saldo anterior, saldo atual, motivo e usuario administrativo quando aplicavel.

Pedidos internos confirmados geram saida de estoque. Cancelamento de pedido confirmado devolve estoque por movimento de entrada.

### Pedidos

Pedidos publicos usam `Order` e `OrderEvent`, com pagamento em `Payment` e cupons em `CouponRedemption`. Pedidos internos do admin usam `VJAdminOrder` e `VJAdminOrderItem`, preservando as tabelas `vj_admin_pedidos` e `vj_admin_pedido_items`.

Pedidos internos salvam valores historicos de preco, custo, taxa, desconto, total, lucro e margem no proprio pedido/item. Relatorios financeiros devem usar esses valores salvos, nao os valores atuais do produto.

### Precificacao

A precificacao do catalogo fica em campos do produto, como custos, markup, precos por forma de pagamento, lucro e margem. A regra compartilhada de calculo continua em servicos, e os modelos apenas persistem os valores calculados.

### Financeiro simples

Financeiro simples usa `Expense` para despesas manuais e `VJAdminOrder` confirmado para resumo operacional. Despesas canceladas nao entram no resumo. Pedidos em rascunho ou cancelados nao entram no resumo.

O resumo financeiro calcula faturamento bruto, descontos, taxas de pagamento, custo dos produtos vendidos, lucro bruto, despesas, lucro liquido estimado, margem liquida estimada, ticket medio, ranking de produtos, ranking de clientes e resumo por forma de pagamento. O dashboard executivo reutiliza esse resumo para evitar divergencia de calculo e acrescenta indicadores operacionais de clientes, produtos publicados, estoque baixo e produtos sem estoque.

Este modulo ainda nao implementa contas a pagar/receber, conciliacao bancaria ou regime de competencia completo.

## Organizacao dos modelos

- `backend/models/base.py`: `Base`, tipos monetarios, percentuais e helpers comuns.
- `backend/models/products.py`: catalogo, imagens e importacao de produtos.
- `backend/models/suppliers.py`: fornecedores.
- `backend/models/customers.py`: clientes do VJ Admin / CRM.
- `backend/models/stock.py`: movimentos de estoque.
- `backend/models/vj_orders.py`: pedidos internos do admin.
- `backend/models/finance.py`: despesas manuais do financeiro simples.
- `backend/models/users.py`: usuarios.
- `backend/models/public_orders.py`: pedidos publicos, eventos, newsletter e cupons.
- `backend/models/payments.py`: pagamentos.
- `backend/models/settings.py`: configuracoes persistidas da loja.
- `backend/models/audit.py`: auditoria administrativa.
- `backend/models/__init__.py`: fachada publica que reexporta os modelos atuais.

## Regras criticas

- Nomes de tabelas e colunas nao devem ser alterados sem migration explicita.
- Alembic importa `backend.models` para registrar todos os modelos em `Base.metadata`.
- Routers e servicos devem importar pela fachada `backend.models`, salvo quando houver motivo claro para usar um modulo interno.
- O app nao altera schema no startup; rode `alembic upgrade head` antes de subir DEV ou PRD.
- O checkout deve recalcular valores, frete e descontos no servidor antes de criar ou confirmar cobranca.
- Dados completos de cartao nunca passam pelo backend; a cobranca acontece no checkout hospedado pela InfinitePay.
- Movimentos de estoque devem preservar trilha de auditoria e saldo anterior/atual.
- Relatorios financeiros e dashboard executivo devem usar valores historicos salvos em pedidos e itens.
- Despesas devem ser canceladas logicamente; nao ha exclusao fisica no fluxo do VJ Admin.