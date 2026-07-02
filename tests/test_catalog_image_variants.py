import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = PROJECT_ROOT / "frontend" / "js" / "main.js"


def run_main_js_assertions(assertions):
    script = f"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const code = fs.readFileSync({json.dumps(str(MAIN_JS))}, 'utf8');
const context = {{
  document: {{ addEventListener() {{}} }},
  formatPrice(value) {{ return `R$ ${{Number(value || 0).toFixed(2)}}`; }},
  calculateInstallment(value) {{ return Number(value || 0) / 12; }},
}};
vm.createContext(context);
vm.runInContext(code, context);
{assertions}
"""
    return subprocess.run(["node", "-e", script], cwd=PROJECT_ROOT, text=True, capture_output=True, check=True)


def test_catalog_card_variant_url_for_local_raster_images():
    run_main_js_assertions(
        """
assert.strictEqual(context.imageCardVariantUrl('images/catalog/produto/img_1.jpg'), 'images/variants/catalog/produto/img_1-card.webp');
assert.strictEqual(context.imageCardVariantUrl('images/catalog/produto/img_1.jpeg'), 'images/variants/catalog/produto/img_1-card.webp');
assert.strictEqual(context.imageCardVariantUrl('images/catalog/produto/img_1.png'), 'images/variants/catalog/produto/img_1-card.webp');
assert.strictEqual(context.imageCardVariantUrl('images/catalog/produto/img_1.webp'), 'images/variants/catalog/produto/img_1-card.webp');
assert.strictEqual(context.imageCardVariantUrl('/images/catalog/produto/img_1.jpg'), '/images/variants/catalog/produto/img_1-card.webp');
"""
    )


def test_catalog_card_variant_keeps_non_variant_sources():
    run_main_js_assertions(
        """
assert.strictEqual(context.imageCardVariantUrl('images/products/anel.svg'), 'images/products/anel.svg');
assert.strictEqual(context.imageCardVariantUrl('https://cdn.example.com/produto.jpg'), 'https://cdn.example.com/produto.jpg');
assert.strictEqual(context.imageCardVariantUrl('data:image/png;base64,abc'), 'data:image/png;base64,abc');
assert.strictEqual(context.imageCardVariantUrl(''), '');
"""
    )


def test_catalog_product_card_uses_variant_with_original_fallback():
    run_main_js_assertions(
        """
const html = context.createProductCard({
  id: 42,
  name: 'Anel Teste',
  category: 'aneis',
  categoryName: 'Aneis',
  description: 'Produto teste',
  price: 120,
  image: 'images/catalog/produto/img_1.jpg',
  icon: 'VJ',
});
assert(html.includes('src="images/variants/catalog/produto/img_1-card.webp"'));
assert(html.includes('data-original-src="images/catalog/produto/img_1.jpg"'));
assert(html.includes('loading="lazy"'));
assert(html.includes('decoding="async"'));
assert(html.includes('onerror="fallbackProductCardImage(this)"'));
"""
    )


def test_catalog_product_card_uses_placeholder_when_image_is_empty():
    run_main_js_assertions(
        """
const html = context.createProductCard({
  id: 43,
  name: 'Sem Imagem',
  category: 'aneis',
  price: 120,
  icon: 'VJ',
});
assert(html.includes('<div class="placeholder">VJ</div>'));
assert(!html.includes('<img'));
"""
    )


def test_catalog_fallback_switches_variant_to_original_once_then_placeholder():
    run_main_js_assertions(
        """
const attrs = {
  src: 'images/variants/catalog/produto/img_1-card.webp',
  'data-original-src': 'images/catalog/produto/img_1.jpg',
};
const placeholder = { style: { display: 'none' } };
const image = {
  dataset: {},
  style: { display: '' },
  nextElementSibling: placeholder,
  getAttribute(name) { return attrs[name] || ''; },
  setAttribute(name, value) { attrs[name] = value; },
};
context.fallbackProductCardImage(image);
assert.strictEqual(attrs.src, 'images/catalog/produto/img_1.jpg');
assert.strictEqual(image.style.display, '');
assert.strictEqual(placeholder.style.display, 'none');
context.fallbackProductCardImage(image);
assert.strictEqual(image.style.display, 'none');
assert.strictEqual(placeholder.style.display, 'flex');
"""
    )


def test_catalog_variant_logic_does_not_use_fetch_or_head():
    source = MAIN_JS.read_text(encoding="utf-8")
    assert "fetch(" not in source
    assert "HEAD" not in source