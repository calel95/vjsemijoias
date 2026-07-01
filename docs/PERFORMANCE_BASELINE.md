# Baseline de Performance da Loja Publica

Data da medicao: 2026-07-01

URL alvo: `https://teste.hubdadospublicos.space/`

Este documento registra a Sprint 004.1 — Medicao e orcamento de performance da loja publica do VJ Semijoias.

Escopo desta sprint:

- Medir paginas publicas da loja em ambiente de teste.
- Registrar baseline inicial para comparacao futura.
- Propor orcamento de performance para a Versao 1.0 Comercial.

Fora do escopo:

- Implementar otimizacoes.
- Alterar frontend, backend, banco, APIs ou comportamento.
- Executar `pytest` ou smoke tests.

---

# Metodologia

## Ferramentas utilizadas

| Ferramenta | Uso | Resultado |
| --- | --- | --- |
| `curl.exe` | Medir status HTTP, TTFB, tempo total e tamanho do HTML | Executado com sucesso. |
| Chrome Headless via DevTools Protocol | Medir FCP, LCP, CLS, TBT aproximado, requests e recursos pesados | Executado com sucesso fora do sandbox. |
| PageSpeed Insights API | Tentar obter scores Lighthouse oficiais | Falhou por quota publica da API. |
| Lighthouse CLI local | Verificar disponibilidade de `lighthouse` | Nao estava instalado no ambiente. |

## Tentativas indisponiveis

### Lighthouse CLI

O comando local `lighthouse` nao estava disponivel no ambiente. Por isso, nao foi possivel gerar os scores oficiais de Performance, Accessibility, Best Practices e SEO via Lighthouse CLI.

Comando de verificacao usado:

```powershell
Get-Command lighthouse -ErrorAction SilentlyContinue
```

### PageSpeed Insights

A API publica do PageSpeed Insights retornou erro de quota:

```text
429 RESOURCE_EXHAUSTED
Quota exceeded for quota metric 'Queries' and limit 'Queries per day'
```

Comando-base usado:

```powershell
curl.exe -L -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<URL>&strategy=mobile&category=performance&category=accessibility&category=best-practices&category=seo"
```

### Chrome Headless

O Chrome Headless falhou dentro do sandbox com erro `Access is denied` em componentes internos do Chrome. A medicao foi repetida fora do sandbox, com permissao, usando Chrome DevTools Protocol.

Modo de medicao usado:

- Chrome Headless.
- Viewport mobile: 390x844, DPR 3.
- Cache desabilitado.
- Service worker bypassado para baseline de carregamento frio.
- Sem throttling Lighthouse oficial.

Observacao: o navegador local injetou um script externo do Kaspersky em todas as paginas medidas. Esse recurso foi tratado como interferencia do ambiente local e nao como recurso da aplicacao.

---

# Paginas medidas

| Fluxo | URL | Observacao |
| --- | --- | --- |
| Home | `https://teste.hubdadospublicos.space/` | Pagina inicial da loja. |
| Catalogo | `https://teste.hubdadospublicos.space/catalogo` | Listagem publica de produtos. |
| Produto | `https://teste.hubdadospublicos.space/produto?id=1` | Produto real escolhido: Brinco Marguerite. |
| Carrinho | `https://teste.hubdadospublicos.space/carrinho` | Carrinho sem alteracao de estado. |
| Checkout | `https://teste.hubdadospublicos.space/checkout` | Checkout sem finalizar pedido. |
| FAQ | `https://teste.hubdadospublicos.space/faq.html` | Pagina institucional. |

---

# Resumo executivo

| Pagina | Performance score | Accessibility | Best Practices | SEO | FCP | LCP | CLS | INP/TBT | TTFB curl | Requests app | Tamanho app aprox. |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Home | N/D | N/D | N/D | N/D | 312 ms | 340 ms | 0,000 | INP N/D / TBT 30 ms | 235 ms | ~13 | ~300 KB |
| Catalogo | N/D | N/D | N/D | N/D | 528 ms | 528 ms | 0,000 | INP N/D / TBT 29 ms | 257 ms | ~14 | ~309 KB |
| Produto | N/D | N/D | N/D | N/D | 228 ms | 648 ms | 0,000 | INP N/D / TBT 75 ms | 309 ms | ~13 | ~314 KB |
| Carrinho | N/D | N/D | N/D | N/D | 232 ms | 452 ms | 0,000 | INP N/D / TBT 0 ms | 213 ms | ~13 | ~311 KB |
| Checkout | N/D | N/D | N/D | N/D | 288 ms | 380 ms | 0,000 | INP N/D / TBT 0 ms | 311 ms | ~13 | ~325 KB |
| FAQ | N/D | N/D | N/D | N/D | 164 ms | 164 ms | 0,000 | INP N/D / TBT 0 ms | 218 ms | ~13 | ~284 KB |

Notas:

- `N/D` significa nao disponivel nesta execucao por ausencia de Lighthouse CLI e quota indisponivel no PageSpeed Insights.
- INP real depende de interacao de usuario e deve ser medido com Lighthouse/CrUX/RUM quando disponivel.
- TBT foi estimado via `PerformanceObserver` de long tasks no Chrome headless, sem o modelo completo do Lighthouse.
- Requests e tamanho app aproximado excluem o script externo injetado pelo ambiente local do Kaspersky.

---

# Medicoes por pagina

## Home

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 235 ms |
| Tamanho HTML curl | 9,6 KB |
| FCP | 312 ms |
| LCP | 340 ms |
| CLS | 0,000 |
| TBT aproximado | 30 ms |
| Requests app aproximados | ~13 |
| Tamanho app aproximado | ~300 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/js/cart.js` | 19 KB |
| `/js/api.js` | 13 KB |
| `/api/products?page=1&per_page=8` | 12 KB |

Principais gargalos:

- Logo aparece como recurso pesado e foi observado mais de uma vez na cascata.
- `style.css` e pilha JS comum sao carregados na entrada da loja.
- Home depende de `/api/products?page=1&per_page=8` para vitrine dinamica.

## Catalogo

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 257 ms |
| Tamanho HTML curl | 11,3 KB |
| FCP | 528 ms |
| LCP | 528 ms |
| CLS | 0,000 |
| TBT aproximado | 29 ms |
| Requests app aproximados | ~14 |
| Tamanho app aproximado | ~309 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/js/cart.js` | 19 KB |
| `/api/products` | 15 KB |
| `/js/api.js` | 13 KB |

Principais gargalos:

- Catalogo depende da API `/api/products` para renderizacao.
- O tamanho inicial ainda e controlado no ambiente de teste, mas tende a crescer com imagens reais de catalogo.
- Scripts comuns sao carregados mesmo quando parte deles pode nao ser essencial para o primeiro render.

## Produto

Produto escolhido: `Brinco Marguerite`, `id=1`.

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 309 ms |
| Tamanho HTML curl | 19,0 KB |
| FCP | 228 ms |
| LCP | 648 ms |
| CLS | 0,000 |
| TBT aproximado | 75 ms |
| Requests app aproximados | ~13 |
| Tamanho app aproximado | ~314 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/produto?id=1` | 19 KB |
| `/js/cart.js` | 19 KB |
| `/api/products` | 15 KB |

Principais gargalos:

- Produto depende de carregamento dinamico do catalogo para localizar o item por `id`.
- LCP foi o maior entre as paginas medidas, ainda abaixo de 1s neste ambiente, mas deve ser acompanhado quando imagens reais maiores forem usadas.
- TBT aproximado foi o maior da rodada, sugerindo atencao a scripts da pagina de produto.

## Carrinho

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 213 ms |
| Tamanho HTML curl | 17,5 KB |
| FCP | 232 ms |
| LCP | 452 ms |
| CLS | 0,000 |
| TBT aproximado | 0 ms |
| Requests app aproximados | ~13 |
| Tamanho app aproximado | ~311 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/js/cart.js` | 19 KB |
| `/carrinho` | 18 KB |
| `/api/products` | 15 KB |

Principais gargalos:

- Carrinho carrega `/api/products`, provavelmente para complementar dados dos itens.
- Peso recorrente de logo, CSS e scripts comuns domina o carregamento inicial.
- Sem itens no carrinho, a medicao nao representa um carrinho cheio com imagens de produtos.

## Checkout

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 311 ms |
| Tamanho HTML curl | 32,2 KB |
| FCP | 288 ms |
| LCP | 380 ms |
| CLS | 0,000 |
| TBT aproximado | 0 ms |
| Requests app aproximados | ~13 |
| Tamanho app aproximado | ~325 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/checkout` | 32 KB |
| `/js/cart.js` | 19 KB |
| `/api/products` | 15 KB |

Principais gargalos:

- Checkout tem o maior HTML entre as paginas medidas.
- A medicao nao finalizou pedido nem acionou InfinitePay; representa apenas carregamento inicial da pagina.
- Como pagina critica de conversao, deve ter orcamento proprio e ser reavaliada com carrinho preenchido.

## FAQ

| Metrica | Valor |
| --- | ---: |
| Status HTTP | 200 |
| TTFB curl | 218 ms |
| Tamanho HTML curl | 5,2 KB |
| FCP | 164 ms |
| LCP | 164 ms |
| CLS | 0,000 |
| TBT aproximado | 0 ms |
| Requests app aproximados | ~13 |
| Tamanho app aproximado | ~284 KB |

Principais recursos pesados:

| Recurso | Peso aproximado |
| --- | ---: |
| `/images/logo.png` | 89 KB |
| `/images/logo.png` novamente como recurso secundario | 89 KB |
| `/css/style.css` | 50 KB |
| `/js/cart.js` | 19 KB |
| `/js/api.js` | 13 KB |
| `/faq.html` | 5 KB |

Principais gargalos:

- FAQ e uma pagina simples, mas carrega a pilha publica comum.
- Ha oportunidade futura de reduzir scripts em paginas institucionais.
- O peso de logo/CSS domina a pagina.

---

# Observacoes sobre ambiente

- Os dados foram medidos em ambiente de teste: `https://teste.hubdadospublicos.space/`.
- O banco atual do ambiente de teste usa PostgreSQL Neon.
- A producao futura usara banco no Dokploy, o que pode alterar TTFB, latencia de API e estabilidade das respostas.
- O baseline deve ser repetido apos o deploy final de producao.
- As medicoes de navegador foram feitas em Chrome Headless com cache desabilitado e service worker bypassado, para observar carregamento frio.
- O resultado nao substitui uma rodada oficial de Lighthouse/PageSpeed quando a ferramenta estiver disponivel.
- A medicao local detectou script injetado pelo Kaspersky. Esse recurso foi desconsiderado como gargalo da aplicacao.

---

# Orcamento de performance sugerido

Metas propostas para a Versao 1.0 Comercial:

| Area | Meta sugerida |
| --- | --- |
| Home mobile | Performance Lighthouse acima de 80 quando medido oficialmente. |
| Catalogo mobile | Performance Lighthouse acima de 75. |
| Produto mobile | Performance Lighthouse acima de 80. |
| Carrinho mobile | Performance Lighthouse acima de 80. |
| Checkout mobile | Performance Lighthouse acima de 80, com carrinho preenchido. |
| FAQ/institucionais | Performance Lighthouse acima de 85. |
| LCP | Abaixo de 2,5s sempre que possivel. |
| CLS | Abaixo de 0,1. |
| INP | Abaixo de 200ms quando houver medicao real de interacao. |
| TTFB HTML | Preferencialmente abaixo de 500ms no ambiente final. |
| CSS publico inicial | Manter abaixo de 75 KB antes de minificacao. |
| JS publico comum | Evitar crescimento sem justificativa; revisar quando passar de 100 KB somados. |
| Imagem de logo | Reduzir peso percebido e evitar requisicoes duplicadas quando possivel. |
| Imagens principais de produto | Buscar imagens abaixo de 150 KB por variante exibida no mobile. |
| Cache | Evitar crescimento sem controle do cache de imagens e assets. |

---

# Proximas acoes recomendadas

| Prioridade | Acao | Motivo |
| --- | --- | --- |
| 🔴 Critico | Repetir Lighthouse oficial quando CLI ou PageSpeed estiver disponivel | Scores oficiais ainda estao N/D. |
| 🔴 Critico | Medir produto e catalogo com imagens reais pesadas do catalogo completo | O ambiente medido usa produtos seed leves em SVG; o risco real esta nas imagens do catalogo. |
| 🔴 Critico | Definir limite de peso e variantes para imagens de produto | Imagens sao o maior risco de degradacao da Sprint 004. |
| 🟡 Importante | Investigar por que `logo.png` aparece mais de uma vez na cascata | Pode haver oportunidade simples de reduzir bytes iniciais. |
| 🟡 Importante | Separar paginas institucionais da pilha JS completa quando seguro | FAQ carrega scripts de loja que podem nao ser essenciais. |
| 🟡 Importante | Repetir medicao com carrinho preenchido e checkout em fluxo real controlado | Checkout vazio nao representa a jornada comercial completa. |
| 🟡 Importante | Medir com service worker ativo em segunda visita | Baseline frio e importante, mas retorno de cliente tambem importa. |
| 🟢 Desejavel | Registrar metricas em desktop alem de mobile | Mobile deve ser prioridade, mas desktop ajuda comparacao. |
| 🟢 Desejavel | Automatizar coleta em script versionado futuramente | Facilita comparar antes/depois de otimizacoes. |

---

# Comandos de referencia

## Medicao curl

```powershell
curl.exe -L -s -o NUL -w "home status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" https://teste.hubdadospublicos.space/
curl.exe -L -s -o NUL -w "catalogo status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" https://teste.hubdadospublicos.space/catalogo
curl.exe -L -s -o NUL -w "produto status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" "https://teste.hubdadospublicos.space/produto?id=1"
curl.exe -L -s -o NUL -w "carrinho status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" https://teste.hubdadospublicos.space/carrinho
curl.exe -L -s -o NUL -w "checkout status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" https://teste.hubdadospublicos.space/checkout
curl.exe -L -s -o NUL -w "faq status=%{http_code} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" https://teste.hubdadospublicos.space/faq.html
```

## Lighthouse futuro

Quando Lighthouse CLI estiver disponivel:

```powershell
lighthouse https://teste.hubdadospublicos.space/ --preset=desktop --output=html --output=json
lighthouse https://teste.hubdadospublicos.space/ --form-factor=mobile --output=html --output=json
```

Ou via PageSpeed Insights, quando a quota/API estiver disponivel:

```powershell
curl.exe -L -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https%3A%2F%2Fteste.hubdadospublicos.space%2F&strategy=mobile&category=performance&category=accessibility&category=best-practices&category=seo"
```

---

# Sprint 004.2 - Performance inicial

## Relatorios Lighthouse Mobile recebidos

| Pagina | Performance | Accessibility | Best Practices | SEO | LCP | Speed Index | Observacoes |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| Home | 74 | N/D | N/D | N/D | 3,5s | 24,2s | Relatorio indicou aviso de carregamento incompleto. |
| Catalogo | 95 | N/D | N/D | N/D | N/D | N/D | Relatorio teve `PROTOCOL_TIMEOUT`, entao deve ser repetido. |
| Produto | 87 | N/D | N/D | 91 | 3,5s | N/D | SEO penalizado por meta description nao detectada. |

## Melhorias implementadas

| Area | Implementacao | Objetivo |
| --- | --- | --- |
| SEO do produto | `frontend/js/seo.js` agora aplica SEO base imediatamente e tenta hidratar metadados de produto pela API em `/produto?id=...`. | Aumentar a chance de o Lighthouse detectar `description`, Open Graph, Twitter Cards e JSON-LD Product antes da avaliacao. |
| Render-blocking | Scripts publicos de paginas institucionais sem fluxo inline passaram a usar `defer`. | Reduzir bloqueio seguro em paginas simples sem alterar checkout ou fluxos comerciais. |
| Cache | `service-worker.js` foi atualizado para `vj-semijoias-v28`, removeu admin do pre-cache publico, removeu paginas transacionais do pre-cache e limitou cache automatico de imagens de produto. | Tornar o cache mais seguro e evitar crescimento sem controle. |
| Logo do rodape | O rodape passou a usar `images/logo-medium.png` com `width`/`height` quando a configuracao publica aponta para a logo padrao. | Evitar baixar a logo maior de 500x500 para exibicao pequena no rodape. |

## Fora do escopo mantido

- Nenhuma conversao massiva de catalogo para WebP/AVIF.
- Nenhum refactor grande de JS por pagina.
- Nenhuma alteracao visual planejada.
- Nenhuma alteracao de backend, banco, APIs ou checkout.
- Nenhuma alteracao de upload/R2.

## Objetivos e resultados esperados

- Produto com CLS proximo de zero por reserva de espaco da galeria e skeleton inicial.
- Produto com LCP inferior ao relatorio anterior por priorizacao da imagem principal.
- SEO do produto preservado em 100, mantendo metadados centralizados em `seo.js`.
- Ausencia de regressao em Home e Catalogo.
- Nenhuma alteracao funcional em checkout, backend, banco, APIs ou regras de negocio.

## Compatibilidade

- A chamada compartilhada de produtos mantem `seo.js` como responsavel pelo SEO dinamico e `products.js` como fonte usada pela pagina.
- O skeleton usa a mesma estrutura visual da pagina e e removido quando o produto real e renderizado.
- Conteudo secundario abaixo da dobra e adiado para idle com fallback seguro.
- Checkout e VJ Admin nao foram alterados.

## Validacoes obrigatorias

- `node --check` em todos os JS alterados.
- `uv run pytest`.
- `uv run python tools/e2e_smoke.py`.
- Alembic nao deve ser executado porque nao houve alteracao de schema.

## Medicao recomendada apos esta sprint

Repetir Lighthouse Mobile para:

- Home: validar LCP e Speed Index apos cache/logo/defer.
- Catalogo: repetir porque o relatorio anterior teve `PROTOCOL_TIMEOUT`.
- Produto: confirmar se a meta description dinamica passou a ser detectada.


---

# Sprint 004.3 - Produto: LCP e CLS

## Relatorios Lighthouse Mobile recebidos

| Pagina | Performance | LCP | CLS | Observacoes |
| --- | ---: | ---: | ---: | --- |
| Home | 90 | 3,0s | 0 | Evolucao positiva apos Sprint 004.2. |
| Catalogo | 95 | 2,3s | 0 | Dentro da meta inicial sugerida para 1.0. |
| Produto | 61 | 4,0s | 0,585 | Prioridade da Sprint 004.3 por LCP alto e CLS critico. |

## Melhorias implementadas

| Area | Implementacao | Objetivo |
| --- | --- | --- |
| CLS do produto | `produto.html` agora renderiza um skeleton inicial dentro de `#product-content`, com a mesma estrutura de galeria/informacoes. | Reservar espaco antes da API responder e evitar deslocamento grande da pagina. |
| Galeria principal | `style.css` reforca `aspect-ratio: 1 / 1`, largura estavel e altura reservada para a imagem principal. | Reduzir instabilidade visual durante carregamento da imagem. |
| LCP do produto | A imagem principal dinamica recebe `loading="eager"`, `fetchpriority="high"`, `decoding="async"`, `width` e `height`. | Priorizar o recurso LCP sem aplicar lazy loading indevido na imagem principal. |
| Miniaturas | Miniaturas recebem `loading="lazy"`, `decoding="async"`, `width` e `height`. | Carregar imagens secundarias com menor prioridade. |
| Fetch duplicado | `seo.js` compartilha o fetch de `/api/products` com `products.js` via promessa global controlada. | Manter SEO dinamico cedo sem duplicar chamada na pagina de produto. |
| 401 publico | `cart.js` evita chamar `/api/auth/me` quando nao existe usuario local salvo. | Evitar 401 desnecessario em visitas publicas sem quebrar login/cadastro. |
| Inicializacao secundaria | `produto.html` usa `requestIdleCallback()` com fallback para `setTimeout()` para renderizar produtos relacionados e buscar configuracao publica apenas quando ela ainda nao estiver em memoria. | Priorizar imagem, nome, preco e botoes antes de conteudo abaixo da dobra. |
| Scripts da pagina | Os scripts criticos da pagina foram mantidos por dependencia direta; `offline.js` passou a carregar com `defer` na pagina de produto. | Reduzir trabalho inicial sem remover suporte offline. |

## Observacao sobre relatorios

O script externo do Kaspersky pode aparecer nos relatorios de navegador/Lighthouse do ambiente local. Esse recurso nao pertence ao projeto VJ Semijoias e deve ser desconsiderado como asset da aplicacao.

## Medicao recomendada apos esta sprint

- Repetir Lighthouse Mobile em `/produto?id=...` para confirmar CLS proximo de 0.
- Confirmar se LCP do produto fica abaixo dos 4,0s medidos antes da sprint.
- Revalidar Home e Catalogo para garantir ausencia de regressao.

---

# Conclusao

O baseline inicial indica que as paginas publicas carregam rapidamente no ambiente de teste, com LCP abaixo de 1s na medicao headless local e TTFB via `curl` entre aproximadamente 213 ms e 311 ms.

Ainda assim, este resultado deve ser interpretado com cautela: os scores oficiais de Lighthouse nao foram obtidos, o ambiente e de teste, o banco atual e Neon, e a producao futura no Dokploy pode alterar a latencia. Para a Sprint 004, a prioridade tecnica deve ser controlar o crescimento de imagens, cache e scripts comuns antes que o catalogo real aumente o peso da loja.