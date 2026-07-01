(function () {
    window.createVJAdminCustomers = function createVJAdminCustomers(ctx) {
        const {
            state,
            $,
            $$,
            api,
            money,
            escapeHTML,
            formatDate,
            orderStatusLabel,
            renderOrderCustomerOptions,
            setMessage,
            showLogin,
        } = ctx;

        function customerFilters() {
            return {
                search: $('#customer-search').value.trim(),
                status: $('#customer-filter-status').value,
                cidade: $('#customer-filter-city').value.trim(),
                origem: $('#customer-filter-source').value.trim(),
            };
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
            const data = await api.customerOrders(id);
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
                const customer = await api.customer(id);
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
                const saved = await api.saveCustomer(customerPayload(), id || null);
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
                const saved = await api.deactivateCustomer(id);
                await loadCustomers();
                await editCustomer(saved.id);
                setMessage('#customer-message', 'Cliente inativado.', 'success');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#customer-message', error.message, 'error');
            }
        }

        async function loadCustomers() {
            state.customers = await api.customers(customerFilters());
            renderCustomers();
        }

        function bindEvents() {
            $('#customer-form').addEventListener('submit', saveCustomer);
            $('#new-customer-button').addEventListener('click', resetCustomerForm);
            $('#deactivate-customer-button').addEventListener('click', deactivateCurrentCustomer);
            $('#clear-customer-filters-button').addEventListener('click', async () => {
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
        }

        return {
            bindEvents,
            loadCustomers,
            renderCustomers,
            resetCustomerForm,
        };
    };
})();