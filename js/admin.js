// ============================================
// ADMIN - VJ Semijoias
// Gerenciamento de produtos via API
// ============================================

let currentFilter = 'all';
let currentSearch = '';
let editingId = null;
let adminProducts = [];
let imageUploadInitialized = false;

// ============================================
// AUTENTICAÇÃO
// ============================================

function isAuthenticated() {
    return API.isLoggedIn();
}

async function handleAdminLogin(event) {
    event.preventDefault();
    const password = document.getElementById('admin-password').value;

    const result = await API.adminLogin(password);
    if (result.success) {
        await showAdminPanel();
        showToast('Bem-vinda ao painel admin!', 'success', 'Login realizado');
    } else {
        showToast(result.error || 'Não foi possível entrar', 'error', 'Acesso negado');
        document.getElementById('admin-password').value = '';
        document.getElementById('admin-password').focus();
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
    const result = await API.getProducts();
    if (!result.success) {
        showToast(result.error || 'Falha ao carregar produtos', 'error');
        logout();
        return;
    }
    adminProducts = result.data;
    apiProductsCache = result.data;
    apiLoaded = true;
    renderAdminProducts();
    await updateStats();
    if (!imageUploadInitialized) {
        setupImageUpload();
        imageUploadInitialized = true;
    }
}

// ============================================
// UPLOAD DE IMAGEM
// ============================================

function setupImageUpload() {
    const uploadArea = document.getElementById('image-upload');
    const input = document.getElementById('image-input');
    
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
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleImageFile(files[0]);
        }
    });
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        handleImageFile(file);
    }
}

function handleImageFile(file) {
    if (!file.type.startsWith('image/')) {
        showToast('Por favor, selecione uma imagem', 'error', 'Arquivo inválido');
        return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
        showToast('Imagem muito grande (máx 5MB)', 'error', 'Arquivo grande');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        showImagePreview(dataUrl);
        document.getElementById('image-url').value = dataUrl;
    };
    reader.readAsDataURL(file);
}

function showImagePreview(src) {
    const preview = document.getElementById('image-preview');
    preview.innerHTML = `<img src="${src}" alt="Preview">`;
}

function syncImageFromUrl() {
    const url = document.getElementById('image-url').value;
    if (url) {
        showImagePreview(url);
    }
}

// ============================================
// FORMULÁRIO
// ============================================

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
        .map(f => f.startsWith('✓') ? f : `✓ ${f}`);
    
    // Pega imagem do preview se houver
    const previewImg = document.querySelector('#image-preview img');
    if (previewImg) {
        data.image = previewImg.src;
    } else if (data.image) {
        // Mantém o que estava na URL
    } else {
        // Sem imagem: usa o ícone
        data.image = null;
    }
    
    // Define ícone padrão se não informado
    if (!data.icon) {
        const iconMap = {
            'brincos': '✨',
            'colares': '📿',
            'pulseiras': '⚜️',
            'aneis': '💍',
            'pingentes': '🔮',
            'chaveiros': '🔑',
            'conjuntos': '🎁'
        };
        data.icon = iconMap[data.category] || '💎';
    }
    
    // Converte preços
    data.price = parseFloat(data.price) || 0;
    data.oldPrice = data.oldPrice ? parseFloat(data.oldPrice) : null;
    
    // Converte badge
    if (!data.badge) data.badge = null;
    
    // Define categoryName
    const categoryMap = {
        'brincos': 'Brincos',
        'colares': 'Colares',
        'pulseiras': 'Pulseiras',
        'aneis': 'Anéis',
        'pingentes': 'Pingentes',
        'chaveiros': 'Chaveiros',
        'conjuntos': 'Conjuntos'
    };
    data.categoryName = categoryMap[data.category] || data.category;
    
    // Validações
    if (!data.name || !data.category || !data.price || !data.description) {
        showToast('Preencha todos os campos obrigatórios', 'error', 'Campos vazios');
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
    document.getElementById('image-preview').innerHTML = `
        <div class="upload-placeholder">
            <div style="font-size: 3rem;">📷</div>
            <p>Clique ou arraste uma imagem</p>
            <small>PNG, JPG até 5MB</small>
        </div>
    `;
    document.getElementById('form-title').textContent = '➕ Adicionar Novo Produto';
    editingId = null;
}

function editProduct(id) {
    const product = adminProducts.find(p => p.id === Number(id));
    if (!product) return;
    
    editingId = id;
    document.getElementById('form-title').textContent = '✏️ Editar Produto';
    
    document.getElementById('product-id').value = id;
    document.getElementById('product-name').value = product.name;
    document.getElementById('product-category').value = product.category;
    document.getElementById('product-price').value = product.price;
    document.getElementById('product-old-price').value = product.oldPrice || '';
    document.getElementById('product-icon').value = product.icon || '';
    document.getElementById('product-badge').value = product.badge || '';
    document.getElementById('product-description').value = product.description;
    document.getElementById('product-features').value = (product.features || []).map(f => f.replace(/^✓\s*/, '')).join('\n');
    document.getElementById('image-url').value = product.image || '';
    
    if (product.image) {
        showImagePreview(product.image);
    }
    
    // Scroll para o form
    document.getElementById('product-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function deleteProduct(id) {
    showConfirmModal(
        'Excluir Produto',
        'Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.',
        async () => {
            const result = await API.deleteProduct(id);
            if (!result.success) {
                showToast(result.error, 'error', 'Erro ao excluir');
                return;
            }
            await showAdminPanel();
            showToast('Produto excluído', 'info', 'Removido');
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
                <div class="icon">📦</div>
                <p>Nenhum produto encontrado</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = products.map(p => {
        const thumbHTML = p.image ? 
            `<img src="${p.image}" alt="${p.name}" onerror="this.style.display='none'; this.parentElement.innerHTML='${p.icon || '💎'}';">` :
            (p.icon || '💎');
        
        const badgeHTML = p.custom
            ? '<span class="badge-mini custom">NOVO</span>'
            : '<span class="badge-mini fixed">CATÁLOGO</span>';
        
        const novoBadge = p.badge === 'new' ? '<span class="badge-mini" style="background: #28a745;">NOVO</span>' : '';
        const saleBadge = p.badge === 'sale' ? '<span class="badge-mini" style="background: #dc3545;">OFERTA</span>' : '';
        
        return `
            <div class="admin-product-item">
                <div class="admin-product-thumb">${thumbHTML}</div>
                <div class="admin-product-info">
                    <h4>${p.name}</h4>
                    <div class="product-meta">
                        <span class="admin-product-price">${formatPrice(p.price)}</span>
                        ${novoBadge}
                        ${saleBadge}
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
            API.logout();
            document.getElementById('login-screen').style.display = 'flex';
        }
    } else {
        document.getElementById('login-screen').style.display = 'flex';
    }
    
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
    showToast('Produtos exportados!', 'success', '📥 Download');
}

async function importProducts(event) {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    const hasManifest = files.some(file => {
        const path = file.webkitRelativePath || file.name;
        return path.replaceAll('\\', '/').split('/').pop() === 'manifest.json';
    });
    if (!hasManifest) {
        showToast(
            'Selecione a pasta completa que contém manifest.json',
            'error',
            'Pasta inválida'
        );
        event.target.value = '';
        return;
    }

    showToast(
        `Enviando ${files.length} arquivos...`,
        'info',
        'Importando catálogo'
    );
    const result = await API.importProductFolder(files);
    event.target.value = '';

    if (!result.success) {
        showToast(result.error, 'error', 'Erro na importação');
        return;
    }

    await showAdminPanel();
    showToast(
        `${result.data.products} produtos processados, ${result.data.images} imagens.`,
        'success',
        'Catálogo importado'
    );
}

// ============================================
// MODAL DE CONFIRMAÇÃO
// ============================================

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
