// ============================================
// CARRINHO DE COMPRAS - VJ SEMIJOIAS
// Gerencia estado do carrinho via localStorage
// ============================================

const CART_KEY = 'vj_cart';
const USER_KEY = 'vj_user';
const ORDERS_KEY = 'vj_orders';
const COUPON_KEY = 'vj_coupon';
const COUPON_PERCENT_KEY = 'vj_coupon_percent';
const CART_PRICING_KEY = 'vj_cart_pricing';
const DEFAULT_SHIPPING_MESSAGE = 'Informe o CEP para calcular o frete';

const Cart = {
    items: [],
    pricing: {
        shipping: 0,
        shippingMessage: DEFAULT_SHIPPING_MESSAGE,
        shippingService: '',
        shippingEstimatedDays: '',
        shippingOption: null,
        shippingOptions: [],
        shippingZipCode: '',
        discount: 0,
        discountCode: '',
        discountPercent: 0,
        loaded: false,
    },

    init() {
        const stored = localStorage.getItem(CART_KEY);
        this.items = stored ? JSON.parse(stored) : [];
        this.loadPricing();
        this.updateBadge();
    },

    loadPricing() {
        const stored = localStorage.getItem(CART_PRICING_KEY);
        if (!stored) return;

        try {
            const pricing = JSON.parse(stored);
            this.pricing = {
                ...this.pricing,
                ...pricing,
                shipping: Number(pricing.shipping || 0),
                shippingOptions: Array.isArray(pricing.shippingOptions) ? pricing.shippingOptions : [],
                shippingZipCode: pricing.shippingZipCode || '',
                shippingOption: pricing.shippingOption || null,
            };
        } catch (_) {
            localStorage.removeItem(CART_PRICING_KEY);
        }
    },

    savePricing() {
        localStorage.setItem(CART_PRICING_KEY, JSON.stringify({
            shipping: this.pricing.shipping || 0,
            shippingMessage: this.pricing.shippingMessage || DEFAULT_SHIPPING_MESSAGE,
            shippingService: this.pricing.shippingService || '',
            shippingEstimatedDays: this.pricing.shippingEstimatedDays || '',
            shippingOption: this.pricing.shippingOption || null,
            shippingOptions: this.pricing.shippingOptions || [],
            shippingZipCode: this.pricing.shippingZipCode || '',
            discount: this.pricing.discount || 0,
            discountCode: this.pricing.discountCode || '',
            discountPercent: this.pricing.discountPercent || 0,
            loaded: this.pricing.loaded || false,
        }));
    },

    clearShippingQuote({ keepZip = false } = {}) {
        const previousZip = this.pricing.shippingZipCode || '';
        this.pricing.shipping = 0;
        this.pricing.shippingMessage = DEFAULT_SHIPPING_MESSAGE;
        this.pricing.shippingService = '';
        this.pricing.shippingEstimatedDays = '';
        this.pricing.shippingOption = null;
        this.pricing.shippingOptions = [];
        this.pricing.shippingZipCode = keepZip ? previousZip : '';
        this.pricing.loaded = false;
        this.savePricing();
    },

    setShippingQuote(zipCode, options = [], selectedOptionId = '') {
        const normalizedOptions = Array.isArray(options) ? options : [];
        const selected = normalizedOptions.find(option => option.id === selectedOptionId) || normalizedOptions[0] || null;
        this.pricing.shippingOptions = normalizedOptions;
        this.pricing.shippingZipCode = String(zipCode || '').replace(/\D/g, '');
        this.setShippingOption(selected);
    },

    setShippingOption(option) {
        this.pricing.shippingOption = option || null;
        this.pricing.shipping = Number(option?.shipping || 0);
        this.pricing.shippingMessage = option?.message || (option ? 'Frete selecionado' : DEFAULT_SHIPPING_MESSAGE);
        this.pricing.shippingService = option?.service || '';
        this.pricing.shippingEstimatedDays = option?.estimated_days || '';
        this.pricing.loaded = Boolean(option);
        this.savePricing();
    },

    selectShippingOption(optionId) {
        const option = (this.pricing.shippingOptions || []).find(item => item.id === optionId);
        if (!option) return false;
        this.setShippingOption(option);
        return true;
    },

    getShippingZipCode() {
        return this.pricing.shippingZipCode || '';
    },

    getShippingOptions() {
        return this.pricing.shippingOptions || [];
    },

    syncProductData() {
        let changed = false;

        this.items = this.items.map(item => {
            const product = getProductById(item.id);
            if (!product) return item;

            const image = product.image || product.images?.[0] || item.image;
            if (
                item.name !== product.name ||
                item.price !== product.price ||
                item.icon !== product.icon ||
                item.image !== image
            ) {
                changed = true;
                return {
                    ...item,
                    name: product.name,
                    price: product.price,
                    icon: product.icon,
                    image,
                };
            }

            return item;
        });

        if (changed) this.save();
    },

    add(productId, quantity = 1) {
        const product = getProductById(productId);
        if (!product) return false;

        const existing = this.items.find(item => item.id === productId);

        if (existing) {
            existing.quantity += quantity;
        } else {
            this.items.push({
                id: product.id,
                name: product.name,
                price: product.price,
                icon: product.icon,
                image: product.image,
                quantity: quantity
            });
        }

        this.clearShippingQuote({ keepZip: true });
        this.save();
        this.updateBadge();
        return true;
    },

    remove(productId) {
        this.items = this.items.filter(item => item.id !== productId);
        this.clearShippingQuote({ keepZip: this.items.length > 0 });
        this.save();
        this.updateBadge();
    },

    updateQuantity(productId, quantity) {
        const item = this.items.find(item => item.id === productId);
        if (item) {
            if (quantity <= 0) {
                this.remove(productId);
            } else {
                item.quantity = quantity;
                this.clearShippingQuote({ keepZip: true });
                this.save();
                this.updateBadge();
            }
        }
    },

    clear() {
        this.items = [];
        this.clearShippingQuote();
        localStorage.removeItem(CART_PRICING_KEY);
        this.save();
        this.updateBadge();
    },

    getTotal() {
        return this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    },

    getCount() {
        return this.items.reduce((sum, item) => sum + item.quantity, 0);
    },

    getSubtotal() { return this.getTotal(); },

    getShipping() {
        return this.pricing.shipping || 0;
    },

    getDiscount() {
        if (typeof this.pricing.discount === 'number') {
            return this.pricing.discount;
        }
        const percent = parseFloat(localStorage.getItem(COUPON_PERCENT_KEY) || '0');
        return percent > 0 ? this.getSubtotal() * (percent / 100) : 0;
    },

    getCouponCode() {
        return this.pricing.discountCode || localStorage.getItem(COUPON_KEY) || '';
    },

    getShippingMessage() {
        const option = this.pricing.shippingOption || {};
        const service = this.pricing.shippingService || option.service || '';
        const estimatedDays = this.pricing.shippingEstimatedDays || option.estimated_days || '';
        const message = this.pricing.shippingMessage || option.message || DEFAULT_SHIPPING_MESSAGE;
        if (service && estimatedDays) {
            return `${message} - ${service}, prazo estimado ${estimatedDays} dias`;
        }
        if (estimatedDays) {
            return `${message} - prazo estimado ${estimatedDays} dias`;
        }
        return message;
    },

    async refreshPricing(zipCode = this.getShippingZipCode()) {
        const subtotal = this.getSubtotal();
        const cepDigits = String(zipCode || '').replace(/\D/g, '');
        const couponResult = await this.refreshCoupon(subtotal);

        if (cepDigits.length !== 8) {
            this.clearShippingQuote({ keepZip: Boolean(this.getShippingZipCode()) });
            this.pricing.discount = couponResult.discount;
            this.pricing.discountCode = couponResult.code;
            this.pricing.discountPercent = couponResult.percent;
            this.savePricing();
            return;
        }

        const shippingResult = await API.calculateShipping(subtotal, cepDigits, this.items);

        if (shippingResult.success) {
            const options = Array.isArray(shippingResult.data.options) && shippingResult.data.options.length
                ? shippingResult.data.options
                : (shippingResult.data.selected_option ? [shippingResult.data.selected_option] : []);
            const previousSelectedId = this.pricing.shippingOption?.id || '';
            const selected = options.find(option => option.id === previousSelectedId)
                || shippingResult.data.selected_option
                || options[0]
                || null;
            this.pricing.shippingOptions = options;
            this.pricing.shippingZipCode = cepDigits;
            this.setShippingOption(selected);
        } else {
            this.pricing.shipping = 0;
            this.pricing.shippingMessage = shippingResult.error || 'Nao foi possivel calcular o frete';
            this.pricing.shippingService = '';
            this.pricing.shippingEstimatedDays = '';
            this.pricing.shippingOption = null;
            this.pricing.shippingOptions = [];
            this.pricing.shippingZipCode = cepDigits;
        }

        this.pricing.discount = couponResult.discount;
        this.pricing.discountCode = couponResult.code;
        this.pricing.discountPercent = couponResult.percent;
        this.savePricing();
    },

    async refreshCoupon(subtotal) {
        const code = (localStorage.getItem(COUPON_KEY) || '').trim().toUpperCase();
        if (!code) {
            localStorage.removeItem(COUPON_PERCENT_KEY);
            return { code: '', percent: 0, discount: 0 };
        }

        const result = await API.validateCoupon(code, { total: subtotal });
        if (!result.success || !result.data.valid) {
            localStorage.removeItem(COUPON_KEY);
            localStorage.removeItem(COUPON_PERCENT_KEY);
            return { code: '', percent: 0, discount: 0 };
        }

        const percent = Number(result.data.discount_percent || 0);
        const discount = Number(result.data.discount || 0);
        localStorage.setItem(COUPON_KEY, result.data.code);
        localStorage.setItem(COUPON_PERCENT_KEY, String(percent));
        return {
            code: result.data.code,
            percent,
            discount: discount || subtotal * (percent / 100),
        };
    },

    getFinalTotal() {
        return this.getSubtotal() + this.getShipping() - this.getDiscount();
    },

    save() {
        localStorage.setItem(CART_KEY, JSON.stringify(this.items));
    },

    updateBadge() {
        const badges = document.querySelectorAll('.cart-badge');
        const count = this.getCount();
        badges.forEach(badge => {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        });
    }
};

// ============================================
// AUTENTICAÇÃO (com suporte a API e fallback localStorage)
// ============================================

const Auth = {
    init() {
        const stored = localStorage.getItem(USER_KEY);
        this.user = stored ? JSON.parse(stored) : null;
        this.updateUI();

        API.getMe().then(result => {
            if (result.success) {
                if (result.data?.is_admin && API.hasAdminToken()) {
                    API.authenticated = false;
                    this.user = null;
                    localStorage.removeItem(USER_KEY);
                    this.updateUI();
                    return;
                }
                API.authenticated = true;
                this.user = result.data;
                localStorage.setItem(USER_KEY, JSON.stringify(this.user));
            } else {
                API.authenticated = false;
                this.user = null;
                localStorage.removeItem(USER_KEY);
            }
            this.updateUI();
        }).catch(() => {
            API.authenticated = !!this.user;
            this.updateUI();
        });
    },

    async register(userData) {
        // Validações locais
        if (!userData.name || !userData.email || !userData.password || !userData.cpf) {
            return { success: false, message: 'Preencha todos os campos obrigatórios' };
        }

        if (userData.password.length < 6) {
            return { success: false, message: 'A senha deve ter no mínimo 6 caracteres' };
        }

        if (!this.validateEmail(userData.email)) {
            return { success: false, message: 'E-mail inválido' };
        }

        if (!this.validateCPF(userData.cpf)) {
            return { success: false, message: 'CPF inválido' };
        }

        // Tenta API primeiro
        const result = await API.register(userData);
        if (result.success) {
            this.user = result.data.user;
            localStorage.setItem(USER_KEY, JSON.stringify(this.user));
            this.updateUI();
            return { success: true, message: 'Cadastro realizado com sucesso! Bem-vinda à VJ Semijoias!' };
        }

        const message = result.offline
            ? 'Não foi possível conectar ao servidor. Tente novamente quando estiver online.'
            : (result.error || 'Erro ao cadastrar');
        return { success: false, message };
    },

    async login(email, password) {
        if (!email || !password) {
            return { success: false, message: 'Preencha e-mail e senha' };
        }

        // Tenta API primeiro
        const result = await API.login(email, password);
        if (result.success) {
            this.user = result.data.user;
            localStorage.setItem(USER_KEY, JSON.stringify(this.user));
            this.updateUI();
            return { success: true, message: 'Login realizado com sucesso!' };
        }

        const message = result.offline
            ? 'Não foi possível conectar ao servidor. Tente novamente quando estiver online.'
            : (result.error || 'E-mail ou senha incorretos');
        return { success: false, message };
    },

    async logout() {
        this.user = null;
        localStorage.removeItem(USER_KEY);
        API.logout();
        this.updateUI();
    },

    isLoggedIn() { return API.isLoggedIn() || !!this.user; },

    getUserName() {
        if (this.user) return this.user.name;
        return '';
    },

    getAllUsers() {
        const stored = localStorage.getItem('vj_users');
        return stored ? JSON.parse(stored) : [];
    },

    validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    validateCPF(cpf) {
        cpf = cpf.replace(/[^\d]/g, '');
        if (cpf.length !== 11) return false;
        if (/^(\d)\1+$/.test(cpf)) return false;

        let sum = 0;
        for (let i = 0; i < 9; i++) sum += parseInt(cpf[i]) * (10 - i);
        let rest = (sum * 10) % 11;
        if (rest === 10) rest = 0;
        if (rest !== parseInt(cpf[9])) return false;

        sum = 0;
        for (let i = 0; i < 10; i++) sum += parseInt(cpf[i]) * (11 - i);
        rest = (sum * 10) % 11;
        if (rest === 10) rest = 0;
        if (rest !== parseInt(cpf[10])) return false;

        return true;
    },

    updateUI() {
        document.querySelectorAll('[data-user-info]').forEach(el => {
            if (this.isLoggedIn()) {
                const name = this.getUserName().split(' ')[0];
                el.innerHTML = `<i>👤</i> ${name}`;
            } else {
                el.innerHTML = '<i>👤</i> Entrar';
            }
        });
    }
};

// ============================================
// PEDIDOS
// ============================================

const Orders = {
    create(orderData) {
        const orders = this.getAll();
        const order = {
            id: 'VJ' + Date.now(),
            ...orderData,
            createdAt: new Date().toISOString()
        };
        orders.push(order);
        localStorage.setItem(ORDERS_KEY, JSON.stringify(orders));
        return order;
    },

    getAll() {
        const stored = localStorage.getItem(ORDERS_KEY);
        return stored ? JSON.parse(stored) : [];
    }
};

// ============================================
// TOAST
// ============================================

function showToast(message, type = 'success', title = '') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const titles = {
        success: title || 'Sucesso!',
        error: title || 'Erro',
        info: title || 'Informação'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-content">
            <strong>${titles[type]}</strong>
            <p>${message}</p>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ============================================
// NAVBAR MOBILE
// ============================================

function toggleMobileMenu() {
    const menu = document.querySelector('.nav-menu');
    const hamburger = document.querySelector('.hamburger');
    menu.classList.toggle('active');
    hamburger.classList.toggle('active');
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    Cart.init();
    Auth.init();
    Cart.updateBadge();

    const hamburger = document.querySelector('.hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', toggleMobileMenu);
    }

    document.querySelectorAll('.nav-menu a').forEach(link => {
        link.addEventListener('click', () => {
            const menu = document.querySelector('.nav-menu');
            if (menu.classList.contains('active')) {
                toggleMobileMenu();
            }
        });
    });
});
