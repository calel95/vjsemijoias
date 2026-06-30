(function () {
    window.createVJAdminFinance = function createVJAdminFinance(ctx) {
        const {
            state,
            $,
            $$,
            api,
            money,
            escapeHTML,
            formatDate,
            formatDateOnly,
            setMessage,
            showLogin,
        } = ctx;

        function financeFilters() {
            return {
                data_inicio: $('#finance-start').value,
                data_fim: $('#finance-end').value,
            };
        }

        function renderFinanceSummary() {
            const summary = state.financeSummary || {};
            $('#finance-metrics').innerHTML = `
                <div><strong>${money(summary.faturamento_bruto)}</strong><span>Faturamento</span></div>
                <div><strong>${money(summary.lucro_bruto)}</strong><span>Lucro bruto</span></div>
                <div><strong>${money(summary.despesas)}</strong><span>Despesas</span></div>
                <div><strong>${money(summary.lucro_liquido_estimado)}</strong><span>Lucro liquido</span></div>
            `;

            const productRanking = summary.ranking_produtos || [];
            $('#finance-products-ranking').innerHTML = productRanking.length ? productRanking.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.nome || 'Produto')}</strong><span>${Number(item.quantidade || 0)} un.</span></div>
                    <div class="row-meta"><span>${escapeHTML(item.codigo || '-')}</span><span>Faturamento ${money(item.faturamento)}</span><span>Lucro ${money(item.lucro_bruto)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem produtos vendidos no periodo.</p>';

            const clientRanking = summary.ranking_clientes || [];
            $('#finance-customers-ranking').innerHTML = clientRanking.length ? clientRanking.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.nome || 'Cliente')}</strong><span>${Number(item.quantidade_pedidos || 0)} pedidos</span></div>
                    <div class="row-meta"><span>${escapeHTML(item.whatsapp || '-')}</span><span>Total ${money(item.total)}</span><span>Ticket ${money(item.ticket_medio)}</span><span>Ultima ${formatDate(item.ultima_compra)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem clientes no periodo.</p>';

            const payments = summary.resumo_pagamentos || [];
            $('#finance-payment-summary').innerHTML = payments.length ? payments.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.forma_pagamento || 'Pagamento')}</strong><span>${Number(item.quantidade_pedidos || 0)} pedidos</span></div>
                    <div class="row-meta"><span>Faturamento ${money(item.faturamento)}</span><span>Taxas ${money(item.taxas)}</span><span>Lucro ${money(item.lucro_bruto)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem pagamentos no periodo.</p>';
        }

        function renderExpenses() {
            const expenses = state.expenses;
            $('#expense-count-label').textContent = `${expenses.length} encontrada${expenses.length === 1 ? '' : 's'}`;
            if (!expenses.length) {
                $('#expense-list').innerHTML = '<p class="empty-state">Nenhuma despesa encontrada.</p>';
                return;
            }
            $('#expense-list').innerHTML = expenses.map((expense) => {
                const active = Number(expense.id) === Number(state.currentExpenseId) ? ' active' : '';
                return `
                    <button class="row-item${active}" type="button" data-expense-id="${expense.id}">
                        <span class="row-title">
                            <strong>${escapeHTML(expense.descricao)}</strong>
                            <span class="status-badge ${escapeHTML(expense.status)}">${escapeHTML(expense.status)}</span>
                        </span>
                        <span class="row-meta"><span>${escapeHTML(expense.categoria || '-')}</span><span>${formatDateOnly(expense.data)}</span><span>${money(expense.valor)}</span></span>
                    </button>
                `;
            }).join('');
            $$('#expense-list [data-expense-id]').forEach((button) => {
                button.addEventListener('click', () => editExpense(button.dataset.expenseId));
            });
        }

        function resetExpenseForm() {
            state.currentExpenseId = null;
            $('#expense-form').reset();
            $('#expense-id').value = '';
            $('#expense-status').value = 'ativo';
            $('#expense-data').value = new Date().toISOString().slice(0, 10);
            $('#expense-form-title').textContent = 'Nova despesa';
            $('#cancel-expense-button').disabled = true;
            setMessage('#expense-message', '');
            renderExpenses();
        }

        function editExpense(id) {
            const expense = state.expenses.find((item) => Number(item.id) === Number(id));
            if (!expense) return;
            state.currentExpenseId = expense.id;
            $('#expense-id').value = expense.id;
            $('#expense-descricao').value = expense.descricao || '';
            $('#expense-categoria').value = expense.categoria || '';
            $('#expense-valor').value = expense.valor ?? '';
            $('#expense-data').value = expense.data || '';
            $('#expense-observacoes').value = expense.observacoes || '';
            $('#expense-status').value = expense.status || 'ativo';
            $('#expense-form-title').textContent = `Editar ${expense.descricao}`;
            $('#cancel-expense-button').disabled = expense.status === 'cancelado';
            renderExpenses();
            setMessage('#expense-message', expense.updated_by?.email ? `Atualizado por ${expense.updated_by.email}` : '');
        }

        function expensePayload() {
            return {
                descricao: $('#expense-descricao').value.trim(),
                categoria: $('#expense-categoria').value.trim(),
                valor: $('#expense-valor').value,
                data: $('#expense-data').value,
                observacoes: $('#expense-observacoes').value.trim(),
                status: $('#expense-status').value,
            };
        }

        async function saveExpense(event) {
            event.preventDefault();
            const id = $('#expense-id').value;
            try {
                const saved = await api.saveExpense(expensePayload(), id || null);
                await loadFinance();
                editExpense(saved.id);
                setMessage('#expense-message', 'Despesa salva.', 'success');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#expense-message', error.message, 'error');
            }
        }

        async function cancelCurrentExpense() {
            const id = $('#expense-id').value;
            if (!id) return;
            if (!window.confirm('Cancelar esta despesa? Ela deixara de entrar no resumo financeiro.')) return;
            try {
                const saved = await api.cancelExpense(id);
                await loadFinance();
                editExpense(saved.id);
                setMessage('#expense-message', 'Despesa cancelada.', 'success');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#expense-message', error.message, 'error');
            }
        }

        async function loadFinance() {
            const filters = financeFilters();
            const [summary, expenses] = await Promise.all([
                api.financeSummary(filters),
                api.expenses(filters),
            ]);
            state.financeSummary = summary;
            state.expenses = expenses;
            renderFinanceSummary();
            renderExpenses();
            if (state.currentExpenseId && !state.expenses.some((item) => Number(item.id) === Number(state.currentExpenseId))) {
                resetExpenseForm();
            }
        }

        function bindEvents() {
            $('#expense-form').addEventListener('submit', saveExpense);
            $('#new-expense-button').addEventListener('click', resetExpenseForm);
            $('#cancel-expense-button').addEventListener('click', cancelCurrentExpense);
            $('#apply-finance-filters-button').addEventListener('click', () => loadFinance());
            $('#clear-finance-filters-button').addEventListener('click', async () => {
                $('#finance-start').value = '';
                $('#finance-end').value = '';
                await loadFinance();
            });
            ['#finance-start', '#finance-end'].forEach((selector) => {
                $(selector).addEventListener('change', () => loadFinance());
            });
        }

        return {
            bindEvents,
            editExpense,
            loadFinance,
            resetExpenseForm,
        };
    };
})();