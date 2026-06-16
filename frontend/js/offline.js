// ============================================
// OFFLINE SUPPORT - VJ Semijoias
// Registra service worker e detecta status de conexão
// ============================================

(function() {
    'use strict';

    // Registra Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('service-worker.js')
                .then(reg => {
                    console.log('✓ Service Worker registrado:', reg.scope);
                })
                .catch(err => {
                    console.warn('Erro ao registrar Service Worker:', err);
                });
        });
    }

    // Detecta online/offline
    function updateOnlineStatus() {
        const notice = document.getElementById('offline-notice');
        if (!notice) return;
        
        if (!navigator.onLine) {
            notice.classList.add('show');
            notice.innerHTML = '⚠️ Você está offline. O site continua funcionando com os produtos salvos.';
        } else {
            notice.classList.remove('show');
        }
    }

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    document.addEventListener('DOMContentLoaded', updateOnlineStatus);

    // Adiciona meta tag para PWA
    if (!document.querySelector('link[rel="manifest"]')) {
        const link = document.createElement('link');
        link.rel = 'manifest';
        link.href = 'manifest.json';
        document.head.appendChild(link);
    }

    // Adiciona meta theme-color
    if (!document.querySelector('meta[name="theme-color"]')) {
        const meta = document.createElement('meta');
        meta.name = 'theme-color';
        meta.content = '#a67c3d';
        document.head.appendChild(meta);
    }
})();
