(function () {
    window.createVJAdminDashboard = function createVJAdminDashboard(ctx) {
        const {
            state,
            $,
            api,
            money,
            percent,
            escapeHTML,
            setMessage,
            showLogin,
        } = ctx;

        function dashboardFilters() {
            const periodo = $('#dashboard-period').value || 'mes_atual';
            return {
                periodo,
                data_inicio: periodo === 'personalizado' ? $('#dashboard-start').value : '',
                data_fim: periodo === 'personalizado' ? $('#dashboard-end').value : '',
            };
        }

        function renderMainMetrics(summary) {
            $('#dashboard-main-metrics').innerHTML = `
                <div><strong>${money(summary.faturamento_mes)}</strong><span>Faturamento do periodo</span></div>
                <div><strong>${money(summary.lucro_liquido_estimado_mes)}</strong><span>Lucro liquido estimado</span></div>
                <div><strong>${Number(summary.pedidos_confirmados_mes || 0)}</strong><span>Pedidos confirmados</span></div>
                <div><strong>${money(summary.ticket_medio_mes)}</strong><span>Ticket medio</span></div>
            `;
            $('#dashboard-operation-metrics').innerHTML = `
                <div><strong>${Number(summary.clientes_ativos || 0)}</strong><span>Clientes ativos</span></div>
                <div><strong>${Number(summary.produtos_ativos_publicados || 0)}</strong><span>Produtos publicados</span></div>
                <div><strong>${Number(summary.produtos_estoque_baixo || 0)}</strong><span>Estoque baixo</span></div>
                <div><strong>${Number(summary.produtos_sem_estoque || 0)}</strong><span>Sem estoque</span></div>
            `;
            $('#dashboard-finance-metrics').innerHTML = `
                <div><strong>${money(summary.despesas_mes)}</strong><span>Despesas</span></div>
                <div><strong>${percent(summary.margem_liquida_estimada)}</strong><span>Margem liquida estimada</span></div>
            `;
        }

        function renderProductRanking(summary) {
            const products = summary.top_produtos || [];
            $('#dashboard-products-ranking').innerHTML = products.length ? products.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.nome || 'Produto')}</strong><span>${money(item.faturamento)}</span></div>
                    <div class="row-meta"><span>${escapeHTML(item.codigo || '-')}</span><span>${Number(item.quantidade || 0)} un.</span><span>Lucro ${money(item.lucro_bruto)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem produtos vendidos no periodo.</p>';
        }

        function renderCustomerRanking(summary) {
            const customers = summary.top_clientes || [];
            $('#dashboard-customers-ranking').innerHTML = customers.length ? customers.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.nome || 'Cliente')}</strong><span>${money(item.total)}</span></div>
                    <div class="row-meta"><span>${escapeHTML(item.whatsapp || '-')}</span><span>${Number(item.quantidade_pedidos || 0)} pedidos</span><span>Ticket ${money(item.ticket_medio)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem clientes no periodo.</p>';
        }

        function renderPaymentSummary(summary) {
            const payments = summary.resumo_pagamentos || [];
            $('#dashboard-payment-summary').innerHTML = payments.length ? payments.map((item) => `
                <article class="stock-history-item">
                    <div class="row-title"><strong>${escapeHTML(item.forma_pagamento || 'Pagamento')}</strong><span>${Number(item.quantidade_pedidos || 0)} pedidos</span></div>
                    <div class="row-meta"><span>Faturamento ${money(item.faturamento)}</span><span>Taxas ${money(item.taxas)}</span><span>Lucro ${money(item.lucro_bruto)}</span></div>
                </article>
            `).join('') : '<p class="empty-state compact">Sem pagamentos no periodo.</p>';
        }

        function renderDashboard() {
            const summary = state.dashboard || {};
            renderMainMetrics(summary);
            renderProductRanking(summary);
            renderCustomerRanking(summary);
            renderPaymentSummary(summary);
            setMessage('#dashboard-message', '');
        }

        async function loadDashboard() {
            try {
                state.dashboard = await api.dashboard(dashboardFilters());
                renderDashboard();
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#dashboard-message', error.message, 'error');
            }
        }

        function bindEvents() {
            $('#dashboard-period').addEventListener('change', () => {
                const custom = $('#dashboard-period').value === 'personalizado';
                $('#dashboard-start').disabled = !custom;
                $('#dashboard-end').disabled = !custom;
                loadDashboard();
            });
            $('#apply-dashboard-filters-button').addEventListener('click', () => loadDashboard());
            ['#dashboard-start', '#dashboard-end'].forEach((selector) => {
                $(selector).addEventListener('change', () => {
                    if ($('#dashboard-period').value === 'personalizado') loadDashboard();
                });
            });
            $('#dashboard-start').disabled = true;
            $('#dashboard-end').disabled = true;
        }

        return {
            bindEvents,
            loadDashboard,
            renderDashboard,
        };
    };
})();