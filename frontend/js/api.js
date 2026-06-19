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

const API = {
    baseUrl: `${API_BASE}/api`,
    token: sessionStorage.getItem('vj_admin_token') || localStorage.getItem('vj_api_token'),

    // ============================================
    // UTILITÁRIOS
    // ============================================

    setToken(token, options = {}) {
        const isAdminToken = options.admin === true;
        this.token = token;
        if (token) {
            if (isAdminToken) {
                sessionStorage.setItem('vj_admin_token', token);
            } else {
                localStorage.setItem('vj_api_token', token);
                sessionStorage.removeItem('vj_admin_token');
            }
        } else {
            localStorage.removeItem('vj_api_token');
            sessionStorage.removeItem('vj_admin_token');
        }
    },

    hasAdminToken() {
        return !!sessionStorage.getItem('vj_admin_token');
    },

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    },

    async request(method, endpoint, body = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: this.getHeaders(),
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

    async getProducts(category = 'all', search = '') {
        let endpoint = '/products';
        const params = [];
        if (category && category !== 'all') params.push(`category=${category}`);
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (params.length) endpoint += '?' + params.join('&');

        return this.request('GET', endpoint);
    },

    async getAdminProducts() {
        return this.request('GET', '/admin/products');
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

        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(`${this.baseUrl}/products/import-folder`, {
                method: 'POST',
                headers,
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
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(`${this.baseUrl}/admin/catalog-pdf`, {
                method: 'POST',
                headers,
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
        if (result.success && result.data.token) {
            this.setToken(result.data.token);
        }
        return result;
    },

    async login(email, password) {
        const result = await this.request('POST', '/auth/login', { email, password });
        if (result.success && result.data.token) {
            this.setToken(result.data.token);
        }
        return result;
    },

    async adminLogin(password) {
        const result = await this.request('POST', '/auth/admin/login', { password });
        if (result.success && result.data.token) {
            this.setToken(result.data.token, { admin: true });
        }
        return result;
    },

    async getMe() {
        return this.request('GET', '/auth/me');
    },

    logout() {
        this.setToken(null);
    },

    isLoggedIn() {
        return !!this.token;
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

    async updateOrderStatus(orderId, status) {
        return this.request('PUT', `/admin/orders/${encodeURIComponent(orderId)}/status`, { status });
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

    async validateCoupon(code) {
        return this.request('POST', '/coupons/validate', { code });
    },

    // ============================================
    // FRETE
    // ============================================

    async calculateShipping(total, zipCode = '') {
        return this.request('POST', '/shipping/calculate', { total, zip_code: zipCode });
    },

    // ============================================
    // ADMIN ESTATÍSTICAS
    // ============================================

    async getAdminStats() {
        return this.request('GET', '/admin/stats');
    }
};
