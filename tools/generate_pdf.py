#!/usr/bin/env python3
"""
Gera o catálogo PDF oficial da VJ Semijoias
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

# Cores da VJ Semijoias (paleta do logo)
GOLD_DARK = HexColor('#a67c3d')
GOLD = HexColor('#c9a86a')
GOLD_LIGHT = HexColor('#e0c489')
GOLD_PALE = HexColor('#f3e7d1')
ROSE_GOLD = HexColor('#d4a373')
ROSE_LIGHT = HexColor('#e9c5a0')
CREAM = HexColor('#fbf6ee')
DARK = HexColor('#1f1815')
GRAY = HexColor('#7a6e64')
GRAY_LIGHT = HexColor('#d8d0c4')

PAGE_W, PAGE_H = A4

# 10 produtos REAIS do catálogo oficial
PRODUCTS = [
    {"id": 1, "name": "Brinco Marguerite", "category": "Brincos", "price": 149.90, "desc": "Brinco argolão cravejado com cristais, acabamento impecável."},
    {"id": 2, "name": "Colar Sol Dourado", "category": "Colares", "price": 199.90, "desc": "Colar delicado com pingente sol, folheado a ouro 18k."},
    {"id": 3, "name": "Pulseira Corrente Tennis", "category": "Pulseiras", "price": 179.90, "desc": "Clássica pulseira de elos, banho 18k, fecho seguro."},
    {"id": 4, "name": "Anel Luna", "category": "Anéis", "price": 129.90, "desc": "Anel ajustável com zircônias, banhado a ouro 18k."},
    {"id": 5, "name": "Pingente Flor de Lis", "category": "Pingentes", "price": 99.90, "desc": "Pingente moderno com acabamento diamantado, 18k."},
    {"id": 6, "name": "Brinco Argola Crocodilo", "category": "Brincos", "price": 159.90, "desc": "Argola texturizada, banho ouro 18k, 3cm diâmetro."},
    {"id": 7, "name": "Colar Gota de Orvalho", "category": "Colares", "price": 229.90, "desc": "Colar com pedra gota, folheado 18k, comprimento 40cm."},
    {"id": 8, "name": "Pulseira Elo Coração", "category": "Pulseiras", "price": 149.90, "desc": "Elos em formato coração, banho 18k, ideal para presentear."},
    {"id": 9, "name": "Anel Duas Cores", "category": "Anéis", "price": 139.90, "desc": "Anel bicolor (ouro e rose) banho 18k, tala larga."},
    {"id": 10, "name": "Pingente Estrela", "category": "Pingentes", "price": 109.90, "desc": "Pingente estrela cravejada, folheado 18k, corrente inclusa."},
]

def fmt_price(p):
    return f"R$ {p:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def draw_header(c, page_num, total_pages):
    # Linha superior dourada
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - 1.5*cm, PAGE_W, 1.5*cm, fill=1, stroke=0)
    
    # Logo VJ
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, PAGE_H - 1*cm, "VJ")
    c.setFont("Helvetica", 8)
    c.drawString(2*cm + 0.7*cm, PAGE_H - 0.7*cm, "SEMIJOIAS")
    
    # Subtítulo
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE_W - 2*cm, PAGE_H - 1*cm, "CATÁLOGO OFICIAL 2024 | BANHADO A OURO 18K")
    
    # Rodapé
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W/2, 1*cm, f"Página {page_num} de {total_pages} | www.vjsemijoias.com | (11) 99999-9999")

def draw_product_card(c, x, y, w, h, product, idx):
    # Background do card
    c.setFillColor(white)
    c.setStrokeColor(GOLD_PALE)
    c.setLineWidth(0.5)
    c.roundRect(x, y - h, w, h, 8, fill=1, stroke=1)
    
    # Categoria
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 0.5*cm, y - 1.2*cm, product['category'].upper())
    
    # Número do produto
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x + w - 0.5*cm, y - 1.2*cm, f"#{product['id']:02d}")
    
    # Nome do produto
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 0.5*cm, y - 2*cm, product['name'])
    
    # Descrição
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    desc = product['desc']
    # Wrap
    words = desc.split()
    lines = []
    current = ""
    for w_word in words:
        if len(current + " " + w_word) <= 55:
            current = (current + " " + w_word).strip()
        else:
            lines.append(current)
            current = w_word
    if current:
        lines.append(current)
    
    text_y = y - 2.6*cm
    for line in lines[:2]:
        c.drawString(x + 0.5*cm, text_y, line)
        text_y -= 0.45*cm
    
    # Preço (destaque)
    price_y = y - h + 0.8*cm
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x + 0.5*cm, price_y, fmt_price(product['price']))
    
    # Detalhe
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(x + 0.5*cm, price_y - 0.4*cm, "Banho de Ouro 18k")

def generate_cover(c, total_pages):
    # Background
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    
    # Círculos decorativos
    c.setFillColor(GOLD_PALE)
    c.circle(PAGE_W * 0.85, PAGE_H * 0.85, 5*cm, fill=1, stroke=0)
    c.circle(PAGE_W * 0.15, PAGE_H * 0.15, 4*cm, fill=1, stroke=0)
    
    c.setFillColor(ROSE_LIGHT)
    c.circle(PAGE_W * 0.7, PAGE_H * 0.3, 3*cm, fill=1, stroke=0)
    
    # Anel decorativo grande (referência ao logo)
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.circle(PAGE_W/2, PAGE_H * 0.55, 4*cm, fill=0, stroke=1)
    
    # Diamante em cima
    c.setFillColor(GOLD)
    c.setStrokeColor(GOLD)
    p = c.beginPath()
    p.moveTo(PAGE_W/2, PAGE_H * 0.55 + 4*cm + 1.5*cm)
    p.lineTo(PAGE_W/2 - 1*cm, PAGE_H * 0.55 + 4*cm)
    p.lineTo(PAGE_W/2 - 0.3*cm, PAGE_H * 0.55 + 4*cm - 0.5*cm)
    p.lineTo(PAGE_W/2, PAGE_H * 0.55 + 4*cm - 0.2*cm)
    p.lineTo(PAGE_W/2 + 0.3*cm, PAGE_H * 0.55 + 4*cm - 0.5*cm)
    p.lineTo(PAGE_W/2 + 1*cm, PAGE_H * 0.55 + 4*cm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    
    # VJ grande centralizado
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 50)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.5, "VJ")
    
    # SEMIJOIAS
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 12)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.45, "S E M I J O I A S")
    
    # Linha decorativa
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(PAGE_W/2 - 4*cm, PAGE_H * 0.4, PAGE_W/2 + 4*cm, PAGE_H * 0.4)
    
    # CATÁLOGO 2024
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.32, "CATÁLOGO 2024")
    
    # Descrição
    c.setFillColor(DARK)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.27, "Coleção Completa Banhada a Ouro 18k")
    
    # Box
    c.setFillColor(GOLD_DARK)
    c.roundRect(2*cm, 2.5*cm, PAGE_W - 4*cm, 1.8*cm, 6, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(PAGE_W/2, 3.7*cm, "www.vjsemijoias.com | contato@vjsemijoias.com | (11) 99999-9999")
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W/2, 3.1*cm, "Siga-nos: @vjsemijoias")

def generate_intro(c, page_num, total_pages):
    draw_header(c, page_num, total_pages)
    
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(2*cm, PAGE_H - 4*cm, "Bem-vinda ao universo")
    c.drawString(2*cm, PAGE_H - 5*cm, "VJ Semijoias")
    
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(2*cm, PAGE_H - 5.5*cm, 8*cm, PAGE_H - 5.5*cm)
    
    c.setFillColor(DARK)
    c.setFont("Helvetica", 11)
    text_lines = [
        "A VJ Semijoias nasceu para encantar mulheres que",
        "valorizam a elegância em cada detalhe. Trabalhamos",
        "com peças banhadas a ouro 18k, selecionadas com",
        "critério e acabamento impecável, unindo qualidade,",
        "design sofisticado e preço justo.",
        "",
        "Cada peça do nosso catálogo foi pensada para",
        "traduzir a sua personalidade única. Da seleção de",
        "cristais ao banho dourado, tudo é feito para durar",
        "e encantar.",
        "",
        "Navegue pelas próximas páginas e descubra nossa",
        "coleção completa. Encontre a peça perfeita para",
        "cada momento, seja um presente especial ou um",
        "mimo para você mesma.",
        "",
        "VJ Semijoias — Brilhe em cada momento. ✦"
    ]
    
    y_pos = PAGE_H - 7*cm
    for line in text_lines:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.6*cm
    
    # Box diferenciais
    c.setFillColor(GOLD_PALE)
    c.roundRect(2*cm, 3.5*cm, PAGE_W - 4*cm, 5*cm, 8, fill=1, stroke=0)
    
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2.5*cm, 7.5*cm, "Nossos Diferenciais")
    
    benefits = [
        ("✦", "Banhado a Ouro 18k", "Qualidade premium garantida"),
        ("💎", "Antialérgico", "Seguro para peles sensíveis"),
        ("🚚", "Frete Grátis", "Acima de R$ 199 para todo Brasil"),
        ("💳", "Parcelamento", "Em até 12x sem juros no cartão"),
        ("🔄", "Troca Garantida", "30 dias para trocar ou devolver"),
        ("📦", "Embalagem Luxo", "Caixa especial para presente"),
    ]
    
    col1_x = 3*cm
    col2_x = 11*cm
    row_y = 6.7*cm
    for i, (icon, title, desc) in enumerate(benefits):
        x = col1_x if i % 2 == 0 else col2_x
        y = row_y - (i // 2) * 1*cm
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(DARK)
        c.drawString(x, y, f"{icon} {title}")
        c.setFont("Helvetica", 9)
        c.setFillColor(GRAY)
        c.drawString(x + 0.5*cm, y - 0.4*cm, desc)
    
    c.setFillColor(DARK)
    c.setFont("Helvetica", 9)
    c.drawString(2*cm, 2.5*cm, "Aceitamos: Cartão de Crédito, Débito, PIX e Boleto | Cupom primeira compra: VJ10 (10% off)")

def generate_products_page(c, page_num, total_pages, products_list, title):
    draw_header(c, page_num, total_pages)
    
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*cm, PAGE_H - 3.5*cm, title)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(2*cm, PAGE_H - 3.8*cm, 8*cm, PAGE_H - 3.8*cm)
    
    # 2 colunas x 3 linhas
    card_w = (PAGE_W - 5*cm) / 2
    card_h = 4.5*cm
    start_x = 2*cm
    start_y = PAGE_H - 4.5*cm
    
    for idx, product in enumerate(products_list):
        col = idx % 2
        row = idx // 2
        
        x = start_x + col * (card_w + 1*cm)
        y = start_y - row * (card_h + 0.5*cm)
        
        draw_product_card(c, x, y, card_w, card_h, product, idx)

def generate_back_cover(c, page_num, total_pages):
    # Background escuro
    c.setFillColor(DARK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    
    # Círculos dourados
    c.setFillColor(GOLD_DARK)
    c.circle(PAGE_W * 0.85, PAGE_H * 0.85, 4*cm, fill=1, stroke=0)
    c.circle(PAGE_W * 0.15, PAGE_H * 0.15, 3*cm, fill=1, stroke=0)
    
    # Logo VJ
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.75, "VJ")
    
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.7, "S E M I J O I A S")
    
    # Slogan
    c.setFillColor(GOLD_LIGHT)
    c.setFont("Helvetica-Oblique", 16)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.62, "Brilhe em cada momento")
    
    # Contato
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W/2, PAGE_H * 0.5, "Entre em Contato")
    
    contact_items = [
        "📧 contato@vjsemijoias.com",
        "📱 (11) 99999-9999",
        "📍 São Paulo - SP",
        "🌐 www.vjsemijoias.com",
        "📷 @vjsemijoias",
    ]
    
    y_pos = PAGE_H * 0.43
    for item in contact_items:
        c.setFillColor(white)
        c.setFont("Helvetica", 12)
        c.drawCentredString(PAGE_W/2, y_pos, item)
        y_pos -= 0.7*cm
    
    # Box cupom
    c.setFillColor(GOLD_DARK)
    c.roundRect(3*cm, 3*cm, PAGE_W - 6*cm, 2.5*cm, 6, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W/2, 4.7*cm, "🎁 CUPOM EXCLUSIVO")
    c.setFont("Helvetica", 14)
    c.drawCentredString(PAGE_W/2, 4*cm, "VJ10 = 10% OFF")
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W/2, 3.3*cm, "Válido para primeira compra no site")

def main():
    output_path = FRONTEND_ROOT / "pdf" / "catalogo-vj-oficial.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    
    # Agrupa produtos por categoria
    brincos = [p for p in PRODUCTS if p['category'] == 'Brincos']
    colares = [p for p in PRODUCTS if p['category'] == 'Colares']
    pulseiras = [p for p in PRODUCTS if p['category'] == 'Pulseiras']
    aneis = [p for p in PRODUCTS if p['category'] == 'Anéis']
    pingentes = [p for p in PRODUCTS if p['category'] == 'Pingentes']
    
    def num_pages(items):
        return max(1, (len(items) + 5) // 6)
    
    total_product_pages = sum([
        num_pages(brincos), num_pages(colares), num_pages(pulseiras),
        num_pages(aneis), num_pages(pingentes)
    ])
    total_pages = 1 + 1 + total_product_pages + 1  # capa + intro + produtos + contracapa
    
    page_num = 1
    
    # Capa
    generate_cover(c, total_pages)
    c.showPage()
    page_num += 1
    
    # Introdução
    generate_intro(c, page_num, total_pages)
    c.showPage()
    page_num += 1
    
    # Páginas por categoria
    categories_data = [
        ("Brincos", brincos),
        ("Colares", colares),
        ("Pulseiras", pulseiras),
        ("Anéis", aneis),
        ("Pingentes", pingentes),
    ]
    
    for cat_name, items in categories_data:
        for i in range(0, len(items), 6):
            page_items = items[i:i+6]
            page_title = cat_name if i == 0 else f"{cat_name} (continuação)"
            generate_products_page(c, page_num, total_pages, page_items, page_title)
            c.showPage()
            page_num += 1
    
    # Contracapa
    generate_back_cover(c, page_num, total_pages)
    c.showPage()
    
    c.save()
    print(f"PDF gerado: {output_path}")
    print(f"Tamanho: {os.path.getsize(output_path) / 1024:.1f} KB")
    print(f"Total de páginas: {total_pages}")

if __name__ == "__main__":
    main()
