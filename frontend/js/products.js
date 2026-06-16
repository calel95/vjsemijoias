// ============================================
// CATÁLOGO DE PRODUTOS - VJ SEMIJOIAS
// Baseado no catálogo oficial (PDF)
// Suporta API backend + fallback offline
// ============================================

const PRODUCTS = [
    {
        id: 1,
        name: "Brinco Marguerite",
        category: "brincos",
        categoryName: "Brincos",
        price: 149.90,
        oldPrice: null,
        image: "images/products/brinco-marguerite.svg",
        icon: "✨",
        badge: null,
        description: "Brinco argolão cravejado com cristais, acabamento impecável. Peça statement para ocasiões especiais.",
        features: [
            "Banho de Ouro 18k",
            "Cravejado com cristais",
            "Fecho de tarraxa",
            "Diâmetro aproximado: 3cm"
        ],
        custom: false
    },
    {
        id: 2,
        name: "Colar Sol Dourado",
        category: "colares",
        categoryName: "Colares",
        price: 199.90,
        oldPrice: null,
        image: "images/products/colar-sol-dourado.svg",
        icon: "☀️",
        badge: "new",
        description: "Colar delicado com pingente sol, folheado a ouro 18k. Energia e brilho para o seu dia a dia.",
        features: [
            "Banho de Ouro 18k",
            "Pingente formato sol",
            "Corrente delicada",
            "Comprimento: 45cm"
        ],
        custom: false
    },
    {
        id: 3,
        name: "Pulseira Corrente Tennis",
        category: "pulseiras",
        categoryName: "Pulseiras",
        price: 179.90,
        oldPrice: null,
        image: "images/products/pulseira-tennis.svg",
        icon: "⚜️",
        badge: null,
        description: "Clássica pulseira de elos, banho 18k, fecho seguro. Elegância atemporal.",
        features: [
            "Banho de Ouro 18k",
            "Modelo tennis clássico",
            "Fecho de segurança",
            "Comprimento: 18cm + extensor"
        ],
        custom: false
    },
    {
        id: 4,
        name: "Anel Luna",
        category: "aneis",
        categoryName: "Anéis",
        price: 129.90,
        oldPrice: null,
        image: "images/products/anel-luna.svg",
        icon: "🌙",
        badge: null,
        description: "Anel ajustável com zircônias, banhado a ouro 18k. Delicadeza que combina com tudo.",
        features: [
            "Banho de Ouro 18k",
            "Zircônias incrustadas",
            "Modelo ajustável",
            "Hipoalergênico"
        ],
        custom: false
    },
    {
        id: 5,
        name: "Pingente Flor de Lis",
        category: "pingentes",
        categoryName: "Pingentes",
        price: 99.90,
        oldPrice: null,
        image: "images/products/pingente-flor-lis.svg",
        icon: "🌸",
        badge: null,
        description: "Pingente moderno com acabamento diamantado, 18k. Símbolo de nobreza e elegância.",
        features: [
            "Banho de Ouro 18k",
            "Acabamento diamantado",
            "Modelo Flor de Lis",
            "Vendido sem corrente"
        ],
        custom: false
    },
    {
        id: 6,
        name: "Brinco Argola Crocodilo",
        category: "brincos",
        categoryName: "Brincos",
        price: 159.90,
        oldPrice: null,
        image: "images/products/brinco-argola-crocodilo.svg",
        icon: "🐊",
        badge: "new",
        description: "Argola texturizada, banho ouro 18k, 3cm de diâmetro. Design moderno e marcante.",
        features: [
            "Banho de Ouro 18k",
            "Textura Crocodilo",
            "Diâmetro: 3cm",
            "Fecho de pressão"
        ],
        custom: false
    },
    {
        id: 7,
        name: "Colar Gota de Orvalho",
        category: "colares",
        categoryName: "Colares",
        price: 229.90,
        oldPrice: null,
        image: "images/products/colar-gota-orvalho.svg",
        icon: "💧",
        badge: null,
        description: "Colar com pedra gota, folheado 18k, comprimento 40cm. Sofisticação em cada detalhe.",
        features: [
            "Banho de Ouro 18k",
            "Pedra em formato gota",
            "Comprimento: 40cm",
            "Fecho mosquetão"
        ],
        custom: false
    },
    {
        id: 8,
        name: "Pulseira Elo Coração",
        category: "pulseiras",
        categoryName: "Pulseiras",
        price: 149.90,
        oldPrice: null,
        image: "images/products/pulseira-elo-coracao.svg",
        icon: "💕",
        badge: null,
        description: "Elos em formato coração, banho 18k, ideal para presentear. Romântico e delicado.",
        features: [
            "Banho de Ouro 18k",
            "Elos coração",
            "Ideal para presente",
            "Comprimento: 17cm + extensor"
        ],
        custom: false
    },
    {
        id: 9,
        name: "Anel Duas Cores",
        category: "aneis",
        categoryName: "Anéis",
        price: 139.90,
        oldPrice: null,
        image: "images/products/anel-duas-cores.svg",
        icon: "💍",
        badge: "new",
        description: "Anel bicolor (ouro e rose) banho 18k, tala larga. Tendência e exclusividade.",
        features: [
            "Banho de Ouro 18k + Rose",
            "Modelo bicolor",
            "Tala larga",
            "Ajustável"
        ],
        custom: false
    },
    {
        id: 10,
        name: "Pingente Estrela",
        category: "pingentes",
        categoryName: "Pingentes",
        price: 109.90,
        oldPrice: null,
        image: "images/products/pingente-estrela.svg",
        icon: "⭐",
        badge: null,
        description: "Pingente estrela cravejada, folheado 18k, corrente fina inclusa. Brilhe sempre.",
        features: [
            "Banho de Ouro 18k",
            "Estrela cravejada",
            "Acompanha corrente 45cm",
            "Fecho mosquetão"
        ],
        custom: false
    }
];

// Categorias para filtros
const CATEGORIES = [
    { id: "all", name: "Todos", icon: "💎" },
    { id: "brincos", name: "Brincos", icon: "✨" },
    { id: "colares", name: "Colares", icon: "📿" },
    { id: "pulseiras", name: "Pulseiras", icon: "⚜️" },
    { id: "aneis", name: "Anéis", icon: "💍" },
    { id: "pingentes", name: "Pingentes", icon: "🔮" },
    { id: "chaveiros", name: "Chaveiros", icon: "🔑" }
];

// Cache de produtos vindo da API
let apiProductsCache = [];
let apiLoaded = false;

// Funções utilitárias
function getAllProducts() {
    const custom = getCustomProducts();
    return [...PRODUCTS, ...custom];
}

function getCustomProducts() {
    try {
        const stored = localStorage.getItem('vj_custom_products');
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function getProductById(id) {
    // Tenta da API primeiro, depois local
    const fromApi = apiProductsCache.find(p => p.id === parseInt(id));
    if (fromApi) return fromApi;
    return getAllProducts().find(p => p.id === parseInt(id));
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
// CARREGAMENTO ASSÍNCRONO DA API
// ============================================

async function loadProductsFromAPI() {
    if (apiLoaded) return apiProductsCache;

    try {
        const result = await API.getProducts();
        if (result.success && result.data && result.data.length > 0) {
            apiProductsCache = result.data;
            apiLoaded = true;
            console.log(`✅ ${apiProductsCache.length} produtos carregados da API`);
            return apiProductsCache;
        }
    } catch (e) {
        console.warn('[API] Falha ao carregar produtos, usando dados locais');
    }
    return null;
}

function getAllProductsMerged() {
    if (apiLoaded && apiProductsCache.length > 0) {
        const custom = getCustomProducts();
        return [...apiProductsCache, ...custom];
    }
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
