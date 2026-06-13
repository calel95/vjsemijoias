// ============================================
// Service Worker - VJ Semijoias
// Permite o site funcionar offline no tablet
// ============================================

const CACHE_NAME = 'vj-semijoias-v16';
const urlsToCache = [
    './',
    './index.html',
    './catalogo.html',
    './produto.html',
    './carrinho.html',
    './checkout.html',
    './login.html',
    './cadastro.html',
    './admin.html',
    './pdf-visualizar.html',
    './css/style.css',
    './css/admin.css',
    './js/api.js',
    './js/products.js',
    './js/cart.js',
    './js/main.js',
    './js/admin.js',
    './images/logo.png',
    './manifest.json',
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
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Navegações e API usam a rede primeiro; assets estáticos usam o cache.
self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
                    return response;
                })
                .catch(() => caches.match(event.request).then(response => response || caches.match('./index.html')))
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
                    return caches.match('./index.html');
                }
            })
    );
});
