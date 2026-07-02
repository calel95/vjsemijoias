// ============================================
// MAIN - Funções principais
// ============================================

function escapeHTML(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizeImageUrl(imageUrl) {
    return String(imageUrl || '').trim().replace(/\\/g, '/');
}

function isExternalImageUrl(imageUrl) {
    const image = normalizeImageUrl(imageUrl).toLowerCase();
    return image.startsWith('http://') || image.startsWith('https://') || image.startsWith('//');
}

function isDataImageUrl(imageUrl) {
    return normalizeImageUrl(imageUrl).toLowerCase().startsWith('data:');
}

function imagePathWithoutQuery(imageUrl) {
    return normalizeImageUrl(imageUrl).split('#')[0].split('?')[0];
}

function isSvgImageUrl(imageUrl) {
    return imagePathWithoutQuery(imageUrl).toLowerCase().endsWith('.svg');
}

function imageCardVariantUrl(imageUrl) {
    const image = normalizeImageUrl(imageUrl);
    if (!image || isExternalImageUrl(image) || isDataImageUrl(image) || isSvgImageUrl(image)) {
        return image;
    }

    const hasLeadingSlash = image.startsWith('/');
    let path = image.replace(/^\/+/, '');
    if (path.startsWith('frontend/images/')) {
        path = path.slice('frontend/'.length);
    }
    if (!path.startsWith('images/')) return image;

    const cleanPath = imagePathWithoutQuery(path);
    const extension = cleanPath.slice(cleanPath.lastIndexOf('.') + 1).toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'webp'].includes(extension)) return image;

    const relativeToImages = cleanPath.slice('images/'.length);
    const lastSlash = relativeToImages.lastIndexOf('/');
    const directory = lastSlash >= 0 ? relativeToImages.slice(0, lastSlash + 1) : '';
    const filename = lastSlash >= 0 ? relativeToImages.slice(lastSlash + 1) : relativeToImages;
    const dotIndex = filename.lastIndexOf('.');
    if (dotIndex <= 0) return image;

    const stem = filename.slice(0, dotIndex);
    return `${hasLeadingSlash ? '/' : ''}images/variants/${directory}${stem}-card.webp`;
}

function productMainImage(product) {
    if (product.image) return product.image;
    if (Array.isArray(product.images) && product.images.length) return product.images[0];
    return '';
}

function productCardImageSrc(product) {
    const image = productMainImage(product);
    return imageCardVariantUrl(image);
}

function fallbackProductCardImage(imageElement) {
    const originalSrc = imageElement.getAttribute('data-original-src');
    const currentSrc = imageElement.getAttribute('src');
    if (originalSrc && currentSrc !== originalSrc && imageElement.dataset.originalFallbackApplied !== 'true') {
        imageElement.dataset.originalFallbackApplied = 'true';
        imageElement.setAttribute('src', originalSrc);
        return;
    }

    imageElement.style.display = 'none';
    if (imageElement.nextElementSibling) {
        imageElement.nextElementSibling.style.display = 'flex';
    }
}

function renderProductImage(product) {
    const productUrl = `/produto?id=${encodeURIComponent(product.id)}`;
    const productName = product.name || 'Produto VJ Semijoias';
    const originalImage = productMainImage(product);

    if (!originalImage) {
        return `<a href="${productUrl}" aria-label="Ver detalhes de ${escapeHTML(productName)}">
            <div class="placeholder">${escapeHTML(product.icon || 'VJ')}</div>
        </a>`;
    }

    const cardImage = productCardImageSrc(product);
    return `<a href="${productUrl}" aria-label="Ver detalhes de ${escapeHTML(productName)}">
        <img src="${escapeHTML(cardImage)}" data-original-src="${escapeHTML(originalImage)}" alt="${escapeHTML(productName)}" loading="lazy" decoding="async" onerror="fallbackProductCardImage(this)">
        <div class="placeholder" style="display:none;">${escapeHTML(product.icon || 'VJ')}</div>
    </a>`;
}

function createProductCard(product) {
    const badgeLabels = {
        new: 'NOVO',
        sale: 'OFERTA',
        bestseller: 'MAIS VENDIDO',
    };
    const badge = product.badge || '';
    const badgeHTML = badge ?
        `<span class="product-badge ${escapeHTML(badge)}">${escapeHTML(badgeLabels[badge] || badge)}</span>` : '';
    const isOutOfStock = product.stock_status === 'out_of_stock';
    const stockHTML = isOutOfStock
        ? '<div class="stock-note unavailable">Sem estoque no momento</div>'
        : (product.stock_status === 'preorder' ? '<div class="stock-note preorder">Sob encomenda</div>' : '');
    const categoryName = product.categoryName || product.category || 'Semijoia';
    const description = product.description || 'Peca selecionada pela curadoria VJ Semijoias.';
    const productUrl = `/produto?id=${encodeURIComponent(product.id)}`;

    const priceHTML = product.oldPrice ?
        `<div class="product-price">
            <span class="old-price">${formatPrice(product.oldPrice)}</span>
            ${formatPrice(product.price)}
        </div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>` :
        `<div class="product-price">${formatPrice(product.price)}</div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>`;

    return `
        <div class="product-card catalog-product-card" data-category="${escapeHTML(product.category || '')}">
            <div class="product-image">
                ${badgeHTML}
                ${renderProductImage(product)}
            </div>
            <div class="product-info">
                <span class="product-category">${escapeHTML(categoryName)}</span>
                <a href="${productUrl}">
                    <h3 class="product-title">${escapeHTML(product.name || 'Produto')}</h3>
                </a>
                <p class="product-description">${escapeHTML(description)}</p>

                ${stockHTML}
                <div class="product-footer">
                    <div>
                        ${priceHTML}
                    </div>
                </div>
                <div class="product-card-actions">
                    <a class="product-view-link" href="${productUrl}">Ver peca</a>
                    <button class="btn-add-cart" onclick="addToCart(${Number(product.id)})" title="Adicionar ao carrinho" ${isOutOfStock ? 'disabled' : ''}>
                        Adicionar
                    </button>
                </div>
            </div>
        </div>
    `;
}function addToCart(productId) {
    const product = getProductById(productId);
    if (!product || product.stock_status === 'out_of_stock') {
        showToast('Produto sem estoque no momento', 'error');
        return;
    }
    const success = Cart.add(productId, 1);
    if (success) {
        if (product) {
            showToast(`${product.name} adicionado ao carrinho!`, 'success');
        }
    }
}

async function handleNewsletter(event) {
    event.preventDefault();
    const email = event.target.querySelector('input').value;
    if (email) {
        // Tenta API primeiro
        try {
            const result = await API.subscribeNewsletter(email);
            if (result.success) {
                showToast(result.data.message || 'E-mail cadastrado!', 'success', 'Bem-vinda!');
                event.target.reset();
                if (result.data.coupon) {
                    localStorage.setItem('vj_coupon', result.data.coupon);
                }
                return;
            }
        } catch (e) { }

        // Fallback offline
        showToast('E-mail cadastrado! Confira os descontos ativos no carrinho.', 'success', 'Bem-vinda!');
        event.target.reset();
    }
}

// Máscaras
function maskCPF(v) {
    return v.replace(/\D/g, '').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2').slice(0, 14);
}
function maskPhone(v) {
    return v.replace(/\D/g, '').replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4,5})(\d{4})$/, '$1-$2').slice(0, 15);
}
function maskCEP(v) {
    return v.replace(/\D/g, '').replace(/(\d{5})(\d)/, '$1-$2').slice(0, 9);
}
function maskCardNumber(v) {
    return v.replace(/\D/g, '').replace(/(\d{4})(\d)/, '$1 $2').replace(/(\d{4})(\d)/, '$1 $2').replace(/(\d{4})(\d)/, '$1 $2').slice(0, 19);
}
function maskCardExpiry(v) {
    return v.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1/$2').slice(0, 5);
}

function applyInputMasks() {
    const masks = {
        cpf: maskCPF,
        phone: maskPhone,
        cep: maskCEP,
        card: maskCardNumber,
        expiry: maskCardExpiry,
    };

    document.querySelectorAll('[data-mask]').forEach(input => {
        const mask = masks[input.dataset.mask];
        if (!mask || input.dataset.maskBound === 'true') return;
        input.addEventListener('input', event => {
            event.target.value = mask(event.target.value);
        });
        input.dataset.maskBound = 'true';
    });
}

document.addEventListener('DOMContentLoaded', applyInputMasks);
