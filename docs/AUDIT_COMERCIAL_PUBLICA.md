# Auditoria Comercial da Loja Pública - VJ Semijoias

Este documento avalia a loja pública do VJ Semijoias sob a perspectiva comercial de uma cliente real que entra no site para comprar uma semijoia.

A auditoria complementa o inventário técnico registrado em `docs/AUDIT_FRONTEND.md`. Ela não substitui o ROADMAP nem implementa melhorias. O objetivo é orientar a Versão 1.0 Comercial com achados, impacto e priorização.

Legenda de prioridade:

| Prioridade | Significado |
| --- | --- |
| 🔴 Crítico para 1.0 | Necessário para operar comercialmente com confiança. |
| 🟡 Importante para 1.0 | Deve ser tratado antes ou durante a consolidação da versão comercial. |
| 🟢 Desejável para 1.5 | Melhora experiência e conversão, mas não bloqueia a operação inicial. |
| ⭐ Futuro / PRODUCT.md | Ideia de produto ou evolução maior para avaliação futura. |

---

# 1. Home

## Pontos fortes

- A home possui proposta visual clara para semijoias banhadas a ouro 18k.
- Existem CTAs diretos para compra, como `Ver Catálogo`, `Mais Vendidos` e `Ver Catálogo Completo`.
- A página comunica benefícios comerciais relevantes: frete, pagamento seguro e troca.
- Há seção institucional `Sobre Nós` e área de contato/newsletter.
- O rodapé da home inclui canais configuráveis, como e-mail, telefone, localização, horário, Instagram e WhatsApp.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| A home informa `Frete Grátis em todos os pedidos para todo o Brasil`, enquanto produto/carrinho/checkout trabalham com cálculo e seleção de frete. | Pode gerar quebra de expectativa e atrito no carrinho ou checkout. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| Links institucionais do rodapé apontam para `#` em itens como política de troca, política de privacidade, termos de uso e FAQ. | Reduz confiança para primeira compra e pode prejudicar credibilidade. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| A seção de contato é também newsletter, o que pode deixar suporte e atendimento menos evidentes. | Cliente com dúvida antes da compra pode não encontrar rapidamente como falar com a loja. | 🟡 Importante para 1.0 | Sprint 002 — Confiança e informações institucionais |
| A promessa comercial de troca aparece, mas sem página detalhada de política. | A cliente vê o benefício, mas não encontra critérios, prazos e condições. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |

## Impacto comercial

A home já cumpre o papel de entrada para a loja, mas precisa alinhar promessas comerciais com o fluxo real de compra. Para versão 1.0, os principais pontos são confiança, clareza institucional e consistência entre o que é prometido na vitrine e o que acontece no carrinho.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 002 — Confiança e informações institucionais

---

# 2. Catálogo

## Pontos fortes

- O catálogo possui rota própria em `/catalogo`.
- Há filtros por categoria, busca e carregamento incremental de produtos.
- Existe CTA para baixar catálogo PDF e para visualizar o PDF online.
- Os cards exibem preço e parcelamento em até 12x sem juros por meio do frontend.
- O catálogo reutiliza produtos vindos da API pública.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| O catálogo tem boa estrutura funcional, mas poucos elementos de confiança próximos aos produtos. | Cliente pode navegar, mas não recebe reforços suficientes de garantia, troca, envio e atendimento durante a decisão. | 🟡 Importante para 1.0 | Sprint 006 — Home e catálogo |
| O rodapé do catálogo tem redes sociais com links `#` e conteúdo diferente da home. | Passa sensação de inconsistência e pode reduzir confiança. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| O contato padrão no catálogo aparece com telefone diferente do exibido na home antes da configuração dinâmica. | Pode gerar dúvida sobre qual contato é oficial. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| O PDF aparece como CTA, mas a relação comercial entre comprar pelo site e consultar o PDF ainda pode ficar ambígua. | Cliente pode sair do fluxo de compra e não voltar para finalizar pedido. | 🟢 Desejável para 1.5 | Sprint 006 — Home e catálogo |

## Impacto comercial

O catálogo já permite descoberta de produtos, mas a versão comercial deve reduzir dúvidas durante a navegação. A compra de semijoias depende de confiança visual, clareza de preço, disponibilidade, banho, garantia, troca e canal de atendimento.

## Prioridade geral

🟡 Importante para 1.0

## Sugestão de sprint futura

Sprint 006 — Home e catálogo

---

# 3. Página de produto

## Pontos fortes

- A página possui rota dedicada em `/produto`.
- Há CTAs claros: `Adicionar ao Carrinho` e `Comprar Agora`.
- O preço e o parcelamento são exibidos na experiência pública.
- Há cálculo de frete diretamente na página do produto.
- Existe mensagem de compra segura e proteção de dados.
- Produto indisponível bloqueia os CTAs de compra.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| A página comunica compra segura, mas não detalha garantia, banho, cuidados, troca e condições comerciais da peça. | Cliente pode hesitar antes de adicionar ao carrinho, principalmente na primeira compra. | 🔴 Crítico para 1.0 | Sprint 004 — Página de produto |
| Não foi identificado SEO comercial específico por produto, como title/description dinâmicos, Open Graph ou dados estruturados. | Reduz potencial de compartilhamento e tráfego orgânico por produto. | 🟡 Importante para 1.0 | Sprint 003 — SEO público básico |
| O cálculo de frete é positivo, mas a home afirma frete grátis geral. | A inconsistência pode gerar abandono se a cliente esperar frete gratuito. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| O rodapé da página de produto é mais simples que o da home e possui links sociais estáticos. | Reduz consistência visual e institucional entre páginas. | 🟡 Importante para 1.0 | Sprint 002 — Confiança e informações institucionais |

## Impacto comercial

A página de produto é um ponto decisivo para conversão. Ela já tem CTAs e frete, mas precisa concentrar as informações que reduzem risco percebido: material, garantia, troca, envio, atendimento e segurança.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 004 — Página de produto

---

# 4. Carrinho

## Pontos fortes

- O carrinho possui rota própria em `/carrinho`.
- Exibe resumo de compra, subtotal, frete, desconto e total.
- O cálculo e seleção de frete são exigidos antes de avançar para o checkout.
- Há CTA principal `Finalizar Compra` e CTA secundário `Continuar Comprando`.
- Mensagens comerciais reforçam compra segura, 12x sem juros e troca em 30 dias.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| A exigência de calcular frete antes do checkout é clara, mas contrasta com a promessa de frete grátis na home. | Pode gerar sensação de cobrança inesperada ou regra confusa. | 🔴 Crítico para 1.0 | Sprint 005 — Carrinho e checkout |
| Os selos textuais de segurança, parcelamento e troca não levam a detalhes ou políticas. | A cliente recebe a promessa, mas não consegue confirmar as condições. | 🟡 Importante para 1.0 | Sprint 002 — Confiança e informações institucionais |
| Não foi identificado link direto para WhatsApp ou atendimento no momento de dúvida do carrinho. | Dúvidas sobre frete, prazo ou pagamento podem virar abandono. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |
| O carrinho depende fortemente de mensagens e estados dinâmicos; qualquer falha de cálculo pode bloquear avanço. | O bloqueio é correto operacionalmente, mas precisa ser acompanhado de comunicação clara para não frustrar a compra. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |

## Impacto comercial

O carrinho está funcionalmente orientado para conversão, mas precisa garantir que nenhum ponto de dúvida comercial fique sem resposta. Frete, prazo, troca, pagamento e atendimento são decisivos nesta etapa.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 005 — Carrinho e checkout

---

# 5. Checkout

## Pontos fortes

- O checkout possui rota própria em `/checkout`.
- O fluxo exige frete selecionado antes de iniciar pagamento.
- Há integração pública com checkout seguro da InfinitePay.
- O CTA principal é objetivo: `Ir para o pagamento seguro`.
- A tela comunica pagamento 100% seguro, entrega garantida e 30 dias para troca.
- Existe acompanhamento de pedido após pagamento ou pedido registrado.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| Não foi identificado aceite explícito de termos, política de troca ou privacidade no checkout. | Pode reduzir transparência e segurança jurídica/comercial da compra. | 🔴 Crítico para 1.0 | Sprint 005 — Carrinho e checkout |
| O checkout informa troca e entrega garantida, mas sem link para regras detalhadas. | Cliente pode desconfiar da promessa por falta de explicação formal. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| A segurança do pagamento é comunicada, mas depende da confiança na InfinitePay sem uma explicação institucional mais completa. | Para primeira compra, a cliente pode abandonar por incerteza sobre pagamento externo. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |
| O rodapé do checkout tem menos dados de contato que outras páginas. | Em caso de dúvida no momento de pagamento, a cliente encontra menos suporte visível. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |

## Impacto comercial

O checkout é o ponto de maior risco comercial. Ele já possui CTA e integração de pagamento, mas a versão 1.0 precisa transmitir segurança suficiente para a cliente concluir a primeira compra sem recorrer a canais externos.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 005 — Carrinho e checkout

---

# 6. Login/cadastro

## Pontos fortes

- Existem páginas públicas separadas para login e cadastro.
- O cliente de API possui endpoints para cadastro, login, sessão e logout.
- O fluxo de recuperação de senha existe no cliente e é acionado pela página de login.
- O cadastro coleta dados essenciais, incluindo e-mail e CPF.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| A recuperação de senha usa prompt do navegador para solicitar e-mail. | Experiência menos polida e menos confiável para uma loja comercial. | 🟢 Desejável para 1.5 | Sprint futura de conta do cliente |
| Não foi identificada página pública dedicada de Minha Conta. | Cliente pode não perceber onde consultar dados, histórico ou pedidos após login. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |
| O fluxo de login/cadastro não parece ser o centro da compra, mas existe no ecossistema da loja. | Pode ser suficiente para o MVP, mas precisa ficar claro se comprar exige conta ou não. | 🟡 Importante para 1.0 | Sprint 005 — Carrinho e checkout |
| Não foram identificadas mensagens institucionais próximas ao cadastro sobre privacidade e uso dos dados. | Cliente pode hesitar ao informar CPF, telefone e e-mail. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |

## Impacto comercial

Login e cadastro impactam confiança porque lidam com dados pessoais. Para versão comercial, a loja precisa explicar por que coleta cada dado e como a cliente acompanha seus pedidos.

## Prioridade geral

🟡 Importante para 1.0

## Sugestão de sprint futura

Sprint 005 — Carrinho e checkout

---

# 7. Confiança e credibilidade

## Pontos fortes

- A loja já possui elementos de confiança distribuídos: compra segura, troca em 30 dias, entrega garantida, contato, localização e horário.
- O rodapé da home usa dados configuráveis via `store-config.js`.
- WhatsApp e Instagram existem como canais previstos na estrutura da home e na configuração pública da loja.
- O acompanhamento de pedido possui rota própria em `/pedido`.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| Rodapés possuem diferenças entre páginas: redes sociais, telefone, quantidade de colunas e dados exibidos variam. | Inconsistência visual e de informação reduz confiança. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| Alguns links institucionais usam `#` e não levam a páginas reais. | Para primeira compra, a loja pode parecer incompleta. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| WhatsApp aparece como possibilidade, mas não está igualmente evidente em todos os pontos críticos de decisão. | Cliente que quer tirar dúvida antes de pagar pode sair do fluxo. | 🟡 Importante para 1.0 | Sprint 002 — Confiança e informações institucionais |
| Não foram identificadas páginas formais de política de troca, privacidade, termos, garantia ou FAQ. | Afeta confiança, clareza comercial e maturidade da versão 1.0. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |
| Garantia aparece como promessa comercial indireta, mas não foi identificada política detalhada. | Semijoias dependem fortemente de garantia, banho, cuidados e condições de uso. | 🔴 Crítico para 1.0 | Sprint 002 — Confiança e informações institucionais |

## Impacto comercial

Este é o maior eixo da versão comercial. Uma cliente que não conhece a loja precisa sentir segurança antes de informar dados, calcular frete e pagar. A loja já tem a base, mas precisa consolidar confiança institucional.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 002 — Confiança e informações institucionais

---

# 8. SEO comercial

## Pontos fortes

- Home e catálogo possuem meta description.
- Todas as páginas públicas inventariadas possuem title.
- O site possui `manifest.json` e favicon via logo.
- As rotas públicas são amigáveis para navegação: `/catalogo`, `/produto`, `/carrinho`, `/checkout`, `/login`, `/cadastro`, `/pedido`.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| Produto, carrinho, checkout, login, cadastro, pedido e PDF não possuem meta description identificada no inventário. | Páginas públicas ficam menos completas para busca e compartilhamento. | 🟡 Importante para 1.0 | Sprint 003 — SEO público básico |
| Não foram identificadas tags Open Graph. | Compartilhamentos em WhatsApp, Instagram, Facebook e mensagens podem ficar pobres. | 🟡 Importante para 1.0 | Sprint 003 — SEO público básico |
| Não foram identificados `sitemap.xml` e `robots.txt`. | Dificulta orientação básica para motores de busca. | 🟡 Importante para 1.0 | Sprint 003 — SEO público básico |
| Não foi identificado schema.org/Product ou dados estruturados. | Produtos perdem oportunidade de exibição mais rica em mecanismos de busca. | 🟢 Desejável para 1.5 | Sprint 003 — SEO público básico |
| A página de produto tem title genérico `Produto - VJ Semijoias`. | Compartilhamento e indexação por produto ficam menos comerciais. | 🟡 Importante para 1.0 | Sprint 003 — SEO público básico |

## Impacto comercial

SEO comercial não bloqueia a primeira venda, mas aumenta a capacidade da loja de ser encontrada e compartilhada com aparência profissional. Para 1.0, o foco mínimo deve ser SEO público básico e compartilhamento confiável.

## Prioridade geral

🟡 Importante para 1.0

## Sugestão de sprint futura

Sprint 003 — SEO público básico

---

# 9. Mobile/responsividade

## Pontos fortes

- As páginas públicas possuem meta viewport.
- O CSS público possui media queries para navegação, rodapé, carrinho, checkout e formulários.
- Os CTAs de produto usam largura flexível e `min-width`, favorecendo adaptação.
- Carrinho, frete e checkout possuem classes específicas para layout responsivo.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| A auditoria documental não executou validação visual em dispositivos móveis. | Risco comercial não confirmado: problemas reais de layout só aparecem com teste visual. | 🟡 Importante para 1.0 | Sprint 006 — Home e catálogo |
| Checkout e carrinho concentram muitos elementos críticos em telas pequenas. | Qualquer atrito mobile pode impactar diretamente conversão. | 🔴 Crítico para 1.0 | Sprint 005 — Carrinho e checkout |
| Rodapés e blocos institucionais variam entre páginas. | No mobile, inconsistências podem ficar mais perceptíveis e prejudicar confiança. | 🟡 Importante para 1.0 | Sprint 002 — Confiança e informações institucionais |
| O fluxo de recuperação de senha via prompt tende a parecer menos integrado no mobile. | Pode afetar percepção de profissionalismo. | 🟢 Desejável para 1.5 | Sprint futura de conta do cliente |

## Impacto comercial

A loja tem base responsiva, mas a versão comercial precisa validar a jornada real no celular, principalmente produto, carrinho e checkout. Em varejo, o mobile tende a ser o principal canal de decisão e compra.

## Prioridade geral

🔴 Crítico para 1.0

## Sugestão de sprint futura

Sprint 005 — Carrinho e checkout

---

# 10. Performance percebida

## Pontos fortes

- A loja pública usa JavaScript simples, sem dependências externas identificadas por CDN.
- Existe service worker com cache de arquivos estáticos, produtos e imagens relacionadas à API de produtos.
- O catálogo de PDF usa iframe com `loading="lazy"`.
- A estrutura do frontend evita bundlers pesados e bibliotecas desnecessárias.

## Problemas encontrados

| Achado | Impacto comercial | Prioridade | Sugestão de sprint futura |
| --- | --- | --- | --- |
| O diretório de catálogo possui grande volume de imagens reais. | Imagens pesadas podem afetar carregamento percebido, especialmente no mobile. | 🟡 Importante para 1.0 | Sprint 006 — Home e catálogo |
| Não foi identificado lazy loading geral para imagens de produto no HTML estático. | Pode aumentar tempo de carregamento em páginas com muitos produtos. | 🟡 Importante para 1.0 | Sprint 006 — Home e catálogo |
| O service worker ajuda cache, mas pode mascarar diferenças entre primeira visita e visitas seguintes. | Primeira compra pode ter experiência diferente da cliente recorrente. | 🟢 Desejável para 1.5 | Sprint futura de performance pública |
| Não houve medição de performance nesta auditoria documental. | Indicadores como LCP, CLS e tempo de interação ainda precisam de validação prática. | 🟡 Importante para 1.0 | Sprint 006 — Home e catálogo |

## Impacto comercial

A performance percebida afeta confiança e abandono, especialmente em catálogo e produto. A base técnica é leve, mas imagens e carregamento mobile devem ser observados antes da versão comercial.

## Prioridade geral

🟡 Importante para 1.0

## Sugestão de sprint futura

Sprint 006 — Home e catálogo

---

# Principais achados comerciais

| Tema | Achado | Prioridade |
| --- | --- | --- |
| Confiança | Políticas institucionais aparecem como links, mas não foram identificadas páginas reais. | 🔴 Crítico para 1.0 |
| Frete | Existe inconsistência entre promessa de frete grátis na home e cálculo/seleção de frete no fluxo de compra. | 🔴 Crítico para 1.0 |
| Rodapé | Rodapés variam entre páginas em links, canais e dados de contato. | 🔴 Crítico para 1.0 |
| Produto | Página de produto precisa concentrar informações comerciais de garantia, troca, cuidados e segurança. | 🔴 Crítico para 1.0 |
| Checkout | Segurança no pagamento existe, mas precisa de mais contexto institucional e links de política. | 🔴 Crítico para 1.0 |
| SEO | SEO básico existe parcialmente; faltam Open Graph, sitemap, robots e metadados em páginas públicas. | 🟡 Importante para 1.0 |
| Mobile | Há base responsiva, mas falta validação comercial visual da jornada mobile. | 🔴 Crítico para 1.0 |
| Performance | Estrutura é leve, mas imagens e primeira visita precisam de atenção comercial. | 🟡 Importante para 1.0 |

---

# Plano sugerido de sprints

## Sprint 002 — Confiança e informações institucionais

Prioridade: 🔴 Crítico para 1.0

Objetivo comercial: deixar a loja confiável para uma primeira compra.

Escopo sugerido:

- Consolidar política de troca.
- Consolidar política de privacidade.
- Consolidar termos de uso.
- Formalizar garantia e cuidados com semijoias.
- Padronizar rodapé entre páginas públicas.
- Revisar dados de contato exibidos em todas as páginas.
- Tornar WhatsApp consistente como canal de atendimento.
- Alinhar promessa de frete com regra real do carrinho/checkout.

## Sprint 003 — SEO público básico

Prioridade: 🟡 Importante para 1.0

Objetivo comercial: melhorar apresentação em busca e compartilhamento.

Escopo sugerido:

- Revisar titles comerciais das páginas públicas.
- Completar meta descriptions públicas.
- Criar Open Graph básico para páginas principais.
- Criar `robots.txt` e `sitemap.xml`, se fizer sentido para o deploy.
- Avaliar metadados específicos para produto.

## Sprint 004 — Página de produto

Prioridade: 🔴 Crítico para 1.0

Objetivo comercial: aumentar confiança no momento de decisão.

Escopo sugerido:

- Reforçar garantia, banho, cuidados e troca na página do produto.
- Exibir informações de frete e prazo com clareza.
- Melhorar hierarquia dos CTAs `Adicionar ao Carrinho` e `Comprar Agora`.
- Avaliar informações comerciais por produto sem duplicar regras de negócio.

## Sprint 005 — Carrinho e checkout

Prioridade: 🔴 Crítico para 1.0

Objetivo comercial: reduzir abandono no fechamento da compra.

Escopo sugerido:

- Revisar comunicação de frete no carrinho e checkout.
- Reforçar segurança do pagamento com InfinitePay.
- Adicionar acesso claro a atendimento no momento de compra.
- Exibir links de política e garantia no checkout.
- Validar jornada mobile de carrinho até pagamento.

## Sprint 006 — Home e catálogo

Prioridade: 🟡 Importante para 1.0

Objetivo comercial: melhorar descoberta, navegação e percepção de valor.

Escopo sugerido:

- Ajustar CTAs da home conforme objetivo comercial principal.
- Reforçar diferenciais reais da loja junto ao catálogo.
- Validar carregamento de imagens e experiência mobile.
- Avaliar papel do catálogo PDF dentro da jornada de compra.
- Padronizar mensagens comerciais entre home, catálogo e produto.

## Sprint futura — Conta do cliente

Prioridade: 🟢 Desejável para 1.5

Objetivo comercial: melhorar relacionamento pós-compra.

Escopo sugerido:

- Evoluir Minha Conta.
- Melhorar recuperação de senha sem prompt nativo.
- Exibir histórico de pedidos com clareza.
- Melhorar dados de perfil e acompanhamento.

## Backlog para PRODUCT.md

Prioridade: ⭐ Futuro / PRODUCT.md

Ideias a avaliar:

- Avaliações/depoimentos de clientes.
- Programa de fidelidade.
- Lista de desejos/favoritos.
- Vitrine personalizada por comportamento.
- Campanhas comerciais integradas ao WhatsApp.
- SEO avançado com dados estruturados completos.

---

# Observação final

Esta auditoria é exclusivamente documental. Nenhum arquivo de frontend ou backend foi alterado, nenhuma rota foi modificada e nenhum comportamento foi implementado.

As prioridades acima servem como orientação comercial para a Versão 1.0 e devem ser avaliadas junto ao ROADMAP e ao PRODUCT.md antes de virarem tarefas de implementação.