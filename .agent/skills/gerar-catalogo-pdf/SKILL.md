---
name: gerar-catalogo-pdf
description: |
  Gera um catálogo PDF oficial e diagramado da VJ Semijoias a partir de uma pasta
  contendo imagens, descrições e preços de produtos (como a saída da skill pdf-catalog-extract).
  Garante a identidade visual da marca (cores dourado/creme/escuro, logo VJ Semijoias e estilo de capa).
  Triggers típicos: "gerar catalogo pdf", "criar catalogo a partir das imagens", "build catalog pdf from products", "criar PDF vj semijoias".
---

# Gerador de Catálogo PDF VJ Semijoias

Este guia orienta o agente na geração automática de catálogos em formato PDF, com a marca oficial da VJ Semijoias, a partir de dados estruturados e imagens extraídas (por exemplo, após a execução da skill `pdf-catalog-extract`).

## Entradas Necessárias
- **Diretório de origem dos produtos:** Caminho para a pasta contendo as imagens e arquivos de metadados (`info.json`) de cada produto (ex: `extract/` ou `extract/products/`).
- **Caminho do PDF de saída:** Onde o catálogo final deve ser gerado (ex: `pdf/catalogo-vj-oficial.pdf`).
- **Layout de exibição:** Quantidade de produtos por página (padrão: 6 produtos por página em uma grade 2x3).
- **Dados complementares (Opcional):** Slogan, cupons, contatos atualizados e informações da introdução.
- **Logo oficial:** Usar a imagem `frontend/images/logo.png` como marca principal na capa e no cabeçalho. Se o arquivo não existir, usar o texto "VJ SEMIJOIAS" como fallback.
- **Contatos oficiais:** Exibir Instagram `@vj_semijoias` e WhatsApp `(51) 98211-0842` nos blocos de contato do PDF.

## Procedimento de Execução

1. **Varredura e Carregamento de Dados:**
   - Escanear o diretório de origem em busca de subpastas do tipo `<NN>_<slug>` (geradas pela extração).
   - Ler o arquivo `info.json` de cada subpasta para extrair:
     - `title` (Título do produto)
     - `primary_price` ou `prices` (Preço formatado)
     - `description` ou `description_lines` (Descrição)
     - `category` (Categoria para separação em abas/páginas)
     - `images` (Lista de caminhos relativos de imagens)
   - Filtrar e ignorar pastas não-produto (como `00_cover_thumbnails`).

2. **Agrupamento por Categoria:**
   - Agrupar os produtos por sua categoria (ex: *Brincos*, *Colares*, *Pulseiras*, *Anéis*, *Pingentes*).
   - Ordenar os produtos numericamente/alfabeticamente para manter a sequência lógica do catálogo.

3. **Cálculo de Páginas:**
   - Calcular o total de páginas do documento para exibir no rodapé (`Página X de Y`):
     - `Página 1`: Capa
     - `Páginas 2 a N`: Páginas de produtos agrupados (máximo de 6 produtos por página)
   - Não gerar página de introdução, página de boas-vindas, diferenciais da loja ou contracapa.

4. **Identidade Visual VJ Semijoias (Paleta de Cores):**
   - **GOLD_DARK:** `#a67c3d` (Destaque de preços, categorias e títulos principais)
   - **GOLD:** `#c9a86a` (Linhas decorativas, logo secundário)
   - **GOLD_PALE:** `#f3e7d1` (Fundo dos diferenciais, bordas de cards)
   - **CREAM:** `#fbf6ee` (Fundo da capa)
   - **DARK:** `#1f1815` (Faixa escura da capa e textos principais)
   - **GRAY:** `#7a6e64` (Textos de descrição e rodapé)

5. **Diagramação e Geração com ReportLab (Python):**
   - **Capa:** Usar uma composição mais preenchida, com faixa escura no topo, círculos decorativos nas cores ouro/rosê, a imagem oficial `frontend/images/logo.png` em destaque, título grande do catálogo, cupom e contatos oficiais.
   - **Grid de Produtos (2 colunas x 3 linhas por página):**
     - Card do Produto: Desenhar um retângulo arredondado de fundo branco com borda suave (`GOLD_PALE`) ocupando bem a altura útil da página.
     - **Imagem do Produto:** Carregar a imagem principal (`img_1.jpeg` ou similar). Redimensioná-la proporcionalmente para caber no lado esquerdo do card, garantindo que a proporção original da foto da joia seja mantida para não distorcê-la.
     - **Textos do Card (Lado Direito):** Desenhar categoria (em letras maiúsculas), número identificador (`#01`, `#02`), título do produto, descrição com quebra automática e o preço em fonte maior e negrito.

6. **Compilação e Verificação:**
   - Gerar o PDF no caminho de saída.
   - Verificar se o arquivo foi criado com sucesso e não está zerado.
   - Reportar ao usuário o tamanho do arquivo gerado e o total de páginas.

## Tratamento de Falhas

- **Produto sem imagem:** Desenhar uma caixa cinza suave com o texto "Imagem indisponível" no lugar da foto, mas preservar todos os textos e preços do produto.
- **Descrição muito longa:** Limitar a descrição a no máximo 2 ou 3 linhas dentro do card para evitar que o texto transborde a borda.
- **Imagem corrompida:** Se o ReportLab falhar ao ler uma imagem específica, capturar a exceção, substituir por uma imagem padrão/placeholder ou caixa cinza e registrar o aviso no terminal para não interromper a geração do PDF inteiro.
- **Categorias vazias:** Ignorar categorias que não possuem nenhum produto cadastrado, recalculando o número total de páginas.

## Execução Automatizada
Para facilitar a execução, utilize o script complementar `.agent/skills/gerar-catalogo-pdf/scripts/generate_catalog.py` que realiza toda a leitura do manifest/imagens e monta o PDF final automaticamente.
