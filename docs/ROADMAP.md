# Visão do Produto

Este documento é a referência oficial para a evolução do projeto VJ Semijoias.
Ele deve ser atualizado sempre que uma funcionalidade relevante for concluída,
alterada ou planejada.

O VJ Semijoias é composto por dois grandes módulos complementares:

1. **Site público**
   Canal de vendas da marca. É responsável por apresentar a loja, exibir o
   catálogo, permitir cadastro e login de clientes, montar carrinho, calcular
   frete e descontos, criar pedidos públicos e direcionar o cliente para o
   pagamento seguro.

2. **VJ Admin**
   Sistema de gestão interna da loja. É responsável por administrar produtos,
   fornecedores, precificação, estoque, pedidos internos, clientes, financeiro
   simples, dashboard, auditoria e configurações operacionais da loja.

O site público deve ser simples e confiável para o cliente final. O VJ Admin
deve ser o centro operacional da empresa, evitando controles paralelos em
planilhas ou processos manuais sempre que uma regra já existir no sistema.

# Status Atual

| Módulo | Status | Observações |
|---|---:|---|
| Site público de vendas | 🟡 Em evolução | Vitrine, catálogo, carrinho, cadastro, login, checkout e pagamento integrado existem; ainda precisa evoluir experiência, SEO e acabamento comercial. |
| Checkout e pagamentos | 🟡 Em evolução | Fluxo com InfinitePay e validações no backend existem; ainda falta validação final em ambiente comercial, maior observabilidade e evoluções de PIX/reconciliação. |
| VJ Admin | 🟡 Em evolução | Painel operacional existe e está organizado por áreas; continua recebendo melhorias de usabilidade e profundidade funcional. |
| Produtos | ✅ Concluído | Cadastro, edição, importação, imagens, status e campos comerciais existem no admin e na API. |
| Fornecedores | ✅ Concluído | Cadastro e gestão de fornecedores já fazem parte do VJ Admin. |
| Precificação automática | ✅ Concluído | Regras de cálculo ficam em services e alimentam campos comerciais do produto. |
| Estoque | ✅ Concluído | Saldo atual e movimentos de estoque estão modelados; pedidos internos confirmados movimentam estoque. |
| Pedidos | 🟡 Em evolução | Existem pedidos públicos e pedidos internos do VJ Admin; melhorias comerciais e operacionais ainda podem ser adicionadas. |
| Clientes / CRM | ✅ Concluído | Cadastro de clientes do admin, normalização de dados e relacionamento com pedidos internos existem. |
| Financeiro simples | 🟡 Em evolução | Já possui despesas manuais e resumo operacional; DRE, fluxo de caixa, contas a pagar/receber e conciliação ficam para fases futuras. |
| Dashboard | 🟡 Em evolução | Indicadores executivos existem e reutilizam cálculos financeiros; deve evoluir para análises mais completas. |
| Auditoria | ✅ Concluído | Eventos administrativos e movimentações relevantes possuem trilha de auditoria. |
| Arquitetura modular | ✅ Concluído | Backend separado em routers, services e models por domínio. |
| Testes automatizados | ✅ Concluído | Suite de testes cobre os principais domínios do backend e do VJ Admin. |
| Alembic organizado | ✅ Concluído | Migrations estão versionadas e o app não altera schema no startup. |
| Smoke tests | ✅ Concluído | `tools/e2e_smoke.py` valida fluxos principais de forma isolada. |
| Documentação de arquitetura | ✅ Concluído | `docs/ARCHITECTURE.md` documenta domínios, regras críticas e organização dos modelos. |
| Permissões e multiusuário | ⬜ Planejado | Ainda não faz parte da base concluída; previsto para uma fase maior do VJ Admin. |
| NFe | ⬜ Planejado | Integração fiscal futura, sem escopo implementado na versão atual. |

# Roadmap

## MVP

Itens já concluídos na base atual do projeto:

- Site público servido pelo FastAPI.
- Catálogo público de produtos.
- Página de produto.
- Carrinho.
- Checkout integrado ao backend.
- Integração de pagamento com InfinitePay.
- Cadastro e login de clientes.
- VJ Admin com autenticação administrativa.
- Gestão de produtos.
- Importação de catálogo.
- Gestão de fornecedores.
- Precificação automática.
- Controle de estoque.
- Movimentos de estoque.
- Pedidos públicos.
- Pedidos internos do VJ Admin.
- Clientes / CRM.
- Financeiro simples com despesas manuais e resumo operacional.
- Dashboard executivo inicial.
- Auditoria administrativa.
- Configurações da loja.
- Arquitetura modular com routers, services e models.
- Migrations Alembic organizadas.
- Testes automatizados.
- Smoke test ponta a ponta.
- Documentação de arquitetura.

## Versão 1.0

Objetivo: deixar o sistema pronto para uso comercial com segurança operacional,
boa experiência de compra e processo de gestão confiável.

- Melhorar a experiência do site público em navegação, busca, filtros e
  apresentação dos produtos.
- Refinar o checkout com mensagens claras de erro, estados de carregamento,
  recuperação de falhas e confirmação de pedido.
- Validar pagamentos, webhook e fluxo de confirmação em ambiente comercial.
- Fortalecer SEO técnico do site público.
- Revisar performance de carregamento das páginas públicas.
- Consolidar políticas de frete, desconto e configurações comerciais.
- Revisar textos, imagens e acabamento visual do catálogo público.
- Definir rotina operacional de backup e restauração.
- Definir checklist de deploy para DEV/PRD.
- Garantir que todos os fluxos críticos tenham testes automatizados e smoke
  test atualizado.
- Manter Alembic sem drift entre models e migrations.

## Versão 1.5

Objetivo: melhorar produtividade, clareza operacional e experiência diária de
uso no site e no VJ Admin.

- Melhorar ergonomia do VJ Admin para tarefas repetitivas.
- Criar filtros e buscas mais completos para produtos, pedidos, clientes,
  estoque e financeiro.
- Evoluir telas longas para fluxos mais escaneáveis e objetivos.
- Melhorar visualização de histórico de cliente, pedidos e movimentações.
- Evoluir etiquetas para separação, embalagem ou identificação de produtos.
- Evoluir geração de catálogo PDF a partir dos dados atuais do produto.
- Melhorar relatórios exportáveis para uso operacional.
- Ampliar feedback visual em ações administrativas importantes.

## Versão 2.0

Objetivo: adicionar funcionalidades maiores que ampliam automação, controle
financeiro e escala operacional.

- Permissões e multiusuário no VJ Admin.
- Contas a pagar.
- Contas a receber.
- Fluxo de caixa.
- DRE.
- Dashboard 2.0.
- Integração operacional com WhatsApp.
- Melhor Envio como fluxo comercial completo de frete e postagem.
- PIX automático com conciliação mais direta.
- NFe.
- IA para descrição de produtos.
- IA para marketing.
- Automações comerciais e operacionais futuras.

# Prioridades

## Alta

- Melhorar experiência do site público.
- Refinar checkout e confirmação de pagamento.
- Validar fluxo comercial em ambiente real.
- Melhorar SEO.
- Garantir backup, deploy e Alembic sem drift.

## Média

- Melhorar telas e filtros do VJ Admin.
- Evoluir etiquetas.
- Evoluir catálogo PDF.
- Melhorar relatórios operacionais.
- Aprofundar dashboard e financeiro.

## Baixa

- IA para descrição de produtos.
- IA para marketing.
- Integrações futuras.
- NFe.
- Automações avançadas.

# Princípios do Projeto

- O site público é o canal de vendas.
- O VJ Admin é o sistema de gestão.
- Regras de negócio não devem ser duplicadas entre frontend, routers e
  services.
- Services devem ser reutilizados sempre que uma regra for compartilhada.
- A arquitetura modular deve ser mantida.
- Toda alteração relevante deve preservar ou ampliar a cobertura de testes.
- Alembic deve permanecer sem drift em relação aos models.
- Todo novo módulo deve possuir testes.
- Toda feature relevante deve atualizar a documentação.
- O backend deve recalcular valores críticos no servidor.
- O `backend/app.py` deve continuar focado em montar a aplicação, registrar
  middlewares, routers e arquivos estáticos.

# Critérios para considerar uma feature concluída

Uma funcionalidade só pode ser marcada como concluída quando o checklist abaixo
estiver atendido:

- [ ] Código implementado.
- [ ] Testes automatizados adicionados ou atualizados.
- [ ] Smoke test executado ou atualizado quando o fluxo for crítico.
- [ ] Alembic check realizado quando houver alteração de models ou schema.
- [ ] Documentação atualizada.
- [ ] Revisão arquitetural concluída.

# Backlog Futuro

Ideias e evoluções futuras que ainda não fazem parte do escopo concluído:

- WhatsApp.
- Evoluir catálogo PDF.
- Etiquetas.
- IA para descrição de produtos.
- IA para marketing.
- Melhor Envio.
- PIX automático.
- NFe.
- Multiusuário.
- Permissões.
- Dashboard 2.0.
- DRE.
- Fluxo de caixa.
- Contas a pagar.
- Contas a receber.

# Histórico

| Versão | Data | Descrição |
|---|---:|---|
| MVP | 2026-07-01 | Base atual consolidada com site público, VJ Admin, arquitetura modular, Alembic, testes, smoke tests e documentação de arquitetura. |
| 1.0 | A definir | Prontidão comercial do site público, checkout, SEO, deploy, backup e validações operacionais. |
| 1.5 | A definir | Melhorias de experiência, filtros, etiquetas, catálogo PDF e relatórios operacionais. |
| 2.0 | A definir | Grandes funcionalidades: multiusuário, permissões, financeiro avançado, integrações e IA. |
