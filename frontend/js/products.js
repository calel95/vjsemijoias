// ============================================
// CATALOGO DE PRODUTOS - VJ SEMIJOIAS
// Usa a API como fonte principal e o service worker como cache offline.
// ============================================

let CATEGORIES = [
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
let categoriesLoaded = false;

function normalizeProducts(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.items)) return data.items;
    return [];
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

function normalizeCategories(data) {
    const categories = Array.isArray(data) ? data : [];
    return categories.filter(category => category && category.id && category.name);
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

async function loadProductsPageFromAPI({ page = 1, perPage = 12, category = 'all', search = '' } = {}) {
    try {
        const result = await API.getProducts(category, search, { page, perPage });
        if (result.success) {
            const items = normalizeProducts(result.data);
            return {
                items,
                page: result.data.page || page,
                perPage: result.data.per_page || perPage,
                total: result.data.total ?? items.length,
                totalPages: result.data.total_pages || 0,
                hasNext: Boolean(result.data.has_next),
                hasPrevious: Boolean(result.data.has_previous),
            };
        }
    } catch (e) {
        console.warn('[API] Falha ao carregar pagina de produtos');
    }

    return {
        items: [],
        page,
        perPage,
        total: 0,
        totalPages: 0,
        hasNext: false,
        hasPrevious: false,
    };
}

async function loadCategoriesFromAPI() {
    if (categoriesLoaded) return CATEGORIES;

    try {
        const result = await API.getCategories();
        if (result.success) {
            const categories = normalizeCategories(result.data);
            if (categories.length) {
                CATEGORIES = categories;
                categoriesLoaded = true;
            }
        }
    } catch (e) {
        console.warn('[API] Falha ao carregar categorias; usando fallback local');
    }

    return CATEGORIES;
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
