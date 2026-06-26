// ============================================
// ADMIN - VJ Semijoias
// Gerenciamento de produtos via API
// ============================================

let currentFilter = 'all';
let currentSearch = '';
let currentOrderFilter = 'all';
let currentOrderSearch = '';
let editingId = null;
let adminProducts = [];
let adminOrders = [];
let adminUsers = [];
let adminAuditLogs = [];
let adminCoupons = [];
let imageUploadInitialized = false;
let productPreviewInitialized = false;
let catalogPdfInitialized = false;
let storeConfigInitialized = false;
let adminSecurityInitialized = false;
let couponAdminInitialized = false;
let catalogPdfItems = [];
let productGalleryImages = [];
let importFolderFiles = [];
let importPreviewState = null;
let activeOrderModalId = null;

const ADMIN_PAGES = {
    overview: {
        title: 'Resumo do painel',
        subtitle: 'Acompanhe indicadores gerais e escolha uma area para operar.',
    },
    orders: {
        title: 'Pedidos',
        subtitle: 'Acompanhe pagamentos, status, rastreio e entregas.',
    },
    settings: {
        title: 'Configuracoes da loja',
        subtitle: 'Ajuste identidade, contato, frete e e-mails transacionais.',
    },
    coupons: {
        title: 'Cupons promocionais',
        subtitle: 'Crie e acompanhe regras de desconto sem redeploy.',
    },
    security: {
        title: 'Acessos e auditoria',
        subtitle: 'Gerencie administradores e revise eventos sensiveis.',
    },
    products: {
        title: 'Produtos',
        subtitle: 'Cadastre, edite estoque e organize o catalogo da loja.',
    },
    catalog: {
        title: 'Catalogo PDF',
        subtitle: 'Monte materiais visuais para compartilhar com clientes.',
    },
    import: {
        title: 'Importacao e acoes globais',
        subtitle: 'Importe pastas, exporte dados e execute operacoes de catalogo.',
    },
};

let activeAdminPage = 'overview';

function adminPageFromHash() {
    const page = String(window.location.hash || '').replace('#', '').trim();
    return ADMIN_PAGES[page] ? page : 'overview';
}

function switchAdminPage(page, { updateHash = true } = {}) {
    const nextPage = ADMIN_PAGES[page] ? page : 'overview';
    activeAdminPage = nextPage;
    document.querySelectorAll('[data-admin-page]').forEach(section => {
        section.classList.toggle('active', section.dataset.adminPage === nextPage);
    });
    document.querySelectorAll('[data-admin-page-target]').forEach(button => {
        const active = button.dataset.adminPageTarget === nextPage;
        button.classList.toggle('active', active);
        button.setAttribute('aria-current', active ? 'page' : 'false');
    });
    const header = ADMIN_PAGES[nextPage];
    const title = document.getElementById('admin-page-title');
    const subtitle = document.getElementById('admin-page-subtitle');
    if (title) title.textContent = header.title;
    if (subtitle) subtitle.textContent = header.subtitle;
    if (updateHash && window.location.hash !== `#${nextPage}`) {
        window.history.replaceState(null, '', `#${nextPage}`);
    }
}
// ============================================
// AUTENTICAÃ‡ÃƒO
// ============================================

function isAuthenticated() {
    return API.hasAdminToken();
}

async function handleAdminLogin(event) {
    event.preventDefault();
    const email = document.getElementById('admin-email').value.trim();
    const password = document.getElementById('admin-password').value;

    const result = await API.adminLogin(email, password);
    if (result.success) {
        await showAdminPanel();
        showToast('Bem-vinda ao painel admin!', 'success', 'Login realizado');
    } else {
        showToast(result.error || 'NÃ£o foi possÃ­vel entrar', 'error', 'Acesso negado');
        document.getElementById('admin-password').value = '';
        document.getElementById(email ? 'admin-password' : 'admin-email').focus();
    }
}

function logout() {
    API.logout();
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('admin-panel').style.display = 'none';
}

async function showAdminPanel() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('admin-panel').style.display = 'block';
    switchAdminPage(adminPageFromHash(), { updateHash: false });
    const result = await API.getAdminProducts();
    if (!result.success) {
        showToast(result.error || 'Falha ao carregar produtos', 'error');
        logout();
        return;
    }
    adminProducts = result.data;
    apiProductsCache = result.data;
    apiLoaded = true;
    await applyStoreEnvironmentConfig();
    await loadAdminStoreConfig();
    await loadAdminCoupons();
    await loadAdminSecurity();
    renderAdminProducts();
    await loadAdminOrders();
    await updateStats();
    if (!imageUploadInitialized) {
        setupImageUpload();
        imageUploadInitialized = true;
    }
    if (!productPreviewInitialized) {
        setupProductFormPreview();
        productPreviewInitialized = true;
    }
    if (!catalogPdfInitialized) {
        setupCatalogPdfDropzone();
        catalogPdfInitialized = true;
    }
    if (!storeConfigInitialized) {
        setupStoreConfigForm();
        storeConfigInitialized = true;
    }
    if (!couponAdminInitialized) {
        setupCouponAdminForm();
        couponAdminInitialized = true;
    }
    if (!adminSecurityInitialized) {
        setupAdminSecurityForm();
        adminSecurityInitialized = true;
    }
}

async function applyStoreEnvironmentConfig() {
    const result = await API.getStoreConfig();
    if (!result.success) return;
    const titleInput = document.getElementById('catalog-pdf-title');
    const collectionInput = document.getElementById('catalog-pdf-collection');
    const sloganInput = document.getElementById('catalog-pdf-slogan');
    const contactInput = document.getElementById('catalog-pdf-contact');
    const couponInput = document.getElementById('catalog-pdf-coupon');
    const filenameInput = document.getElementById('catalog-pdf-filename');
    const catalog = result.data.catalog || {};
    const brand = result.data.brand || {};
    const coupon = result.data.coupon;
    if (titleInput && catalog.title) titleInput.value = catalog.title;
    if (collectionInput && catalog.collection) collectionInput.value = catalog.collection;
    if (sloganInput && brand.slogan) sloganInput.value = brand.slogan;
    if (contactInput && catalog.contact_line) contactInput.value = catalog.contact_line;
    if (filenameInput && catalog.filename) filenameInput.value = catalog.filename;
    if (couponInput && coupon?.enabled && coupon.code) {
        couponInput.value = `${coupon.code} = ${coupon.discount_percent}% OFF`;
    } else if (couponInput) {
        couponInput.value = '';
    }
}

function setupStoreConfigForm() {
    const form = document.getElementById('store-config-form');
    if (!form) return;
    form.addEventListener('submit', handleStoreConfigSubmit);
}

async function loadAdminStoreConfig() {
    const form = document.getElementById('store-config-form');
    if (!form) return;

    const result = await API.getAdminStoreConfig();
    if (!result.success) {
        showToast(result.error || 'Falha ao carregar configuracoes', 'error');
        return;
    }

    fillStoreConfigForm(result.data.values || {});
}

function fillStoreConfigForm(values) {
    document.querySelectorAll('[data-store-config]').forEach(field => {
        const key = field.dataset.storeConfig;
        if (!(key in values)) return;
        if (field.type === 'checkbox') {
            field.checked = String(values[key]).toLowerCase() === 'true';
        } else {
            field.value = values[key] ?? '';
        }
    });
}

function readStoreConfigForm() {
    const values = {};
    document.querySelectorAll('[data-store-config]').forEach(field => {
        const key = field.dataset.storeConfig;
        values[key] = field.type === 'checkbox' ? field.checked : field.value.trim();
    });
    return values;
}

async function handleStoreConfigSubmit(event) {
    event.preventDefault();
    const submit = document.getElementById('store-config-submit');
    if (submit) {
        submit.disabled = true;
        submit.textContent = 'Salvando...';
    }

    const result = await API.updateAdminStoreConfig(readStoreConfigForm());
    if (submit) {
        submit.disabled = false;
        submit.textContent = 'Salvar configuracoes';
    }

    if (!result.success) {
        showToast(result.error || 'Falha ao salvar configuracoes', 'error');
        return;
    }

    fillStoreConfigForm(result.data.values || {});
    await applyStoreEnvironmentConfig();
    showToast('Configuracoes da loja atualizadas', 'success');
}

async function sendTestEmail() {
    const button = document.getElementById('email-test-submit');
    const recipientField = document.getElementById('email-test-recipient');
    const storeEmailField = document.querySelector('[data-store-config="STORE_EMAIL"]');
    const email = (recipientField?.value || storeEmailField?.value || '').trim();
    if (!email) {
        showToast('Informe um e-mail para teste', 'error');
        return;
    }
    if (button) {
        button.disabled = true;
        button.textContent = 'Enviando...';
    }

    const saveResult = await API.updateAdminStoreConfig(readStoreConfigForm());
    if (!saveResult.success) {
        if (button) {
            button.disabled = false;
            button.textContent = 'Enviar teste';
        }
        showToast(saveResult.error || 'Falha ao salvar configuracoes de e-mail', 'error');
        return;
    }
    fillStoreConfigForm(saveResult.data.values || {});
    await applyStoreEnvironmentConfig();

    const result = await API.sendAdminEmailTest(email);
    if (button) {
        button.disabled = false;
        button.textContent = 'Enviar teste';
    }
    if (!result.success) {
        showToast(result.error || 'Falha ao enviar e-mail de teste', 'error');
        return;
    }
    showToast(result.data?.message || 'E-mail de teste enviado', 'success');
}

// ============================================
// CUPONS PROMOCIONAIS
// ============================================

function setupCouponAdminForm() {
    const form = document.getElementById('admin-coupon-form');
    if (!form) return;
    form.addEventListener('submit', handleCouponSubmit);
}

async function loadAdminCoupons() {
    const list = document.getElementById('admin-coupons-list');
    if (!list) return;
    const result = await API.getAdminCoupons();
    if (!result.success) {
        showToast(result.error || 'Falha ao carregar cupons', 'error');
        return;
    }
    adminCoupons = result.data || [];
    renderAdminCoupons();
}

function readCouponForm() {
    return {
        code: document.getElementById('coupon-code').value.trim(),
        discount_type: document.getElementById('coupon-discount-type').value,
        discount_value: document.getElementById('coupon-discount-value').value,
        minimum_subtotal: document.getElementById('coupon-minimum-subtotal').value || '0',
        usage_limit: document.getElementById('coupon-usage-limit').value || '0',
        per_customer_limit: document.getElementById('coupon-per-customer-limit').value || '0',
        starts_at: document.getElementById('coupon-starts-at').value,
        ends_at: document.getElementById('coupon-ends-at').value,
        is_active: document.getElementById('coupon-is-active').checked,
    };
}

function resetCouponForm() {
    const form = document.getElementById('admin-coupon-form');
    if (!form) return;
    form.reset();
    document.getElementById('coupon-id').value = '';
    document.getElementById('coupon-is-active').checked = true;
    document.getElementById('coupon-minimum-subtotal').value = '0';
    document.getElementById('coupon-usage-limit').value = '0';
    document.getElementById('coupon-per-customer-limit').value = '0';
    document.getElementById('coupon-form-title').textContent = 'Novo cupom';
    document.getElementById('coupon-submit').textContent = 'Salvar cupom';
}

function dateInputValue(value) {
    if (!value) return '';
    return String(value).slice(0, 10);
}

function editCoupon(id) {
    const coupon = adminCoupons.find(item => Number(item.id) === Number(id));
    if (!coupon) return;
    document.getElementById('coupon-id').value = coupon.id;
    document.getElementById('coupon-code').value = coupon.code || '';
    document.getElementById('coupon-discount-type').value = coupon.discount_type || 'percent';
    document.getElementById('coupon-discount-value').value = coupon.discount_value || '';
    document.getElementById('coupon-minimum-subtotal').value = coupon.minimum_subtotal || 0;
    document.getElementById('coupon-usage-limit').value = coupon.usage_limit || 0;
    document.getElementById('coupon-per-customer-limit').value = coupon.per_customer_limit || 0;
    document.getElementById('coupon-starts-at').value = dateInputValue(coupon.starts_at);
    document.getElementById('coupon-ends-at').value = dateInputValue(coupon.ends_at);
    document.getElementById('coupon-is-active').checked = Boolean(coupon.is_active);
    document.getElementById('coupon-form-title').textContent = `Editar ${coupon.code}`;
    document.getElementById('coupon-submit').textContent = 'Atualizar cupom';
}

async function toggleCoupon(id) {
    const coupon = adminCoupons.find(item => Number(item.id) === Number(id));
    if (!coupon) return;
    const result = await API.updateAdminCoupon(id, { is_active: !coupon.is_active });
    if (!result.success) {
        showToast(result.error || 'Falha ao atualizar cupom', 'error');
        return;
    }
    await loadAdminCoupons();
    showToast(coupon.is_active ? 'Cupom pausado' : 'Cupom reativado', 'success');
}

async function handleCouponSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('coupon-id').value;
    const submit = document.getElementById('coupon-submit');
    const payload = readCouponForm();

    if (submit) {
        submit.disabled = true;
        submit.textContent = id ? 'Atualizando...' : 'Criando...';
    }

    const result = id
        ? await API.updateAdminCoupon(id, payload)
        : await API.createAdminCoupon(payload);

    if (submit) {
        submit.disabled = false;
        submit.textContent = id ? 'Atualizar cupom' : 'Salvar cupom';
    }

    if (!result.success) {
        showToast(result.error || 'Falha ao salvar cupom', 'error');
        return;
    }

    resetCouponForm();
    await loadAdminCoupons();
    await loadAdminSecurity();
    showToast('Cupom salvo com sucesso', 'success');
}

function couponDiscountLabel(coupon) {
    if (coupon.discount_type === 'fixed') {
        return `${formatPrice(coupon.discount_value || 0)} OFF`;
    }
    return `${Number(coupon.discount_value || coupon.discount_percent || 0)}% OFF`;
}

function couponValidityLabel(coupon) {
    const start = coupon.starts_at ? dateInputValue(coupon.starts_at) : 'agora';
    const end = coupon.ends_at ? dateInputValue(coupon.ends_at) : 'sem fim';
    return `${start} ate ${end}`;
}

function renderAdminCoupons() {
    const container = document.getElementById('admin-coupons-list');
    if (!container) return;

    if (!adminCoupons.length) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">CUP</div>
                <p>Nenhum cupom cadastrado ainda.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = adminCoupons.map(coupon => {
        const redemptions = Array.isArray(coupon.redemptions) ? coupon.redemptions : [];
        const latest = redemptions.slice(0, 3).map(redemption => `
            <small>${escapeHTML(redemption.customer_email || redemption.customer_cpf || 'cliente')} - ${formatPrice(redemption.discount_amount || 0)}</small>
        `).join('');
        const usageLimit = coupon.usage_limit > 0 ? coupon.usage_limit : 'sem limite';
        const perCustomer = coupon.per_customer_limit > 0 ? coupon.per_customer_limit : 'sem limite';
        return `
            <div class="admin-coupon-row ${coupon.is_active ? '' : 'inactive'}">
                <div class="admin-coupon-main">
                    <div>
                        <strong>${escapeHTML(coupon.code)}</strong>
                        <span>${escapeHTML(couponDiscountLabel(coupon))}</span>
                    </div>
                    <span class="coupon-status">${coupon.is_active ? 'Ativo' : 'Pausado'}</span>
                </div>
                <div class="admin-coupon-meta">
                    <small>Usos: ${coupon.used_count || 0}/${usageLimit}</small>
                    <small>Por cliente: ${perCustomer}</small>
                    <small>Minimo: ${formatPrice(coupon.minimum_subtotal || 0)}</small>
                    <small>Validade: ${escapeHTML(couponValidityLabel(coupon))}</small>
                </div>
                ${latest ? `<div class="admin-coupon-redemptions">${latest}</div>` : ''}
                <div class="admin-coupon-actions">
                    <button class="btn btn-outline" type="button" onclick="editCoupon(${coupon.id})">Editar</button>
                    <button class="btn btn-outline" type="button" onclick="toggleCoupon(${coupon.id})">
                        ${coupon.is_active ? 'Pausar' : 'Reativar'}
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// ADMINISTRADORES E AUDITORIA
// ============================================

function setupAdminSecurityForm() {
    const form = document.getElementById('admin-user-form');
    if (!form) return;
    form.addEventListener('submit', handleAdminUserSubmit);
}

async function loadAdminSecurity() {
    const usersResult = await API.getAdminUsers();
    if (usersResult.success) {
        adminUsers = usersResult.data || [];
        renderAdminUsers();
    }

    const logsResult = await API.getAdminAuditLogs(80);
    if (logsResult.success) {
        adminAuditLogs = logsResult.data || [];
        renderAdminAuditLogs();
    }
}

function adminAuditLabel(action) {
    return {
        'admin.login.succeeded': 'Login admin realizado',
        'admin.login.failed': 'Tentativa de login falhou',
        'admin.user.created': 'Administrador criado',
        'store.config.updated': 'Configuracoes da loja alteradas',
        'catalog.imported': 'Catalogo importado',
        'catalog.cleared': 'Catalogo limpo',
        'coupon.created': 'Cupom criado',
        'coupon.updated': 'Cupom alterado',
    }[action] || action || 'Evento';
}

function adminAuditDetail(log) {
    const metadata = log.metadata || {};
    if (Array.isArray(metadata.sensitive_keys) && metadata.sensitive_keys.length) {
        return `Campos sensiveis: ${metadata.sensitive_keys.join(', ')}`;
    }
    if (Array.isArray(metadata.changed_keys) && metadata.changed_keys.length) {
        return `Campos: ${metadata.changed_keys.join(', ')}`;
    }
    if (typeof metadata.deleted === 'number') {
        return `${metadata.deleted} produtos removidos`;
    }
    if (typeof metadata.products === 'number') {
        return `${metadata.products} produtos, ${metadata.images || 0} imagens`;
    }
    if (metadata.email) {
        return metadata.email;
    }
    return log.resource || '';
}

function renderAdminUsers() {
    const container = document.getElementById('admin-users-list');
    if (!container) return;

    if (!adminUsers.length) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">ADM</div>
                <p>Nenhum administrador encontrado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = adminUsers.map(user => `
        <div class="admin-user-row">
            <div>
                <strong>${escapeHTML(user.name || user.email)}</strong>
                <span>${escapeHTML(user.email || '')}</span>
            </div>
            <div>
                <small>Criado em ${formatOrderDate(user.created_at)}</small>
                <small>Ultimo login ${formatOrderDate(user.last_login_at)}</small>
            </div>
        </div>
    `).join('');
}

function renderAdminAuditLogs() {
    const container = document.getElementById('admin-audit-list');
    if (!container) return;

    if (!adminAuditLogs.length) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">LOG</div>
                <p>Nenhum log encontrado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = adminAuditLogs.map(log => `
        <div class="admin-audit-row ${String(log.action || '').includes('failed') ? 'warning' : ''}">
            <div>
                <strong>${escapeHTML(adminAuditLabel(log.action))}</strong>
                <span>${escapeHTML(adminAuditDetail(log))}</span>
            </div>
            <div>
                <small>${formatOrderDate(log.created_at)}</small>
                <small>${escapeHTML(log.ip_address || '')}</small>
            </div>
        </div>
    `).join('');
}

async function handleAdminUserSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const name = document.getElementById('new-admin-name').value.trim();
    const email = document.getElementById('new-admin-email').value.trim();
    const password = document.getElementById('new-admin-password').value;
    const submit = document.getElementById('admin-user-submit');

    if (submit) {
        submit.disabled = true;
        submit.textContent = 'Criando...';
    }

    const result = await API.createAdminUser({ name, email, password });

    if (submit) {
        submit.disabled = false;
        submit.textContent = 'Criar admin';
    }

    if (!result.success) {
        showToast(result.error || 'Falha ao criar administrador', 'error');
        return;
    }

    form.reset();
    await loadAdminSecurity();
    showToast('Administrador criado com sucesso', 'success');
}

// ============================================
// UPLOAD DE IMAGEM
// ============================================

function setupImageUpload() {
    const uploadArea = document.getElementById('image-upload');
    if (!uploadArea) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.add('dragging');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragging');
        });
    });

    uploadArea.addEventListener('drop', (e) => {
        addProductImageFiles(Array.from(e.dataTransfer.files || []));
    });
}

function handleImageUpload(event) {
    addProductImageFiles(Array.from(event.target.files || []));
    event.target.value = '';
}

function addProductImageFiles(files) {
    const validFiles = files.filter(file => file.type.startsWith('image/'));
    if (validFiles.length !== files.length) {
        showToast('Alguns arquivos foram ignorados porque nao sao imagens', 'info');
    }

    validFiles.forEach(file => {
        if (file.size > 5 * 1024 * 1024) {
            showToast(`Imagem muito grande: ${file.name}`, 'error', 'Arquivo grande');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            productGalleryImages.push(e.target.result);
            syncProductImageUrlField();
            renderProductGalleryPreview();
            renderProductFormPreview();
        };
        reader.readAsDataURL(file);
    });
}

function showImagePreview(src) {
    setProductGalleryImages(src ? [src] : []);
}

function setProductGalleryImages(images) {
    productGalleryImages = [...new Set((images || []).map(item => String(item || '').trim()).filter(Boolean))];
    syncProductImageUrlField();
    renderProductGalleryPreview();
    renderProductFormPreview();
}

function syncProductImageUrlField() {
    document.getElementById('image-url').value = productGalleryImages.join('\n');
}

function removeProductGalleryImage(index) {
    productGalleryImages.splice(index, 1);
    syncProductImageUrlField();
    renderProductGalleryPreview();
    renderProductFormPreview();
}

function moveProductGalleryImage(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= productGalleryImages.length) return;
    const [image] = productGalleryImages.splice(index, 1);
    productGalleryImages.splice(target, 0, image);
    syncProductImageUrlField();
    renderProductGalleryPreview();
    renderProductFormPreview();
}

function renderProductGalleryPreview() {
    const preview = document.getElementById('image-preview');
    if (productGalleryImages.length === 0) {
        preview.innerHTML = `
            <div class="upload-placeholder">
                <div style="font-size: 3rem;">ðŸ“·</div>
                <p>Clique ou arraste as imagens</p>
                <small>PNG, JPG ate 5MB cada</small>
            </div>
        `;
        return;
    }

    preview.innerHTML = `
        <div class="product-gallery-admin">
            ${productGalleryImages.map((image, index) => `
                <div class="product-gallery-admin-item ${index === 0 ? 'main' : ''}">
                    <img src="${image}" alt="Foto ${index + 1}">
                    <span>${index === 0 ? 'Principal' : `Foto ${index + 1}`}</span>
                    <div class="product-gallery-admin-actions">
                        <button type="button" onclick="moveProductGalleryImage(${index}, -1)">Up</button>
                        <button type="button" onclick="moveProductGalleryImage(${index}, 1)">Down</button>
                        <button type="button" onclick="removeProductGalleryImage(${index})">X</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function syncImageFromUrl() {
    const images = document.getElementById('image-url').value
        .split(/\r?\n/)
        .map(item => item.trim())
        .filter(Boolean);
    setProductGalleryImages(images);
}

// ============================================
// FORMULÃRIO
// ============================================

function escapeHTML(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function escapeJSString(value) {
    return String(value ?? '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function badgeLabel(badge) {
    return {
        new: 'NOVO',
        sale: 'OFERTA',
        bestseller: 'MAIS VENDIDO',
    }[badge] || '';
}

function stockLabel(stockStatus) {
    return {
        available: 'Disponivel',
        preorder: 'Sob encomenda',
        out_of_stock: 'Sem estoque',
    }[stockStatus] || 'Disponivel';
}

function setupProductFormPreview() {
    const form = document.getElementById('product-form');
    if (!form) return;
    form.querySelectorAll('input, select, textarea').forEach(field => {
        field.addEventListener('input', renderProductFormPreview);
        field.addEventListener('change', renderProductFormPreview);
    });
    renderProductFormPreview();
}

function currentFormProduct() {
    const category = document.getElementById('product-category').value || 'semijoias';
    const categoryMap = {
        brincos: 'Brincos',
        colares: 'Colares',
        pulseiras: 'Pulseiras',
        aneis: 'Aneis',
        pingentes: 'Pingentes',
        chaveiros: 'Chaveiros',
        conjuntos: 'Conjuntos',
    };
    return {
        id: editingId || 0,
        name: document.getElementById('product-name').value.trim(),
        category,
        categoryName: categoryMap[category] || category,
        price: parseFloat(document.getElementById('product-price').value) || 0,
        oldPrice: parseFloat(document.getElementById('product-old-price').value) || null,
        sku: document.getElementById('product-sku')?.value.trim() || '',
        image: productGalleryImages[0] || '',
        icon: document.getElementById('product-icon').value.trim() || 'ðŸ’Ž',
        badge: document.getElementById('product-badge').value || null,
        is_active: document.getElementById('product-active')?.checked ?? true,
        stock_status: document.getElementById('product-stock-status')?.value || 'available',
        stock_quantity: parseInt(document.getElementById('product-stock-quantity')?.value || '0', 10) || 0,
        low_stock_alert: parseInt(document.getElementById('product-low-stock-alert')?.value || '0', 10) || 0,
        weight_grams: parseInt(document.getElementById('product-weight-grams')?.value || '100', 10) || 100,
        height_cm: parseFloat(document.getElementById('product-height-cm')?.value || '2') || 2,
        width_cm: parseFloat(document.getElementById('product-width-cm')?.value || '10') || 10,
        length_cm: parseFloat(document.getElementById('product-length-cm')?.value || '15') || 15,
        shipping_profile: document.getElementById('product-shipping-profile')?.value.trim() || 'default',
        description: document.getElementById('product-description').value.trim(),
    };
}

function renderProductFormPreview() {
    const container = document.getElementById('product-card-preview');
    if (!container) return;
    const product = currentFormProduct();
    if (!product.name && !product.price && !product.image && !product.description) {
        container.className = 'admin-product-preview empty';
        container.textContent = 'Preencha os dados para visualizar o card.';
        return;
    }

    const badge = badgeLabel(product.badge);
    const badgeHTML = badge
        ? `<span class="product-badge ${product.badge}">${badge}</span>`
        : '';
    const statusHTML = !product.is_active
        ? '<span class="preview-status inactive">Inativo no site</span>'
        : `<span class="preview-status ${product.stock_status}">${stockLabel(product.stock_status)}</span>`;
    const imageHTML = product.image
        ? `<img src="${escapeHTML(product.image)}" alt="${escapeHTML(product.name || 'Produto')}">`
        : `<div class="placeholder">${escapeHTML(product.icon || 'ðŸ’Ž')}</div>`;
    const priceHTML = product.price ? formatPrice(product.price) : 'R$ 0,00';
    const oldPriceHTML = product.oldPrice
        ? `<span class="old-price">${formatPrice(product.oldPrice)}</span>`
        : '';
    const stockHTML = `<small>SKU: ${escapeHTML(product.sku || 'sem SKU')} | Estoque: ${product.stock_quantity}</small>`;
    const shippingHTML = `<small>Frete: ${product.weight_grams}g | ${product.length_cm} x ${product.width_cm} x ${product.height_cm} cm</small>`;

    container.className = 'admin-product-preview';
    container.innerHTML = `
        <div class="preview-card">
            <div class="preview-image">
                ${badgeHTML}
                ${imageHTML}
            </div>
            <div class="preview-info">
                <div class="preview-topline">
                    <span>${escapeHTML(product.categoryName)}</span>
                    ${statusHTML}
                </div>
                <strong>${escapeHTML(product.name || 'Nome do produto')}</strong>
                <p>${escapeHTML(product.description || 'Descricao curta do produto.')}</p>
                ${stockHTML}
                ${shippingHTML}
                <div class="preview-price">${oldPriceHTML}${priceHTML}</div>
            </div>
        </div>
    `;
}

async function handleProductSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {};
    
    // Pega todos os campos exceto features
    for (let [key, value] of formData.entries()) {
        if (key !== 'features') {
            data[key] = value.trim();
        }
    }
    
    // Processa features
    const featuresText = formData.get('features') || '';
    data.features = featuresText
        .split('\n')
        .map(f => f.trim())
        .filter(f => f.length > 0)
        .map(f => f.startsWith('âœ“') ? f : `âœ“ ${f}`);
    
    data.images = [...productGalleryImages];
    data.image = data.images[0] || null;
    
    // Define Ã­cone padrÃ£o se nÃ£o informado
    if (!data.icon) {
        const iconMap = {
            'brincos': 'âœ¨',
            'colares': 'ðŸ“¿',
            'pulseiras': 'âšœï¸',
            'aneis': 'ðŸ’',
            'pingentes': 'ðŸ”®',
            'chaveiros': 'ðŸ”‘',
            'conjuntos': 'ðŸŽ'
        };
        data.icon = iconMap[data.category] || 'ðŸ’Ž';
    }
    
    // Converte preÃ§os
    data.price = parseFloat(data.price) || 0;
    data.oldPrice = data.oldPrice ? parseFloat(data.oldPrice) : null;
    data.sku = data.sku || null;
    data.stock_quantity = parseInt(data.stock_quantity || '0', 10);
    data.low_stock_alert = parseInt(data.low_stock_alert || '0', 10);
    data.weight_grams = parseInt(data.weight_grams || '100', 10);
    data.height_cm = parseFloat(data.height_cm || '2');
    data.width_cm = parseFloat(data.width_cm || '10');
    data.length_cm = parseFloat(data.length_cm || '15');
    data.shipping_profile = data.shipping_profile || 'default';
    data.is_active = document.getElementById('product-active')?.checked ?? true;
    data.stock_status = document.getElementById('product-stock-status')?.value || 'available';
    
    // Converte badge
    if (!data.badge) data.badge = null;
    
    // Define categoryName
    const categoryMap = {
        'brincos': 'Brincos',
        'colares': 'Colares',
        'pulseiras': 'Pulseiras',
        'aneis': 'AnÃ©is',
        'pingentes': 'Pingentes',
        'chaveiros': 'Chaveiros',
        'conjuntos': 'Conjuntos'
    };
    data.categoryName = categoryMap[data.category] || data.category;
    
    // ValidaÃ§Ãµes
    if (!data.name || !data.category || !data.price || !data.description) {
        showToast('Preencha todos os campos obrigatÃ³rios', 'error', 'Campos vazios');
        return;
    }
    
    if (editingId) {
        const result = await API.updateProduct(editingId, data);
        if (!result.success) {
            showToast(result.error, 'error', 'Erro ao atualizar');
            return;
        }
        showToast('Produto atualizado com sucesso!', 'success', 'Atualizado');
    } else {
        delete data.id;
        const result = await API.createProduct(data);
        if (!result.success) {
            showToast(result.error, 'error', 'Erro ao adicionar');
            return;
        }
        showToast('Produto adicionado com sucesso!', 'success', 'Novo produto');
    }

    resetForm();
    await showAdminPanel();
}

function resetForm() {
    document.getElementById('product-form').reset();
    document.getElementById('product-active').checked = true;
    document.getElementById('product-stock-status').value = 'available';
    document.getElementById('product-stock-quantity').value = '1';
    document.getElementById('product-low-stock-alert').value = '1';
    document.getElementById('product-weight-grams').value = '100';
    document.getElementById('product-height-cm').value = '2.00';
    document.getElementById('product-width-cm').value = '10.00';
    document.getElementById('product-length-cm').value = '15.00';
    document.getElementById('product-shipping-profile').value = 'default';
    setProductGalleryImages([]);
    document.getElementById('form-title').textContent = 'âž• Adicionar Novo Produto';
    editingId = null;
    renderProductFormPreview();
}

function editProduct(id) {
    const product = adminProducts.find(p => p.id === Number(id));
    if (!product) return;
    
    editingId = id;
    document.getElementById('form-title').textContent = 'âœï¸ Editar Produto';
    
    document.getElementById('product-id').value = id;
    document.getElementById('product-name').value = product.name;
    document.getElementById('product-category').value = product.category;
    document.getElementById('product-price').value = product.price;
    document.getElementById('product-old-price').value = product.oldPrice || '';
    document.getElementById('product-sku').value = product.sku || '';
    document.getElementById('product-icon').value = product.icon || '';
    document.getElementById('product-badge').value = product.badge || '';
    document.getElementById('product-active').checked = product.is_active !== false;
    document.getElementById('product-stock-status').value = product.stock_status || 'available';
    document.getElementById('product-stock-quantity').value = product.stock_quantity ?? 0;
    document.getElementById('product-low-stock-alert').value = product.low_stock_alert ?? 1;
    document.getElementById('product-weight-grams').value = product.weight_grams ?? 100;
    document.getElementById('product-height-cm').value = product.height_cm ?? 2;
    document.getElementById('product-width-cm').value = product.width_cm ?? 10;
    document.getElementById('product-length-cm').value = product.length_cm ?? 15;
    document.getElementById('product-shipping-profile').value = product.shipping_profile || 'default';
    document.getElementById('product-description').value = product.description;
    document.getElementById('product-features').value = (product.features || []).map(f => f.replace(/^âœ“\s*/, '')).join('\n');
    setProductGalleryImages(
        Array.isArray(product.images) && product.images.length
            ? product.images
            : (product.image ? [product.image] : [])
    );
    renderProductFormPreview();
    
    // Scroll para o form
    document.getElementById('product-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function deleteProduct(id) {
    showConfirmModal(
        'Excluir Produto',
        'Tem certeza que deseja excluir este produto? Esta aÃ§Ã£o nÃ£o pode ser desfeita.',
        async () => {
            const result = await API.deleteProduct(id);
            if (!result.success) {
                showToast(result.error, 'error', 'Erro ao excluir');
                return;
            }
            await showAdminPanel();
            showToast('Produto excluÃ­do', 'info', 'Removido');
        }
    );
}

function confirmClearCatalog() {
    showConfirmModal(
        'Limpar Catalogo',
        'Esta acao apaga todos os produtos do catalogo. Clique em Confirmar e digite LIMPAR CATALOGO para continuar.',
        async () => {
            const typed = window.prompt('Digite LIMPAR CATALOGO para confirmar a limpeza do catalogo:');
            if (typed !== 'LIMPAR CATALOGO') {
                showToast('Confirmacao incorreta. O catalogo foi preservado.', 'info', 'Acao cancelada');
                return;
            }

            const result = await API.deleteAllProducts(typed);
            if (!result.success) {
                showToast(result.error || 'Erro ao limpar catalogo', 'error', 'Limpeza falhou');
                return;
            }

            adminProducts = [];
            apiProductsCache = [];
            apiLoaded = false;
            renderAdminProducts();
            await updateStats();
            showToast(`${result.data.deleted || 0} produtos removidos.`, 'success', 'Catalogo limpo');
        }
    );
}

// ============================================
// LISTA DE PRODUTOS
// ============================================

function renderAdminProducts() {
    const container = document.getElementById('admin-products-list');
    let products = [...adminProducts];
    
    // Aplica filtro
    if (currentFilter === 'custom') {
        products = products.filter(p => p.custom);
    } else if (currentFilter === 'inactive') {
        products = products.filter(p => p.is_active === false);
    } else if (currentFilter === 'low_stock') {
        products = products.filter(p => p.stock_is_low);
    } else if (currentFilter === 'out_of_stock') {
        products = products.filter(p => p.stock_status === 'out_of_stock');
    } else if (currentFilter !== 'all') {
        products = products.filter(p => p.category === currentFilter);
    }
    
    // Aplica busca
    if (currentSearch) {
        const search = currentSearch.toLowerCase();
        products = products.filter(p => 
            p.name.toLowerCase().includes(search) ||
            p.description.toLowerCase().includes(search)
        );
    }
    
    if (products.length === 0) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">ðŸ“¦</div>
                <p>Nenhum produto encontrado</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = products.map(p => {
        const thumbHTML = p.image ? 
            `<img src="${p.image}" alt="${p.name}" onerror="this.style.display='none'; this.parentElement.innerHTML='${p.icon || 'ðŸ’Ž'}';">` :
            (p.icon || 'ðŸ’Ž');
        
        const badgeHTML = p.custom
            ? '<span class="badge-mini custom">NOVO</span>'
            : '<span class="badge-mini fixed">CATÃLOGO</span>';
        
        const storefrontBadgeLabel = badgeLabel(p.badge);
        const storefrontBadge = storefrontBadgeLabel
            ? `<span class="badge-mini storefront ${p.badge}">${storefrontBadgeLabel}</span>`
            : '';
        const activeBadge = p.is_active === false
            ? '<span class="badge-mini inactive">INATIVO</span>'
            : '<span class="badge-mini active">ATIVO</span>';
        const stockBadge = `<span class="badge-mini stock ${p.stock_status || 'available'}">${stockLabel(p.stock_status)}</span>`;
        const lowStockBadge = p.stock_is_low ? '<span class="badge-mini stock low">BAIXO</span>' : '';
        const stockMeta = `SKU ${escapeHTML(p.sku || '-')} | Estoque ${p.stock_quantity ?? 0}`;
        const shippingMeta = `${p.weight_grams ?? 100}g | ${p.length_cm ?? 15} x ${p.width_cm ?? 10} x ${p.height_cm ?? 2} cm`;
        
        return `
            <div class="admin-product-item">
                <div class="admin-product-thumb">${thumbHTML}</div>
                <div class="admin-product-info">
                    <h4>${p.name}</h4>
                    <p>${stockMeta}</p>
                    <p>${shippingMeta}</p>
                    <div class="product-meta">
                        <span class="admin-product-price">${formatPrice(p.price)}</span>
                        ${storefrontBadge}
                        ${activeBadge}
                        ${stockBadge}
                        ${lowStockBadge}
                        ${badgeHTML}
                    </div>
                </div>
                <div class="admin-product-actions">
                    <button class="btn-edit" onclick="editProduct(${p.id})" title="Editar">Editar</button>
                    <button class="btn-delete" onclick="deleteProduct(${p.id})" title="Excluir">Excluir</button>
                </div>
            </div>
        `;
    }).join('');
}

async function updateStats() {
    const all = adminProducts;
    const custom = all.filter(p => p.custom);
    const categories = new Set(all.map(p => p.category)).size;
    const avgPrice = all.length > 0 ? all.reduce((sum, p) => sum + p.price, 0) / all.length : 0;
    
    document.getElementById('stat-total').textContent = all.length;
    document.getElementById('stat-custom').textContent = custom.length;
    document.getElementById('stat-categories').textContent = categories;
    document.getElementById('stat-avg-price').textContent = formatPrice(avgPrice);
    document.getElementById('stat-orders-pending').textContent =
        adminOrders.filter(order => ['pending', 'payment_pending'].includes(order.status)).length;
    document.getElementById('stat-orders-paid').textContent =
        adminOrders.filter(order => ['paid', 'processing', 'shipped', 'delivered'].includes(order.status)).length;
}

// ============================================
// PEDIDOS
// ============================================

function orderStatusOptions(selectedStatus = '') {
    const statuses = ['pending', 'payment_pending', 'paid', 'processing', 'shipped', 'delivered', 'canceled', 'failed'];
    return statuses.map(status => `
        <option value="${status}" ${status === selectedStatus ? 'selected' : ''}>${orderStatusLabel(status)}</option>
    `).join('');
}
function orderStatusLabel(status) {
    return {
        pending: 'Pendente',
        payment_pending: 'Aguardando pagamento',
        paid: 'Pago',
        processing: 'Em separacao',
        shipped: 'Enviado',
        delivered: 'Entregue',
        canceled: 'Cancelado',
        failed: 'Falhou',
    }[status] || status || 'Pendente';
}

function formatOrderDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function orderItemsSummary(order) {
    const items = Array.isArray(order.items) ? order.items : [];
    if (!items.length) return 'Sem itens';
    return items
        .slice(0, 3)
        .map(item => `${item.quantity || 1}x ${item.name || `Produto ${item.id}`}`)
        .join(', ') + (items.length > 3 ? ` +${items.length - 3}` : '');
}

function orderEventsTimeline(order) {
    const events = Array.isArray(order.events) ? order.events : [];
    if (!events.length) return '';
    return `
        <div class="order-events-timeline">
            ${events.slice(-4).map(event => `
                <div class="order-event-row">
                    <span>${escapeHTML(event.message || orderStatusLabel(event.status))}</span>
                    <small>${formatOrderDate(event.created_at)}</small>
                </div>
            `).join('')}
        </div>
    `;
}

function orderTrackingSummary(order) {
    if (!order.tracking_code && !order.tracking_carrier) return '';
    return `
        <div class="order-tracking-summary">
            <span>Rastreio: ${escapeHTML(order.tracking_code || '-')}</span>
            <small>${escapeHTML(order.tracking_carrier || 'Transportadora nao informada')}</small>
        </div>
    `;
}

async function loadAdminOrders() {
    const result = await API.getOrders();
    if (!result.success) {
        showToast(result.error || 'Falha ao carregar pedidos', 'error');
        return;
    }
    adminOrders = result.data || [];
    renderAdminOrders();
}

function renderAdminOrders() {
    const container = document.getElementById('admin-orders-list');
    if (!container) return;

    let orders = [...adminOrders];
    if (currentOrderFilter !== 'all') {
        orders = orders.filter(order => order.status === currentOrderFilter);
    }
    if (currentOrderSearch) {
        const search = currentOrderSearch.toLowerCase();
        orders = orders.filter(order =>
            String(order.id || '').toLowerCase().includes(search) ||
            String(order.customer_name || '').toLowerCase().includes(search) ||
            String(order.customer_email || '').toLowerCase().includes(search)
        );
    }

    if (!orders.length) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">PED</div>
                <p>Nenhum pedido encontrado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = orders.map(order => `
        <article class="admin-order-item">
            <div class="order-main">
                <div>
                    <strong>${escapeHTML(order.id)}</strong>
                    <span>${formatOrderDate(order.created_at)}</span>
                </div>
                <span class="order-status ${order.status}">${orderStatusLabel(order.status)}</span>
            </div>
            <div class="order-customer">
                <strong>${escapeHTML(order.customer_name || 'Cliente')}</strong>
                <span>${escapeHTML(order.customer_email || '')}</span>
                <span>${escapeHTML(order.customer_phone || '')}</span>
            </div>
            <p class="order-items-summary">${escapeHTML(orderItemsSummary(order))}</p>
            ${orderTrackingSummary(order)}
            ${orderEventsTimeline(order)}
            <div class="order-footer">
                <strong>${formatPrice(order.total || 0)}</strong>
                <button class="btn btn-outline order-manage-btn" type="button" onclick="openOrderModal('${escapeJSString(order.id)}')">Gerenciar</button>
            </div>
        </article>
    `).join('');
}

function orderModalItemsHTML(order) {
    const items = Array.isArray(order.items) ? order.items : [];
    if (!items.length) return '<p class="empty-admin-list">Nenhum item registrado.</p>';
    return items.map(item => `
        <div class="order-modal-row">
            <span>${escapeHTML(item.quantity || 1)}x ${escapeHTML(item.name || `Produto ${item.id || ''}`)}</span>
            <strong>${formatPrice((item.price || 0) * (item.quantity || 1))}</strong>
        </div>
    `).join('');
}

function orderModalEventsHTML(order) {
    const events = Array.isArray(order.events) ? [...order.events].reverse() : [];
    if (!events.length) return '<p class="empty-admin-list">Nenhum historico registrado.</p>';
    return events.map(event => `
        <div class="order-modal-event">
            <span>${escapeHTML(event.message || orderStatusLabel(event.status))}</span>
            <small>${formatOrderDate(event.created_at)}</small>
        </div>
    `).join('');
}

function openOrderModal(orderId) {
    const order = adminOrders.find(item => item.id === orderId);
    if (!order) return;
    activeOrderModalId = orderId;
    document.getElementById('order-modal-title').textContent = `Pedido ${order.id}`;
    document.getElementById('order-modal-subtitle').textContent = `${order.customer_name || 'Cliente'} - ${formatOrderDate(order.created_at)}`;
    document.getElementById('order-modal-status').innerHTML = orderStatusOptions(order.status);
    document.getElementById('order-modal-tracking-code').value = order.tracking_code || '';
    document.getElementById('order-modal-tracking-carrier').value = order.tracking_carrier || '';
    document.getElementById('order-modal-summary').innerHTML = `
        <div><span>Cliente</span><strong>${escapeHTML(order.customer_name || '-')}</strong></div>
        <div><span>E-mail</span><strong>${escapeHTML(order.customer_email || '-')}</strong></div>
        <div><span>Total</span><strong>${formatPrice(order.total || 0)}</strong></div>
        <div><span>Frete</span><strong>${escapeHTML(order.shipping_company || order.shipping_service || order.shipping_provider || 'Frete')}</strong></div>
        <div><span>Destino</span><strong>${escapeHTML([order.address_city, order.address_state].filter(Boolean).join('/') || '-')}</strong></div>
    `;
    document.getElementById('order-modal-items').innerHTML = orderModalItemsHTML(order);
    document.getElementById('order-modal-events').innerHTML = orderModalEventsHTML(order);
    document.getElementById('order-modal').classList.add('active');
    document.getElementById('order-modal').setAttribute('aria-hidden', 'false');
}

function closeOrderModal() {
    activeOrderModalId = null;
    document.getElementById('order-modal')?.classList.remove('active');
    document.getElementById('order-modal')?.setAttribute('aria-hidden', 'true');
}

async function changeOrderStatus(orderId, status, payload = {}) {
    const result = await API.updateOrderStatus(orderId, status, payload);
    if (!result.success) {
        showToast(result.error || 'Erro ao atualizar pedido', 'error');
        return false;
    }
    const index = adminOrders.findIndex(order => order.id === orderId);
    if (index >= 0) adminOrders[index] = result.data;
    renderAdminOrders();
    updateStats();
    showToast('Status do pedido atualizado', 'success');
    return true;
}

async function saveOrderModal(event) {
    event.preventDefault();
    if (!activeOrderModalId) return;
    const submit = document.getElementById('order-modal-submit');
    const status = document.getElementById('order-modal-status').value;
    const payload = {
        tracking_code: document.getElementById('order-modal-tracking-code').value.trim(),
        tracking_carrier: document.getElementById('order-modal-tracking-carrier').value.trim(),
    };
    submit.disabled = true;
    submit.textContent = 'Salvando...';
    const success = await changeOrderStatus(activeOrderModalId, status, payload);
    submit.disabled = false;
    submit.textContent = 'Salvar pedido';
    if (success) closeOrderModal();
}

// ============================================
// FILTROS
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    if (isAuthenticated()) {
        const result = await API.getMe();
        if (result.success && result.data.is_admin) {
            await showAdminPanel();
        } else {
            sessionStorage.removeItem('vj_admin_authenticated');
            document.getElementById('login-screen').style.display = 'flex';
        }
    } else {
        document.getElementById('login-screen').style.display = 'flex';
    }
    
    window.addEventListener('hashchange', () => {
        if (document.getElementById('admin-panel')?.style.display !== 'none') {
            switchAdminPage(adminPageFromHash(), { updateHash: false });
        }
    });

    // Filtros
    document.querySelectorAll('.admin-filters .filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.admin-filters .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderAdminProducts();
        });
    });
    
    // Search
    const search = document.getElementById('admin-search');
    if (search) {
        let timeout;
        search.addEventListener('input', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                currentSearch = e.target.value;
                renderAdminProducts();
            }, 300);
        });
    }

    const ordersSearch = document.getElementById('orders-search');
    if (ordersSearch) {
        let orderTimeout;
        ordersSearch.addEventListener('input', (e) => {
            clearTimeout(orderTimeout);
            orderTimeout = setTimeout(() => {
                currentOrderSearch = e.target.value;
                renderAdminOrders();
            }, 300);
        });
    }

    const ordersFilter = document.getElementById('orders-filter');
    if (ordersFilter) {
        ordersFilter.addEventListener('change', (e) => {
            currentOrderFilter = e.target.value;
            renderAdminOrders();
        });
    }
});

// ============================================
// EXPORT / IMPORT
// ============================================

function exportProducts() {
    const dataStr = JSON.stringify(adminProducts, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vj-produtos-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showToast('Produtos exportados!', 'success', 'ðŸ“¥ Download');
}

function importFilePath(file) {
    return String(file.webkitRelativePath || file.name || '').replaceAll('\\', '/').replace(/^\/+/, '');
}

function relativeToImportRoot(path, root) {
    if (!root || root === '.') return path;
    return path.startsWith(`${root}/`) ? path.slice(root.length + 1) : path;
}

function manifestImagePath(image) {
    if (typeof image === 'string') {
        return image.replaceAll('\\', '/').replace(/^\/+/, '');
    }
    if (image && typeof image === 'object' && image.file) {
        return String(image.file).replaceAll('\\', '/').replace(/^\/+/, '');
    }
    return '';
}

function manifestProductTitle(product, index) {
    return String(product.name || product.title || product.nome || `Produto ${index + 1}`).trim();
}

function manifestProductPrice(product) {
    return product.price || product.primary_price || product.preco || '';
}

function manifestProductFolder(product) {
    return String(product.folder || product.source_folder || '').replaceAll('\\', '/').replace(/^\/+|\/+$/g, '');
}

async function analyzeImportFolder(files) {
    const paths = files.map(importFilePath);
    const manifestFiles = files.filter(file => importFilePath(file).split('/').pop() === 'manifest.json');
    const errors = [];
    const warnings = [];

    if (manifestFiles.length !== 1) {
        errors.push(
            manifestFiles.length === 0
                ? 'Nenhum manifest.json foi encontrado na pasta selecionada.'
                : 'Mais de um manifest.json foi encontrado. Selecione apenas uma pasta de catalogo.'
        );
        return { errors, warnings, products: [], files, imageCount: 0 };
    }

    const manifestPath = importFilePath(manifestFiles[0]);
    const importRoot = manifestPath.includes('/')
        ? manifestPath.split('/').slice(0, -1).join('/')
        : '.';
    const relativeFiles = new Set(paths.map(path => relativeToImportRoot(path, importRoot)));

    let manifest;
    try {
        manifest = JSON.parse(await manifestFiles[0].text());
    } catch (error) {
        errors.push(`manifest.json invalido: ${error.message}`);
        return { errors, warnings, products: [], files, imageCount: 0 };
    }

    const products = Array.isArray(manifest.products) ? manifest.products : [];
    if (products.length === 0) {
        errors.push('O manifest.json precisa conter uma lista products com pelo menos um produto.');
    }

    let imageCount = 0;
    const previewProducts = products.map((product, index) => {
        const title = manifestProductTitle(product, index);
        const price = manifestProductPrice(product);
        const category = product.category || product.category_id || product.categoria || '';
        const description = product.description || product.descricao || '';
        const folder = manifestProductFolder(product);
        const rawImages = Array.isArray(product.images) ? product.images : [];
        const imagePaths = rawImages.map(manifestImagePath).filter(Boolean);
        const missingImages = [];

        if (!product.name && !product.title && !product.nome) {
            errors.push(`Produto #${index + 1} esta sem nome.`);
        }
        if (!String(price).trim()) {
            errors.push(`Produto "${title}" esta sem preco.`);
        }
        if (!String(category).trim()) {
            warnings.push(`Produto "${title}" esta sem categoria; o importador vai tentar inferir.`);
        }
        if (!String(description).trim()) {
            warnings.push(`Produto "${title}" esta sem descricao; o importador vai usar o nome.`);
        }
        if (imagePaths.length === 0) {
            warnings.push(`Produto "${title}" nao possui imagens no manifest.`);
        }

        imagePaths.forEach(imagePath => {
            const folderPath = folder ? `${folder}/${imagePath}` : imagePath;
            if (!relativeFiles.has(imagePath) && !relativeFiles.has(folderPath)) {
                missingImages.push(imagePath);
                errors.push(`Imagem nao encontrada para "${title}": ${imagePath}`);
            }
        });

        imageCount += imagePaths.length;
        return {
            title,
            price,
            category,
            description,
            folder,
            imageCount: imagePaths.length,
            missingImages,
            status: missingImages.length ? 'error' : 'ok',
        };
    });

    return {
        errors,
        warnings,
        products: previewProducts,
        files,
        imageCount,
        manifestPath,
        importRoot,
    };
}

function renderImportPreview(state) {
    const container = document.getElementById('import-preview');
    const confirmButton = document.getElementById('import-confirm-btn');
    const clearButton = document.getElementById('import-clear-btn');
    if (!container || !confirmButton || !clearButton) return;

    importPreviewState = state;
    confirmButton.disabled = !state || state.errors.length > 0 || state.products.length === 0;
    clearButton.style.display = state ? 'inline-flex' : 'none';

    if (!state) {
        container.className = 'import-preview empty';
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">CSV</div>
                <p>Nenhuma pasta selecionada ainda.</p>
                <small>O preview vai validar manifest.json, produtos e imagens antes da importacao.</small>
            </div>
        `;
        return;
    }

    const statusClass = state.errors.length ? 'has-errors' : 'ready';
    const extraWarnings = Math.max(0, state.warnings.length - 8);
    const issueItems = [
        ...state.errors.map(error => ({ type: 'error', text: error })),
        ...state.warnings.slice(0, 8).map(warning => ({ type: 'warning', text: warning })),
    ];
    const productsHtml = state.products.slice(0, 12).map(product => `
        <div class="import-product-row ${product.status}">
            <div>
                <strong>${escapeCatalogValue(product.title)}</strong>
                <span>${escapeCatalogValue(product.category || 'Categoria pendente')}</span>
            </div>
            <div class="import-price">${escapeCatalogValue(String(product.price || 'Preco pendente'))}</div>
            <div class="import-count">${product.imageCount} img</div>
            <div><span class="import-row-status ${product.missingImages.length ? 'error' : 'ok'}">${product.missingImages.length ? 'Corrigir' : 'OK'}</span></div>
        </div>
    `).join('');

    container.className = `import-preview ${statusClass}`;
    container.innerHTML = `
        <div class="import-preview-header">
            <div>
                <span class="import-kicker">Preview da importacao</span>
                <h4>${state.errors.length ? 'A pasta precisa de ajustes' : 'Catalogo pronto para importar'}</h4>
            </div>
            <span class="import-status-pill ${statusClass}">
                ${state.errors.length ? `${state.errors.length} erro(s)` : 'Validado'}
            </span>
        </div>
        <div class="import-summary-grid">
            <div><strong>${state.products.length}</strong><span>Produtos</span></div>
            <div><strong>${state.imageCount}</strong><span>Imagens citadas</span></div>
            <div><strong>${state.files.length}</strong><span>Arquivos</span></div>
            <div><strong>${state.errors.length}</strong><span>Erros</span></div>
        </div>
        <div class="import-preview-status">
            <div>
                ${state.errors.length
                    ? '<strong>Corrija os erros antes de importar.</strong>'
                    : '<strong>Estrutura validada. Pronto para importar.</strong>'}
                <small>Manifest: ${escapeCatalogValue(state.manifestPath || 'manifest.json')}</small>
            </div>
        </div>
        ${issueItems.length ? `
            <div class="import-issues">
                ${issueItems.map(item => `
                    <div class="${item.type}">${escapeCatalogValue(item.text)}</div>
                `).join('')}
                ${extraWarnings ? `<small class="import-more">Mais ${extraWarnings} aviso(s) ocultos para manter o preview compacto.</small>` : ''}
            </div>
        ` : ''}
        <div class="import-products-card">
            <div class="import-products-head">
                <span>Produto</span>
                <span>Preco</span>
                <span>Fotos</span>
                <span>Status</span>
            </div>
            <div class="import-products-preview">
                ${productsHtml || '<p>Nenhum produto para mostrar.</p>'}
            </div>
        </div>
        ${state.products.length > 12 ? `<small class="import-more">Mostrando 12 de ${state.products.length} produtos.</small>` : ''}
    `;
}

async function handleImportFolderSelection(event) {
    const files = Array.from(event.target.files || []);
    importFolderFiles = files;
    if (files.length === 0) {
        renderImportPreview(null);
        return;
    }

    try {
        const state = await analyzeImportFolder(files);
        renderImportPreview(state);
        if (state.errors.length) {
            showToast('A pasta tem erros. Veja o preview antes de importar.', 'error', 'Validacao falhou');
        } else {
            showToast(`${state.products.length} produtos validados.`, 'success', 'Preview pronto');
        }
    } catch (error) {
        renderImportPreview({
            errors: [`Nao foi possivel validar a pasta: ${error.message}`],
            warnings: [],
            products: [],
            files,
            imageCount: 0,
        });
    }
}

function clearImportPreview() {
    importFolderFiles = [];
    importPreviewState = null;
    const input = document.getElementById('import-file');
    if (input) input.value = '';
    renderImportPreview(null);
}

async function confirmImportProducts() {
    if (!importPreviewState || importPreviewState.errors.length > 0 || importFolderFiles.length === 0) {
        showToast('Selecione uma pasta valida antes de importar', 'error', 'Importacao bloqueada');
        return;
    }

    await uploadValidatedImport(importFolderFiles);
}

async function uploadValidatedImport(files) {
    const storageStatus = await API.getStorageStatus();
    const isRemoteHost = !['localhost', '127.0.0.1', ''].includes(window.location.hostname);
    if (
        storageStatus.success &&
        isRemoteHost &&
        storageStatus.data.backend !== 'r2'
    ) {
        showToast(
            'Storage remoto nao esta usando R2. Configure STORAGE_BACKEND=r2 no Render antes de importar.',
            'error',
            'Importacao bloqueada'
        );
        return;
    }

    showToast(
        `Enviando ${files.length} arquivos...`,
        'info',
        'Importando catalogo'
    );
    const result = await API.importProductFolder(files);

    if (!result.success) {
        showToast(result.error, 'error', 'Erro na importacao');
        return;
    }

    clearImportPreview();
    await showAdminPanel();
    showToast(
        `${result.data.products} produtos processados, ${result.data.images} imagens.`,
        'success',
        'Catalogo importado'
    );
}

async function legacyImportProducts(event) {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    const hasManifest = files.some(file => {
        const path = file.webkitRelativePath || file.name;
        return path.replaceAll('\\', '/').split('/').pop() === 'manifest.json';
    });
    if (!hasManifest) {
        showToast(
            'Selecione a pasta completa que contÃ©m manifest.json',
            'error',
            'Pasta invÃ¡lida'
        );
        event.target.value = '';
        return;
    }

    showToast(
        `Enviando ${files.length} arquivos...`,
        'info',
        'Importando catÃ¡logo'
    );
    const result = await API.importProductFolder(files);
    event.target.value = '';

    if (!result.success) {
        showToast(result.error, 'error', 'Erro na importaÃ§Ã£o');
        return;
    }

    await showAdminPanel();
    showToast(
        `${result.data.products} produtos processados, ${result.data.images} imagens.`,
        'success',
        'CatÃ¡logo importado'
    );
}

// ============================================
// MODAL DE CONFIRMAÃ‡ÃƒO
// ============================================

// ============================================
// GERADOR DE CATALOGO PDF
// ============================================

function setupCatalogPdfDropzone() {
    const dropzone = document.getElementById('catalog-pdf-dropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, event => {
            event.preventDefault();
            event.stopPropagation();
            dropzone.classList.add('dragging');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, event => {
            event.preventDefault();
            event.stopPropagation();
            dropzone.classList.remove('dragging');
        });
    });

    dropzone.addEventListener('drop', event => {
        addCatalogPdfFiles(Array.from(event.dataTransfer.files || []));
    });
}

function handleCatalogPdfFiles(event) {
    addCatalogPdfFiles(Array.from(event.target.files || []));
    event.target.value = '';
}

function catalogTitleFromFilename(filename) {
    return filename
        .replace(/\.[^.]+$/, '')
        .replace(/^\d+[-_\s]*/, '')
        .replace(/[-_]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .replace(/\b\w/g, letter => letter.toUpperCase()) || 'Produto VJ';
}

function addCatalogPdfFiles(files) {
    const validFiles = files.filter(file => file.type.startsWith('image/'));
    if (validFiles.length !== files.length) {
        showToast('Alguns arquivos foram ignorados porque nao sao imagens', 'info');
    }

    validFiles.forEach(file => {
        catalogPdfItems.push({
            file,
            previewUrl: URL.createObjectURL(file),
            name: catalogTitleFromFilename(file.name),
            price: '',
            category: 'Semijoias',
            description: '',
        });
    });

    renderCatalogPdfItems();
}

function clearCatalogPdfItems() {
    catalogPdfItems.forEach(item => URL.revokeObjectURL(item.previewUrl));
    catalogPdfItems = [];
    renderCatalogPdfItems();
}

function updateCatalogPdfItem(index, field, value) {
    if (!catalogPdfItems[index]) return;
    catalogPdfItems[index][field] = value;
}

function moveCatalogPdfItem(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= catalogPdfItems.length) return;
    const [item] = catalogPdfItems.splice(index, 1);
    catalogPdfItems.splice(target, 0, item);
    renderCatalogPdfItems();
}

function removeCatalogPdfItem(index) {
    const [item] = catalogPdfItems.splice(index, 1);
    if (item) URL.revokeObjectURL(item.previewUrl);
    renderCatalogPdfItems();
}

function escapeCatalogValue(value) {
    return String(value || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function renderCatalogPdfItems() {
    const container = document.getElementById('catalog-pdf-products');
    if (!container) return;

    if (catalogPdfItems.length === 0) {
        container.innerHTML = `
            <div class="empty-admin-list">
                <div class="icon">PDF</div>
                <p>Nenhuma imagem adicionada ainda</p>
            </div>
        `;
        return;
    }

    container.innerHTML = catalogPdfItems.map((item, index) => `
        <div class="catalog-product-row">
            <div class="catalog-product-preview">
                <img src="${item.previewUrl}" alt="${escapeCatalogValue(item.name)}">
            </div>
            <div class="catalog-product-fields">
                <div class="form-group">
                    <label>Nome</label>
                    <input type="text" value="${escapeCatalogValue(item.name)}" oninput="updateCatalogPdfItem(${index}, 'name', this.value)">
                </div>
                <div class="form-group">
                    <label>Preco</label>
                    <input type="text" value="${escapeCatalogValue(item.price)}" placeholder="199,00" oninput="updateCatalogPdfItem(${index}, 'price', this.value)">
                </div>
                <div class="form-group">
                    <label>Categoria</label>
                    <input type="text" value="${escapeCatalogValue(item.category)}" placeholder="Colares" oninput="updateCatalogPdfItem(${index}, 'category', this.value)">
                </div>
                <div class="form-group">
                    <label>Arquivo</label>
                    <input type="text" value="${escapeCatalogValue(item.file.name)}" disabled>
                </div>
                <div class="form-group wide">
                    <label>Descricao</label>
                    <textarea oninput="updateCatalogPdfItem(${index}, 'description', this.value)" placeholder="Banho 18K, garantia, medidas...">${escapeCatalogValue(item.description)}</textarea>
                </div>
            </div>
            <div class="catalog-product-controls">
                <button type="button" onclick="moveCatalogPdfItem(${index}, -1)" title="Subir">â†‘</button>
                <button type="button" onclick="moveCatalogPdfItem(${index}, 1)" title="Descer">â†“</button>
                <button type="button" class="danger" onclick="removeCatalogPdfItem(${index})" title="Remover">Ã—</button>
            </div>
        </div>
    `).join('');
}

async function handleCatalogPdfSubmit(event) {
    event.preventDefault();
    if (catalogPdfItems.length === 0) {
        showToast('Adicione pelo menos uma imagem', 'error', 'Catalogo vazio');
        return;
    }

    const submit = document.getElementById('catalog-pdf-submit');
    submit.disabled = true;
    submit.textContent = 'Gerando PDF...';

    const formData = new FormData();
    catalogPdfItems.forEach(item => formData.append('images', item.file, item.file.name));
    formData.append('names', catalogPdfItems.map(item => item.name).join('|'));
    formData.append('prices', catalogPdfItems.map(item => item.price).join('|'));
    formData.append('categories', catalogPdfItems.map(item => item.category).join('|'));
    formData.append('descriptions', catalogPdfItems.map(item => item.description).join('|'));
    formData.append('catalog_title', document.getElementById('catalog-pdf-title').value);
    formData.append('collection', document.getElementById('catalog-pdf-collection').value);
    formData.append('slogan', document.getElementById('catalog-pdf-slogan').value);
    formData.append('contact', document.getElementById('catalog-pdf-contact').value);
    formData.append('coupon', document.getElementById('catalog-pdf-coupon').value);
    formData.append('products_per_page', document.getElementById('catalog-pdf-products-per-page').value);
    formData.append('output_filename', document.getElementById('catalog-pdf-filename').value);

    const result = await API.generateCatalogPdf(formData);
    submit.disabled = false;
    submit.textContent = 'Gerar e baixar PDF';

    if (!result.success) {
        showToast(result.error || 'Erro ao gerar PDF', 'error', 'Falha no catalogo');
        return;
    }

    const url = URL.createObjectURL(result.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    showToast(
        `${result.products || catalogPdfItems.length} produtos em ${result.pages || '?'} paginas.`,
        'success',
        'PDF gerado'
    );
}

function showConfirmModal(title, message, onConfirm) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-modal').classList.add('active');
    
    const yesBtn = document.getElementById('confirm-yes');
    const newYesBtn = yesBtn.cloneNode(true);
    yesBtn.parentNode.replaceChild(newYesBtn, yesBtn);
    
    newYesBtn.addEventListener('click', () => {
        closeConfirmModal();
        onConfirm();
    });
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.remove('active');
}
