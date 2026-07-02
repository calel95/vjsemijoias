# Auditoria de Conversao Comercial - Site Publico VJ Semijoias

Documento base do Epico 3 - Conversao Comercial.

Loja auditada prioritariamente: https://teste.hubdadospublicos.space

Consulta realizada em 2026-07-01, considerando a experiencia publica de uma cliente navegando pela loja publicada. O codigo-fonte foi usado apenas como apoio para confirmar rotas, comportamento dinamico e textos carregados por JavaScript quando necessario.

## Objetivo da auditoria

O objetivo desta auditoria e identificar oportunidades para aumentar conversao, confianca e ticket medio no Site Publico da VJ Semijoias, mantendo a arquitetura existente e sem propor reescrita da loja.

A analise observa a jornada comercial real: descoberta da marca, avaliacao do catalogo, decisao no produto, revisao do carrinho, preenchimento do checkout, pagamento e acompanhamento do pedido. O foco e responder uma pergunta simples: o que hoje ajuda ou atrapalha uma cliente a comprar com seguranca?

Esta auditoria nao implementa melhorias, nao altera frontend, nao altera backend e nao substitui `ROADMAP.md`, `PRODUCT.md` ou `ARCHITECTURE.md`. Ela organiza o backlog futuro do Epico 3.

## Jornada da cliente

Fluxo principal observado:

```text
Home
↓
Catalogo
↓
Produto
↓
Carrinho
↓
Checkout
↓
Pedido
```

### Primeira impressao

A loja comunica rapidamente o universo de semijoias banhadas a ouro 18k. A identidade visual e consistente com o segmento: tons dourados, linguagem delicada, logo visivel, CTAs de catalogo e promessa de elegancia.

O ponto mais forte da primeira impressao e a clareza do que esta sendo vendido. O ponto mais fraco e que a home ainda usa mais a marca e a proposta geral do que imagens comerciais fortes de produto em uso, prova social ou argumentos de compra acima da dobra.

### Navegacao

A navegacao principal e direta: Inicio, Catalogo, Categorias, Sobre, Contato, conta e carrinho. No catalogo, filtros, busca, ordenacao e botao de carregar mais ajudam a cliente a explorar.

O fluxo de compra e coerente: produto adiciona ao carrinho, carrinho exige frete selecionado, checkout coleta dados e envia para pagamento seguro da InfinitePay. A continuidade e boa, mas pode ficar mais persuasiva com mensagens de apoio no momento certo.

### Clareza

A loja explica categorias, preco, parcelamento, frete, garantia, troca, pagamento e acompanhamento. A clareza funcional e boa.

Ainda ha oportunidade de melhorar a clareza comercial: diferenciar melhor beneficios, condicoes de garantia, cuidados da semijoia, estoque baixo, personalizacao, prazos e por que comprar agora.

### Facilidade

A jornada e relativamente simples: poucos menus, formularios diretos e CTAs visiveis. O carrinho bloqueia o checkout quando nao ha frete escolhido, o que protege a operacao.

Esse bloqueio precisa ser tratado como ponto sensivel de conversao: se a mensagem ou o calculo de frete falhar, a cliente fica impedida de comprar. Por isso o carrinho e um ponto critico do Epico 3.

### Confianca

Os principais sinais de confianca ja existem: garantia de 2 anos, troca, privacidade, FAQ, termos, pagamento via InfinitePay, WhatsApp, Instagram, CNPJ, localizacao, horario, acompanhamento de pedido e politicas institucionais.

A oportunidade agora e transformar esses sinais em seguranca percebida durante a decisao. Em joias e semijoias, a cliente compra imagem, presente, durabilidade e confianca. Esses pontos precisam aparecer perto do produto, do carrinho e do checkout, nao apenas no rodape.

### Continuidade da jornada

A continuidade tecnica do fluxo e boa. A continuidade comercial ainda pode melhorar:

- Home deve conduzir mais fortemente para colecoes, presentes e best sellers.
- Catalogo deve ajudar a escolher melhor, nao apenas listar.
- Produto deve reduzir duvida e aumentar desejo.
- Carrinho deve confirmar valor, frete e seguranca.
- Checkout deve passar tranquilidade para pagar fora do ambiente da loja.
- Pedido deve orientar proximos passos e atendimento pos-compra.

## Avaliacao por pagina

Notas de 0 a 10, considerando a loja publicada e a experiencia percebida da cliente.

| Pagina | Clareza | Confianca | Conversao | Mobile | Visual | Performance percebida |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 7 | 7 | 6 | 7 | 7 | 8 |
| Catalogo | 8 | 6 | 7 | 7 | 7 | 7 |
| Produto | 8 | 8 | 8 | 7 | 7 | 7 |
| Carrinho | 8 | 7 | 8 | 7 | 7 | 7 |
| Checkout | 8 | 8 | 7 | 7 | 7 | 7 |
| Cadastro/Login | 7 | 6 | 6 | 7 | 7 | 8 |
| Pedido | 8 | 8 | 7 | 7 | 7 | 8 |

### Home

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 7 |
| Confianca | 7 |
| Conversao | 6 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 8 |

Analise:

- Hero: comunica elegancia e ouro 18k, mas usa a logo como imagem principal. Para conversao, imagens reais de produto, composicoes de uso ou campanha tendem a gerar mais desejo.
- Banner: a area inicial e bonita, mas poderia vender uma colecao, beneficio ou oferta mais concreta.
- CTA: `Ver Catalogo` e claro. `Mais Vendidos` aponta para destaques, mas a secao se chama colecao e pode nao provar que sao realmente mais vendidos.
- Categorias: boas para navegacao; as categorias sao facilmente reconheciveis.
- Produtos: a vitrine inicial carrega produtos da API, o que ajuda atualizacao. A oportunidade e destacar criterios comerciais como lancamentos, presentes, estoque limitado ou personalizados.
- Beneficios: ouro 18k, frete, parcelamento e troca aparecem. Sao bons sinais, mas poderiam estar conectados a links ou explicacoes curtas.
- Prova social: nao ha depoimentos, avaliacoes, fotos de clientes ou sinais de vendas reais.
- Identidade: a marca esta presente e coerente.
- Hierarquia visual: boa, mas ainda mais institucional do que orientada a compra imediata.

Diagnostico comercial:

A Home apresenta a marca de forma agradavel, mas ainda nao trabalha todo o potencial de desejo e urgencia. Para conversao, precisa antecipar perguntas: por que essa loja, por que essa peca, por que agora e por que posso confiar?

### Catalogo

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 8 |
| Confianca | 6 |
| Conversao | 7 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 7 |

Analise:

- Filtros: existem filtros por categoria e botao para limpar filtros.
- Organizacao: ha busca, ordenacao por recente, nome e preco, alem de contagem de resultados.
- Fotos: produtos importados usam fotos reais, mas os produtos iniciais usam SVGs simples. A mistura pode dar percepcao desigual de catalogo.
- Paginacao: a loja usa `Carregar mais produtos`, adequado para catalogo simples.
- Busca: existe busca textual com debounce.
- Badges: ha suporte a badge como `new`, mas o uso comercial ainda pode ser mais estrategico.
- Informacoes dos cards: cards exibem categoria, nome, descricao, preco, parcelamento e botao de adicionar. Bons fundamentos.

Diagnostico comercial:

O Catalogo e funcional e ja permite comprar sem entrar em produto. A principal oportunidade e ajudar a cliente a comparar: material, banho, garantia, estoque, personalizacao, presenteavel, mais vendidos e fotos com melhor consistencia.

### Produto

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 8 |
| Confianca | 8 |
| Conversao | 8 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 7 |

Analise:

- Fotos: ha galeria com imagem principal e miniaturas quando o produto possui mais de uma foto. Ponto forte.
- Descricao: existe, mas em alguns produtos e curta demais, como apenas nome ou lista de beneficios. Falta narrativa comercial.
- Garantia: aparece com destaque de 2 anos.
- Parcelamento: aparece em ate 12x.
- Frete: pode ser calculado na pagina do produto sem ir ao carrinho. Ponto muito positivo.
- CTA: `Adicionar ao Carrinho` e `Comprar Agora` sao claros.
- Informacoes tecnicas: ainda pouco visiveis para cliente. Material, banho, medidas, peso e cuidados poderiam aparecer de forma mais organizada quando existirem.
- Beneficios: ha cards de garantia, banho ouro 18k, compra segura, envio rapido e WhatsApp.
- Produtos relacionados: existem produtos relacionados por categoria.

Diagnostico comercial:

A pagina de produto e o ponto mais promissor da loja. Ela ja tem boa estrutura de conversao. O maior ganho futuro esta em enriquecer conteudo por produto: fotos melhores, descricao emocional, especificacoes, cuidados, prova de garantia e sugestoes para aumentar ticket medio.

### Carrinho

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 8 |
| Confianca | 7 |
| Conversao | 8 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 7 |

Analise:

- Clareza: itens, quantidade, subtotal, cupom, frete, desconto e total aparecem de forma objetiva.
- Resumo: o resumo do pedido e forte e fica separado dos itens.
- Confianca: mostra compra segura, 12x sem juros e troca em 30 dias.
- Frete: o frete e calculado e a selecao e obrigatoria antes de finalizar. Isso evita pedido sem regra de entrega.
- Continuacao da compra: ha `Continuar Comprando` e `Finalizar Compra`.

Diagnostico comercial:

O carrinho protege a operacao e orienta a compra. O risco comercial e que ele concentra um bloqueio: sem frete selecionado, nao ha checkout. A comunicacao desse ponto precisa ser impecavel, especialmente no mobile.

### Checkout

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 8 |
| Confianca | 8 |
| Conversao | 7 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 7 |

Analise:

- Simplicidade: o checkout esta em uma pagina unica, com dados pessoais, endereco, pagamento e observacoes.
- Quantidade de etapas: nao ha wizard; tudo aparece no mesmo fluxo. Bom para transparencia, mas pode parecer longo no celular.
- Seguranca percebida: a loja explica que o pagamento ocorre no ambiente protegido da InfinitePay e que nao pede dados sensiveis por WhatsApp, telefone ou e-mail. Excelente sinal.
- Comunicacao: ha painel de confianca com pagamento seguro, protecao de dados, acompanhamento, troca e garantia.

Diagnostico comercial:

O Checkout tem boa base de confianca. Para melhorar conversao, deve reduzir a sensacao de risco ao redirecionar para InfinitePay e reforcar que a cliente voltara a acompanhar o pedido na loja.

### Cadastro/Login

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 7 |
| Confianca | 6 |
| Conversao | 6 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 8 |

Analise:

- Facilidade: login e cadastro sao simples e centralizados.
- Clareza: os campos sao reconheciveis. O cadastro explica beneficios e newsletter.
- Recuperacao de senha: existe, mas usa prompt nativo do navegador. Funciona, porem passa menos profissionalismo.
- Mensagens: ha toasts de sucesso/erro.
- Login social: botoes de Google e Facebook exibem `em breve`. Isso pode criar frustracao se a cliente clicar esperando usar.

Diagnostico comercial:

Cadastro/Login nao parecem ser barreira obrigatoria para comprar, o que e bom. Mas, por envolver CPF e dados pessoais, precisam transmitir mais privacidade, finalidade e seguranca.

### Pedido

Notas:

| Criterio | Nota |
| --- | ---: |
| Clareza | 8 |
| Confianca | 8 |
| Conversao | 7 |
| Mobile | 7 |
| Visual | 7 |
| Performance percebida | 8 |

Analise:

- Pagina final: existe pagina de acompanhamento em `/pedido`.
- Proximos passos: a pagina permite consultar por numero do pedido, token seguro, e-mail e CPF.
- Comunicacao: exibe status, progresso, entrega, resumo, itens, historico e rastreio quando disponivel.

Diagnostico comercial:

A pagina de Pedido e um bom diferencial de confianca para uma loja pequena. Ela ajuda pos-compra, reduz ansiedade e pode diminuir atendimento manual. Falta apenas explorar melhor a continuidade comercial pos-compra, como WhatsApp, troca, cuidados e recomendacoes.

## Objecoes da cliente

Pontos que podem fazer a cliente desistir ou adiar a compra:

- "Nao conheco essa loja; sera confiavel?"
- "As fotos mostram bem o tamanho e o acabamento da peca?"
- "E semijoia mesmo? O banho e de ouro 18k?"
- "A garantia de 2 anos cobre exatamente o que?"
- "Posso trocar se nao gostar ou se nao servir?"
- "O frete vai ficar caro?"
- "Por que preciso calcular frete antes de ir para o checkout?"
- "O prazo de entrega esta claro?"
- "Posso falar com alguem antes de pagar?"
- "O pagamento vai sair da loja para InfinitePay; e seguro?"
- "Meus dados de CPF, telefone e endereco estao protegidos?"
- "O produto tem estoque real?"
- "Produto personalizado demora mais?"
- "Faltam detalhes tecnicos, medidas ou cuidados."
- "O produto parece bonito, mas nao vejo depoimentos ou prova social."
- "O botao de Google/Facebook aparece, mas nao funciona ainda."
- "Se der problema no pagamento, como acompanho?"
- "Depois que comprar, como recebo o codigo de rastreio?"
- "Nao sei se o desconto/cupom esta aplicado corretamente."
- "No celular, formularios longos podem cansar antes do pagamento."

## Oportunidades

### 🔴 Alta prioridade

- Reforcar prova de confianca nos pontos de decisao: produto, carrinho e checkout.
- Transformar garantia, troca, privacidade e FAQ em argumentos visiveis durante a compra, nao apenas links de rodape.
- Melhorar a comunicacao do frete: quando e calculado, quando e gratis, prazo, transportadora e por que precisa ser selecionado antes do checkout.
- Explicar melhor o redirecionamento para InfinitePay antes do clique final.
- Remover ou ajustar CTAs de login social enquanto nao estiverem ativos.
- Enriquecer a pagina de produto com especificacoes, medidas, cuidados, banho, estoque e personalizacao.
- Melhorar consistencia das fotos do catalogo para reduzir diferenca entre produtos SVG e fotos reais.
- Criar prova social inicial: depoimentos, fotos de clientes, destaques de atendimento ou garantia.
- Validar o fluxo mobile de produto → carrinho → checkout → pagamento, pois e o caminho mais sensivel de conversao.

### 🟡 Media prioridade

- Criar vitrines comerciais na Home: lancamentos, presentes, personalizados, ate R$ X, mais vendidos.
- Melhorar hierarquia dos cards no Catalogo para comparacao rapida.
- Destacar cupom `VJ10` de forma controlada e estrategica, sem poluir a experiencia.
- Inserir WhatsApp contextual em produto, carrinho e checkout para duvidas antes da compra.
- Melhorar recuperacao de senha com tela propria em vez de prompt nativo.
- Criar uma pagina ou area de Minha Conta mais clara para historico e dados da cliente.
- Usar badges comerciais mais objetivos: Novo, Ultimas unidades, Personalizavel, Presenteavel.
- Adicionar conteudo de cuidado das semijoias na jornada pos-compra e produto.

### 🟢 Baixa prioridade

- Evoluir recomendacoes de produtos relacionados por complementaridade, nao apenas categoria.
- Criar lista de desejos/favoritos.
- Criar guias de presente por ocasiao.
- Criar campanhas sazonais com landing pages.
- Melhorar microcopy de newsletter e pos-compra.
- Evoluir SEO de produto com conteudo editorial e colecoes.
- Criar testes A/B futuros para CTAs e banners, quando houver volume de trafego.

## Comparacao

Boas praticas observadas em grandes e-commerces de joias e semijoias, sem copiar layouts:

- Confianca sempre perto da decisao: marcas maiores nao deixam garantia, troca, privacidade e atendimento apenas no rodape. Elas repetem esses sinais perto do preco, do CTA e do checkout.
- Produto como vitrine principal: fotos multiplas, zoom, uso no corpo, medidas, composicao, banho, cuidados e embalagem aumentam seguranca.
- Compra para presente: joias e semijoias vendem muito por ocasiao. Boas lojas organizam sugestoes por presente, estilo, faixa de preco e momento.
- Frete transparente: prazo, custo, gratis acima de determinado valor e transportadora aparecem antes do pagamento.
- Prova social: avaliacoes, depoimentos, fotos reais e quantidade de vendas reduzem risco percebido.
- Pagamento externo explicado: quando o pagamento vai para outro ambiente, boas lojas avisam antes e reforcam seguranca.
- Checkout curto e previsivel: formularios longos sao quebrados por blocos claros, com resumo sempre visivel e mensagens de seguranca.
- Pos-compra ativo: pagina de pedido, rastreio, e-mail, WhatsApp e orientacoes de cuidado ajudam recompra e reduzem suporte manual.

Comparando com essas praticas, a VJ Semijoias ja tem uma base forte para uma loja em evolucao: catalogo, produto, carrinho, checkout, pagamento seguro e acompanhamento. O maior salto do Epico 3 e tornar a experiencia mais persuasiva e confiavel, com conteudo comercial no momento certo.

## Plano sugerido

### Sprint 005 — Home Comercial

Objetivo: transformar a Home em uma pagina comercial que desperte desejo, transmita confianca e conduza naturalmente ao catalogo.

Impacto esperado: aumentar entrada no catalogo.

Escopo sugerido:

- Hero comercial.
- Banner principal.
- Categorias em destaque.
- Produtos em destaque.
- Beneficios.
- CTA.
- Prova social.
- Hierarquia visual.

### Sprint 006 — Catalogo

Objetivo: facilitar descoberta de produtos.

Impacto esperado: aumentar visualizacoes de produtos.

Escopo sugerido:

- Badges.
- Fotos.
- Organizacao.
- Destaques.
- Comparacao.
- Descoberta.

### Sprint 007 — Pagina de Produto

Objetivo: aumentar taxa de adicionar ao carrinho.

Impacto esperado: maior conversao produto -> carrinho.

Escopo sugerido:

- Descricao comercial.
- Informacoes tecnicas.
- Garantia.
- Cuidados.
- Medidas.
- Combinacoes.
- Produtos relacionados.
- Prova social.

### Sprint 008 — Carrinho

Objetivo: reduzir abandono.

Impacto esperado: maior continuidade para checkout.

Escopo sugerido:

- Clareza.
- Frete.
- Comunicacao.
- Resumo.
- Seguranca.

### Sprint 009 — Checkout

Objetivo: reduzir desistencia antes do pagamento.

Impacto esperado: maior taxa de pedidos concluidos.

Escopo sugerido:

- Comunicacao.
- Seguranca.
- InfinitePay.
- Mensagens.
- Campos.
- UX mobile.

### Sprint 010 — Pos-compra

Objetivo: fidelizacao.

Impacto esperado: maior recompra.

Escopo sugerido:

- Pagina do pedido.
- Rastreio.
- Cuidados.
- Recomendacoes.
- Atendimento.
- Recompra.

## KPIs do Epico 3

Cada sprint do Epico 3 devera possuir indicadores de sucesso para orientar priorizacao, validacao e evolucao do funil comercial.

| Sprint | KPI principal |
|---------|---------------|
| Sprint 005 | Cliques para Catalogo |
| Sprint 006 | Visualizacoes de Produto |
| Sprint 007 | Adicoes ao Carrinho |
| Sprint 008 | Reducao de Abandono do Carrinho |
| Sprint 009 | Pedidos Concluidos |
| Sprint 010 | Recompra |

No momento os KPIs sao metas arquiteturais. Futuramente poderao ser medidos por ferramentas como Google Analytics, PostHog, Plausible ou outra solucao de analytics.

## Restricoes observadas

- Nenhuma melhoria foi implementada.
- Apenas `docs/AUDIT_CONVERSAO.md` foi alterado.
- Nenhum outro documento foi alterado.
- O frontend nao foi modificado.
- O backend nao foi modificado.
- O banco de dados nao foi modificado.
- As APIs nao foram modificadas.
- `ROADMAP.md` nao foi modificado.
- `PRODUCT.md` nao foi modificado.
- `ARCHITECTURE.md` nao foi modificado.

## Validacoes

Esta tarefa foi exclusivamente documental. Por isso, nao foram executados:

- `pytest`
- smoke tests
- `node --check`
- Alembic

A validacao realizada foi de auditoria comercial/documental. Testes automatizados nao seriam proporcionais ao escopo, pois nao houve alteracao de codigo, frontend, backend, banco de dados, APIs ou comportamento.
