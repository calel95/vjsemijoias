import re
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from backend.store_config import store_settings


GOLD_DARK = HexColor("#a67c3d")
GOLD = HexColor("#c9a86a")
GOLD_LIGHT = HexColor("#e0c489")
GOLD_PALE = HexColor("#f3e7d1")
ROSE_LIGHT = HexColor("#e9c5a0")
CREAM = HexColor("#fbf6ee")
DARK = HexColor("#1f1815")
GRAY = HexColor("#7a6e64")
IMAGE_PLACEHOLDER = HexColor("#f7f4ef")
PAGE_W, PAGE_H = A4
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRAND_LOGO_PATH = store_settings.logo_file
DEFAULT_CONTACT = store_settings.catalog_contact_line


@dataclass
class CatalogProduct:
    title: str
    image_path: Path
    price: str = ""
    category: str = "Semijoias"
    description: str = ""


@dataclass
class CatalogOptions:
    title: str = store_settings.catalog.title
    collection: str = store_settings.catalog.collection
    slogan: str = store_settings.brand.slogan
    contact: str = DEFAULT_CONTACT
    coupon: str = store_settings.coupon_label
    products_per_page: int = 6


def split_values(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in re.split(r"\r?\n|\|", value) if item.strip()]


def value_at(values: list[str], index: int, default: str = "") -> str:
    return values[index] if index < len(values) else default


def title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"^\d+[_\-\s]*", "", stem)
    return re.sub(r"[_\-]+", " ", stem).strip().title() or "Produto VJ"


def format_price(value: str) -> str:
    value = value.strip()
    if not value:
        return "Consulte o preço"
    return value if value.upper().startswith("R$") else f"R$ {value}"


def wrap_text(text: str, font: str, size: float, max_width: float, max_lines: int):
    words = text.split()
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


def draw_logo_image(c, x, y, width, height, path: Path = BRAND_LOGO_PATH):
    if not path.is_file():
        return False
    try:
        logo = ImageReader(str(path))
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
    except Exception:
        return False


def draw_brand(c, color=GOLD_DARK, y=None):
    y = y or PAGE_H * 0.58
    if color == GOLD_DARK and draw_logo_image(
        c,
        PAGE_W / 2 - 3.15 * cm,
        y - 3.3 * cm,
        6.3 * cm,
        6.3 * cm,
    ):
        return
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 46)
    c.drawCentredString(PAGE_W / 2, y, "VJ")
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_W / 2, y - 0.55 * cm, "S E M I J O I A S")


def draw_cover(c, options: CatalogOptions):
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(DARK)
    c.rect(0, PAGE_H - 8.7 * cm, PAGE_W, 8.7 * cm, fill=1, stroke=0)
    c.setFillColor(GOLD_PALE)
    c.circle(PAGE_W * 0.88, PAGE_H * 0.88, 4.8 * cm, fill=1, stroke=0)
    c.circle(PAGE_W * 0.12, PAGE_H * 0.12, 3.4 * cm, fill=1, stroke=0)
    c.setFillColor(ROSE_LIGHT)
    c.circle(PAGE_W * 0.76, PAGE_H * 0.37, 2.7 * cm, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    c.roundRect(1.2 * cm, 1.2 * cm, PAGE_W - 2.4 * cm, PAGE_H - 2.4 * cm, 18, fill=0, stroke=1)
    if not draw_logo_image(
        c,
        PAGE_W / 2 - 3.4 * cm,
        PAGE_H - 7.8 * cm,
        6.8 * cm,
        6.8 * cm,
    ):
        draw_brand(c, white, PAGE_H - 4.2 * cm)
    c.setFillColor(GOLD_LIGHT)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 8.1 * cm, options.slogan)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(4 * cm, PAGE_H - 11.4 * cm, PAGE_W - 4 * cm, PAGE_H - 11.4 * cm)
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 34)
    for offset, line in enumerate(
        wrap_text(options.title.upper(), "Helvetica-Bold", 34, PAGE_W - 5 * cm, 2)
    ):
        c.drawCentredString(PAGE_W / 2, PAGE_H - 10.4 * cm - offset * 0.9 * cm, line)
    c.setFillColor(DARK)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 14.1 * cm, options.collection)
    c.setFillColor(GOLD_PALE)
    c.roundRect(3 * cm, 10.2 * cm, PAGE_W - 6 * cm, 2.1 * cm, 8, fill=1, stroke=0)
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 11.35 * cm, options.coupon)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, 10.75 * cm, "Cupom exclusivo para sua compra")
    c.setFillColor(GOLD_DARK)
    c.roundRect(2 * cm, 2.5 * cm, PAGE_W - 4 * cm, 2.1 * cm, 8, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W / 2, 3.75 * cm, options.contact)

def draw_header(c, options: CatalogOptions, page_num: int, total_pages: int):
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - 1.45 * cm, PAGE_W, 1.45 * cm, fill=1, stroke=0)
    if not draw_logo_image(c, 1.45 * cm, PAGE_H - 1.32 * cm, 1.05 * cm, 1.05 * cm):
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 17)
        c.drawString(1.5 * cm, PAGE_H - 0.95 * cm, "VJ")
        c.setFont("Helvetica", 8)
        c.drawString(2.25 * cm, PAGE_H - 0.95 * cm, "SEMIJOIAS")
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - 1.5 * cm, PAGE_H - 0.95 * cm, options.collection.upper())
    c.setFillColor(GRAY)
    c.drawCentredString(
        PAGE_W / 2,
        0.75 * cm,
        f"Página {page_num} de {total_pages} | {options.contact}",
    )


def draw_product_card(c, product: CatalogProduct, x, y, width, height, number):
    c.setFillColor(white)
    c.setStrokeColor(GOLD_PALE)
    c.setLineWidth(0.7)
    c.roundRect(x, y - height, width, height, 8, fill=1, stroke=1)
    padding = 0.35 * cm
    image_height = height * 0.52
    try:
        c.drawImage(
            str(product.image_path),
            x + padding,
            y - image_height - padding,
            width=width - 2 * padding,
            height=image_height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
    except Exception:
        c.setFillColor(IMAGE_PLACEHOLDER)
        c.roundRect(
            x + padding,
            y - image_height - padding,
            width - 2 * padding,
            image_height,
            4,
            fill=1,
            stroke=0,
        )
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + width / 2, y - image_height / 2, "Imagem indisponível")

    text_y = y - image_height - 0.75 * cm
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + padding, text_y, product.category.upper()[:24])
    c.setFillColor(GOLD)
    c.drawRightString(x + width - padding, text_y, f"#{number:02d}")
    text_y -= 0.48 * cm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    for line in wrap_text(
        product.title, "Helvetica-Bold", 10, width - 2 * padding, 2
    ):
        c.drawString(x + padding, text_y, line)
        text_y -= 0.4 * cm
    if product.description:
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        for line in wrap_text(
            product.description, "Helvetica", 7.5, width - 2 * padding, 2
        ):
            c.drawString(x + padding, text_y, line)
            text_y -= 0.3 * cm
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + padding, y - height + 0.45 * cm, format_price(product.price))


def draw_products_page(
    c,
    products: list[CatalogProduct],
    options: CatalogOptions,
    page_num: int,
    total_pages: int,
    category: str,
    start_number: int,
):
    draw_header(c, options, page_num, total_pages)
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(1.5 * cm, PAGE_H - 2.65 * cm, category)
    c.setStrokeColor(GOLD)
    c.line(1.5 * cm, PAGE_H - 2.95 * cm, 8 * cm, PAGE_H - 2.95 * cm)
    columns = 2
    rows = 2 if options.products_per_page == 4 else 3
    gap = 0.55 * cm
    available_width = PAGE_W - 3 * cm
    available_height = PAGE_H - 5 * cm
    card_width = (available_width - gap) / columns
    card_height = (available_height - gap * (rows - 1)) / rows
    start_x = 1.5 * cm
    start_y = PAGE_H - 3.35 * cm
    for index, product in enumerate(products):
        row, column = divmod(index, columns)
        x = start_x + column * (card_width + gap)
        y = start_y - row * (card_height + gap)
        draw_product_card(
            c,
            product,
            x,
            y,
            card_width,
            card_height,
            start_number + index,
        )

def generate_catalog_pdf(
    products: list[CatalogProduct],
    output_path: Path,
    options: CatalogOptions,
):
    if not products:
        raise ValueError("Adicione pelo menos uma imagem de produto")
    if options.products_per_page not in {4, 6}:
        raise ValueError("products_per_page deve ser 4 ou 6")

    grouped: dict[str, list[CatalogProduct]] = {}
    for product in products:
        grouped.setdefault(product.category or "Semijoias", []).append(product)

    product_pages = sum(
        (len(items) + options.products_per_page - 1) // options.products_per_page
        for items in grouped.values()
    )
    total_pages = product_pages + 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    pdf.setTitle(options.title)

    draw_cover(pdf, options)
    pdf.showPage()

    page_num = 2
    product_number = 1
    for category, items in grouped.items():
        for offset in range(0, len(items), options.products_per_page):
            page_items = items[offset : offset + options.products_per_page]
            page_title = category if offset == 0 else f"{category} - continuação"
            draw_products_page(
                pdf,
                page_items,
                options,
                page_num,
                total_pages,
                page_title,
                product_number,
            )
            product_number += len(page_items)
            page_num += 1
            pdf.showPage()

    pdf.save()
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("O PDF não foi gerado corretamente")
    return {"pages": total_pages, "products": len(products), "size": output_path.stat().st_size}
