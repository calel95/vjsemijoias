(function () {
    window.createVJAdminAudit = function createVJAdminAudit(ctx) {
        const {
            state,
            $,
            api,
            escapeHTML,
            formatDate,
            setMessage,
            showLogin,
        } = ctx;

        function auditFilters() {
            return {
                action: $('#audit-action').value.trim(),
                recurso: $('#audit-resource').value,
                data_inicio: $('#audit-start').value,
                data_fim: $('#audit-end').value,
            };
        }

        function actionLabel(action) {
            return String(action || '').replaceAll('_', ' ');
        }

        function metadataText(metadata) {
            const entries = Object.entries(metadata || {}).filter(([, value]) => value !== null && value !== undefined && value !== '');
            if (!entries.length) return '-';
            return entries.map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' | ');
        }

        function renderAuditLogs() {
            const logs = state.auditLogs || [];
            $('#audit-count-label').textContent = `${logs.length} registro${logs.length === 1 ? '' : 's'}`;
            if (!logs.length) {
                $('#audit-list').innerHTML = '<p class="empty-state">Nenhum registro de auditoria encontrado.</p>';
                return;
            }
            $('#audit-list').innerHTML = logs.map((log) => `
                <article class="stock-history-item audit-log-row">
                    <div class="row-title">
                        <strong>${escapeHTML(actionLabel(log.action))}</strong>
                        <span>${formatDate(log.created_at)}</span>
                    </div>
                    <div class="row-meta">
                        <span>Usuario ${escapeHTML(log.admin_email || log.admin_user?.email || '-')}</span>
                        <span>Recurso ${escapeHTML(log.resource || '-')} #${escapeHTML(log.resource_id || '-')}</span>
                        <span>IP ${escapeHTML(log.ip_address || '-')}</span>
                    </div>
                    <p>${escapeHTML(metadataText(log.metadata))}</p>
                </article>
            `).join('');
        }

        async function loadAuditLogs() {
            try {
                state.auditLogs = await api.auditLogs(auditFilters());
                renderAuditLogs();
                setMessage('#audit-message', '');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#audit-message', error.message, 'error');
            }
        }

        function bindEvents() {
            $('#apply-audit-filters-button').addEventListener('click', () => loadAuditLogs());
            $('#clear-audit-filters-button').addEventListener('click', async () => {
                $('#audit-action').value = '';
                $('#audit-resource').value = '';
                $('#audit-start').value = '';
                $('#audit-end').value = '';
                await loadAuditLogs();
            });
            ['#audit-action', '#audit-resource', '#audit-start', '#audit-end'].forEach((selector) => {
                $(selector).addEventListener('change', () => loadAuditLogs());
            });
        }

        return {
            bindEvents,
            loadAuditLogs,
            renderAuditLogs,
        };
    };
})();