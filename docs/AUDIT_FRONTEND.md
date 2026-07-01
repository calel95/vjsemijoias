# Auditoria da Loja Pública - VJ Semijoias

Este documento registra o inventário atual da loja pública do VJ Semijoias. Ele tem caráter descritivo e serve como base para a Auditoria Comercial da versão 1.0.

Não há recomendações, alterações de comportamento ou propostas de melhoria neste documento.

---

# Estrutura

## Páginas HTML

| Arquivo | Rota pública | Responsabilidade |
| --- | --- | --- |
| `frontend/index.html` | `/` | Home da loja pública, vitrine inicial, categorias, produtos em destaque e newsletter. |
| `frontend/catalogo.html` | `/catalogo` | Catálogo público com listagem, busca, filtros e paginação de produtos. |
| `frontend/produto.html` | `/produto` | Página pública de detalhe do produto. |
| `frontend/carrinho.html` | `/carrinho` | Carrinho de compras, resumo, cupom e cálculo de frete. |
| `frontend/checkout.html` | `/checkout` | Finalização de compra, dados do cliente, entrega e pagamento. |
| `frontend/login.html` | `/login` | Login do cliente e fluxo de recuperação de senha. |
| `frontend/cadastro.html` | `/cadastro` | Cadastro público de cliente. |
| `frontend/pedido.html` | `/pedido` | Acompanhamento público de pedido. |
| `frontend/pdf-visualizar.html` | `/pdf-visualizar` | Visualização do catálogo PDF. |

Arquivos HTML administrativos presentes no mesmo diretório, mas fora do escopo da loja pública:

| Arquivo | Rota | Observação |
| --- | --- | --- |
| `frontend/admin.html` | `/admin` | Área administrativa antiga. |
| `frontend/vj-admin.html` | `/vj-admin` | VJ Admin. |

## Arquivos CSS

| Arquivo | Uso |
| --- | --- |
| `frontend/css/style.css` | Estilos da loja pública. Usado pelas páginas públicas. |
| `frontend/css/admin.css` | Estilos administrativos, fora do escopo da loja pública. |
| `frontend/css/vj-admin.css` | Estilos do VJ Admin, fora do escopo da loja pública. |

O CSS público define variáveis de tema, tipografia, layout, botões, navegação, cards de produto, carrinho, checkout, autenticação, modais, rodapé e responsividade.

## Arquivos JavaScript

| Arquivo | Uso na loja pública |
| --- | --- |
| `frontend/js/api.js` | Cliente central de API, configuração de base URL, cookies, CSRF e chamadas HTTP. |
| `frontend/js/store-config.js` | Carrega e aplica configurações públicas da loja. |
| `frontend/js/products.js` | Carregamento, normalização e cache local de produtos e categorias. |
| `frontend/js/cart.js` | Carrinho, autenticação do cliente, pedidos locais, cupom e cálculo de frete. |
| `frontend/js/main.js` | Interações gerais da loja, cards de produto, newsletter, máscaras e comportamento de UI. |
| `frontend/js/offline.js` | Registro e suporte ao funcionamento offline/PWA. |
| `frontend/service-worker.js` | Cache estático, cache de produtos e estratégia de fallback. |

Arquivos JavaScript administrativos presentes, mas fora do escopo da loja pública:

- `frontend/js/admin.js`
- `frontend/js/vj-admin/*`

## Componentes reutilizados

| Componente | Arquivos envolvidos | Observação |
| --- | --- | --- |
| Cabeçalho e navegação | HTML público, `style.css`, `cart.js`, `store-config.js` | Logo, links principais e indicador de carrinho. |
| Rodapé | HTML público, `style.css`, `store-config.js` | Informações institucionais e contatos configuráveis. |
| Cards de produto | `main.js`, `products.js`, `style.css` | Renderização de produtos no catálogo, home e listagens. |
| Botões e estados visuais | `style.css`, `main.js` | Botões primários, secundários e ações de compra. |
| Categorias e filtros | `catalogo.html`, `products.js`, `main.js`, `style.css` | Filtros e navegação por categoria. |
| Carrinho | `carrinho.html`, `cart.js`, `style.css` | Itens, quantidade, subtotal, frete, cupom e total. |
| Checkout | `checkout.html`, `cart.js`, `api.js`, `style.css` | Dados do cliente, entrega, pagamento e criação do pedido. |
| Autenticação | `login.html`, `cadastro.html`, `cart.js`, `api.js`, `style.css` | Login, cadastro, sessão local e integração com API de auth. |
| Newsletter | `index.html`, `main.js`, `api.js` | Envio de e-mail para a API de newsletter. |
| Visualizador de PDF | `pdf-visualizar.html` | Exibe `frontend/pdf/catalogo-vj.pdf` em iframe. |

## Imagens

| Local | Conteúdo |
| --- | --- |
| `frontend/images/logo.png` | Logo principal e favicon usado pelas páginas públicas. |
| `frontend/images/logo-medium.png` | Ícone maior usado no manifest PWA. |
| `frontend/images/products/*.svg` | Imagens SVG de produtos de exemplo. |
| `frontend/images/catalog/` | Imagens reais de catálogo organizadas em subpastas. |
| `frontend/pdf/catalogo-vj.pdf` | Catálogo PDF atual. |
| `frontend/pdf/catalogo-original.pdf` | Catálogo PDF original preservado. |

Inventário atual de imagens em `frontend/images`:

| Tipo | Quantidade |
| --- | ---: |
| `.jpeg` | 156 |
| `.jpg` | 79 |
| `.png` | 2 |
| `.svg` | 10 |

O diretório `frontend/images/catalog` contém 235 arquivos de imagem distribuídos em 98 subpastas.

## Ícones

| Origem | Uso |
| --- | --- |
| `frontend/images/logo.png` | Favicon e identidade visual. |
| `frontend/images/logo-medium.png` | Ícone PWA no `manifest.json`. |
| SVGs em `frontend/images/products/` | Imagens vetoriais de produtos de exemplo. |
| Caracteres visuais no HTML/JS | Ícones textuais usados em partes da interface. |

Não foi identificado uso de biblioteca externa de ícones na loja pública.

## Fontes

A loja pública utiliza pilhas de fontes do sistema definidas em `frontend/css/style.css`:

| Variável | Família |
| --- | --- |
| `--font-body` | `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `Helvetica Neue`, `Arial`, `sans-serif` |
| `--font-serif` | `ui-serif`, `Georgia`, `Times New Roman`, `Cambria`, `Liberation Serif`, `serif` |

Não foram identificados arquivos locais de fonte nem importação externa de fontes na loja pública.

---

# Fluxos

## Home

| Item | Informação |
| --- | --- |
| Rota | `/` |
| Página | `frontend/index.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/products.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `GET /api/products`, `GET /api/categories`, `GET /api/store/config`, `POST /api/newsletter` |
| Armazenamento local | Carrinho em `localStorage` por meio de `vj_cart`. |

## Catálogo

| Item | Informação |
| --- | --- |
| Rota | `/catalogo` |
| Página | `frontend/catalogo.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/products.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `GET /api/products`, `GET /api/categories`, `GET /api/store/config` |
| Parâmetros suportados pelo cliente de API | `category`, `search`, `page`, `per_page` |

## Página de produto

| Item | Informação |
| --- | --- |
| Rota | `/produto` |
| Página | `frontend/produto.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/products.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `GET /api/products/{id}`, `GET /api/store/config` |
| Armazenamento local | Carrinho em `localStorage` por meio de `vj_cart`. |

## Carrinho

| Item | Informação |
| --- | --- |
| Rota | `/carrinho` |
| Página | `frontend/carrinho.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/products.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `POST /api/shipping/calculate`, `POST /api/coupons/validate`, `GET /api/store/config` |
| Armazenamento local | `vj_cart`, `vj_coupon`, `vj_coupon_percent`, `vj_cart_pricing`. |

## Checkout

| Item | Informação |
| --- | --- |
| Rota | `/checkout` |
| Página | `frontend/checkout.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/products.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `POST /api/orders`, `GET /api/payments/config`, `POST /api/payments/infinitepay/checkout`, `POST /api/payments/infinitepay/confirm`, `GET /api/payments/{orderId}/status`, `POST /api/shipping/calculate`, `GET /api/address/cep/{cep}`, `POST /api/coupons/validate`, `GET /api/store/config` |
| Armazenamento local | Carrinho, cupom e dados de precificação do carrinho. |

## Login

| Item | Informação |
| --- | --- |
| Rota | `/login` |
| Página | `frontend/login.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, `GET /api/store/config` |
| Armazenamento local | `vj_user` para estado local do cliente autenticado. |

## Cadastro

| Item | Informação |
| --- | --- |
| Rota | `/cadastro` |
| Página | `frontend/cadastro.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `POST /api/auth/register`, `GET /api/auth/me`, `GET /api/store/config` |
| Armazenamento local | `vj_user` e fallback local `vj_users` no script de carrinho/autenticação. |

## Recuperação de senha

| Item | Informação |
| --- | --- |
| Rota | `/login` |
| Página | `frontend/login.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `POST /api/auth/password-reset/request`, `POST /api/auth/password-reset/confirm`, `GET /api/store/config` |
| Observação | O fluxo está associado à página de login; não há HTML público separado para recuperação de senha. |

## Minha Conta

| Item | Informação |
| --- | --- |
| Rota | Não foi identificada rota pública dedicada. |
| Página | Não foi identificado arquivo `minha-conta.html` ou equivalente no frontend público. |
| Arquivos relacionados | `js/cart.js`, `js/api.js` |
| APIs relacionadas | `GET /api/auth/me`, `POST /api/auth/logout`, `GET /api/orders`, `GET /api/orders/{orderId}` |
| Observação | Existem funções de autenticação e pedidos do cliente no cliente de API, mas não foi identificada uma página pública dedicada de Minha Conta. |

## Favoritos

| Item | Informação |
| --- | --- |
| Rota | Não identificada. |
| Página | Não identificada. |
| Arquivos relacionados | Não foram identificados arquivos públicos dedicados a favoritos. |
| APIs relacionadas | Não foram identificadas chamadas públicas específicas para favoritos. |
| Observação | O fluxo de favoritos não foi encontrado no frontend público atual. |

## Acompanhamento de pedido

| Item | Informação |
| --- | --- |
| Rota | `/pedido` |
| Página | `frontend/pedido.html` |
| Arquivos envolvidos | `css/style.css`, `js/api.js`, `js/store-config.js`, `js/cart.js`, `js/main.js`, `js/offline.js` |
| APIs utilizadas | `GET /api/orders/{orderId}/public?token=...`, `POST /api/orders/public/lookup`, `GET /api/payments/{orderId}/status?token=...`, `GET /api/store/config` |

---

# SEO

## Title

| Página | Title atual |
| --- | --- |
| `index.html` | `VJ Semijoias - Banhadas a Ouro 18k` |
| `catalogo.html` | `Catálogo - VJ Semijoias` |
| `produto.html` | `Produto - VJ Semijoias` |
| `carrinho.html` | `Carrinho - VJ Semijoias` |
| `checkout.html` | `Finalizar Compra - VJ Semijoias` |
| `login.html` | `Entrar - VJ Semijoias` |
| `cadastro.html` | `Cadastro - VJ Semijoias` |
| `pedido.html` | `Acompanhar Pedido - VJ Semijoias` |
| `pdf-visualizar.html` | `Catálogo PDF - VJ Semijoias` |

## Meta description

| Página | Status |
| --- | --- |
| `index.html` | Possui meta description. |
| `catalogo.html` | Possui meta description. |
| `produto.html` | Não identificada no inventário. |
| `carrinho.html` | Não identificada no inventário. |
| `checkout.html` | Não identificada no inventário. |
| `login.html` | Não identificada no inventário. |
| `cadastro.html` | Não identificada no inventário. |
| `pedido.html` | Não identificada no inventário. |
| `pdf-visualizar.html` | Não identificada no inventário. |

## Open Graph

Não foram identificadas tags Open Graph nas páginas públicas inventariadas.

## Sitemap

Não foi identificado arquivo `sitemap.xml` no frontend ou na raiz do projeto durante o inventário.

## Robots

Não foi identificado arquivo `robots.txt` no frontend ou na raiz do projeto durante o inventário.

## Favicon

As páginas públicas usam `frontend/images/logo.png` como favicon por meio de `<link rel="icon">`.

## Manifest

Arquivo identificado: `frontend/manifest.json`.

| Campo | Valor |
| --- | --- |
| `name` | `VJ Semijoias` |
| `short_name` | `VJ` |
| `description` | `Catálogo e loja de semijoias banhadas a ouro 18k` |
| `start_url` | `/` |
| `display` | `standalone` |
| `background_color` | `#fbf6ee` |
| `theme_color` | `#a67c3d` |
| `orientation` | `portrait` |
| Ícones | `images/logo.png`, `images/logo-medium.png` |

## Schema.org

Não foram identificados blocos `schema.org` ou `application/ld+json` nas páginas públicas inventariadas.

---

# Performance

## Imagens

| Item | Inventário |
| --- | --- |
| Logos | `logo.png` e `logo-medium.png`. |
| Produtos SVG | 10 arquivos em `frontend/images/products`. |
| Catálogo de imagens | 235 imagens em `frontend/images/catalog`. |
| Formatos encontrados | `.jpeg`, `.jpg`, `.png`, `.svg`. |
| PDF | `frontend/pdf/catalogo-vj.pdf` e `frontend/pdf/catalogo-original.pdf`. |

## Lazy loading

Foi identificado `loading="lazy"` no iframe do catálogo PDF em `frontend/pdf-visualizar.html`.

Não foi identificado inventário de `loading="lazy"` aplicado de forma geral às imagens de produto no HTML estático.

## Cache

O arquivo `frontend/service-worker.js` define:

| Cache | Uso |
| --- | --- |
| `vj-semijoias-v25` | Cache estático da aplicação. |
| `vj-semijoias-api-v1` | Cache específico para respostas e imagens relacionadas a produtos. |

Estratégias identificadas:

| Recurso | Estratégia |
| --- | --- |
| Arquivos estáticos | Pré-cache na instalação do service worker. |
| Navegação | Network-first com fallback para `/`. |
| Scripts e CSS | Network-first com fallback para cache. |
| `GET /api/products` | Network-first com atualização do cache. |
| Imagens retornadas pela API de produtos | Cache individual quando possível. |
| Demais chamadas `/api/` | Network-only. |

## JavaScript

| Item | Inventário |
| --- | --- |
| Organização | JavaScript modular por arquivos globais, sem bundler identificado. |
| Cliente HTTP | `frontend/js/api.js`, baseado em `fetch`. |
| Estado local | `localStorage` para carrinho, usuário, pedidos locais, cupom e precificação. |
| PWA/offline | `frontend/js/offline.js` e `frontend/service-worker.js`. |
| Bibliotecas externas | Não foram identificadas bibliotecas externas carregadas por CDN nas páginas públicas. |

## CSS

| Item | Inventário |
| --- | --- |
| CSS público principal | `frontend/css/style.css`. |
| Estratégia | Arquivo único para a loja pública, com variáveis CSS e media queries. |
| CSS externo | Não foi identificado CSS externo carregado por CDN nas páginas públicas. |
| CSS administrativo | `admin.css` e `vj-admin.css`, fora do escopo público. |

---

# Dependências

## Bibliotecas utilizadas no frontend público

Não foram identificadas dependências externas de frontend, bibliotecas por CDN ou pacote JavaScript específico para a loja pública.

## APIs nativas do navegador utilizadas

| API | Uso |
| --- | --- |
| `fetch` | Comunicação com backend. |
| `localStorage` | Carrinho, usuário, pedidos locais, cupom e precificação. |
| `sessionStorage` | Estado temporário de navegação quando usado pelos scripts. |
| Cookies | Leitura de token CSRF no cliente de API. |
| Service Worker API | Cache e suporte offline. |
| Cache API | Armazenamento de arquivos estáticos, produtos e imagens. |
| DOM API | Renderização e interações da interface. |

## Dependências de backend consumidas pelo frontend público

| Domínio | Endpoints consumidos |
| --- | --- |
| Produtos | `GET /api/products`, `GET /api/products/{id}`, `GET /api/categories` |
| Configuração da loja | `GET /api/store/config` |
| Autenticação | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, `POST /api/auth/password-reset/request`, `POST /api/auth/password-reset/confirm` |
| Pedidos | `POST /api/orders`, `GET /api/orders`, `GET /api/orders/{orderId}`, `GET /api/orders/{orderId}/public`, `POST /api/orders/public/lookup` |
| Pagamentos | `GET /api/payments/config`, `POST /api/payments/infinitepay/checkout`, `POST /api/payments/infinitepay/confirm`, `GET /api/payments/{orderId}/status` |
| Frete | `POST /api/shipping/calculate` |
| Endereço | `GET /api/address/cep/{cep}` |
| Cupons | `POST /api/coupons/validate` |
| Newsletter | `POST /api/newsletter` |

---

# Organização

Árvore simplificada do frontend:

```text
frontend/
├── index.html
├── catalogo.html
├── produto.html
├── carrinho.html
├── checkout.html
├── login.html
├── cadastro.html
├── pedido.html
├── pdf-visualizar.html
├── manifest.json
├── service-worker.js
├── css/
│   ├── style.css
│   ├── admin.css
│   └── vj-admin.css
├── js/
│   ├── api.js
│   ├── store-config.js
│   ├── products.js
│   ├── cart.js
│   ├── main.js
│   ├── offline.js
│   ├── admin.js
│   └── vj-admin/
├── images/
│   ├── logo.png
│   ├── logo-medium.png
│   ├── products/
│   └── catalog/
└── pdf/
    ├── catalogo-vj.pdf
    └── catalogo-original.pdf
```

---

# Resultado esperado

Este documento deve servir como base para a Auditoria Comercial da versão 1.0 da loja pública do VJ Semijoias.

Ele registra a estrutura atual, os fluxos existentes, os arquivos envolvidos, as rotas públicas, as APIs utilizadas e o inventário técnico de SEO, performance, dependências e organização.

Este documento não altera produto, código, comportamento, frontend, backend, banco de dados ou rotas existentes.