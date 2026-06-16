#!/usr/bin/env python3
"""
Gera um catálogo PDF diagramado da VJ Semijoias a partir de dados estruturados
(manifest.json ou products.csv) e imagens de produtos extraídos.

Uso:
    python3 generate_catalog.py --src <diretorio_origem> --out <caminho_pdf_saida>

Exemplo:
    python3 generate_catalog.py --src ./extract --out ./pdf/catalogo-vj-oficial.pdf
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab", file=sys.stderr)
    sys.exit(1)

# ---------- CORES E GEOMETRIA DA VJ SEMIJOIAS ----------------------------------
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
DEFAULT_CONTACT = (
    "www.vjsemijoias.com | Instagram: @vj_semijoias | "
    "WhatsApp: (51) 98211-0842"
)


def find_brand_logo() -> Path | None:
    for root in [Path.cwd(), *Path(__file__).resolve().parents]:
        candidate = root / "frontend" / "images" / "logo.png"
        if candidate.is_file():
            return candidate
    return None


BRAND_LOGO_PATH = find_brand_logo()


# ---------- AUXILIARES --------------------------------------------------------
def fmt_price(p) -> str:
    if isinstance(p, str):
        # Limpar e converter string para float
        try:
            p_clean = p.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            p = float(p_clean)
        except ValueError:
            # Retorna o valor original caso não consiga converter
            return p if p.startswith('R$') else f"R$ {p}"
    return f"R$ {p:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def guess_category(title: str) -> str:
    title_lower = title.lower()
    if any(k in title_lower for k in ["brinco", "argola", "piercing"]):
        return "Brincos"
    elif any(k in title_lower for k in ["colar", "gargantilha", "corrente", "choker"]):
        return "Colares"
    elif any(k in title_lower for k in ["pulseira", "bracelete"]):
        return "Pulseiras"
    elif any(k in title_lower for k in ["anel", "aliança"]):
        return "Anéis"
    elif any(k in title_lower for k in ["pingente", "medalha"]):
        return "Pingentes"
    else:
        return "Acessórios"


def draw_logo_image(c, x, y, width, height):
    if not BRAND_LOGO_PATH:
        return False
    try:
        logo = ImageReader(str(BRAND_LOGO_PATH))
        image_width, image_height = logo.getSize()
        scale = min(width / image_width, height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        c.drawImage(
            logo,
            x + (width - draw_width) / 2,
            y + (height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        return True
    except Exception as exc:
        print(f"WARN: Erro ao desenhar logo {BRAND_LOGO_PATH}: {exc}", file=sys.stderr)
        return False


def image_file_from(entry) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("file") or entry.get("path") or ""
    return ""


def product_description_from(data: dict) -> str:
    if data.get("description"):
        return data["description"]
    lines = data.get("description_lines") or data.get("features") or []
    if isinstance(lines, list):
        return ". ".join(str(line).strip().rstrip(".") for line in lines if str(line).strip())
    return str(lines or "")


def wrap_pdf_text(text: str, font: str, size: float, max_width: float, max_lines: int):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        last = lines[-1]
        while stringWidth(f"{last}...", font, size) > max_width and last:
            last = last[:-1]
        lines[-1] = f"{last.rstrip()}..."
    return lines


# ---------- RENDERIZADORES DE PÁGINAS -----------------------------------------
def draw_header(c, page_num, total_pages):
    # Linha superior dourada
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - 1.5*cm, PAGE_W, 1.5*cm, fill=1, stroke=0)
    
    # Logo VJ no Cabeçalho
    if not draw_logo_image(c, 1.8*cm, PAGE_H - 1.35*cm, 1.1*cm, 1.1*cm):
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
    c.drawCentredString(PAGE_W/2, 1*cm, f"Página {page_num} de {total_pages} | {DEFAULT_CONTACT}")


def draw_product_card(c, x, y, w, h, product, idx, src_dir):
    # Background do card
    c.setFillColor(white)
    c.setStrokeColor(GOLD_PALE)
    c.setLineWidth(0.5)
    c.roundRect(x, y - h, w, h, 8, fill=1, stroke=1)
    
    # Espaco da imagem (esquerda)
    img_w = 3.9*cm
    img_h = min(5.4*cm, h - 1.1*cm)
    img_x = x + 0.4*cm
    img_y = y - h + (h - img_h) / 2
    
    has_img = False
    if product.get('images'):
        img_file = image_file_from(product['images'][0])
        img_path = Path(src_dir) / img_file
        if img_file and img_path.exists():
            try:
                c.drawImage(str(img_path), img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
                has_img = True
            except Exception as e:
                print(f"WARN: Erro ao desenhar imagem {img_file}: {e}", file=sys.stderr)
                
    if not has_img:
        # Caixa cinza caso não haja imagem
        c.setFillColor(HexColor('#f7f4ef'))
        c.roundRect(img_x, img_y, img_w, img_h, 4, fill=1, stroke=0)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(img_x + img_w/2, img_y + img_h/2, "Sem Foto")

    # Informações textuais (Direita)
    text_x = x + 4.65*cm
    text_max_width = x + w - 0.4*cm - text_x
    
    # Categoria
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(text_x, y - 0.75*cm, product.get('category', 'ACESSÓRIOS').upper()[:24])
    
    # ID/Número
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x + w - 0.4*cm, y - 0.75*cm, f"#{idx:02d}")
    
    # Nome
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10.2)
    title = product.get('title', 'Produto VJ')
    title_y = y - 1.35*cm
    for line in wrap_pdf_text(title.upper(), "Helvetica-Bold", 10.2, text_max_width, 2):
        c.drawString(text_x, title_y, line)
        title_y -= 0.42*cm
    
    # Descrição
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    desc = product.get('description', '')
    text_y = title_y - 0.18*cm
    for line in wrap_pdf_text(desc, "Helvetica", 8, text_max_width, 4):
        c.drawString(text_x, text_y, line)
        text_y -= 0.38*cm
        
    # Preço
    price_y = y - h + 1.0*cm
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 14)
    price = product.get('primary_price', '0,00')
    c.drawString(text_x, price_y, fmt_price(price))
    
    # Detalhe
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(text_x, price_y - 0.38*cm, "Banho de Ouro 18k")


def generate_cover(c, total_pages):
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(DARK)
    c.rect(0, PAGE_H - 8.7*cm, PAGE_W, 8.7*cm, fill=1, stroke=0)

    c.setFillColor(GOLD_PALE)
    c.circle(PAGE_W * 0.88, PAGE_H * 0.88, 4.8*cm, fill=1, stroke=0)
    c.circle(PAGE_W * 0.12, PAGE_H * 0.12, 3.4*cm, fill=1, stroke=0)
    c.setFillColor(ROSE_LIGHT)
    c.circle(PAGE_W * 0.76, PAGE_H * 0.37, 2.7*cm, fill=1, stroke=0)

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    c.roundRect(1.2*cm, 1.2*cm, PAGE_W - 2.4*cm, PAGE_H - 2.4*cm, 18, fill=0, stroke=1)

    # Logo Central VJ Semijoias
    if not draw_logo_image(
        c,
        PAGE_W/2 - 3.4*cm,
        PAGE_H - 7.8*cm,
        6.8*cm,
        6.8*cm,
    ):
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 50)
        c.drawCentredString(PAGE_W/2, PAGE_H - 4.2*cm, "VJ")

        c.setFillColor(GOLD)
        c.setFont("Helvetica", 12)
        c.drawCentredString(PAGE_W/2, PAGE_H - 5.0*cm, "S E M I J O I A S")

    c.setFillColor(GOLD_LIGHT)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(PAGE_W/2, PAGE_H - 8.1*cm, "Brilhe em cada momento")

    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(PAGE_W/2 - 4.2*cm, PAGE_H - 11.4*cm, PAGE_W/2 + 4.2*cm, PAGE_H - 11.4*cm)

    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(PAGE_W/2, PAGE_H - 10.4*cm, "CATALOGO VJ")
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(PAGE_W/2, PAGE_H - 12.7*cm, "SEMIJOIAS")

    c.setFillColor(DARK)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PAGE_W/2, PAGE_H - 14.1*cm, "Colecao completa banhada a ouro 18k")

    c.setFillColor(GOLD_PALE)
    c.roundRect(3*cm, 10.2*cm, PAGE_W - 6*cm, 2.1*cm, 8, fill=1, stroke=0)
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W/2, 11.35*cm, "VJ10 = 10% OFF")
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W/2, 10.75*cm, "Cupom exclusivo para sua compra")

    c.setFillColor(GOLD_DARK)
    c.roundRect(2*cm, 2.5*cm, PAGE_W - 4*cm, 2.1*cm, 8, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(PAGE_W/2, 3.75*cm, DEFAULT_CONTACT)
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W/2, 3.15*cm, "Siga-nos: @vj_semijoias")

def generate_products_page(c, page_num, total_pages, products_list, title, src_dir, start_index):
    draw_header(c, page_num, total_pages)
    
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1.25*cm, PAGE_H - 2.65*cm, title)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(1.25*cm, PAGE_H - 2.95*cm, 8*cm, PAGE_H - 2.95*cm)
    
    # Layout 2x3 ocupando melhor a pagina
    gap_x = 0.55*cm
    gap_y = 0.35*cm
    margin_x = 1.25*cm
    card_w = (PAGE_W - 2*margin_x - gap_x) / 2
    card_h = 7.55*cm
    start_x = margin_x
    start_y = PAGE_H - 3.35*cm
    
    for idx, product in enumerate(products_list):
        col = idx % 2
        row = idx // 2
        
        x = start_x + col * (card_w + gap_x)
        y = start_y - row * (card_h + gap_y)
        
        draw_product_card(c, x, y, card_w, card_h, product, start_index + idx, src_dir)

# ---------- FLUXO PRINCIPAL ----------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Gera catálogo PDF oficial da VJ Semijoias a partir de pasta estruturada")
    ap.add_argument("--src", default="./extract", help="Diretório de origem dos produtos (contém manifest.json ou produtos)")
    ap.add_argument("--out", default="./pdf/catalogo-vj-oficial.pdf", help="Caminho do PDF de saída")
    args = ap.parse_args()

    src_dir = Path(args.src).resolve()
    out_pdf = Path(args.out).resolve()
    
    # Garante a existência do diretório de saída
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    products = []
    
    # 1. Carrega dados de manifest.json
    manifest_path = src_dir / "manifest.json"
    csv_path = src_dir / "products.csv"
    
    if manifest_path.exists():
        print(f"Carregando produtos do manifest: {manifest_path}")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw_products = data.get("products", [])
            for p in raw_products:
                title = p.get("title") or p.get("name") or p.get("nome") or "Produto"
                # Normaliza campos
                products.append({
                    "title": title,
                    "primary_price": p.get("primary_price") or p.get("price") or p.get("preco") or "0,00",
                    "description": product_description_from(p),
                    "images": p.get("images", []),
                    "category": p.get("categoryName") or p.get("category_name") or p.get("category") or guess_category(title)
                })
        except Exception as e:
            print(f"ERROR: Falha ao ler manifest.json: {e}", file=sys.stderr)
            sys.exit(1)
            
    # 2. Alternativa: Carrega dados do products.csv
    elif csv_path.exists():
        print(f"manifest.json não encontrado. Carregando produtos de: {csv_path}")
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    images = []
                    if row.get('image_files'):
                        for f_img in row['image_files'].split('|'):
                            images.append({'file': f_img.strip()})
                    products.append({
                        "title": row.get('title', 'Produto'),
                        "primary_price": row.get('primary_price', '0,00'),
                        "description": row.get('description', ''),
                        "images": images,
                        "category": guess_category(row.get('title', ''))
                    })
        except Exception as e:
            print(f"ERROR: Falha ao ler products.csv: {e}", file=sys.stderr)
            sys.exit(1)
            
    else:
        # Tenta escenar pastas individuais info.json como último recurso
        print(f"Nenhum arquivo de índice encontrado em {src_dir}. Procurando info.json nas subpastas...")
        for p_sub in sorted(src_dir.glob("**/info.json")):
            try:
                p_data = json.loads(p_sub.read_text(encoding="utf-8"))
                products.append({
                    "title": p_data.get("title", "Produto"),
                    "primary_price": p_data.get("primary_price", "0,00"),
                    "description": p_data.get("description", ""),
                    "images": p_data.get("images", []),
                    "category": p_data.get("category") or guess_category(p_data.get("title", ""))
                })
            except Exception as e:
                print(f"WARN: Falha ao carregar {p_sub}: {e}", file=sys.stderr)

    if not products:
        print(f"ERROR: Nenhum produto encontrado no diretório: {src_dir}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Total de produtos carregados: {len(products)}")

    # 3. Agrupa por categoria
    categories: dict[str, list[dict]] = {}
    for p in products:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p)
        
    # Ordena as categorias para exibição no catálogo
    sorted_categories = sorted(categories.keys())

    # 4. Calcula total de páginas
    def num_pages(items_count):
        return max(1, (items_count + 5) // 6)
        
    total_product_pages = sum(num_pages(len(categories[cat])) for cat in sorted_categories)
    total_pages = 1 + total_product_pages  # capa + paginas de produtos

    # 5. Gera o PDF Canvas
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    page_num = 1
    
    # Capa
    generate_cover(c, total_pages)
    c.showPage()
    page_num += 1
    
    # Páginas de Produtos
    global_product_index = 1
    for cat_name in sorted_categories:
        items = categories[cat_name]
        for i in range(0, len(items), 6):
            page_items = items[i:i+6]
            page_title = cat_name if i == 0 else f"{cat_name} (continuação)"
            generate_products_page(c, page_num, total_pages, page_items, page_title, src_dir, global_product_index)
            c.showPage()
            page_num += 1
            global_product_index += len(page_items)

    c.save()
    
    print(f"\nCatálogo PDF gerado com sucesso!")
    print(f"  Caminho: {out_pdf}")
    print(f"  Páginas: {total_pages}")
    print(f"  Tamanho: {os.path.getsize(out_pdf) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
