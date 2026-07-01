(function () {
    const state = {
        dashboard: null,
        auditLogs: [],
        products: [],
        suppliers: [],
        customers: [],
        currentProductId: null,
        currentSupplierId: null,
        currentCustomerId: null,
        financeSummary: null,
        expenses: [],
        currentExpenseId: null,
        orders: [],
        currentOrderId: null,
        currentOrderStatus: 'rascunho',
        orderItems: [],
        orderProducts: [],
        stockProducts: [],
        currentStockProductId: null,
    };
    let auditModule = null;
    let dashboardModule = null;
    let productsModule = null;
    let suppliersModule = null;
    let stockModule = null;
    let financeModule = null;
    let ordersModule = null;
    let customersModule = null;

    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));

    function money(value) {
        return Number(value || 0).toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
        });
    }

    function percent(value) {
        return `${(Number(value || 0) * 100).toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })}%`;
    }

    function escapeHTML(value) {
        return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;',
        }[char]));
    }

    function setMessage(id, text, type = '') {
        const element = $(id);
        if (!element) return;
        element.textContent = text || '';
        element.className = `form-message ${type}`.trim();
    }

    function showLogin() {
        $('#login-view').classList.remove('hidden');
        $('#admin-shell').classList.add('hidden');
    }

    function showAdmin() {
        $('#login-view').classList.add('hidden');
        $('#admin-shell').classList.remove('hidden');
    }

    function switchView(view) {
        $$('.nav-item').forEach((button) => button.classList.toggle('active', button.dataset.view === view));
        $$('.view').forEach((section) => section.classList.toggle('active', section.id === `${view}-view`));
        const titles = {
            dashboard: ['Dashboard', 'Indicadores consolidados da operacao'],
            audit: ['Auditoria', 'Acoes criticas registradas'],
            products: ['Produtos', 'Cadastro, publicacao e precificacao'],
            orders: ['Pedidos', 'Vendas simples, estoque e margem'],
            customers: ['Clientes', 'Cadastro, historico e relacionamento'],
            finance: ['Financeiro', 'Resumo simples da operacao'],
            stock: ['Estoque', 'Entradas, saidas, ajustes e historico'],
            suppliers: ['Fornecedores', 'Origem das pecas e contatos'],
        };
        const [title, subtitle] = titles[view] || titles.dashboard;
        $('#view-title').textContent = title;
        $('#view-subtitle').textContent = subtitle;
    }

    function supplierName(id) {
        const supplier = state.suppliers.find((item) => Number(item.id) === Number(id));
        return supplier ? supplier.nome : 'Sem fornecedor';
    }

    function uniqueCategories(products) {
        const values = new Map();
        products.forEach((product) => {
            const id = product.categoria || product.category;
            if (!id) return;
            values.set(id, product.categoryName || product.categoria || product.category);
        });
        return Array.from(values.entries()).sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'));
    }

    function orderStatusLabel(status) {
        return ordersModule ? ordersModule.orderStatusLabel(status) : (status || 'Rascunho');
    }

    function renderOrderCustomerOptions(extraCustomer = null) {
        if (ordersModule) ordersModule.renderOrderCustomerOptions(extraCustomer);
    }

    async function loadOrders() {
        if (!ordersModule) return;
        return ordersModule.loadOrders();
    }

    async function loadOrderProducts() {
        if (!ordersModule) return;
        return ordersModule.loadOrderProducts();
    }

    function formatDate(value) {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '-';
        return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    }

    function formatDateOnly(value) {
        if (!value) return '-';
        const parts = String(value).slice(0, 10).split('-');
        return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : formatDate(value);
    }

    async function loadAuditLogs() {
        if (!auditModule) return;
        return auditModule.loadAuditLogs();
    }

    async function loadDashboard() {
        if (!dashboardModule) return;
        return dashboardModule.loadDashboard();
    }

    async function loadCustomers() {
        if (!customersModule) return;
        return customersModule.loadCustomers();
    }

    async function loadFinance() {
        if (!financeModule) return;
        return financeModule.loadFinance();
    }

    async function loadProducts(options = {}) {
        if (!productsModule) return;
        return productsModule.loadProducts(options);
    }

    async function loadStock() {
        if (!stockModule) return;
        return stockModule.loadStock();
    }

    async function loadSuppliers() {
        if (!suppliersModule) return;
        return suppliersModule.loadSuppliers();
    }

    function renderPricing() {
        if (productsModule) productsModule.renderPricing();
    }

    function renderProductFilterOptions() {
        if (productsModule) productsModule.renderFilterOptions();
    }

    function renderStockFilterOptions() {
        if (stockModule) stockModule.renderStockFilterOptions();
    }

    async function refresh() {
        try {
            await loadDashboard();
            await loadAuditLogs();
            await loadSuppliers();
            await loadCustomers();
            await loadProducts({ updateOptions: true });
            await loadOrderProducts();
            await loadOrders();
            await loadStock();
            await loadFinance();
            renderPricing();
            showAdmin();
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#login-message', error.message, 'error');
            showLogin();
        }
    }

    function bindEvents() {
        $('#login-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            setMessage('#login-message', '');
            try {
                await VJAdminAPI.login($('#login-email').value.trim(), $('#login-password').value);
                $('#login-password').value = '';
                await refresh();
            } catch (error) {
                setMessage('#login-message', error.message, 'error');
            }
        });
        $('#logout-button').addEventListener('click', async () => {
            await VJAdminAPI.logout();
            showLogin();
        });
        $$('.nav-item').forEach((button) => button.addEventListener('click', async () => {
            switchView(button.dataset.view);
            if (button.dataset.view === 'dashboard') await loadDashboard();
            if (button.dataset.view === 'audit') await loadAuditLogs();
            if (button.dataset.view === 'orders') await loadOrders();
            if (button.dataset.view === 'customers') await loadCustomers();
            if (button.dataset.view === 'finance') await loadFinance();
            if (button.dataset.view === 'stock') await loadStock();
        }));
        auditModule.bindEvents();
        dashboardModule.bindEvents();
        productsModule.bindEvents();
        suppliersModule.bindEvents();
        stockModule.bindEvents();
        financeModule.bindEvents();
        ordersModule.bindEvents();
        customersModule.bindEvents();
    }

    document.addEventListener('DOMContentLoaded', () => {
        auditModule = window.createVJAdminAudit({
            state,
            $,
            api: VJAdminAPI,
            escapeHTML,
            formatDate,
            setMessage,
            showLogin,
        });
        dashboardModule = window.createVJAdminDashboard({
            state,
            $,
            api: VJAdminAPI,
            money,
            percent,
            escapeHTML,
            setMessage,
            showLogin,
        });
        productsModule = window.createVJAdminProducts({
            state,
            $,
            $$,
            api: VJAdminAPI,
            pricing: VJAdminPricing,
            money,
            percent,
            escapeHTML,
            supplierName,
            setMessage,
            showLogin,
            renderStockFilterOptions,
        });
        suppliersModule = window.createVJAdminSuppliers({
            state,
            $,
            $$,
            api: VJAdminAPI,
            escapeHTML,
            setMessage,
            showLogin,
            afterSuppliersChanged: renderProductFilterOptions,
        });
        stockModule = window.createVJAdminStock({
            state,
            $,
            $$,
            api: VJAdminAPI,
            escapeHTML,
            formatDate,
            supplierName,
            uniqueCategories,
            setMessage,
            showLogin,
            loadProducts,
            loadOrderProducts,
        });
        ordersModule = window.createVJAdminOrders({
            state,
            $,
            $$,
            api: VJAdminAPI,
            pricing: VJAdminPricing,
            money,
            percent,
            escapeHTML,
            formatDate,
            setMessage,
            showLogin,
            loadStock,
            loadFinance,
        });
        customersModule = window.createVJAdminCustomers({
            state,
            $,
            $$,
            api: VJAdminAPI,
            money,
            escapeHTML,
            formatDate,
            orderStatusLabel,
            renderOrderCustomerOptions,
            setMessage,
            showLogin,
        });
        financeModule = window.createVJAdminFinance({
            state,
            $,
            $$,
            api: VJAdminAPI,
            money,
            escapeHTML,
            formatDate,
            formatDateOnly,
            setMessage,
            showLogin,
        });
        bindEvents();
        refresh();
    });
})();