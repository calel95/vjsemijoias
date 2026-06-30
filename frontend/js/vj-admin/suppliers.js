(function () {
    window.createVJAdminSuppliers = function createVJAdminSuppliers(ctx) {
        const {
            state,
            $,
            $$,
            api,
            escapeHTML,
            setMessage,
            showLogin,
            afterSuppliersChanged,
        } = ctx;

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
                const saved = await api.saveSupplier(supplierPayload(), id || null);
                await loadSuppliers();
                editSupplier(saved.id);
                setMessage('#supplier-message', 'Fornecedor salvo.', 'success');
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#supplier-message', error.message, 'error');
            }
        }

        async function loadSuppliers() {
            state.suppliers = await api.suppliers();
            renderSuppliers();
            afterSuppliersChanged();
        }

        function bindEvents() {
            $('#supplier-form').addEventListener('submit', saveSupplier);
            $('#new-supplier-button').addEventListener('click', resetSupplierForm);
        }

        return {
            bindEvents,
            loadSuppliers,
            renderSuppliers,
        };
    };
})();