(function () {
    window.createVJAdminOrders = function createVJAdminOrders(ctx) {
        const {
            state,
            $,
            $$,
            api,
            pricing,
            money,
            percent,
            escapeHTML,
            formatDate,
            setMessage,
            showLogin,
            loadStock,
            loadFinance,
        } = ctx;

        function orderFilters() {
            return {
                search: $('#order-search').value.trim(),
                status: $('#order-filter-status').value,
            };
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
            return Number(pricing.fees[orderPaymentField()] || 0);
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
                const order = await api.order(id);
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
            const saved = await api.saveOrder(orderPayload(), $('#order-id').value || null);
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
                const confirmed = await api.confirmOrder(id);
                await loadOrders();
                await loadStock();
                await loadFinance();
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
                const canceled = await api.cancelOrder(id);
                await loadOrders();
                await loadStock();
                await loadFinance();
                await loadOrderProducts();
                await editOrder(canceled.id);
                setMessage('#order-message', 'Pedido cancelado.', 'success');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#order-message', error.message, 'error');
            }
        }

        async function loadOrders() {
            state.orders = await api.orders(orderFilters());
            renderOrders();
        }

        async function loadOrderProducts() {
            state.orderProducts = await api.products({});
            renderOrderProductOptions();
            renderOrderItems();
        }

        function bindEvents() {
            $('#order-form').addEventListener('submit', saveOrder);
            $('#new-order-button').addEventListener('click', resetOrderForm);
            $('#add-order-item-button').addEventListener('click', addOrderItem);
            $('#confirm-order-button').addEventListener('click', confirmCurrentOrder);
            $('#cancel-order-button').addEventListener('click', cancelCurrentOrder);
            $('#order-customer').addEventListener('change', syncOrderCustomerFields);
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
        }

        return {
            bindEvents,
            loadOrders,
            loadOrderProducts,
            orderStatusLabel,
            renderOrderCustomerOptions,
            resetOrderForm,
        };
    };
})();