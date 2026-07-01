# Auditoria de Performance da Loja Pública

Data da auditoria: 2026-07-01

Este documento registra o estado atual de performance da loja pública do VJ Semijoias para orientar a Sprint 004 da Versão 1.0 Comercial.

Escopo:

- Loja pública e páginas institucionais em `frontend/`.
- Recursos estáticos servidos pelo frontend.
- JavaScript, CSS, imagens, PDFs, manifest e service worker.

Fora do escopo:

- Otimizações implementadas.
- Alterações de frontend, backend, JavaScript, CSS, banco ou APIs.
- Testes automatizados, por se tratar exclusivamente de documentação.

---

# Recursos estáticos

## Inventário geral

| Tipo | Quantidade | Peso aproximado | Organização | Observações |
| --- | ---: | ---: | --- | --- |
| HTML | 16 | 0,22 MB | Raiz de `frontend/` | Inclui loja pública, páginas institucionais e páginas admin. |
| CSS | 3 | 0,09 MB | `frontend/css/` | `style.css` é a folha pública principal; `admin.css` e `vj-admin.css` são administrativas. |
| JavaScript | 21 | 0,25 MB | `frontend/js/` e `frontend/service-worker.js` | Inclui módulos públicos, admin legado, VJ Admin modular e service worker. |
| Imagens JPEG | 235 | 25,67 MB | `frontend/images/catalog/` | Principal concentração de peso estático. |
| Imagens PNG | 2 | 0,11 MB | `frontend/images/` | Logos e ícones do manifest. |
| SVG | 10 | 0,02 MB | `frontend/images/products/` | Imagens leves usadas como produtos/placeholder do catálogo base. |
| PDFs | 2 | 0,02 MB | `frontend/pdf/` | Catálogos em PDF. |
| Manifest | 1 | ~0 MB | `frontend/manifest.json` | Define PWA básico e ícones. |
| Robots/Sitemap | 2 | ~0 MB | `frontend/robots.txt` e `frontend/sitemap.xml` | Preparados para SEO público. |

## Organização atual

| Diretório | Função | Observações de performance |
| --- | --- | --- |
| `frontend/` | Páginas HTML públicas e admin | Arquivos HTML pequenos; várias páginas públicas repetem a mesma pilha de scripts. |
| `frontend/css/` | Estilos públicos e administrativos | A loja pública centraliza estilo em `style.css`, o que facilita cache, mas carrega CSS amplo em todas as páginas públicas. |
| `frontend/js/` | Scripts públicos, admin e VJ Admin | Scripts públicos são pequenos, mas carregados de forma ampla. |
| `frontend/images/` | Logo, placeholders e catálogo | O catálogo concentra o maior peso total. |
| `frontend/images/catalog/` | Imagens reais de produtos | 98 subpastas e 235 arquivos `.jpeg/.jpg`. |
| `frontend/images/products/` | SVGs de produtos exemplo/placeholder | Baixo impacto de peso. |
| `frontend/pdf/` | Catálogos PDF | Baixo peso atual. |

## Possíveis duplicidades

| Item | Evidência | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- | --- |
| Pares de imagens com mesmo nome base em `.jpg` e `.jpeg` | 79 grupos possíveis, totalizando 158 arquivos em grupos duplicados | Alto, pois aumenta armazenamento, cache e risco de carregar variantes desnecessárias | Média | 🟡 Importante |
| Logos em dois tamanhos (`logo.png`, `logo-medium.png`) | Usados por páginas e manifest | Baixo, pois o peso é pequeno e há função clara no PWA | Baixa | 🟢 Desejável |
| CSS/JS admin no mesmo diretório do público | Organização compartilhada em `frontend/` | Baixo para navegação pública, exceto pelo service worker que pré-cacheia parte admin | Média | 🟢 Desejável |

---

# JavaScript

## Arquivos públicos principais

| Arquivo | Peso aproximado | Função | Uso atual |
| --- | ---: | --- | --- |
| `frontend/js/api.js` | 13,0 KB | Cliente de API e autenticação | Carregado nas páginas públicas. |
| `frontend/js/store-config.js` | 3,1 KB | Configurações públicas da loja | Carregado nas páginas públicas. |
| `frontend/js/seo.js` | 14,4 KB | SEO centralizado e metadados dinâmicos | Carregado com `defer` no `<head>`. |
| `frontend/js/products.js` | 5,1 KB | Catálogo e produtos | Carregado nas páginas públicas. |
| `frontend/js/public-layout.js` | 3,0 KB | Layout público reutilizável | Carregado nas páginas públicas. |
| `frontend/js/cart.js` | 18,5 KB | Carrinho | Carregado nas páginas públicas. |
| `frontend/js/main.js` | 5,2 KB | Renderização de cards e comportamento geral | Carregado nas páginas públicas. |
| `frontend/js/offline.js` | 1,8 KB | Registro/apoio offline | Carregado nas páginas públicas. |
| `frontend/service-worker.js` | Não listado em `frontend/js/` | Cache offline/PWA | Registrado pelo fluxo offline. |

## Arquivos administrativos no mesmo frontend

| Grupo | Arquivos | Observação |
| --- | --- | --- |
| Admin legado | `admin.js` | Não pertence à jornada pública de compra, mas está em `frontend/js/`. |
| VJ Admin modular | `vj-admin/*.js` | Não pertence à loja pública; deve permanecer fora da análise de otimização comercial pública, salvo impacto no service worker/cache. |

## Carregamento por página pública

| Página | Scripts carregados | Ordem | `defer`/`async` | Observações |
| --- | --- | --- | --- | --- |
| `index.html` | `seo.js`, `api.js`, `store-config.js`, `products.js`, `public-layout.js`, `cart.js`, `main.js`, `offline.js`, script inline | SEO no `<head>`, demais no final do `body` | Apenas `seo.js` usa `defer`; nenhum `async` | Home carrega pilha completa. |
| `catalogo.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Uso coerente de produtos/catálogo; ainda carrega módulos gerais. |
| `produto.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais antes do script inline | Apenas `seo.js` usa `defer` | SEO dinâmico é aplicado via `window.VJSEO.applyProductSEO(product)`. |
| `carrinho.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Carrinho depende de `cart.js`; produtos podem ser necessários para dados auxiliares. |
| `checkout.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Checkout carrega pilha pública, sem alterar integração de pagamento. |
| `login.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Possível carregamento de módulos de catálogo/carrinho sem necessidade principal. |
| `cadastro.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Similar ao login. |
| `pedido.html` | Mesma pilha pública + script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | Consulta/acompanhamento de pedido com scripts comuns. |
| Páginas institucionais | Mesma pilha pública, geralmente sem script inline | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | FAQ, garantia, termos, privacidade e troca carregam módulos de produto/carrinho. |
| `pdf-visualizar.html` | Mesma pilha pública | SEO no `<head>`, demais no final | Apenas `seo.js` usa `defer` | O iframe do PDF usa `loading="lazy"`. |

## Pontos observados

| Item | Estado atual | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- | --- |
| Scripts públicos pequenos, mas carregados amplamente | Páginas institucionais e autenticação carregam módulos de produtos/carrinho/main | Médio | Média | 🟡 Importante |
| `seo.js` com `defer` | Boa prática já presente | Positivo | Baixa | 🟢 Desejável |
| Scripts no fim do `body` sem `defer` | Evita bloqueio inicial do HTML, mas não permite uma política uniforme de carregamento | Baixo a médio | Baixa | 🟢 Desejável |
| Ausência de bundling/minificação | Arquivos são pequenos, mas não minificados | Baixo no momento | Média | 🟢 Desejável |
| Scripts inline por página | Facilita implementação local, mas dificulta cache e auditoria fina | Médio | Média | 🟡 Importante |

---

# CSS

## Folhas carregadas

| Arquivo | Peso aproximado | Escopo | Observações |
| --- | ---: | --- | --- |
| `frontend/css/style.css` | 49,8 KB | Loja pública | Carregado em todas as páginas públicas. |
| `frontend/css/admin.css` | 32,5 KB | Admin legado | Não é carregado nas páginas públicas, mas é pré-cacheado pelo service worker. |
| `frontend/css/vj-admin.css` | 14,2 KB | VJ Admin | Não faz parte da loja pública. |

## Reutilização e redundâncias

| Item | Estado atual | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- | --- |
| CSS público centralizado | `style.css` atende a loja e páginas institucionais | Positivo para cache e manutenção | Baixa | 🟢 Desejável |
| CSS único para todas as páginas públicas | Páginas simples carregam o mesmo CSS de páginas complexas | Médio em conexões lentas | Média | 🟡 Importante |
| Estilos inline em páginas públicas | Há estilos inline em home, carrinho, checkout, login, produto e PDF | Médio para cache e manutenção | Média | 🟡 Importante |
| Sem `@import` ou `@font-face` identificado | Não há custo externo aparente de fontes | Positivo | Baixa | 🟢 Desejável |

---

# Imagens

## Inventário

| Formato | Quantidade | Peso aproximado | Uso |
| --- | ---: | ---: | --- |
| `.jpeg` | 156 | 23,23 MB | Catálogo real de produtos. |
| `.jpg` | 79 | 2,44 MB | Catálogo real de produtos, com possíveis pares duplicados. |
| `.png` | 2 | 0,11 MB | Logo e ícone maior do manifest. |
| `.svg` | 10 | 0,02 MB | Produtos exemplo/placeholder. |

## Maiores imagens observadas

| Arquivo | Peso aproximado |
| --- | ---: |
| `frontend/images/catalog/32-products-piercing-fake-liso/img_3.jpeg` | 0,46 MB |
| `frontend/images/catalog/19-products-brinco-verde-esmeralda-zirconias-no-contorno/img_1.jpeg` | 0,46 MB |
| `frontend/images/catalog/28-products-colar-verde-esmerallda-zirconias-no-contorno/img_1.jpeg` | 0,46 MB |
| `frontend/images/catalog/26-products-colar-brasil-mapa/img_1.jpeg` | 0,45 MB |
| `frontend/images/catalog/23-products-colar-banhado-a-prata-ponto-de-luz-7mm/img_1.jpeg` | 0,42 MB |

## Lazy loading

| Local | Estado atual | Observações |
| --- | --- | --- |
| Cards de produto em `main.js` | Usa `loading="lazy"` nas imagens dos cards | Bom para catálogo e home. |
| `pdf-visualizar.html` | Iframe do PDF usa `loading="lazy"` | Bom para evitar carregamento imediato do PDF embutido. |
| `produto.html` | Imagem principal e miniaturas são renderizadas sem `loading="lazy"` | A imagem principal tende a ser acima da dobra; miniaturas podem ser avaliadas em otimização futura. |
| Logo/header | Sem lazy loading | Adequado para imagem crítica e pequena. |

## Oportunidades identificadas

| Item | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- |
| Criar variantes responsivas para imagens de produto | Alto | Alta | 🔴 Crítico |
| Converter catálogo para formatos modernos quando compatível (`WebP`/`AVIF`) | Alto | Média | 🔴 Crítico |
| Revisar possíveis duplicidades `.jpg`/`.jpeg` | Médio a alto | Média | 🟡 Importante |
| Definir política de imagem principal vs miniaturas | Médio | Média | 🟡 Importante |
| Padronizar dimensões e compressão de upload/importação | Alto | Alta | 🔴 Crítico |
| Manter SVGs de placeholder leves | Baixo | Baixa | 🟢 Desejável |

---

# Service Worker

## Estratégia atual

| Item | Estado atual |
| --- | --- |
| Versão do cache estático | `vj-semijoias-v27` |
| Versão do cache de API | `vj-semijoias-api-v1` |
| Instalação | Abre cache estático e executa `cache.addAll(urlsToCache)`. |
| Ativação | Remove caches antigos que não estejam na lista válida. |
| `/api/products` | Usa estratégia network-first com fallback para cache de API. |
| Demais `/api/` | Usa rede direta, sem cache persistente. |
| Navegação | Usa rede primeiro e fallback para `/`. |
| Scripts e estilos | Usa rede primeiro e atualiza cache quando a resposta é válida. |
| Outros assets GET | Usa cache/fetch com armazenamento de respostas válidas. |
| Imagens de produto | Há rotina para cachear imagens vindas da resposta de produtos. |

## Arquivos pré-cacheados

O pré-cache inclui:

- Rotas públicas principais: `/`, `/catalogo`, `/produto`, `/carrinho`, `/checkout`, `/pedido`, `/login`, `/cadastro`, `/pdf-visualizar`.
- Páginas institucionais: política de troca, privacidade, termos, garantia e FAQ.
- CSS público e administrativo.
- JS público e admin legado.
- Logo, manifest, robots, sitemap.
- SVGs de produtos base.
- `pdf/catalogo-vj.pdf`.

## Limitações observadas

| Limitação | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- |
| Pré-cache inclui assets administrativos junto da experiência pública | Baixo a médio | Média | 🟢 Desejável |
| Lista de pré-cache é manual | Médio para manutenção | Média | 🟡 Importante |
| Cache de imagens pode crescer conforme catálogo | Alto em catálogo grande | Alta | 🔴 Crítico |
| Falta política explícita de expiração/tamanho de cache | Alto em dispositivos com pouco armazenamento | Alta | 🔴 Crítico |
| Navegação com fallback genérico para `/` | Baixo para performance, mas pode mascarar páginas offline específicas | Média | 🟢 Desejável |

---

# Performance

## Oportunidades documentadas

| Oportunidade | Estado atual | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- | --- |
| Imagens responsivas | Não há `srcset`/`sizes` identificado nas imagens dinâmicas | Alto | Alta | 🔴 Crítico |
| Compressão/conversão de imagens | Catálogo usa majoritariamente `.jpeg/.jpg`; maiores imagens chegam a ~0,46 MB | Alto | Média | 🔴 Crítico |
| Lazy loading refinado | Existe em cards e iframe PDF; pode ser revisado em galerias/miniaturas | Médio | Média | 🟡 Importante |
| Preload de recursos críticos | Não foram identificados `rel="preload"` nas páginas públicas | Médio | Média | 🟡 Importante |
| Preconnect | Não há dependências externas aparentes; benefício depende de integrações futuras | Baixo | Baixa | 🟢 Desejável |
| Minificação de CSS/JS | Arquivos não parecem minificados | Baixo a médio | Média | 🟢 Desejável |
| Code splitting por página | Páginas simples carregam a pilha pública completa | Médio | Média/Alta | 🟡 Importante |
| Cache do service worker | Já existe, mas sem política visível de expiração/tamanho | Alto em catálogo crescente | Alta | 🔴 Crítico |
| Cache HTTP/CDN | Não avaliado no repositório; depende do ambiente de deploy | Alto em produção | Média | 🟡 Importante |
| PDFs | Peso atual baixo; iframe já usa lazy loading | Baixo | Baixa | 🟢 Desejável |
| CSS crítico | `style.css` único simplifica cache, mas pode atrasar páginas simples | Médio | Média | 🟡 Importante |

---

# Dependências

## Bibliotecas utilizadas no frontend

Não foram identificadas bibliotecas externas carregadas via CDN nas páginas públicas analisadas.

O frontend público utiliza principalmente APIs nativas do navegador:

| Recurso | Uso | Impacto na performance |
| --- | --- | --- |
| `fetch` | Comunicação com APIs | Baixo; depende do tempo de resposta das APIs. |
| `localStorage` | Carrinho/sessão local | Baixo; adequado para dados pequenos. |
| DOM API | Renderização dinâmica | Médio quando listas de produtos crescem. |
| Service Worker | Cache e suporte offline | Positivo, mas exige política de cache para catálogo grande. |
| Cache API | Armazenamento de assets/API | Positivo, com risco de crescimento sem expiração. |
| Manifest/PWA | Experiência instalável | Baixo impacto direto de carregamento. |

## Possíveis impactos

| Item | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- |
| Ausência de dependências externas reduz roundtrips | Positivo | Baixa | 🟢 Desejável |
| Implementação própria exige disciplina de modularização | Médio | Média | 🟡 Importante |
| Crescimento do catálogo pode pressionar DOM, imagens e cache | Alto | Alta | 🔴 Crítico |

---

# Classificação

| Item | Impacto estimado | Dificuldade | Prioridade |
| --- | --- | --- | --- |
| Otimizar imagens do catálogo | Alto | Média/Alta | 🔴 Crítico |
| Criar imagens responsivas para produto/listagem | Alto | Alta | 🔴 Crítico |
| Definir política de expiração/tamanho do cache de imagens | Alto | Alta | 🔴 Crítico |
| Revisar scripts carregados por página | Médio | Média | 🟡 Importante |
| Rever pré-cache do service worker | Médio | Média | 🟡 Importante |
| Avaliar CSS crítico e estilos inline | Médio | Média | 🟡 Importante |
| Mapear duplicidades `.jpg`/`.jpeg` | Médio | Média | 🟡 Importante |
| Minificar CSS/JS | Baixo a médio | Média | 🟢 Desejável |
| Adicionar preload apenas para recursos críticos validados | Médio | Média | 🟡 Importante |
| Manter PDFs com lazy loading | Baixo | Baixa | 🟢 Desejável |

---

# Plano sugerido

## Plano da Sprint 004

### Sprint 004.1 — Medição e orçamento de performance

- Definir páginas alvo: home, catálogo, produto, carrinho e checkout.
- Registrar métricas iniciais em desktop e mobile.
- Definir orçamento de peso para imagens, JS, CSS e cache.
- Documentar ambiente de medição para repetir comparações.

### Sprint 004.2 — Imagens do catálogo

- Auditar duplicidades `.jpg`/`.jpeg`.
- Definir tamanho máximo por imagem.
- Criar estratégia de compressão sem perda visual relevante.
- Preparar política de formatos modernos.

### Sprint 004.3 — Imagens responsivas

- Definir variantes para card, galeria e imagem principal.
- Planejar `srcset`/`sizes`.
- Separar imagem crítica da página de produto das imagens secundárias.

### Sprint 004.4 — JavaScript por página

- Mapear dependências reais de cada página.
- Separar scripts comuns mínimos de scripts específicos.
- Reduzir scripts carregados em páginas institucionais, login e cadastro quando possível.

### Sprint 004.5 — CSS público

- Identificar estilos realmente usados nas páginas públicas.
- Avaliar CSS crítico para primeira dobra.
- Reduzir estilos inline recorrentes quando fizer sentido.

### Sprint 004.6 — Service Worker e cache

- Revisar itens pré-cacheados.
- Separar necessidades públicas de admin.
- Definir limite/expiração para cache de imagens.
- Planejar atualização de versão de cache por release.

### Sprint 004.7 — PDFs e recursos auxiliares

- Confirmar peso real dos catálogos em produção.
- Manter carregamento tardio do PDF embutido.
- Definir se PDFs entram ou não no pré-cache em produção.

---

# Conclusão

A loja pública possui base estática relativamente simples e leve em HTML, CSS e JavaScript. O principal ponto de atenção para a Versão 1.0 Comercial é o peso e a gestão das imagens do catálogo, especialmente por volume total, possíveis duplicidades e ausência de variantes responsivas.

O segundo ponto de atenção é a granularidade do carregamento: páginas simples carregam a mesma pilha pública usada por páginas comerciais mais complexas. O service worker já oferece uma base positiva de cache, mas precisa de política mais explícita para catálogo crescente e separação entre escopo público e administrativo.
