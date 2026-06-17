// ============================================
// CATALOGO DE PRODUTOS - VJ SEMIJOIAS
// Usa a API como fonte principal e o service worker como cache offline.
// ============================================

const CATEGORIES = [
    { id: "all", name: "Todos", icon: "💎" },
    { id: "brincos", name: "Brincos", icon: "✨" },
    { id: "colares", name: "Colares", icon: "📿" },
    { id: "pulseiras", name: "Pulseiras", icon: "⚜️" },
    { id: "aneis", name: "Aneis", icon: "💍" },
    { id: "pingentes", name: "Pingentes", icon: "🔮" },
    { id: "chaveiros", name: "Chaveiros", icon: "🔑" }
];

// Cache em memoria dos produtos recebidos da API. Quando offline, o service
// worker pode responder esta mesma chamada com o ultimo catalogo salvo.
let apiProductsCache = [];
let apiLoaded = false;

function normalizeProducts(data) {
    return Array.isArray(data) ? data : [];
}

function getCustomProducts() {
    try {
        const stored = localStorage.getItem('vj_custom_products');
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function getAllProducts() {
    return [...apiProductsCache, ...getCustomProducts()];
}

function getProductById(id) {
    const productId = parseInt(id);
    const fromApi = apiProductsCache.find(p => p.id === productId);
    if (fromApi) return fromApi;
    return getCustomProducts().find(p => p.id === productId);
}

function getProductsByCategory(category) {
    const all = getAllProductsMerged();
    if (category === "all") return all;
    return all.filter(p => p.category === category);
}

function saveCustomProducts(products) {
    try {
        localStorage.setItem('vj_custom_products', JSON.stringify(products));
    } catch (e) {
        console.warn('Erro ao salvar produtos customizados:', e);
    }
}

function addCustomProduct(product) {
    const custom = getCustomProducts();
    const newId = Date.now();
    product.id = newId;
    product.custom = true;
    custom.push(product);
    saveCustomProducts(custom);
    return product;
}

function updateCustomProduct(id, data) {
    const custom = getCustomProducts();
    const idx = custom.findIndex(p => p.id === id);
    if (idx !== -1) {
        custom[idx] = { ...custom[idx], ...data };
        saveCustomProducts(custom);
    }
}

function deleteCustomProduct(id) {
    const custom = getCustomProducts().filter(p => p.id !== id);
    saveCustomProducts(custom);
}

// ============================================
// CARREGAMENTO ASSINCRONO DA API
// ============================================

async function loadProductsFromAPI() {
    if (apiLoaded) return apiProductsCache;

    try {
        const result = await API.getProducts();
        if (result.success) {
            apiProductsCache = normalizeProducts(result.data);
            apiLoaded = apiProductsCache.length > 0;
            console.log(`${apiProductsCache.length} produtos carregados da API ou cache offline`);
            return apiProductsCache;
        }
    } catch (e) {
        console.warn('[API] Falha ao carregar produtos e cache offline indisponivel');
    }

    apiProductsCache = [];
    apiLoaded = false;
    return [];
}

function getAllProductsMerged() {
    return getAllProducts();
}

function formatPrice(price) {
    return Number(price).toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });
}

function calculateInstallment(price) {
    return price / 12;
}
