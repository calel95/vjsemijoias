// ============================================
// API CLIENT - VJ Semijoias Backend
// Comunicação com o servidor FastAPI
// ============================================

const standaloneFrontendPorts = ['5500', '8000', '8080'];
const API_BASE = window.location.protocol === 'file:'
    ? 'http://localhost:5000'
    : (standaloneFrontendPorts.includes(window.location.port)
        ? `${window.location.protocol}//${window.location.hostname}:5000`
        : window.location.origin);

function getFilenameFromDisposition(disposition) {
    if (!disposition) return null;
    const match = disposition.match(/filename="?([^"]+)"?/i);
    return match ? match[1] : null;
}

function getCookieValue(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : [];
    const prefix = `${encodeURIComponent(name)}=`;
    const match = cookies.find((cookie) => cookie.startsWith(prefix));
    return match ? decodeURIComponent(match.slice(prefix.length)) : '';
}

const API = {
    baseUrl: `${API_BASE}/api`,
    authenticated: false,
    csrfCookieName: 'vj_csrf_token',
    csrfHeaderName: 'X-CSRF-Token',

    // ============================================
    // UTILITÁRIOS
    // ============================================

    setToken(token, options = {}) {
        const isAdminToken = options.admin === true;
        localStorage.removeItem('vj_api_token');
        sessionStorage.removeItem('vj_admin_token');
        if (isAdminToken) {
            this.authenticated = false;
            sessionStorage.setItem('vj_admin_authenticated', 'true');
        } else if (token) {
            this.authenticated = true;
            sessionStorage.removeItem('vj_admin_authenticated');
        } else {
            this.authenticated = false;
            sessionStorage.removeItem('vj_admin_authenticated');
        }
    },

    hasAdminToken() {
        return sessionStorage.getItem('vj_admin_authenticated') === 'true';
    },

    getCsrfHeaders(method) {
        if (['GET', 'HEAD', 'OPTIONS'].includes(String(method || '').toUpperCase())) {
            return {};
        }
        const token = getCookieValue(this.csrfCookieName);
        return token ? { [this.csrfHeaderName]: token } : {};
    },

    getHeaders(method = 'GET') {
        return {
            'Content-Type': 'application/json',
            ...this.getCsrfHeaders(method),
        };
    },

    async request(method, endpoint, body = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: this.getHeaders(method),
            credentials: 'include',
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            const data = await response.json();

            if (!response.ok) {
                return { success: false, error: data.error || 'Erro na requisição', status: response.status, data };
            }

            return { success: true, data, status: response.status };
        } catch (error) {
            console.warn(`[API] Erro de conexão com o servidor:`, error.message);
            return { success: false, error: 'Servidor offline', offline: true };
        }
    },

    // ============================================
    // PRODUTOS
    // ============================================

    async getProducts(category = 'all', search = '', options = {}) {
        let endpoint = '/products';
        const params = [];
        if (category && category !== 'all') params.push(`category=${encodeURIComponent(category)}`);
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (options.page) params.push(`page=${encodeURIComponent(options.page)}`);
        if (options.perPage) params.push(`per_page=${encodeURIComponent(options.perPage)}`);
        if (params.length) endpoint += '?' + params.join('&');

        return this.request('GET', endpoint);
    },

    async getAdminProducts() {
        return this.request('GET', '/admin/products');
    },

    async getStorageStatus() {
        return this.request('GET', '/admin/storage/status');
    },

    async getProduct(id) {
        return this.request('GET', `/products/${id}`);
    },

    async createProduct(productData) {
        return this.request('POST', '/products', productData);
    },

    async importProductFolder(files) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file, file.webkitRelativePath || file.name);
        }

        const headers = this.getCsrfHeaders('POST');

        try {
            const response = await fetch(`${this.baseUrl}/products/import-folder`, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: formData,
            });
            const data = await response.json();
            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || 'Erro ao importar catálogo',
                    status: response.status,
                    data,
                };
            }
            return { success: true, data, status: response.status };
        } catch (error) {
            return {
                success: false,
                error: 'Servidor offline',
                offline: true,
            };
        }
    },

    async generateCatalogPdf(formData) {
        const headers = this.getCsrfHeaders('POST');

        try {
            const response = await fetch(`${this.baseUrl}/admin/catalog-pdf`, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: formData,
            });

            if (!response.ok) {
                let error = 'Erro ao gerar catalogo';
                try {
                    const data = await response.json();
                    error = data.error || error;
                } catch (_) {
                    error = await response.text() || error;
                }
                return { success: false, error, status: response.status };
            }

            return {
                success: true,
                blob: await response.blob(),
                filename: getFilenameFromDisposition(response.headers.get('content-disposition')) || 'catalogo-vj-semijoias.pdf',
                products: response.headers.get('x-catalog-products'),
                pages: response.headers.get('x-catalog-pages'),
            };
        } catch (error) {
            return { success: false, error: 'Servidor offline', offline: true };
        }
    },

    async updateProduct(id, productData) {
        return this.request('PUT', `/products/${id}`, productData);
    },

    async deleteProduct(id) {
        return this.request('DELETE', `/products/${id}`);
    },

    async deleteAllProducts(confirm) {
        return this.request('DELETE', '/admin/products', { confirm });
    },

    // ============================================
    // CATEGORIAS
    // ============================================

    async getCategories() {
        return this.request('GET', '/categories');
    },

    // ============================================
    // AUTENTICAÇÃO
    // ============================================

    async register(userData) {
        const result = await this.request('POST', '/auth/register', userData);
        if (result.success) {
            this.setToken(result.data.token || 'cookie');
        }
        return result;
    },

    async login(email, password) {
        const result = await this.request('POST', '/auth/login', { email, password });
        if (result.success) {
            this.setToken(result.data.token || 'cookie');
        }
        return result;
    },

    async requestPasswordReset(email) {
        return this.request('POST', '/auth/password-reset/request', { email });
    },

    async confirmPasswordReset(token, password) {
        const result = await this.request('POST', '/auth/password-reset/confirm', {
            token,
            password,
        });
        if (result.success) {
            this.setToken(result.data.token || 'cookie');
        }
        return result;
    },

    async adminLogin(email, password) {
        const result = await this.request('POST', '/auth/admin/login', { email, password });
        if (result.success && result.data.token) {
            this.setToken(result.data.token, { admin: true });
        }
        return result;
    },

    async createAdminUser(userData) {
        return this.request('POST', '/auth/admin/users', userData);
    },

    async getAdminUsers() {
        return this.request('GET', '/auth/admin/users');
    },

    async getAdminAuditLogs(limit = 80) {
        return this.request('GET', `/auth/admin/audit-logs?limit=${encodeURIComponent(limit)}`);
    },

    async getMe() {
        return this.request('GET', '/auth/me');
    },

    logout() {
        fetch(`${this.baseUrl}/auth/logout`, {
            method: 'POST',
            headers: this.getCsrfHeaders('POST'),
            credentials: 'include',
        }).catch(() => {});
        this.setToken(null);
    },

    isLoggedIn() {
        return this.authenticated;
    },

    // ============================================
    // PEDIDOS
    // ============================================

    async createOrder(orderData) {
        return this.request('POST', '/orders', orderData);
    },

    async getPaymentConfig() {
        return this.request('GET', '/payments/config');
    },

    async getStoreConfig() {
        return this.request('GET', '/store/config');
    },

    async getAdminStoreConfig() {
        return this.request('GET', '/admin/store-config');
    },

    async updateAdminStoreConfig(values) {
        return this.request('PUT', '/admin/store-config', { values });
    },

    async createInfinitePayCheckout(orderData) {
        return this.request('POST', '/payments/infinitepay/checkout', orderData);
    },

    async confirmInfinitePayPayment(paymentData) {
        return this.request('POST', '/payments/infinitepay/confirm', paymentData);
    },

    async getPaymentStatus(orderId, checkoutToken) {
        return this.request(
            'GET',
            `/payments/${encodeURIComponent(orderId)}/status?token=${encodeURIComponent(checkoutToken)}`
        );
    },

    async getOrders() {
        return this.request('GET', '/orders');
    },

    async getOrder(orderId) {
        return this.request('GET', `/orders/${orderId}`);
    },

    async getPublicOrder(orderId, token) {
        return this.request(
            'GET',
            `/orders/${encodeURIComponent(orderId)}/public?token=${encodeURIComponent(token)}`
        );
    },

    async updateOrderStatus(orderId, status, data = {}) {
        return this.request('PUT', `/admin/orders/${encodeURIComponent(orderId)}/status`, {
            status,
            ...data,
        });
    },

    // ============================================
    // NEWSLETTER
    // ============================================

    async subscribeNewsletter(email) {
        return this.request('POST', '/newsletter', { email });
    },

    // ============================================
    // CUPONS
    // ============================================

    async validateCoupon(code, options = {}) {
        return this.request('POST', '/coupons/validate', { code, ...options });
    },

    async getAdminCoupons() {
        return this.request('GET', '/admin/coupons');
    },

    async createAdminCoupon(data) {
        return this.request('POST', '/admin/coupons', data);
    },

    async updateAdminCoupon(id, data) {
        return this.request('PUT', `/admin/coupons/${encodeURIComponent(id)}`, data);
    },

    // ============================================
    // FRETE
    // ============================================

    async calculateShipping(total, zipCode = '', items = []) {
        const payload = { total, zip_code: zipCode };
        if (Array.isArray(items) && items.length > 0) {
            payload.items = items.map(item => ({
                id: item.id,
                quantity: item.quantity || 1,
            }));
        }
        return this.request('POST', '/shipping/calculate', payload);
    },

    // ============================================
    // ENDERECO
    // ============================================

    async lookupCep(cep) {
        return this.request('GET', `/address/cep/${encodeURIComponent(cep)}`);
    },

    // ============================================
    // ADMIN ESTATÍSTICAS
    // ============================================

    async getAdminStats() {
        return this.request('GET', '/admin/stats');
    }
};
