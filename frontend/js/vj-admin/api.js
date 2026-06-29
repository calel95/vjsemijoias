(function () {
    const standaloneFrontendPorts = ['5500', '8000', '8080'];
    const API_BASE = window.location.protocol === 'file:'
        ? 'http://localhost:5000'
        : (standaloneFrontendPorts.includes(window.location.port)
            ? `${window.location.protocol}//${window.location.hostname}:5000`
            : window.location.origin);

    function getCookieValue(name) {
        const cookies = document.cookie ? document.cookie.split('; ') : [];
        const prefix = `${encodeURIComponent(name)}=`;
        const match = cookies.find((cookie) => cookie.startsWith(prefix));
        return match ? decodeURIComponent(match.slice(prefix.length)) : '';
    }

    function queryString(params = {}) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && String(value).trim() !== '') {
                search.set(key, value);
            }
        });
        const value = search.toString();
        return value ? `?${value}` : '';
    }

    async function request(method, endpoint, body) {
        const headers = { 'Content-Type': 'application/json' };
        if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
            const csrf = getCookieValue('vj_csrf_token');
            if (csrf) headers['X-CSRF-Token'] = csrf;
        }
        const response = await fetch(`${API_BASE}/api${endpoint}`, {
            method,
            headers,
            credentials: 'include',
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        let data = null;
        try {
            data = await response.json();
        } catch (_) {
            data = {};
        }
        if (!response.ok) {
            const error = new Error(data.error || data.detail || 'Falha na requisicao');
            error.status = response.status;
            error.data = data;
            throw error;
        }
        return data;
    }

    async function download(endpoint, filename) {
        const headers = {};
        const response = await fetch(`${API_BASE}/api${endpoint}`, {
            method: 'GET',
            headers,
            credentials: 'include',
        });
        if (!response.ok) {
            let data = {};
            try { data = await response.json(); } catch (_) {}
            const error = new Error(data.error || data.detail || 'Falha ao baixar arquivo');
            error.status = response.status;
            throw error;
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    window.VJAdminAPI = {
        async login(email, password) {
            return request('POST', '/auth/admin/login', { email, password });
        },
        async logout() {
            try { await request('POST', '/auth/logout', {}); } catch (_) {}
        },
        async products(filters = {}) {
            return request('GET', `/vj-admin/produtos${queryString(filters)}`);
        },
        async exportProductsCsv(filters = {}) {
            return download(`/vj-admin/produtos/export.csv${queryString(filters)}`, 'vj-admin-produtos.csv');
        },
        async orders(filters = {}) {
            return request('GET', `/vj-admin/pedidos${queryString(filters)}`);
        },
        async order(id) {
            return request('GET', `/vj-admin/pedidos/${encodeURIComponent(id)}`);
        },
        async saveOrder(payload, id) {
            return id
                ? request('PUT', `/vj-admin/pedidos/${encodeURIComponent(id)}`, payload)
                : request('POST', '/vj-admin/pedidos', payload);
        },
        async confirmOrder(id) {
            return request('POST', `/vj-admin/pedidos/${encodeURIComponent(id)}/confirmar`, {});
        },
        async cancelOrder(id) {
            return request('POST', `/vj-admin/pedidos/${encodeURIComponent(id)}/cancelar`, {});
        },
        async stock(filters = {}) {
            return request('GET', `/vj-admin/estoque${queryString(filters)}`);
        },
        async productStock(id) {
            return request('GET', `/vj-admin/produtos/${encodeURIComponent(id)}/estoque`);
        },
        async moveStock(id, payload) {
            return request('POST', `/vj-admin/produtos/${encodeURIComponent(id)}/estoque/movimentar`, payload);
        },
        async product(id) {
            return request('GET', `/vj-admin/produtos/${encodeURIComponent(id)}`);
        },
        async saveProduct(payload, id) {
            return id
                ? request('PUT', `/vj-admin/produtos/${encodeURIComponent(id)}`, payload)
                : request('POST', '/vj-admin/produtos', payload);
        },
        async publishProduct(id) {
            return request('POST', `/vj-admin/produtos/${encodeURIComponent(id)}/publicar`, {});
        },
        async unpublishProduct(id) {
            return request('POST', `/vj-admin/produtos/${encodeURIComponent(id)}/despublicar`, {});
        },
        async deactivateProduct(id, confirm) {
            return request('POST', `/vj-admin/produtos/${encodeURIComponent(id)}/inativar`, { confirm });
        },
        async suppliers() {
            return request('GET', '/vj-admin/fornecedores');
        },
        async saveSupplier(payload, id) {
            return id
                ? request('PUT', `/vj-admin/fornecedores/${encodeURIComponent(id)}`, payload)
                : request('POST', '/vj-admin/fornecedores', payload);
        },
    };
})();



