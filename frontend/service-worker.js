// ============================================
// Service Worker - VJ Semijoias
// Permite o site funcionar offline no tablet
// ============================================

const CACHE_NAME = 'vj-semijoias-v28';
const API_CACHE_NAME = 'vj-semijoias-api-v1';
const urlsToCache = [
    '/',
    '/catalogo',
    '/produto',
    '/pdf-visualizar',
    '/politica-troca.html',
    '/politica-privacidade.html',
    '/termos-uso.html',
    '/garantia.html',
    '/faq.html',
    './css/style.css',
    './js/api.js',
    './js/store-config.js',
    './js/public-layout.js',
    './js/seo.js',
    './js/products.js',
    './js/cart.js',
    './js/main.js',
    './js/offline.js',
    './images/logo.png',
    './images/logo-medium.png',
    './manifest.json',
    './robots.txt',
    './sitemap.xml',
    './images/products/brinco-marguerite.svg',
    './images/products/colar-sol-dourado.svg',
    './images/products/pulseira-tennis.svg',
    './images/products/anel-luna.svg',
    './images/products/pingente-flor-lis.svg',
    './images/products/brinco-argola-crocodilo.svg',
    './images/products/colar-gota-orvalho.svg',
    './images/products/pulseira-elo-coracao.svg',
    './images/products/anel-duas-cores.svg',
    './images/products/pingente-estrela.svg',
    './pdf/catalogo-vj.pdf'
];

const CACHEABLE_NAVIGATION_PATHS = new Set([
    '/',
    '/catalogo',
    '/produto',
    '/pdf-visualizar',
    '/politica-troca.html',
    '/politica-privacidade.html',
    '/termos-uso.html',
    '/garantia.html',
    '/faq.html',
]);
const NETWORK_ONLY_NAVIGATION_PATHS = new Set([
    '/carrinho',
    '/checkout',
    '/pedido',
    '/login',
    '/cadastro',
]);
const PRODUCT_IMAGE_CACHE_LIMIT = 24;
const PRODUCT_IMAGE_MAX_BYTES = 300 * 1024;

// Instala o service worker e faz cache dos arquivos
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Cache aberto');
                return cache.addAll(urlsToCache);
            })
            .catch(err => console.error('Erro no cache:', err))
    );
    self.skipWaiting();
});

// Ativação - limpa caches antigos
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            const validCaches = [CACHE_NAME, API_CACHE_NAME];
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (!validCaches.includes(cacheName)) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Navegações e API usam a rede primeiro; assets estáticos usam o cache.
function productImageUrls(products) {
    const urls = new Set();
    products.forEach(product => {
        const images = Array.isArray(product.images) && product.images.length
            ? product.images
            : (product.image ? [product.image] : []);
        images.forEach(image => {
            try {
                const imageUrl = new URL(image, self.location.origin);
                if (imageUrl.origin === self.location.origin) {
                    urls.add(imageUrl.href);
                }
            } catch (_) {
                // Ignora caminhos invalidos vindos do catalogo.
            }
        });
    });
    return [...urls];
}

function productsFromPayload(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.items)) return payload.items;
    return [];
}

async function cacheProductImages(products) {
    const cache = await caches.open(CACHE_NAME);
    const imageUrls = productImageUrls(products).slice(0, PRODUCT_IMAGE_CACHE_LIMIT);
    await Promise.allSettled(
        imageUrls.map(async url => {
            const response = await fetch(url);
            if (!response.ok) return;
            const buffer = await response.clone().arrayBuffer();
            if (buffer.byteLength > PRODUCT_IMAGE_MAX_BYTES) return;
            await cache.put(url, response);
        })
    );
}

async function networkFirstProducts(request, event) {
    const cache = await caches.open(API_CACHE_NAME);
    try {
        const response = await fetch(request);
        if (response.ok) {
            await cache.put(request, response.clone());
            const imageCacheTask = response.clone().json()
                .then(payload => cacheProductImages(productsFromPayload(payload)))
                .catch(() => {});
            event.waitUntil(imageCacheTask);
            return response;
        }
        const cached = await cache.match(request);
        if (cached) return cached;
        return response;
    } catch (error) {
        const cached = await cache.match(request);
        if (cached) return cached;
        throw error;
    }
}

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (url.pathname === '/api/products') {
        event.respondWith(networkFirstProducts(event.request, event));
        return;
    }

    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (event.request.mode === 'navigate') {
        const shouldCacheNavigation = CACHEABLE_NAVIGATION_PATHS.has(url.pathname) && !NETWORK_ONLY_NAVIGATION_PATHS.has(url.pathname);
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (shouldCacheNavigation && response.ok) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
                    }
                    return response;
                })
                .catch(() => {
                    if (!shouldCacheNavigation) return caches.match('/');
                    return caches.match(event.request).then(response => response || caches.match('/'));
                })
        );
        return;
    }

    if (event.request.destination === 'script' || event.request.destination === 'style') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    if (event.request.destination === 'image') {
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request).then(response => {
                    // Cache novos requests
                    if (response && response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return response;
                });
            })
            .catch(() => {
                // Fallback offline
                if (event.request.destination === 'document') {
                    return caches.match('/');
                }
            })
    );
});
