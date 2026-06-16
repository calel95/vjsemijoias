// ============================================
// CARRINHO DE COMPRAS - VJ SEMIJOIAS
// Gerencia estado do carrinho via localStorage
// ============================================

const CART_KEY = 'vj_cart';
const USER_KEY = 'vj_user';
const ORDERS_KEY = 'vj_orders';
const COUPON_KEY = 'vj_coupon';
const COUPON_PERCENT_KEY = 'vj_coupon_percent';

const Cart = {
    items: [],
    pricing: {
        shipping: 0,
        shippingMessage: 'Frete Gratis!',
        discount: 0,
        discountCode: '',
        discountPercent: 0,
        loaded: false,
    },

    init() {
        const stored = localStorage.getItem(CART_KEY);
        this.items = stored ? JSON.parse(stored) : [];
        this.updateBadge();
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

        this.save();
        this.updateBadge();
        return true;
    },

    remove(productId) {
        this.items = this.items.filter(item => item.id !== productId);
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
                this.save();
                this.updateBadge();
            }
        }
    },

    clear() {
        this.items = [];
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
        return this.pricing.shippingMessage || 'Frete calculado no checkout';
    },

    async refreshPricing(zipCode = '') {
        const subtotal = this.getSubtotal();
        const [shippingResult, couponResult] = await Promise.all([
            API.calculateShipping(subtotal, zipCode),
            this.refreshCoupon(subtotal),
        ]);

        if (shippingResult.success) {
            this.pricing.shipping = Number(shippingResult.data.shipping || 0);
            this.pricing.shippingMessage = shippingResult.data.message || '';
        } else {
            this.pricing.shipping = 0;
            this.pricing.shippingMessage = 'Frete calculado no fechamento do pedido';
        }

        this.pricing.discount = couponResult.discount;
        this.pricing.discountCode = couponResult.code;
        this.pricing.discountPercent = couponResult.percent;
        this.pricing.loaded = true;
    },

    async refreshCoupon(subtotal) {
        const code = (localStorage.getItem(COUPON_KEY) || '').trim().toUpperCase();
        if (!code) {
            localStorage.removeItem(COUPON_PERCENT_KEY);
            return { code: '', percent: 0, discount: 0 };
        }

        const result = await API.validateCoupon(code);
        if (!result.success || !result.data.valid) {
            localStorage.removeItem(COUPON_KEY);
            localStorage.removeItem(COUPON_PERCENT_KEY);
            return { code: '', percent: 0, discount: 0 };
        }

        const percent = Number(result.data.discount_percent || 0);
        localStorage.setItem(COUPON_KEY, result.data.code);
        localStorage.setItem(COUPON_PERCENT_KEY, String(percent));
        return {
            code: result.data.code,
            percent,
            discount: subtotal * (percent / 100),
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
        if (API.token) {
            API.getMe().then(result => {
                if (result.success) {
                    this.user = result.data;
                    localStorage.setItem(USER_KEY, JSON.stringify(this.user));
                    this.updateUI();
                } else {
                    this.logout();
                }
            }).catch(() => { });
        } else {
            this.user = null;
            localStorage.removeItem(USER_KEY);
        }
        this.updateUI();
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

    isLoggedIn() { return !!API.token; },

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
