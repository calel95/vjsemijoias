(function () {
    window.createVJAdminStock = function createVJAdminStock(ctx) {
        const {
            state,
            $,
            $$,
            api,
            escapeHTML,
            formatDate,
            supplierName,
            uniqueCategories,
            setMessage,
            showLogin,
            loadProducts,
            loadOrderProducts,
        } = ctx;

        function stockFilters() {
            return {
                produto: $('#stock-search').value.trim(),
                categoria: $('#stock-filter-category').value,
                fornecedor_id: $('#stock-filter-supplier').value,
                status: $('#stock-filter-status').value,
            };
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
                const data = await api.productStock(id);
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
                const saved = await api.moveStock(id, {
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

        async function loadStock() {
            state.stockProducts = await api.stock(stockFilters());
            renderStockList();
            if (state.currentStockProductId && state.stockProducts.some((item) => Number(item.id) === Number(state.currentStockProductId))) {
                await selectStockProduct(state.currentStockProductId);
            } else if (!state.stockProducts.length) {
                state.currentStockProductId = null;
                renderStockDetail(null, []);
            }
        }

        function bindEvents() {
            $('#stock-movement-form').addEventListener('submit', saveStockMovement);
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
        }

        return {
            bindEvents,
            loadStock,
            renderStockFilterOptions,
        };
    };
})();