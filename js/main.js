// ============================================
// MAIN - Funções principais
// ============================================

function createProductCard(product) {
    const badgeHTML = product.badge ?
        `<span class="product-badge ${product.badge}">${product.badge === 'new' ? 'NOVO' : 'OFERTA'}</span>` : '';

    const priceHTML = product.oldPrice ?
        `<div class="product-price">
            <span class="old-price">${formatPrice(product.oldPrice)}</span>
            ${formatPrice(product.price)}
        </div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>` :
        `<div class="product-price">${formatPrice(product.price)}</div>
        <div class="product-installment">ou 12x de ${formatPrice(calculateInstallment(product.price))} sem juros</div>`;

    // Decide se mostra imagem real ou placeholder
    const imageHTML = product.image ?
        `<a href="produto.html?id=${product.id}">
            <img src="${product.image}" alt="${product.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="placeholder" style="display:none;">${product.icon || '💎'}</div>
        </a>` :
        `<a href="produto.html?id=${product.id}">
            <div class="placeholder">${product.icon || '💎'}</div>
        </a>`;

    return `
        <div class="product-card" data-category="${product.category}">
            <div class="product-image">
                ${badgeHTML}
                ${imageHTML}
            </div>
            <div class="product-info">
                <span class="product-category">${product.categoryName}</span>
                <a href="produto.html?id=${product.id}">
                    <h3 class="product-title">${product.name}</h3>
                </a>
                <p class="product-description">${product.description}</p>
                <div class="product-footer">
                    <div>
                        ${priceHTML}
                    </div>
                    <button class="btn-add-cart" onclick="addToCart(${product.id})" title="Adicionar ao carrinho">
                        🛒 Add
                    </button>
                </div>
            </div>
        </div>
    `;
}

function addToCart(productId) {
    const success = Cart.add(productId, 1);
    if (success) {
        const product = getProductById(productId);
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
                localStorage.setItem('vj_coupon', 'VJ10');
                return;
            }
        } catch (e) { }

        // Fallback offline
        showToast('E-mail cadastrado! Use o cupom VJ10 e ganhe 10% off', 'success', 'Bem-vinda!');
        event.target.reset();
        localStorage.setItem('vj_coupon', 'VJ10');
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

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mask="cpf"]').forEach(i => i.addEventListener('input', e => e.target.value = maskCPF(e.target.value)));
    document.querySelectorAll('[data-mask="phone"]').forEach(i => i.addEventListener('input', e => e.target.value = maskPhone(e.target.value)));
    document.querySelectorAll('[data-mask="cep"]').forEach(i => i.addEventListener('input', e => e.target.value = maskCEP(e.target.value)));
    document.querySelectorAll('[data-mask="card"]').forEach(i => i.addEventListener('input', e => e.target.value = maskCardNumber(e.target.value)));
    document.querySelectorAll('[data-mask="expiry"]').forEach(i => i.addEventListener('input', e => e.target.value = maskCardExpiry(e.target.value)));
});
