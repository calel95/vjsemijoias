# Arquitetura do backend

Este backend FastAPI separa rotas, servicos e modelos por dominio. A Fase Arquitetural 1 transforma `backend.models` em um pacote, mantendo a compatibilidade com imports existentes como `from backend.models import Product`.

## Dominios

### Dominio publico

O dominio publico atende vitrine, cadastro, checkout e consulta segura de pedidos. Ele usa `Order`, `OrderEvent`, `Payment`, `Newsletter`, `Coupon` e `CouponRedemption`, alem dos servicos de pedidos, cupons, frete, email e pagamento.

### Dominio VJ Admin

O dominio VJ Admin concentra operacoes internas do painel: catalogo, fornecedores, pedidos internos, auditoria e configuracoes. Os modelos principais sao `Product`, `ProductImage`, `ProductImport`, `Supplier`, `VJAdminOrder`, `VJAdminOrderItem`, `AdminAuditLog`, `User` e `StoreSetting`.

### Estoque

Estoque fica separado em `backend.models.stock` e nos servicos de estoque. `Product.stock_quantity` guarda o saldo atual e `StockMovement` registra entradas, saidas e ajustes com saldo anterior, saldo atual, motivo e usuario administrativo quando aplicavel.

### Pedidos

Pedidos publicos usam `Order` e `OrderEvent`, com pagamento em `Payment` e cupons em `CouponRedemption`. Pedidos internos do admin usam `VJAdminOrder` e `VJAdminOrderItem`, preservando as tabelas `vj_admin_pedidos` e `vj_admin_pedido_items`.

### Precificacao

A precificacao do catalogo fica em campos do produto, como custos, markup, precos por forma de pagamento, lucro e margem. A regra compartilhada de calculo continua em servicos, e os modelos apenas persistem os valores calculados.

## Organizacao dos modelos

- `backend/models/base.py`: `Base`, tipos monetarios, percentuais e helpers comuns.
- `backend/models/products.py`: catalogo, imagens e importacao de produtos.
- `backend/models/suppliers.py`: fornecedores.
- `backend/models/stock.py`: movimentos de estoque.
- `backend/models/vj_orders.py`: pedidos internos do admin.
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
