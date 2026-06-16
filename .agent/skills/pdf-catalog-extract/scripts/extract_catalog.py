#!/usr/bin/env python3
"""
PDF catalog extractor.

Pulls per-product images, titles, prices, and descriptions from a catalog PDF
where each page has 1+ product cards (image + title + R$ price + description).
Pages with images but no text are treated as cover/back-cover thumbnails.

Usage:
    python3 extract_catalog.py <input.pdf> [--out <dir>] [--bg-w 1500] [--bg-h 2000]
                                       [--header "phrase 1" "phrase 2" ...]

Outputs (under <out>/):
    products/<NN>_<slug>/
        img_1.jpeg, img_2.jpeg, ...     one or more images per product
        info.json                        full metadata
    products/00_cover_thumbnails/
        thumb_*.jpeg                     showcase-page images
    products.csv                         flat: page,title,primary_price,...
    manifest.json                        full structured dump

Dependencies: pymupdf (pip install pymupdf)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install --break-system-packages pymupdf", file=sys.stderr)
    sys.exit(1)


# ---------- heuristics ---------------------------------------------------------

PRICE_RX = re.compile(r"^\s*R\$\s*([\d\.,]+)(.*)$")
PRICE_VALUE_RX = re.compile(r"^\s*[\d\.,]+\s*(CADA|cada)?\s*$|^\s*[\d\.,]+.*[A-Za-zÀ-ÿ].*$")
TITLE_RX = re.compile(r"^[A-ZÀ-Ý0-9][A-ZÀ-Ý0-9 \-+/().,'&]+$")
DEFAULT_HEADER_PHRASES = ["coleção", "colecao", "dia dos namorados"]


# ---------- helpers -----------------------------------------------------------

def is_header(text: str, extra_headers: list[str]) -> bool:
    t = text.strip().lower()
    for h in DEFAULT_HEADER_PHRASES + [h.lower() for h in extra_headers]:
        if h in t:
            return True
    if t.startswith("coleção") and "namorados" in t:
        return True
    return False


def is_background_image(info: dict, bg_w: int, bg_h: int) -> bool:
    return info["width"] >= bg_w or info["height"] >= bg_h


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return s[:maxlen] or "produto"


def natural_sort_key(p: Path):
    m = re.search(r"(\d+)", p.stem)
    return (int(m.group(1)) if m else 999)


# ---------- text extraction ---------------------------------------------------

def extract_lines(page):
    """Return list of dicts: {text, x0, y0, x1, y1, block_no, line_no}."""
    d = page.get_text("dict")
    lines = []
    for bi, block in enumerate(d.get("blocks", [])):
        if block.get("type", 0) != 0:
            continue
        for li, line in enumerate(block.get("lines", [])):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = " ".join(s["text"] for s in spans).strip()
            if not text:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            y0 = min(s["bbox"][1] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            y1 = max(s["bbox"][3] for s in spans)
            lines.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "block_no": bi, "line_no": li})
    return lines


def merge_price_lines(lines):
    """Glue 'R$' (alone) with the nearest price value at the same y, even across blocks."""
    merged = []
    used = [False] * len(lines)
    for i, ln in enumerate(lines):
        if used[i]:
            continue
        text = ln["text"]
        if text.strip() in ("R$", "R$ ", "R$  "):
            best_j, best_dy = None, 999
            for j in range(i + 1, len(lines)):
                if used[j]:
                    continue
                dy = abs(lines[j]["y0"] - ln["y0"])
                if dy < 8 and dy < best_dy and PRICE_VALUE_RX.match(lines[j]["text"]):
                    best_dy = dy
                    best_j = j
            if best_j is not None:
                j = best_j
                ln = {
                    "text": f"R$ {lines[j]['text']}".strip(),
                    "x0": min(ln["x0"], lines[j]["x0"]),
                    "y0": min(ln["y0"], lines[j]["y0"]),
                    "x1": max(ln["x1"], lines[j]["x1"]),
                    "y1": max(ln["y1"], lines[j]["y1"]),
                    "block_no": ln["block_no"],
                    "line_no": ln["line_no"],
                }
                used[j] = True
        used[i] = True
        merged.append(ln)
    return merged


def split_text_into_title_prices_desc(lines, extra_headers):
    body = [ln for ln in lines if not is_header(ln["text"], extra_headers)]
    title = None
    prices = []
    desc_lines = []
    for ln in body:
        text = ln["text"]
        m = re.match(r"^\s*R\$\s*([\d\.,]+)(.*)$", text)
        if m:
            prices.append({"value": m.group(1), "suffix": m.group(2).strip(), "y": ln["y0"]})
            continue
        if title is None and len(text) >= 6 and re.match(r"^[A-ZÀ-Ý0-9]", text) and text == text.upper() and not text.startswith("R$"):
            title = {"text": text, "y": ln["y0"]}
            continue
        desc_lines.append(text)
    return title, prices, desc_lines


# ---------- main --------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Extract products from a catalog PDF")
    ap.add_argument("pdf", help="Path to the source PDF")
    ap.add_argument("--out", default="./extract", help="Output directory (default: ./extract)")
    ap.add_argument("--bg-w", type=int, default=1500, help="Background-image width threshold (default 1500)")
    ap.add_argument("--bg-h", type=int, default=2000, help="Background-image height threshold (default 2000)")
    ap.add_argument("--header", nargs="*", default=[], help="Extra header phrases to ignore (lowercase)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.out).resolve()
    products_dir = out / "products"
    products_dir.mkdir(parents=True, exist_ok=True)
    cover_dir = products_dir / "00_cover_thumbnails"
    cover_dir.mkdir(exist_ok=True)

    doc = fitz.open(str(pdf_path))
    products = []
    cover_imgs = []

    for pno in range(len(doc)):
        page = doc[pno]
        # 1. collect product images
        imgs_info = []
        for im in page.get_images(full=True):
            xref = im[0]
            try:
                info = doc.extract_image(xref)
            except Exception as e:
                print(f"WARN p{pno+1} xref={xref} extract_image failed: {e}", file=sys.stderr)
                continue
            if is_background_image(info, args.bg_w, args.bg_h):
                continue
            for r in page.get_image_rects(xref):
                imgs_info.append({"xref": xref, "w": info["width"], "h": info["height"], "ext": info["ext"],
                                  "x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1})

        # 2. classify text
        lines = extract_lines(page)
        lines = merge_price_lines(lines)
        title, prices, desc_lines = split_text_into_title_prices_desc(lines, args.header)

        if not imgs_info and not title and not prices:
            continue

        if not title and not prices:
            # cover-style page
            for im in imgs_info:
                im["page"] = pno + 1
                cover_imgs.append(im)
            continue

        # 3. save product
        title_text = title["text"] if title else f"PRODUTO_PAG{pno+1}"
        slug = slugify(title_text)
        prod_dir = products_dir / f"{pno+1:02d}_{slug}"
        prod_dir.mkdir(exist_ok=True)

        imgs_sorted = sorted(imgs_info, key=lambda im: (im["y0"], im["x0"]))
        saved_imgs = []
        for k, im in enumerate(imgs_sorted, start=1):
            data = doc.extract_image(im["xref"])["image"]
            ext = doc.extract_image(im["xref"])["ext"]
            fname = f"img_{k}.{ext}"
            (prod_dir / fname).write_bytes(data)
            saved_imgs.append({"file": str((prod_dir / fname).relative_to(out)),
                               "width": im["w"], "height": im["h"],
                               "rect": [round(im["x0"], 1), round(im["y0"], 1),
                                        round(im["x1"], 1), round(im["y1"], 1)]})

        desc_text = "\n".join(desc_lines).strip()
        main = [p for p in prices if not p["suffix"]]
        primary = (main[0] if main else prices[0])["value"] if prices else None

        product = {
            "page": pno + 1,
            "title": title_text,
            "prices": [{"value": p["value"], "suffix": p["suffix"]} for p in prices],
            "primary_price": primary,
            "description": desc_text,
            "description_lines": desc_lines,
            "images": saved_imgs,
            "folder": str(prod_dir.relative_to(out)),
        }
        products.append(product)
        (prod_dir / "info.json").write_text(json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"page {pno+1:>2}  '{title_text[:50]:<50}'  R$ {primary or '?'}  imgs={len(saved_imgs)}")

    # 4. cover thumbnails
    if cover_imgs:
        for k, im in enumerate(sorted(cover_imgs, key=lambda x: (x["page"], x["x0"])), start=1):
            data = doc.extract_image(im["xref"])["image"]
            ext = doc.extract_image(im["xref"])["ext"]
            (cover_dir / f"thumb_{k}.{ext}").write_bytes(data)
        print(f"\nCover thumbnails: {len(cover_imgs)} saved to {cover_dir.relative_to(out)}")

    # 5. manifest + csv
    manifest = {
        "source_pdf": str(pdf_path),
        "page_count": len(doc),
        "product_count": len(products),
        "cover_thumbnails": len(cover_imgs),
        "products": products,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "products.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "title", "primary_price", "all_prices", "description", "image_count", "folder", "image_files"])
        for p in products:
            w.writerow([
                p["page"], p["title"], p["primary_price"] or "",
                " | ".join(f"R$ {x['value']} {x['suffix']}".strip() for x in p["prices"]),
                p["description"].replace("\n", " | "), len(p["images"]),
                p["folder"], " | ".join(im["file"] for im in p["images"]),
            ])

    print(f"\nWrote {len(products)} products.")
    print(f"  manifest: {out / 'manifest.json'}")
    print(f"  csv:      {out / 'products.csv'}")


if __name__ == "__main__":
    main()
