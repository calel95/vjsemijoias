(function () {
    window.createVJAdminProducts = function createVJAdminProducts(ctx) {
        const {
            state,
            $,
            $$,
            api,
            pricing,
            money,
            percent,
            escapeHTML,
            supplierName,
            setMessage,
            showLogin,
            renderStockFilterOptions,
        } = ctx;

        const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        const ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif'];
        const IMAGE_MAX_BYTES = 8 * 1024 * 1024;
        let galleryImages = [];

        function productFilters() {
            return {
                search: $('#product-search').value.trim(),
                categoria: $('#filter-category').value,
                fornecedor_id: $('#filter-supplier').value,
                status: $('#filter-status').value,
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

        function currentPricingInput() {
            return pricing.calculate(
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
        function cleanGalleryImage(value) {
            const image = String(value || '').trim();
            return image || null;
        }

        function isDataImage(value) {
            return String(value || '').startsWith('data:image/');
        }

        function galleryFromProduct(product) {
            const images = Array.isArray(product.images) ? product.images : [];
            const cleanedImages = images.map(cleanGalleryImage).filter(Boolean);
            if (cleanedImages.length) return cleanedImages;
            const image = cleanGalleryImage(product.imagem_url || product.image);
            return image ? [image] : [];
        }

        function currentGalleryImages() {
            return galleryImages.map(cleanGalleryImage).filter(Boolean);
        }

        function syncMainImageInput() {
            const firstImage = currentGalleryImages()[0] || '';
            $('#product-imagem').value = firstImage && !isDataImage(firstImage) ? firstImage : '';
        }

        function updateClearButtonVisibility() {
            $('#product-imagem-clear').classList.toggle('hidden', currentGalleryImages().length === 0);
        }

        function imageLabel(image, index) {
            if (isDataImage(image)) return `Imagem selecionada ${index + 1}`;
            const compact = image.length > 44 ? `${image.slice(0, 41)}...` : image;
            return compact || `Imagem ${index + 1}`;
        }

        function renderGalleryPreview() {
            const box = $('#product-gallery-preview');
            const images = currentGalleryImages();
            galleryImages = images;
            syncMainImageInput();
            updateClearButtonVisibility();
            if (!images.length) {
                box.innerHTML = '<div class="gallery-empty">Sem imagens na galeria</div>';
                return;
            }
            box.innerHTML = images.map((image, index) => {
                const safeImage = isDataImage(image) ? image : escapeHTML(image);
                const mainBadge = index === 0 ? '<span class="status-badge publicado">Principal</span>' : '';
                return `
                    <article class="gallery-item${index === 0 ? ' is-main' : ''}">
                        <div class="gallery-thumb"><img src="${safeImage}" alt="Preview da imagem ${index + 1}"></div>
                        ${mainBadge}
                        <small>${escapeHTML(imageLabel(image, index))}</small>
                        <div class="gallery-actions">
                            <button class="secondary-button" type="button" data-gallery-action="main" data-index="${index}" ${index === 0 ? 'disabled' : ''}>Principal</button>
                            <button class="secondary-button" type="button" data-gallery-action="up" data-index="${index}" ${index === 0 ? 'disabled' : ''}>Subir</button>
                            <button class="secondary-button" type="button" data-gallery-action="down" data-index="${index}" ${index === images.length - 1 ? 'disabled' : ''}>Descer</button>
                            <button class="danger-button" type="button" data-gallery-action="remove" data-index="${index}">Remover</button>
                        </div>
                    </article>
                `;
            }).join('');
            $$('#product-gallery-preview [data-gallery-action]').forEach((button) => {
                button.addEventListener('click', () => updateGalleryOrder(button.dataset.galleryAction, Number(button.dataset.index)));
            });
        }

        function updateGalleryOrder(action, index) {
            const images = currentGalleryImages();
            if (!images[index]) return;
            if (action === 'remove') {
                images.splice(index, 1);
            } else if (action === 'main') {
                const [image] = images.splice(index, 1);
                images.unshift(image);
            } else if (action === 'up' && index > 0) {
                [images[index - 1], images[index]] = [images[index], images[index - 1]];
            } else if (action === 'down' && index < images.length - 1) {
                [images[index], images[index + 1]] = [images[index + 1], images[index]];
            }
            galleryImages = images;
            renderGalleryPreview();
        }

        function clearSelectedImage() {
            galleryImages = [];
            $('#product-imagem-file').value = '';
            $('#product-imagem').value = '';
            renderGalleryPreview();
        }

        function validateImageFile(file) {
            if (!file) return 'Nenhum arquivo selecionado.';
            const fileName = (file.name || '').toLowerCase();
            const extension = fileName.slice(fileName.lastIndexOf('.'));
            if (!ALLOWED_IMAGE_EXTENSIONS.includes(extension)) {
                return `Formato nao suportado: ${extension}. Use JPG, PNG, WebP ou GIF.`;
            }
            if (file.size > IMAGE_MAX_BYTES) {
                const maxMb = IMAGE_MAX_BYTES / (1024 * 1024);
                return `Imagem maior que ${maxMb} MB.`;
            }
            if (file.type && !ALLOWED_IMAGE_TYPES.includes(file.type)) {
                return `Tipo de arquivo nao suportado: ${file.type}.`;
            }
            return null;
        }

        function readImageFile(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(new Error('Falha ao ler o arquivo selecionado.'));
                reader.readAsDataURL(file);
            });
        }

        async function handleImageFileSelect(event) {
            const files = Array.from(event.target.files || []);
            if (!files.length) return;
            const error = files.map(validateImageFile).find(Boolean);
            if (error) {
                setMessage('#product-message', error, 'error');
                $('#product-imagem-file').value = '';
                return;
            }
            try {
                const selectedImages = await Promise.all(files.map(readImageFile));
                galleryImages = currentGalleryImages().concat(selectedImages);
                renderGalleryPreview();
                const count = selectedImages.length;
                setMessage('#product-message', `${count} imagem${count === 1 ? '' : 's'} adicionada${count === 1 ? '' : 's'}. Salve para enviar.`, 'success');
            } catch (error) {
                setMessage('#product-message', error.message || 'Falha ao ler arquivo selecionado.', 'error');
            } finally {
                $('#product-imagem-file').value = '';
            }
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
            galleryImages = [];
            $('#product-imagem-file').value = '';
            renderGalleryPreview();
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
            $('#product-descricao').value = product.descricao || product.description || '';
            $('#product-form-title').textContent = `Editar ${product.codigo || product.nome || product.id}`;
            galleryImages = galleryFromProduct(product);
            $('#product-imagem-file').value = '';
            renderGalleryPreview();
            const audit = [
                product.created_by?.email ? `Criado por ${product.created_by.email}` : '',
                product.updated_by?.email ? `Atualizado por ${product.updated_by.email}` : '',
            ].filter(Boolean).join(' | ');
            setMessage('#product-message', audit, audit ? 'success' : '');
            renderPricing(product);
            renderProducts();
        }

        function productPayload() {
            const manualImage = cleanGalleryImage($('#product-imagem').value);
            if (manualImage) {
                galleryImages = currentGalleryImages();
                if (galleryImages.length) galleryImages[0] = manualImage;
                else galleryImages = [manualImage];
            }
            const images = currentGalleryImages();
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
                imagem_url: images[0] || '',
                images,
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
                const saved = await api.saveProduct(productPayload(), id || null);
                $('#product-imagem-file').value = '';
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
                    ? await api.publishProduct(id)
                    : await api.unpublishProduct(id);
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
                const saved = await api.deactivateProduct(id, confirmText);
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
            const pricingValues = currentPricingInput();
            const image = payload.images[0] || payload.imagem_url;
            const safeImage = image && image.startsWith('data:') ? image : escapeHTML(image);
            $('#product-preview-card').innerHTML = `
                <div class="preview-image-box">${image ? `<img src="${safeImage}" alt="${escapeHTML(payload.nome || 'Produto')}">` : '<span>Sem imagem</span>'}</div>
                <div class="preview-info">
                    <span class="status-badge ${payload.publicado ? 'publicado' : payload.status}">${escapeHTML(payload.publicado ? 'publicado' : payload.status)}</span>
                    <h3>${escapeHTML(payload.nome || 'Produto sem nome')}</h3>
                    <p>${escapeHTML(payload.descricao || 'Sem descricao')}</p>
                    <dl>
                        <div><dt>Codigo</dt><dd>${escapeHTML(payload.codigo || '-')}</dd></div>
                        <div><dt>Categoria</dt><dd>${escapeHTML(payload.categoria || '-')}</dd></div>
                        <div><dt>Fornecedor</dt><dd>${escapeHTML(supplierName(payload.fornecedor_id))}</dd></div>
                        <div><dt>Pix</dt><dd>${money(pricingValues.preco_pix)}</dd></div>
                        <div><dt>Credito 12x</dt><dd>${money(pricingValues.preco_credito_12x)}</dd></div>
                        <div><dt>Margem Pix</dt><dd>${percent(pricingValues.margem_pix)}</dd></div>
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
                await api.exportProductsCsv(productFilters());
            } catch (error) {
                if (error.status === 401) return showLogin();
                setMessage('#product-message', error.message, 'error');
            }
        }

        async function loadProducts({ updateOptions = false } = {}) {
            state.products = await api.products(productFilters());
            if (updateOptions) renderFilterOptions();
            renderProducts();
            renderMetrics();
        }

        function bindEvents() {
            $('#product-form').addEventListener('submit', saveProduct);
            $('#new-product-button').addEventListener('click', resetProductForm);
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
            $('#product-imagem-file').addEventListener('change', handleImageFileSelect);
            $('#product-imagem-clear').addEventListener('click', clearSelectedImage);
            $('#product-imagem').addEventListener('input', () => {
                const manualImage = cleanGalleryImage($('#product-imagem').value);
                const images = currentGalleryImages();
                if (manualImage) {
                    if (images.length) images[0] = manualImage;
                    else images.push(manualImage);
                } else if (images.length && !isDataImage(images[0])) {
                    images.shift();
                }
                galleryImages = images;
                renderGalleryPreview();
            });
        }

        return {
            bindEvents,
            loadProducts,
            renderFilterOptions,
            renderPricing,
        };
    };
})();