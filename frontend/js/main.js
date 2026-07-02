// ============================================
// MAIN - Funções principais
// ============================================

function createProductCard(product) {
    const badgeLabels = {
        new: 'NOVO',
        sale: 'OFERTA',
        bestseller: 'MAIS VENDIDO',
    };
    const badgeHTML = product.badge ?
        `<span class="product-badge ${product.badge}">${badgeLabels[product.badge] || product.badge}</span>` : '';
    const isOutOfStock = product.stock_status === 'out_of_stock';
    const stockHTML = isOutOfStock
        ? '<div class="stock-note unavailable">Sem estoque no momento</div>'
        : (product.stock_status === 'preorder' ? '<div class="stock-note preorder">Sob encomenda</div>' : '');
    const categoryName = product.categoryName || product.category || 'Semijoia';
    const description = product.description || 'Peça selecionada pela curadoria VJ Semijoias.';
    const productUrl = `/produto?id=${product.id}`;

    const priceHTML = product.oldPrice ?
        `<div class="product-price">
            <span class="old-price">${formatPrice(product.oldPrice)}</span>
            ${formatPrice(product.price)}
        </div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>` :
        `<div class="product-price">${formatPrice(product.price)}</div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>`;

    const imageHTML = product.image ?
        `<a href="${productUrl}" aria-label="Ver detalhes de ${product.name}">
            <img src="${product.image}" alt="${product.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="placeholder" style="display:none;">${product.icon || 'VJ'}</div>
        </a>` :
        `<a href="${productUrl}" aria-label="Ver detalhes de ${product.name}">
            <div class="placeholder">${product.icon || 'VJ'}</div>
        </a>`;

    return `
        <div class="product-card catalog-product-card" data-category="${product.category}">
            <div class="product-image">
                ${badgeHTML}
                ${imageHTML}
            </div>
            <div class="product-info">
                <span class="product-category">${categoryName}</span>
                <a href="${productUrl}">
                    <h3 class="product-title">${product.name}</h3>
                </a>
                <p class="product-description">${description}</p>

                ${stockHTML}
                <div class="product-footer">
                    <div>
                        ${priceHTML}
                    </div>
                </div>
                <div class="product-card-actions">
                    <a class="product-view-link" href="${productUrl}">Ver peça</a>
                    <button class="btn-add-cart" onclick="addToCart(${product.id})" title="Adicionar ao carrinho" ${isOutOfStock ? 'disabled' : ''}>
                        Adicionar
                    </button>
                </div>
            </div>
        </div>
    `;
}
function addToCart(productId) {
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
