---
name: pdf-catalog-extract
description: |
  Extract product catalog data from a PDF: per-product images, title, price(s),
  description, plus cover thumbnails. Use this skill when the user wants to
  pull structured product data (image + name + price + description) out of a
  visual catalog PDF where each page has one or more product cards. Typical
  triggers: "extrair produtos do PDF", "extract products from this catalog",
  "parse the catalog PDF into images and prices", "PDF de catálogo com foto,
  descrição e preço". Do NOT use for: scanned/image-only PDFs without a text
  layer (needs OCR first, route through the pdf skill's vision path), single
  product or non-catalog PDFs (just use the pdf skill), PDF reading for
  general document questions, or generating new catalogs (use the pdf skill).
---

# PDF Catalog Extractor

## Inputs to collect
- Path to the source PDF (read from `attachments/` or wherever the user dropped it)
- Output directory (default: `<workspace>/extract/`)
- Optional: list of header phrases to ignore (default: ["coleção", "dia dos namorados"] — the skill auto-detects headers but the user can override)
- Optional: known duplicate pairs to merge (after first run, the user may want to fold hero+variant pages into one product)

Don't ask up-front; the script has sensible defaults and the user can refine after seeing the first pass.

## Procedure

1. **Inspect the PDF structure first.** Open with PyMuPDF, print page count, page size, and a sample of image dimensions per page. Reason: catalog templates vary — some use a full-bleed background image (typically 1500–3000px on the long side) that must be filtered out; a few use A4 portrait with centered cards; some are 16:9 landscape. Locking the page geometry first prevents wrong assumptions downstream.

2. **Detect the background-image rule.** A page is usually 1440×810 (16:9) or 595×842 (A4) pts. Background images are the *largest* image on the page (often 2000×3000 in jpeg) that spans the whole canvas. Product images are smaller. The default filter is `info["width"] >= 1500 or info["height"] >= 2000`. Reason: 16:9 catalogs use a "design wallpaper" image that looks like a product photo in the listing — keeping it would corrupt every folder. Adjust the threshold if the catalog is not 16:9.

3. **Classify text per page using position-aware extraction.** Use `page.get_text("dict")` to get word-level bounding boxes. Group into lines, then classify:
   - **Header** (skip): any line containing "coleção" or "dia dos namorados" (catalog-specific) — the user can override this list.
   - **Price**: any line matching `^\s*R\$\s*[\d.,]+` (with optional suffix like "CADA" or "Pingente letra").
   - **Title**: first line that is all-caps, length ≥ 6, not a price.
   - **Description**: everything else, joined with newlines.

4. **Merge split price lines.** PDFs often put "R$" and the value in separate text blocks at the same y. After classification, find any line that is just "R$" and merge it with the nearest line at the same y that looks like a price value (regex `^\s*[\d.,]+`). Reason: separate blocks at the same y are visually the same line; without this, the CSV will have blank prices.

5. **Save each product as a folder.**
   ```
   products/<NN>_<slug>/
     img_1.jpeg, img_2.jpeg, ...   # sorted by (y, x) of their rect
     info.json                      # full metadata for the product
   ```
   `NN` is the 2-digit page number, `<slug>` is a slugified version of the title (or `produto_pNN` if title is empty). Sort images by (rect.y0, rect.x0) so a hero shot that sits above a row of variants comes first, and variants are left-to-right.

6. **Treat cover/back-cover pages as thumbnails.** Pages with images but no text are usually showcase pages (1 cover, 1 back). Save their images to `products/00_cover_thumbnails/thumb_*.jpeg` (sort filenames numerically, not alphabetically — use a natural-sort on the digit suffix).

7. **Write the manifest and CSV at the end.**
   - `manifest.json` — full product objects with images, prices, description, source folder.
   - `products.csv` — flat: `page,title,primary_price,all_prices,description,image_count,folder,image_files`. `primary_price` is the first price without a suffix; if all have suffixes, fall back to the first.

8. **Surface duplicates to the user, don't auto-merge.** Many catalogs split one product across two pages (hero + color variants). After the first pass, look for adjacent pages with the same title (or near-same title, e.g. a stray double space) and same price. Tell the user "p24 + p25 look like the same product — keep or merge?" and provide a one-shot dedup script. Reason: the user has domain context; auto-merging might lose a real distinction (e.g. p59/p60 had different SKUs even though title and price matched).

## Output contract
- `extract/products/<NN>_<slug>/img_*.jpeg` — one or more images per product, original bytes, sorted by visual order on the page
- `extract/products/<NN>_<slug>/info.json` — `{page, title, prices:[{value, suffix}], primary_price, description, description_lines, images:[{file, width, height, rect}], folder}`
- `extract/products/00_cover_thumbnails/thumb_*.jpeg` — showcase page images
- `extract/products.csv` — one row per product, for spreadsheet review
- `extract/manifest.json` — full structured dump, all products + cover thumbs + counts
- `extract/catalogo_extraido.zip` — everything zipped, ready to hand to the user

## Failure handling

- **No images on a page that has text** → still save the product with an empty images list; the title/price/description are still useful.
- **No text on a page that has images** → it's a cover/back-cover; save images to the `00_cover_thumbnails/` folder, do NOT create a product entry.
- **Text is gibberish or `(cid:NNN)`** → the PDF has no text layer (scanned). Stop and tell the user: this needs OCR or the pdf skill's vision path, not this extractor.
- **Price line doesn't match the regex** → log the line to stderr and continue with `primary_price=null`; the user can spot it in the CSV.
- **Background image gets through the filter** → user reports a folder full of full-page backgrounds. Re-tighten the threshold: print `info["width"] x info["height"]` of the largest image on a known-product page and set the threshold just above that.
- **Title shows up as "DIA DOS NAMORADOS" or "COLEÇÃO"** → header filter missed it. Add the exact string to the header list and re-run. The default filter checks both `coleção` and `dia dos namorados` in any combination; some catalogs use other collection names — confirm with the user.
- **Two pages have identical images and titles** → likely a true duplicate (the catalog author copy-pasted a page). Merge by hash: keep one, delete the other, log a warning.

## Examples

**Input**: A 20-page 16:9 PDF catalog where pages 2–20 each have 1 product (image + title in gold banner + R$ price + description), and page 1 is a cover with 4 thumbnails and no text.

**Output**:
```
extract/
  products/
    00_cover_thumbnails/
      thumb_1.jpeg, thumb_2.jpeg, thumb_3.jpeg, thumb_4.jpeg
    02_medalha_personalizada_iniciais_data/
      img_1.jpeg
      info.json
    03_medalha_personalizada_placa/
      img_1.jpeg, img_2.jpeg        # 2 angles of the same product
      info.json
    ...
  products.csv
  manifest.json
  catalogo_extraido.zip
```

User can then ask: "merge p24 + p25 (same product, hero + 4 color variants)" → run a small dedup pass that moves the hero image into the variant folder and rewrites the JSON/CSV.

**Input that should NOT trigger this skill**:
- "Read this PDF and tell me what it's about" → use the `pdf` skill's read path.
- "Convert this PDF to a Word document" → use the `pdf` skill.
- "Generate a new catalog from these products" → use the `pdf` skill's CREATE route.
- "Pull the photos out of this scanned PDF" → no text layer; needs OCR or `pdf` skill's vision path.
