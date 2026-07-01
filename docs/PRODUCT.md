# Produto VJ Semijoias

Este documento registra a gestão de produto do projeto VJ Semijoias. Ele não
substitui o `ROADMAP.md`: aqui ficam ideias, backlog, decisões e critérios de
priorização; no roadmap ficam versões, objetivos e grandes entregas.

## Objetivo do produto

O VJ Semijoias é um sistema integrado para venda e gestão de semijoias. O site
público deve facilitar a descoberta de produtos, o carrinho e o checkout. O VJ
Admin deve centralizar a operação da loja, incluindo produtos, fornecedores,
precificação, estoque, pedidos, clientes, financeiro, dashboard e auditoria.

O produto deve evoluir sem duplicar regras de negócio, preservando a arquitetura
modular e a confiabilidade operacional.

---

## Como priorizamos

Toda nova ideia deve responder:

1. Melhora as vendas do site público?
2. Melhora a operação do VJ Admin?
3. Aumenta dívida técnica?
4. Está madura para implementação?
5. Em qual versão do ROADMAP ela pertence?

As ideias com impacto direto em vendas, checkout, gestão operacional ou
confiabilidade tendem a ter prioridade maior. Ideias com alto custo, baixa
clareza de requisito ou dependência externa devem permanecer em análise ou ser
adiadas até que estejam mais maduras.

---

## Ideias em análise

| Funcionalidade | Impacto | Complexidade | Versão sugerida | Status |
|---|---|---|---|---|
| Upload de imagens + URL + armazenamento Cloudflare R2 | Alto | Alta | 1.0 | Em análise |
| Painel do cliente | Médio | Média | 1.5 | Em análise |
| Recuperação de senha | Alto | Média | 1.0 | Em análise |
| Confirmação por e-mail | Médio | Média | 1.0 | Em análise |
| Infraestrutura para emissão de documentos fiscais | Alto | Alta | 2.0 | Em análise |
| Painel de configurações da loja | Alto | Média | 1.0 | Em análise |
| Catálogo PDF avançado | Médio | Média | 1.5 | Em análise |

---

## Funcionalidades aprovadas

Nenhuma funcionalidade aprovada registrada neste momento.

---

## Funcionalidades adiadas

Nenhuma funcionalidade adiada registrada neste momento.

---

## Funcionalidades rejeitadas

Nenhuma funcionalidade rejeitada registrada neste momento.

---

## Decisões de produto

| Data | Decisão | Motivo |
|---|---|---|
| 2026-07-01 | Separar `ROADMAP.md` e `PRODUCT.md` | Manter o roadmap focado em versões e usar este documento para backlog, ideias e decisões de produto. |

---

## Relação com ROADMAP

O `ROADMAP.md` responde:

> O que será entregue em cada versão?

O `PRODUCT.md` responde:

> Quais ideias existem e como elas estão sendo avaliadas?

Uma ideia pode nascer neste documento, ser analisada, aprovada, adiada ou
rejeitada. Quando uma ideia aprovada virar entrega planejada de versão, ela deve
ser refletida no `ROADMAP.md` sem transformar o roadmap em uma lista completa de
todas as possibilidades futuras.