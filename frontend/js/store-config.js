// ============================================
// STORE CONFIG - aplica configuracoes publicas da loja
// ============================================

async function getStoreConfig() {
    if (window.__vjStoreConfig) return window.__vjStoreConfig;
    if (!window.API?.getStoreConfig) return null;
    const result = await API.getStoreConfig();
    if (!result.success) return null;
    window.__vjStoreConfig = result.data;
    return window.__vjStoreConfig;
}

function whatsappLink(number) {
    const digits = String(number || '').replace(/\D/g, '');
    return digits ? `https://wa.me/55${digits.replace(/^55/, '')}` : '';
}

function instagramLink(username) {
    const clean = String(username || '').replace(/^@/, '');
    return clean ? `https://instagram.com/${clean}` : '';
}

function setText(selector, value) {
    document.querySelectorAll(selector).forEach(element => {
        element.textContent = value || '';
    });
}

function setHref(selector, value) {
    document.querySelectorAll(selector).forEach(element => {
        if (value) {
            element.href = value;
            element.removeAttribute('aria-disabled');
            return;
        }
        element.removeAttribute('href');
        element.setAttribute('aria-disabled', 'true');
    });
}

function applyStoreConfig(config) {
    if (!config) return;
    const brand = config.brand || {};
    const contact = config.contact || {};

    document.querySelectorAll('.logo-img, .footer-logo, .hero-logo, .auth-logo-img').forEach(image => {
        if (brand.logo_path) image.src = brand.logo_path;
        if (brand.name) image.alt = brand.name;
    });

    setText('.logo-vj, .auth-logo-text', brand.short_name);
    setText('.logo-tagline, .auth-logo-tagline', brand.tagline);
    setText('[data-store-name]', brand.name);
    setText('[data-store-description]', brand.description);
    setText('[data-store-email]', contact.email ? `📧 ${contact.email}` : '');
    setText('[data-store-phone]', contact.phone ? `📱 ${contact.phone}` : '');
    setText('[data-store-whatsapp]', contact.whatsapp ? `💬 ${contact.whatsapp}` : '');
    setText('[data-store-instagram]', contact.instagram ? `📷 @${String(contact.instagram).replace(/^@/, '')}` : '');
    setText('[data-store-location]', contact.location ? `📍 ${contact.location}` : '');
    setText('[data-store-hours]', contact.business_hours ? `🕐 ${contact.business_hours}` : '');
    setText(
        '[data-store-copyright]',
        `© 2026 ${brand.name || 'Loja'}. Todos os direitos reservados.${contact.cnpj ? ` CNPJ: ${contact.cnpj}` : ''}`
    );

    setHref('[data-store-whatsapp-link]', whatsappLink(contact.whatsapp || contact.phone));
    setHref('[data-store-instagram-link]', instagramLink(contact.instagram));
}

async function refreshPublicStoreConfig() {
    const config = await getStoreConfig();
    applyStoreConfig(config);
    return config;
}

window.getStoreConfig = getStoreConfig;
window.applyStoreConfig = applyStoreConfig;
window.refreshPublicStoreConfig = refreshPublicStoreConfig;

document.addEventListener('DOMContentLoaded', async () => {
    await refreshPublicStoreConfig();
});
