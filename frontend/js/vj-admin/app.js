(function () {
    const state = {
        products: [],
        suppliers: [],
        customers: [],
        currentProductId: null,
        currentSupplierId: null,
        currentCustomerId: null,
        orders: [],
        currentOrderId: null,
        currentOrderStatus: 'rascunho',
        orderItems: [],
        orderProducts: [],
        stockProducts: [],
        currentStockProductId: null,
    };

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
            products: ['Produtos', 'Cadastro, publicacao e precificacao'],
            orders: ['Pedidos', 'Vendas simples, estoque e margem'],
            customers: ['Clientes', 'Cadastro, historico e relacionamento'],
            stock: ['Estoque', 'Entradas, saidas, ajustes e historico'],
            suppliers: ['Fornecedores', 'Origem das pecas e contatos'],
        };
        const [title, subtitle] = titles[view] || titles.products;
        $('#view-title').textContent = title;
        $('#view-subtitle').textContent = subtitle;
    }

    function supplierName(id) {
        const supplier = state.suppliers.find((item) => Number(item.id) === Number(id));
        return supplier ? supplier.nome : 'Sem fornecedor';
    }

    function productFilters() {
        return {
            search: $('#product-search').value.trim(),
            categoria: $('#filter-category').value,
            fornecedor_id: $('#filter-supplier').value,
            status: $('#filter-status').value,
        };
    }

    function orderFilters() {
        return {
            search: $('#order-search').value.trim(),
            status: $('#order-filter-status').value,
        };
    }


    function customerFilters() {
        return {
            search: $('#customer-search').value.trim(),
            status: $('#customer-filter-status').value,
            cidade: $('#customer-filter-city').value.trim(),
            origem: $('#customer-filter-source').value.trim(),
        };
    }
    function stockFilters() {
        return {
            produto: $('#stock-search').value.trim(),
            categoria: $('#stock-filter-category').value,
            fornecedor_id: $('#stock-filter-supplier').value,
            status: $('#stock-filter-status').value,
        };
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

    function renderFilterOptions() {
        const selectedCategory = $('#filter-category').value;
        const selectedSupplier = $('#filter-supplier').value;
        $('#filter-category').innerHTML = '<option value="">Todas</option>' + uniqueCategories(state.products)
            .map(([id, label]) => `<option value="${escapeHTML(id)}">${escapeHTML(label)}</option>`)
            .join('');
        $('#filter-category').value = selectedCategory;
        $('#filter-supplier').innerHTML = '<option value="">Todos</option>' + state.suppliers
            .map((supplier) => `<option value="${supplier.id}">${escapeHTML(supplier.nome)}</option>`)
            .join('');
        $('#filter-supplier').value = selectedSupplier;
        renderStockFilterOptions();
    }

    function renderStockFilterOptions() {
        const category = $('#stock-filter-category');
        const supplier = $('#stock-filter-supplier');
        if (!category || !supplier) return;
        const selectedCategory = category.value;
        const selectedSupplier = supplier.value;
        category.innerHTML = '<option value="">Todas</option>' + uniqueCategories(state.products)
            .map(([id, label]) => `<option value="${escapeHTML(id)}">${escapeHTML(label)}</option>`)
            .join('');
        category.value = selectedCategory;
        supplier.innerHTML = '<option value="">Todos</option>' + state.suppliers
            .map((item) => `<option value="${item.id}">${escapeHTML(item.nome)}</option>`)
            .join('');
        supplier.value = selectedSupplier;
    }

    function renderMetrics() {
        const products = state.products;
        const published = products.filter((item) => item.publicado && ['publicado', 'ativo'].includes(item.status));
        const avgPix = products.length
            ? products.reduce((sum, item) => sum + Number(item.preco_pix || item.price || 0), 0) / products.length
            : 0;
        const avgProfit = products.length
            ? products.reduce((sum, item) => sum + Number(item.lucro_pix || 0), 0) / products.length
            : 0;
        $('#product-metrics').innerHTML = `
            <div><strong>${products.length}</strong><span>Produtos</span></div>
            <div><strong>${published.length}</strong><span>Publicados</span></div>
            <div><strong>${money(avgPix)}</strong><span>Preco pix medio</span></div>
            <div><strong>${money(avgProfit)}</strong><span>Lucro pix medio</span></div>
        `;
    }

    function renderProducts() {
        const products = state.products;
        $('#product-count-label').textContent = `${products.length} encontrado${products.length === 1 ? '' : 's'}`;
        if (!products.length) {
            $('#product-list').innerHTML = '<p class="empty-state">Nenhum produto encontrado.</p>';
            return;
        }
        $('#product-list').innerHTML = products.map((product) => {
            const active = Number(product.id) === Number(state.currentProductId) ? ' active' : '';
            const status = product.publicado ? 'publicado' : (product.status || 'rascunho');
            const updatedBy = product.updated_by?.email ? `Atualizado por ${product.updated_by.email}` : 'Sem editor registrado';
            return `
                <button class="row-item${active}" type="button" data-product-id="${product.id}">
                    <span class="row-title">
                        <strong>${escapeHTML(product.nome || product.name)}</strong>
                        <span class="status-badge ${escapeHTML(status)}">${escapeHTML(status)}</span>
                    </span>
                    <span class="row-meta">
                        <span>${escapeHTML(product.codigo || '-')}</span>
                        <span>${escapeHTML(product.categoria || product.category || '-')}</span>
                        <span>${escapeHTML(supplierName(product.fornecedor_id))}</span>
                    </span>
                    <span class="row-meta">
                        <span>Pix ${money(product.preco_pix || product.price)}</span>
                        <span>Custo ${money(product.custo_total)}</span>
                        <span>Estoque ${Number(product.estoque || product.stock_quantity || 0)}</span>
                    </span>
                    <span class="row-meta"><span>${escapeHTML(updatedBy)}</span></span>
                </button>
            `;
        }).join('');
        $$('#product-list [data-product-id]').forEach((button) => {
            button.addEventListener('click', () => editProduct(button.dataset.productId));
        });
    }

    function roundMoney(value) {
        return Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100;
    }

    function orderProduct(id) {
        return state.orderProducts.find((item) => Number(item.id) === Number(id));
    }

    function orderPaymentField() {
        const method = $('#order-payment-method').value;
        const installments = Number($('#order-installments').value || 1);
        if (method === 'pix') return 'preco_pix';
        if (method === 'debito') return 'preco_debito';
        return installments <= 1 ? 'preco_credito_vista' : `preco_credito_${installments}x`;
    }

    function orderPaymentFee() {
        return Number(VJAdminPricing.fees[orderPaymentField()] || 0);
    }

    function orderUnitPrice(product) {
        const field = orderPaymentField();
        return Number(product?.[field] ?? product?.price ?? 0);
    }

    function orderUnitCost(product) {
        return Number(product?.custo_total ?? 0);
    }

    function orderStatusLabel(status) {
        return {
            rascunho: 'Rascunho',
            confirmado: 'Confirmado',
            cancelado: 'Cancelado',
        }[status] || status || 'Rascunho';
    }


    function customerOptionLabel(customer) {
        const contact = customer.whatsapp || customer.email || customer.instagram || 'sem contato';
        return `${customer.nome} - ${contact}`;
    }

    function renderOrderCustomerOptions(extraCustomer = null) {
        const select = $('#order-customer');
        if (!select) return;
        const selected = select.value;
        const activeCustomers = state.customers.filter((customer) => customer.status === 'ativo');
        const hasExtra = extraCustomer && !activeCustomers.some((customer) => Number(customer.id) === Number(extraCustomer.id));
        const customers = hasExtra ? activeCustomers.concat([extraCustomer]) : activeCustomers;
        select.innerHTML = '<option value="">Pedido avulso</option>' + customers
            .map((customer) => `<option value="${customer.id}">${escapeHTML(customerOptionLabel(customer))}</option>`)
            .join('');
        select.value = selected;
    }

    function selectedOrderCustomer() {
        const id = $('#order-customer')?.value;
        if (!id) return null;
        return state.customers.find((customer) => Number(customer.id) === Number(id)) || null;
    }

    function syncOrderCustomerFields() {
        const customer = selectedOrderCustomer();
        if (customer) {
            $('#order-client-name').value = customer.nome || '';
            $('#order-client-whatsapp').value = customer.whatsapp || '';
        }
        setOrderLocked();
    }
    function renderOrderProductOptions() {
        const select = $('#order-product');
        if (!select) return;
        const selected = select.value;
        select.innerHTML = '<option value="">Selecione</option>' + state.orderProducts
            .map((product) => {
                const balance = Number(product.saldo_estoque ?? product.stock_quantity ?? product.estoque ?? 0);
                const label = `${product.codigo || product.id} - ${product.nome || product.name} (${balance})`;
                return `<option value="${product.id}">${escapeHTML(label)}</option>`;
            })
            .join('');
        select.value = selected;
    }

    function orderTotals() {
        const fee = orderPaymentFee();
        const items = state.orderItems.map((item) => {
            const product = orderProduct(item.produto_id) || item.produto || {};
            const quantity = Number(item.quantidade || 0);
            const unitPrice = Number(item.preco_unitario ?? orderUnitPrice(product));
            const unitCost = Number(item.custo_unitario ?? orderUnitCost(product));
            const unitFee = roundMoney(unitPrice * fee / 100);
            const unitProfit = roundMoney(Number(item.lucro_unitario ?? (unitPrice - unitCost - unitFee)));
            return {
                ...item,
                product,
                quantity,
                unitPrice,
                unitCost,
                unitProfit,
                total: roundMoney(unitPrice * quantity),
                costTotal: roundMoney(unitCost * quantity),
            };
        });
        const subtotal = roundMoney(items.reduce((sum, item) => sum + item.total, 0));
        const discount = Math.min(roundMoney($('#order-discount').value || 0), subtotal);
        const total = roundMoney(subtotal - discount);
        const paymentTax = roundMoney(total * fee / 100);
        const costTotal = roundMoney(items.reduce((sum, item) => sum + item.costTotal, 0));
        const profit = roundMoney(total - paymentTax - costTotal);
        const margin = total ? profit / total : 0;
        return { items, subtotal, discount, total, paymentTax, profit, margin, fee };
    }

    function renderOrderItems() {
        const locked = state.currentOrderStatus !== 'rascunho';
        const totals = orderTotals();
        if (!state.orderItems.length) {
            $('#order-items-list').innerHTML = '<p class="empty-state compact">Nenhum item adicionado.</p>';
        } else {
            $('#order-items-list').innerHTML = totals.items.map((item, index) => {
                const productName = item.product?.nome || item.product?.name || item.produto?.nome || `Produto ${item.produto_id}`;
                const code = item.product?.codigo || item.produto?.codigo || item.produto_id;
                return `
                    <article class="order-item-row">
                        <div>
                            <strong>${escapeHTML(productName)}</strong>
                            <span>${escapeHTML(code)} | Qtd ${item.quantity}</span>
                        </div>
                        <div>
                            <strong>${money(item.total)}</strong>
                            <span>${money(item.unitPrice)} un. | Lucro ${money(item.unitProfit)} un.</span>
                        </div>
                        ${locked ? '' : `<button class="ghost-button" type="button" data-remove-order-item="${index}">Remover</button>`}
                    </article>
                `;
            }).join('');
            $$('[data-remove-order-item]').forEach((button) => {
                button.addEventListener('click', () => {
                    state.orderItems.splice(Number(button.dataset.removeOrderItem), 1);
                    renderOrderItems();
                });
            });
        }
        $('#order-totals').innerHTML = `
            <div class="readonly-grid order-total-grid">
                <label class="readonly-field"><span>Subtotal</span><input value="${money(totals.subtotal)}" readonly tabindex="-1"></label>
                <label class="readonly-field"><span>Desconto</span><input value="${money(totals.discount)}" readonly tabindex="-1"></label>
                <label class="readonly-field"><span>Taxa pagamento</span><input value="${money(totals.paymentTax)}" readonly tabindex="-1"></label>
                <label class="readonly-field"><span>Total</span><input value="${money(totals.total)}" readonly tabindex="-1"></label>
                <label class="readonly-field"><span>Lucro estimado</span><input value="${money(totals.profit)}" readonly tabindex="-1"></label>
                <label class="readonly-field"><span>Margem</span><input value="${percent(totals.margin)}" readonly tabindex="-1"></label>
            </div>
        `;
    }

    function setOrderLocked() {
        const locked = state.currentOrderStatus !== 'rascunho';
        ['#order-customer', '#order-client-name', '#order-client-whatsapp', '#order-payment-method', '#order-installments', '#order-discount', '#order-product', '#order-quantity', '#add-order-item-button']
            .forEach((selector) => { $(selector).disabled = locked; });
        const linkedCustomer = Boolean($('#order-customer')?.value);
        $('#order-client-name').readOnly = locked || linkedCustomer;
        $('#order-client-whatsapp').readOnly = locked || linkedCustomer;
        $('#save-order-button').disabled = locked;
        $('#confirm-order-button').disabled = locked || !state.orderItems.length;
        $('#cancel-order-button').disabled = state.currentOrderStatus === 'cancelado';
    }

    function renderOrders() {
        const orders = state.orders;
        $('#order-count-label').textContent = `${orders.length} encontrado${orders.length === 1 ? '' : 's'}`;
        if (!orders.length) {
            $('#order-list').innerHTML = '<p class="empty-state">Nenhum pedido encontrado.</p>';
            return;
        }
        $('#order-list').innerHTML = orders.map((order) => {
            const active = Number(order.id) === Number(state.currentOrderId) ? ' active' : '';
            return `
                <button class="row-item${active}" type="button" data-order-id="${order.id}">
                    <span class="row-title">
                        <strong>#${order.id} ${escapeHTML(order.cliente_nome || 'Cliente')}</strong>
                        <span class="status-badge ${escapeHTML(order.status)}">${escapeHTML(orderStatusLabel(order.status))}</span>
                    </span>
                    <span class="row-meta">
                        <span>${escapeHTML(order.cliente_whatsapp || '-')}</span>
                        <span>${escapeHTML(order.forma_pagamento || 'pix')} ${Number(order.parcelas || 1)}x</span>
                        <span>${formatDate(order.updated_at || order.created_at)}</span>
                    </span>
                    <span class="row-meta"><span>Total ${money(order.total)}</span><span>Lucro ${money(order.lucro_estimado)}</span></span>
                </button>
            `;
        }).join('');
        $$('#order-list [data-order-id]').forEach((button) => {
            button.addEventListener('click', () => editOrder(button.dataset.orderId));
        });
    }

    function resetOrderForm() {
        state.currentOrderId = null;
        state.currentOrderStatus = 'rascunho';
        state.orderItems = [];
        $('#order-form').reset();
        $('#order-id').value = '';
        $('#order-customer').value = '';
        $('#order-installments').value = '1';
        $('#order-discount').value = '0';
        $('#order-form-title').textContent = 'Novo pedido';
        $('#order-status-label').textContent = 'Rascunho';
        setMessage('#order-message', '');
        renderOrderItems();
        setOrderLocked();
        renderOrders();
    }

    async function editOrder(id) {
        try {
            const order = await VJAdminAPI.order(id);
            state.currentOrderId = order.id;
            state.currentOrderStatus = order.status || 'rascunho';
            state.orderItems = (order.items || []).map((item) => ({
                produto_id: item.produto_id,
                quantidade: item.quantidade,
                preco_unitario: item.preco_unitario,
                custo_unitario: item.custo_unitario,
                lucro_unitario: item.lucro_unitario,
                produto: item.produto,
            }));
            $('#order-id').value = order.id;
            renderOrderCustomerOptions(order.customer);
            $('#order-customer').value = order.customer_id || '';
            $('#order-client-name').value = order.cliente_nome || '';
            $('#order-client-whatsapp').value = order.cliente_whatsapp || '';
            $('#order-payment-method').value = order.forma_pagamento || 'pix';
            $('#order-installments').value = order.parcelas || 1;
            $('#order-discount').value = order.desconto_total || 0;
            $('#order-form-title').textContent = `Pedido #${order.id}`;
            $('#order-status-label').textContent = orderStatusLabel(order.status);
            renderOrderItems();
            setOrderLocked();
            renderOrders();
            setMessage('#order-message', order.updated_by?.email ? `Atualizado por ${order.updated_by.email}` : '');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#order-message', error.message, 'error');
        }
    }

    function orderPayload() {
        return {
            customer_id: $('#order-customer').value || null,

            cliente_nome: $('#order-client-name').value.trim(),
            cliente_whatsapp: $('#order-client-whatsapp').value.trim(),
            forma_pagamento: $('#order-payment-method').value,
            parcelas: $('#order-installments').value || 1,
            desconto_total: $('#order-discount').value || 0,
            items: state.orderItems.map((item) => ({
                produto_id: item.produto_id,
                quantidade: item.quantidade,
            })),
        };
    }

    async function persistCurrentOrder() {
        const saved = await VJAdminAPI.saveOrder(orderPayload(), $('#order-id').value || null);
        await loadOrders();
        await editOrder(saved.id);
        return saved;
    }

    async function saveOrder(event) {
        event.preventDefault();
        try {
            await persistCurrentOrder();
            setMessage('#order-message', 'Pedido salvo.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#order-message', error.message, 'error');
        }
    }

    function addOrderItem() {
        const productId = Number($('#order-product').value || 0);
        const quantity = Number($('#order-quantity').value || 1);
        if (!productId || quantity < 1) {
            setMessage('#order-message', 'Selecione produto e quantidade.', 'error');
            return;
        }
        const existing = state.orderItems.find((item) => Number(item.produto_id) === productId);
        if (existing) existing.quantidade = Number(existing.quantidade || 0) + quantity;
        else state.orderItems.push({ produto_id: productId, quantidade: quantity });
        $('#order-quantity').value = '1';
        setMessage('#order-message', '');
        renderOrderItems();
        setOrderLocked();
    }

    async function confirmCurrentOrder() {
        if (!state.orderItems.length) {
            setMessage('#order-message', 'Pedido deve conter ao menos um item.', 'error');
            return;
        }
        if (!window.confirm('Confirmar pedido e baixar estoque?')) return;
        try {
            const saved = $('#order-id').value ? null : await persistCurrentOrder();
            const id = $('#order-id').value || saved?.id;
            const confirmed = await VJAdminAPI.confirmOrder(id);
            await loadOrders();
            await loadStock();
            await loadOrderProducts();
            await editOrder(confirmed.id);
            setMessage('#order-message', 'Pedido confirmado e estoque baixado.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#order-message', error.message, 'error');
        }
    }

    async function cancelCurrentOrder() {
        const id = $('#order-id').value;
        if (!id) {
            resetOrderForm();
            return;
        }
        if (!window.confirm('Cancelar pedido? Se estiver confirmado, o estoque sera devolvido.')) return;
        try {
            const canceled = await VJAdminAPI.cancelOrder(id);
            await loadOrders();
            await loadStock();
            await loadOrderProducts();
            await editOrder(canceled.id);
            setMessage('#order-message', 'Pedido cancelado.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#order-message', error.message, 'error');
        }
    }
    function formatDate(value) {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '-';
        return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    }

    function stockStatusLabel(product) {
        if ((product.status || '').toLowerCase() === 'inativo') return 'Inativo';
        if (product.stock_status === 'out_of_stock') return 'Sem estoque';
        if (product.stock_status === 'preorder') return 'Sob encomenda';
        return 'Disponivel';
    }

    function isLowStock(product) {
        const balance = Number(product.saldo_estoque ?? product.stock_quantity ?? product.estoque ?? 0);
        const alert = Number(product.low_stock_alert ?? 0);
        return balance > 0 && alert >= 0 && balance <= alert;
    }

    function renderStockList() {
        const products = state.stockProducts;
        $('#stock-count-label').textContent = `${products.length} encontrado${products.length === 1 ? '' : 's'}`;
        if (!products.length) {
            $('#stock-list').innerHTML = '<p class="empty-state">Nenhum produto encontrado.</p>';
            renderStockDetail(null, []);
            return;
        }
        $('#stock-list').innerHTML = products.map((product) => {
            const balance = Number(product.saldo_estoque ?? product.stock_quantity ?? product.estoque ?? 0);
            const active = Number(product.id) === Number(state.currentStockProductId) ? ' active' : '';
            const low = isLowStock(product) ? ' low-stock' : '';
            const empty = balance <= 0 ? ' out-of-stock' : '';
            return `
                <button class="row-item stock-row${active}${low}${empty}" type="button" data-stock-product-id="${product.id}">
                    <span class="row-title">
                        <strong>${escapeHTML(product.nome || product.name)}</strong>
                        <span class="status-badge ${escapeHTML(product.stock_status || 'available')}">${escapeHTML(stockStatusLabel(product))}</span>
                    </span>
                    <span class="row-meta">
                        <span>${escapeHTML(product.codigo || '-')}</span>
                        <span>${escapeHTML(product.categoria || product.category || '-')}</span>
                        <span>${escapeHTML(supplierName(product.fornecedor_id))}</span>
                    </span>
                    <span class="row-meta">
                        <span>Saldo ${balance}</span>
                        <span>Alerta ${Number(product.low_stock_alert ?? 0)}</span>
                        ${isLowStock(product) ? '<span>Estoque baixo</span>' : ''}
                    </span>
                </button>
            `;
        }).join('');
        $$('#stock-list [data-stock-product-id]').forEach((button) => {
            button.addEventListener('click', () => selectStockProduct(button.dataset.stockProductId));
        });
    }

    function renderStockDetail(product, movements = []) {
        if (!product) {
            $('#stock-product-id').value = '';
            $('#stock-product-title').textContent = 'Movimentacao';
            $('#stock-product-balance').textContent = 'Selecione um produto';
            $('#stock-summary').innerHTML = '<p class="empty-state compact">Escolha um produto para registrar entrada, saida ou ajuste.</p>';
            $('#stock-history').innerHTML = '<p class="empty-state compact">Sem produto selecionado.</p>';
            return;
        }
        const balance = Number(product.saldo_estoque ?? product.stock_quantity ?? product.estoque ?? 0);
        $('#stock-product-id').value = product.id;
        $('#stock-product-title').textContent = product.codigo || product.nome || 'Produto';
        $('#stock-product-balance').textContent = `Saldo atual: ${balance}`;
        $('#stock-summary').innerHTML = `
            <div><span>Produto</span><strong>${escapeHTML(product.nome || product.name)}</strong></div>
            <div><span>Categoria</span><strong>${escapeHTML(product.categoria || product.category || '-')}</strong></div>
            <div><span>Fornecedor</span><strong>${escapeHTML(supplierName(product.fornecedor_id))}</strong></div>
            <div><span>Status</span><strong>${escapeHTML(stockStatusLabel(product))}</strong></div>
        `;
        if (!movements.length) {
            $('#stock-history').innerHTML = '<p class="empty-state compact">Nenhuma movimentacao registrada.</p>';
            return;
        }
        $('#stock-history').innerHTML = movements.map((movement) => `
            <article class="stock-history-item">
                <div class="row-title">
                    <strong>${escapeHTML(movement.tipo)}</strong>
                    <span>${formatDate(movement.created_at)}</span>
                </div>
                <div class="row-meta">
                    <span>Qtd ${Number(movement.quantidade || 0)}</span>
                    <span>Delta ${Number(movement.delta || 0)}</span>
                    <span>${Number(movement.saldo_anterior || 0)} -> ${Number(movement.saldo_atual || 0)}</span>
                </div>
                <p>${escapeHTML(movement.motivo || '-')}</p>
                ${movement.observacoes ? `<small>${escapeHTML(movement.observacoes)}</small>` : ''}
                <small>${escapeHTML(movement.created_by?.email || 'Usuario nao registrado')}</small>
            </article>
        `).join('');
    }

    async function selectStockProduct(id) {
        state.currentStockProductId = Number(id);
        renderStockList();
        try {
            const data = await VJAdminAPI.productStock(id);
            renderStockDetail(data.produto, data.movimentacoes || []);
            setMessage('#stock-message', '');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#stock-message', error.message, 'error');
        }
    }

    async function saveStockMovement(event) {
        event.preventDefault();
        const id = $('#stock-product-id').value;
        if (!id) {
            setMessage('#stock-message', 'Selecione um produto.', 'error');
            return;
        }
        const tipo = $('#stock-movement-type').value;
        const quantidade = $('#stock-movement-quantity').value;
        if (tipo !== 'entrada' && !window.confirm('Confirmar movimentacao de estoque?')) return;
        try {
            const saved = await VJAdminAPI.moveStock(id, {
                tipo,
                quantidade,
                motivo: $('#stock-movement-reason').value.trim(),
                observacoes: $('#stock-movement-notes').value.trim(),
            });
            $('#stock-movement-form').reset();
            await loadProducts({ updateOptions: true });
            await loadOrderProducts();
            await loadStock();
            await selectStockProduct(saved.produto.id);
            setMessage('#stock-message', 'Movimentacao registrada.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#stock-message', error.message, 'error');
        }
    }
    function renderSuppliers() {
        const options = ['<option value="">Sem fornecedor</option>'].concat(
            state.suppliers.map((supplier) => `<option value="${supplier.id}">${escapeHTML(supplier.nome)}</option>`)
        );
        $('#product-fornecedor').innerHTML = options.join('');
        if (!state.suppliers.length) {
            $('#supplier-list').innerHTML = '<p class="empty-state">Nenhum fornecedor cadastrado.</p>';
            return;
        }
        $('#supplier-list').innerHTML = state.suppliers.map((supplier) => {
            const active = Number(supplier.id) === Number(state.currentSupplierId) ? ' active' : '';
            return `
                <button class="row-item${active}" type="button" data-supplier-id="${supplier.id}">
                    <span class="row-title"><strong>${escapeHTML(supplier.nome)}</strong></span>
                    <span class="row-meta">
                        <span>${escapeHTML(supplier.whatsapp || 'WhatsApp nao informado')}</span>
                        <span>${escapeHTML(supplier.instagram || 'Instagram nao informado')}</span>
                    </span>
                </button>
            `;
        }).join('');
        $$('#supplier-list [data-supplier-id]').forEach((button) => {
            button.addEventListener('click', () => editSupplier(button.dataset.supplierId));
        });
    }

    function currentPricingInput() {
        return VJAdminPricing.calculate(
            $('#product-custo-peca').value,
            $('#product-custo-embalagem').value || 9.34,
            $('#product-markup').value || 2,
        );
    }

    function renderPricing(values = currentPricingInput()) {
        const cells = [
            ['Custo total', money(values.custo_total)],
            ['Markup', Number(values.markup || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })],
            ['Lucro pix', money(values.lucro_pix)],
            ['Margem pix', percent(values.margem_pix)],
            ['Pix', money(values.preco_pix)],
            ['Debito', money(values.preco_debito)],
            ['Credito 1x', money(values.preco_credito_vista)],
            ['Credito 2x', money(values.preco_credito_2x)],
            ['Credito 3x', money(values.preco_credito_3x)],
            ['Credito 4x', money(values.preco_credito_4x)],
            ['Credito 5x', money(values.preco_credito_5x)],
            ['Credito 6x', money(values.preco_credito_6x)],
            ['Credito 7x', money(values.preco_credito_7x)],
            ['Credito 8x', money(values.preco_credito_8x)],
            ['Credito 9x', money(values.preco_credito_9x)],
            ['Credito 10x', money(values.preco_credito_10x)],
            ['Credito 11x', money(values.preco_credito_11x)],
            ['Credito 12x', money(values.preco_credito_12x)],
        ];
        $('#pricing-preview').innerHTML = `<div class="readonly-grid">${cells.map(([label, value]) => `
            <label class="readonly-field"><span>${label}</span><input value="${escapeHTML(value)}" readonly tabindex="-1"></label>
        `).join('')}</div>`;
    }

    function resetProductForm() {
        state.currentProductId = null;
        $('#product-form').reset();
        $('#product-id').value = '';
        $('#product-custo-embalagem').value = '9.34';
        $('#product-markup').value = '2.00';
        $('#product-estoque').value = '0';
        $('#product-estoque').readOnly = false;
        $('#product-status').value = 'rascunho';
        $('#product-publicado').checked = false;
        $('#product-form-title').textContent = 'Novo produto';
        setMessage('#product-message', '');
        renderPricing();
        renderProducts();
    }

    function editProduct(id) {
        const product = state.products.find((item) => Number(item.id) === Number(id));
        if (!product) return;
        state.currentProductId = product.id;
        $('#product-id').value = product.id;
        $('#product-codigo').value = product.codigo || product.sku || '';
        $('#product-nome').value = product.nome || product.name || '';
        $('#product-categoria').value = product.categoria || product.category || '';
        $('#product-fornecedor').value = product.fornecedor_id || '';
        $('#product-material').value = product.material || '';
        $('#product-banho').value = product.banho || '';
        $('#product-cor').value = product.cor || '';
        $('#product-estoque').value = product.estoque ?? product.stock_quantity ?? 0;
        $('#product-estoque').readOnly = true;
        $('#product-custo-peca').value = product.custo_peca ?? '';
        $('#product-custo-embalagem').value = product.custo_embalagem ?? 9.34;
        $('#product-markup').value = product.markup ?? 2;
        $('#product-status').value = ['rascunho', 'publicado', 'inativo'].includes(product.status) ? product.status : 'publicado';
        $('#product-publicado').checked = Boolean(product.publicado);
        $('#product-imagem').value = product.imagem_url || product.image || '';
        $('#product-descricao').value = product.descricao || product.description || '';
        $('#product-form-title').textContent = `Editar ${product.codigo || product.nome || product.id}`;
        const audit = [
            product.created_by?.email ? `Criado por ${product.created_by.email}` : '',
            product.updated_by?.email ? `Atualizado por ${product.updated_by.email}` : '',
        ].filter(Boolean).join(' | ');
        setMessage('#product-message', audit, audit ? 'success' : '');
        renderPricing(product);
        renderProducts();
    }

    function productPayload() {
        const payload = {
            codigo: $('#product-codigo').value.trim(),
            nome: $('#product-nome').value.trim(),
            categoria: $('#product-categoria').value.trim(),
            fornecedor_id: $('#product-fornecedor').value || null,
            material: $('#product-material').value.trim(),
            banho: $('#product-banho').value.trim(),
            cor: $('#product-cor').value.trim(),
            descricao: $('#product-descricao').value.trim(),
            custo_peca: $('#product-custo-peca').value,
            custo_embalagem: $('#product-custo-embalagem').value || 9.34,
            markup: $('#product-markup').value || 2,
            imagem_url: $('#product-imagem').value.trim(),
            status: $('#product-status').value,
            publicado: $('#product-publicado').checked,
        };
        if (!$('#product-id').value) payload.estoque = $('#product-estoque').value || 0;
        return payload;
    }

    async function saveProduct(event) {
        event.preventDefault();
        const id = $('#product-id').value;
        try {
            const saved = await VJAdminAPI.saveProduct(productPayload(), id || null);
            await loadProducts();
            editProduct(saved.id);
            setMessage('#product-message', 'Produto salvo.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#product-message', error.message, 'error');
        }
    }

    async function publishCurrentProduct(published) {
        const id = $('#product-id').value;
        if (!id) return;
        if (!published && !window.confirm('Despublicar este produto do site?')) return;
        try {
            const saved = published
                ? await VJAdminAPI.publishProduct(id)
                : await VJAdminAPI.unpublishProduct(id);
            await loadProducts();
            editProduct(saved.id);
            setMessage('#product-message', published ? 'Produto publicado.' : 'Produto despublicado.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#product-message', error.message, 'error');
        }
    }

    async function deactivateCurrentProduct() {
        const id = $('#product-id').value;
        if (!id) return;
        const code = $('#product-codigo').value.trim();
        const confirmText = window.prompt(`Para inativar, digite INATIVAR ou o codigo ${code}.`);
        if (!confirmText) return;
        try {
            const saved = await VJAdminAPI.deactivateProduct(id, confirmText);
            await loadProducts();
            editProduct(saved.id);
            setMessage('#product-message', 'Produto inativado.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#product-message', error.message, 'error');
        }
    }

    function previewProduct() {
        const payload = productPayload();
        const pricing = currentPricingInput();
        const image = payload.imagem_url;
        $('#product-preview-card').innerHTML = `
            <div class="preview-image-box">${image ? `<img src="${escapeHTML(image)}" alt="${escapeHTML(payload.nome || 'Produto')}">` : '<span>Sem imagem</span>'}</div>
            <div class="preview-info">
                <span class="status-badge ${payload.publicado ? 'publicado' : payload.status}">${escapeHTML(payload.publicado ? 'publicado' : payload.status)}</span>
                <h3>${escapeHTML(payload.nome || 'Produto sem nome')}</h3>
                <p>${escapeHTML(payload.descricao || 'Sem descricao')}</p>
                <dl>
                    <div><dt>Codigo</dt><dd>${escapeHTML(payload.codigo || '-')}</dd></div>
                    <div><dt>Categoria</dt><dd>${escapeHTML(payload.categoria || '-')}</dd></div>
                    <div><dt>Fornecedor</dt><dd>${escapeHTML(supplierName(payload.fornecedor_id))}</dd></div>
                    <div><dt>Pix</dt><dd>${money(pricing.preco_pix)}</dd></div>
                    <div><dt>Credito 12x</dt><dd>${money(pricing.preco_credito_12x)}</dd></div>
                    <div><dt>Margem Pix</dt><dd>${percent(pricing.margem_pix)}</dd></div>
                </dl>
            </div>
        `;
        $('#product-preview-modal').classList.remove('hidden');
    }

    function closePreview() {
        $('#product-preview-modal').classList.add('hidden');
    }

    async function exportProducts() {
        try {
            await VJAdminAPI.exportProductsCsv(productFilters());
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#product-message', error.message, 'error');
        }
    }

    function resetSupplierForm() {
        state.currentSupplierId = null;
        $('#supplier-form').reset();
        $('#supplier-id').value = '';
        $('#supplier-form-title').textContent = 'Novo fornecedor';
        setMessage('#supplier-message', '');
        renderSuppliers();
    }

    function editSupplier(id) {
        const supplier = state.suppliers.find((item) => Number(item.id) === Number(id));
        if (!supplier) return;
        state.currentSupplierId = supplier.id;
        $('#supplier-id').value = supplier.id;
        $('#supplier-nome').value = supplier.nome || '';
        $('#supplier-whatsapp').value = supplier.whatsapp || '';
        $('#supplier-instagram').value = supplier.instagram || '';
        $('#supplier-site').value = supplier.site || '';
        $('#supplier-observacoes').value = supplier.observacoes || '';
        $('#supplier-form-title').textContent = `Editar ${supplier.nome}`;
        renderSuppliers();
    }

    function supplierPayload() {
        return {
            nome: $('#supplier-nome').value.trim(),
            whatsapp: $('#supplier-whatsapp').value.trim(),
            instagram: $('#supplier-instagram').value.trim(),
            site: $('#supplier-site').value.trim(),
            observacoes: $('#supplier-observacoes').value.trim(),
        };
    }

    async function saveSupplier(event) {
        event.preventDefault();
        const id = $('#supplier-id').value;
        try {
            const saved = await VJAdminAPI.saveSupplier(supplierPayload(), id || null);
            await loadSuppliers();
            editSupplier(saved.id);
            setMessage('#supplier-message', 'Fornecedor salvo.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#supplier-message', error.message, 'error');
        }
    }


    function renderCustomers() {
        const customers = state.customers;
        $('#customer-count-label').textContent = `${customers.length} encontrado${customers.length === 1 ? '' : 's'}`;
        renderOrderCustomerOptions();
        if (!customers.length) {
            $('#customer-list').innerHTML = '<p class="empty-state">Nenhum cliente encontrado.</p>';
            return;
        }
        $('#customer-list').innerHTML = customers.map((customer) => {
            const active = Number(customer.id) === Number(state.currentCustomerId) ? ' active' : '';
            return `
                <button class="row-item${active}" type="button" data-customer-id="${customer.id}">
                    <span class="row-title">
                        <strong>${escapeHTML(customer.nome)}</strong>
                        <span class="status-badge ${escapeHTML(customer.status)}">${escapeHTML(customer.status)}</span>
                    </span>
                    <span class="row-meta">
                        <span>${escapeHTML(customer.whatsapp || 'WhatsApp nao informado')}</span>
                        <span>${escapeHTML(customer.email || 'E-mail nao informado')}</span>
                        <span>${escapeHTML(customer.instagram ? '@' + customer.instagram : 'Instagram nao informado')}</span>
                    </span>
                    <span class="row-meta">
                        <span>${escapeHTML(customer.cidade || '-')}</span>
                        <span>${escapeHTML(customer.origem || '-')}</span>
                    </span>
                </button>
            `;
        }).join('');
        $$('#customer-list [data-customer-id]').forEach((button) => {
            button.addEventListener('click', () => editCustomer(button.dataset.customerId));
        });
    }

    function resetCustomerForm() {
        state.currentCustomerId = null;
        $('#customer-form').reset();
        $('#customer-id').value = '';
        $('#customer-status').value = 'ativo';
        $('#customer-form-title').textContent = 'Novo cliente';
        $('#deactivate-customer-button').disabled = true;
        $('#customer-summary').innerHTML = '<p class="empty-state compact">Salve ou selecione um cliente para ver detalhes.</p>';
        $('#customer-orders').innerHTML = '<p class="empty-state compact">Nenhum cliente selecionado.</p>';
        setMessage('#customer-message', '');
        renderCustomers();
    }

    async function renderCustomerDetails(id) {
        if (!id) return;
        const data = await VJAdminAPI.customerOrders(id);
        const metrics = data.metricas || {};
        $('#customer-summary').innerHTML = `
            <div><span>Total gasto</span><strong>${money(metrics.total_gasto)}</strong></div>
            <div><span>Pedidos</span><strong>${Number(metrics.quantidade_pedidos || 0)}</strong></div>
            <div><span>Ticket medio</span><strong>${money(metrics.ticket_medio)}</strong></div>
            <div><span>Ultima compra</span><strong>${formatDate(metrics.ultima_compra)}</strong></div>
        `;
        const orders = data.pedidos || [];
        if (!orders.length) {
            $('#customer-orders').innerHTML = '<p class="empty-state compact">Nenhum pedido vinculado.</p>';
            return;
        }
        $('#customer-orders').innerHTML = orders.map((order) => `
            <article class="stock-history-item">
                <div class="row-title">
                    <strong>Pedido #${order.id}</strong>
                    <span class="status-badge ${escapeHTML(order.status)}">${escapeHTML(orderStatusLabel(order.status))}</span>
                </div>
                <div class="row-meta">
                    <span>${formatDate(order.updated_at || order.created_at)}</span>
                    <span>Total ${money(order.total)}</span>
                    <span>${escapeHTML(order.forma_pagamento || 'pix')} ${Number(order.parcelas || 1)}x</span>
                </div>
            </article>
        `).join('');
    }

    async function editCustomer(id) {
        try {
            const customer = await VJAdminAPI.customer(id);
            state.currentCustomerId = customer.id;
            $('#customer-id').value = customer.id;
            $('#customer-nome').value = customer.nome || '';
            $('#customer-whatsapp').value = customer.whatsapp || '';
            $('#customer-email').value = customer.email || '';
            $('#customer-cpf').value = customer.cpf || '';
            $('#customer-instagram').value = customer.instagram || '';
            $('#customer-cidade').value = customer.cidade || '';
            $('#customer-estado').value = customer.estado || '';
            $('#customer-data-nascimento').value = customer.data_nascimento || '';
            $('#customer-observacoes').value = customer.observacoes || '';
            $('#customer-origem').value = customer.origem || '';
            $('#customer-status').value = customer.status || 'ativo';
            $('#customer-form-title').textContent = `Editar ${customer.nome}`;
            $('#deactivate-customer-button').disabled = customer.status === 'inativo';
            renderCustomers();
            await renderCustomerDetails(customer.id);
            setMessage('#customer-message', customer.updated_by?.email ? `Atualizado por ${customer.updated_by.email}` : '');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#customer-message', error.message, 'error');
        }
    }

    function customerPayload() {
        return {
            nome: $('#customer-nome').value.trim(),
            whatsapp: $('#customer-whatsapp').value.trim(),
            email: $('#customer-email').value.trim(),
            cpf: $('#customer-cpf').value.trim(),
            instagram: $('#customer-instagram').value.trim(),
            cidade: $('#customer-cidade').value.trim(),
            estado: $('#customer-estado').value.trim(),
            data_nascimento: $('#customer-data-nascimento').value || null,
            observacoes: $('#customer-observacoes').value.trim(),
            origem: $('#customer-origem').value.trim(),
            status: $('#customer-status').value,
        };
    }

    async function saveCustomer(event) {
        event.preventDefault();
        const id = $('#customer-id').value;
        try {
            const saved = await VJAdminAPI.saveCustomer(customerPayload(), id || null);
            await loadCustomers();
            await editCustomer(saved.id);
            setMessage('#customer-message', 'Cliente salvo.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#customer-message', error.message, 'error');
        }
    }

    async function deactivateCurrentCustomer() {
        const id = $('#customer-id').value;
        if (!id) return;
        if (!window.confirm('Inativar cliente? Pedidos vinculados continuarao no historico.')) return;
        try {
            const saved = await VJAdminAPI.deactivateCustomer(id);
            await loadCustomers();
            await editCustomer(saved.id);
            setMessage('#customer-message', 'Cliente inativado.', 'success');
        } catch (error) {
            if (error.status === 401) return showLogin();
            setMessage('#customer-message', error.message, 'error');
        }
    }
    async function loadProducts({ updateOptions = false } = {}) {
        state.products = await VJAdminAPI.products(productFilters());
        if (updateOptions) renderFilterOptions();
        renderProducts();
        renderMetrics();
    }

    async function loadOrders() {
        state.orders = await VJAdminAPI.orders(orderFilters());
        renderOrders();
    }

    async function loadOrderProducts() {
        state.orderProducts = await VJAdminAPI.products({});
        renderOrderProductOptions();
        renderOrderItems();
    }

    async function loadStock() {
        state.stockProducts = await VJAdminAPI.stock(stockFilters());
        renderStockList();
        if (state.currentStockProductId && state.stockProducts.some((item) => Number(item.id) === Number(state.currentStockProductId))) {
            await selectStockProduct(state.currentStockProductId);
        } else if (!state.stockProducts.length) {
            state.currentStockProductId = null;
            renderStockDetail(null, []);
        }
    }


    async function loadCustomers() {
        state.customers = await VJAdminAPI.customers(customerFilters());
        renderCustomers();
    }
    async function loadSuppliers() {
        state.suppliers = await VJAdminAPI.suppliers();
        renderSuppliers();
        renderFilterOptions();
    }

    async function refresh() {
        try {
            await loadSuppliers();
            await loadCustomers();
            await loadProducts({ updateOptions: true });
            await loadOrderProducts();
            await loadOrders();
            await loadStock();
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
            if (button.dataset.view === 'orders') await loadOrders();
            if (button.dataset.view === 'customers') await loadCustomers();
            if (button.dataset.view === 'stock') await loadStock();
        }));
        $('#product-form').addEventListener('submit', saveProduct);
        $('#supplier-form').addEventListener('submit', saveSupplier);
        $('#customer-form').addEventListener('submit', saveCustomer);
        $('#order-form').addEventListener('submit', saveOrder);
        $('#stock-movement-form').addEventListener('submit', saveStockMovement);
        $('#new-product-button').addEventListener('click', resetProductForm);
        $('#new-supplier-button').addEventListener('click', resetSupplierForm);
        $('#new-customer-button').addEventListener('click', resetCustomerForm);
        $('#new-order-button').addEventListener('click', resetOrderForm);
        $('#add-order-item-button').addEventListener('click', addOrderItem);
        $('#confirm-order-button').addEventListener('click', confirmCurrentOrder);
        $('#cancel-order-button').addEventListener('click', cancelCurrentOrder);
        $('#order-customer').addEventListener('change', syncOrderCustomerFields);
        $('#deactivate-customer-button').addEventListener('click', deactivateCurrentCustomer);
        $('#publish-button').addEventListener('click', () => publishCurrentProduct(true));
        $('#unpublish-button').addEventListener('click', () => publishCurrentProduct(false));
        $('#deactivate-button').addEventListener('click', deactivateCurrentProduct);
        $('#recalculate-button').addEventListener('click', () => {
            renderPricing();
            setMessage('#product-message', 'Precos recalculados no preview. Salve para persistir.', 'success');
        });
        $('#preview-button').addEventListener('click', previewProduct);
        $('#close-preview-button').addEventListener('click', closePreview);
        $('#export-products-button').addEventListener('click', exportProducts);
        $('#clear-filters-button').addEventListener('click', async () => {
            $('#product-search').value = '';
            $('#filter-category').value = '';
            $('#filter-supplier').value = '';
            $('#filter-status').value = '';
            await loadProducts({ updateOptions: true });
        });
        ['#product-search', '#filter-category', '#filter-supplier', '#filter-status'].forEach((selector) => {
            $(selector).addEventListener('input', () => loadProducts());
            $(selector).addEventListener('change', () => loadProducts());
        });        $('#clear-customer-filters-button').addEventListener('click', async () => {
            $('#customer-search').value = '';
            $('#customer-filter-status').value = '';
            $('#customer-filter-city').value = '';
            $('#customer-filter-source').value = '';
            await loadCustomers();
        });
        ['#customer-search', '#customer-filter-status', '#customer-filter-city', '#customer-filter-source'].forEach((selector) => {
            $(selector).addEventListener('input', () => loadCustomers());
            $(selector).addEventListener('change', () => loadCustomers());
        });

        $('#clear-order-filters-button').addEventListener('click', async () => {
            $('#order-search').value = '';
            $('#order-filter-status').value = '';
            await loadOrders();
        });
        ['#order-search', '#order-filter-status'].forEach((selector) => {
            $(selector).addEventListener('input', () => loadOrders());
            $(selector).addEventListener('change', () => loadOrders());
        });
        ['#order-payment-method', '#order-installments', '#order-discount'].forEach((selector) => {
            $(selector).addEventListener('input', () => renderOrderItems());
            $(selector).addEventListener('change', () => {
                if (selector === '#order-payment-method' && ['pix', 'debito'].includes($(selector).value)) {
                    $('#order-installments').value = '1';
                }
                renderOrderItems();
            });
        });
        $('#clear-stock-filters-button').addEventListener('click', async () => {
            $('#stock-search').value = '';
            $('#stock-filter-category').value = '';
            $('#stock-filter-supplier').value = '';
            $('#stock-filter-status').value = '';
            await loadStock();
        });
        ['#stock-search', '#stock-filter-category', '#stock-filter-supplier', '#stock-filter-status'].forEach((selector) => {
            $(selector).addEventListener('input', () => loadStock());
            $(selector).addEventListener('change', () => loadStock());
        });
        ['#product-custo-peca', '#product-custo-embalagem', '#product-markup'].forEach((selector) => {
            $(selector).addEventListener('input', () => renderPricing());
        });
        $('#product-publicado').addEventListener('change', () => {
            if ($('#product-publicado').checked) $('#product-status').value = 'publicado';
        });
        $('#product-status').addEventListener('change', () => {
            $('#product-publicado').checked = $('#product-status').value === 'publicado';
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindEvents();
        refresh();
    });
})();









