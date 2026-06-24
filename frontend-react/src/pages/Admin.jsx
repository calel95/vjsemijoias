import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { API } from '../services/api';
import { 
  Package, ShoppingBag, Tag, Shield, Sliders, FileText, Upload, Plus, Trash2, 
  Edit3, Eye, FileDown, ToggleLeft, ToggleRight, Check, AlertCircle, RefreshCw, X
} from 'lucide-react';

const Admin = () => {
  const navigate = useNavigate();
  const { isAdmin, logoutAdmin, formatPrice, showToast } = useStore();

  if (!isAdmin) {
    return <Navigate to="/login" replace />;
  }

  // --- TAB STATE ---
  const [activeTab, setActiveTab] = useState('products');

  // --- GLOBAL LOADS STATE ---
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [adminUsers, setAdminUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [stats, setStats] = useState({
    total_products: 0,
    custom_products: 0,
    total_categories: 0,
    average_price: 0,
    pending_orders: 0,
    paid_orders: 0
  });

  const [loading, setLoading] = useState(false);

  // --- FETCH ALL ADMIN DATA ---
  const refreshAdminData = async () => {
    setLoading(true);
    try {
      const [prodsRes, ordersRes, couponsRes, usersRes, logsRes, statsRes] = await Promise.all([
        API.getAdminProducts(),
        API.getOrders(),
        API.getAdminCoupons(),
        API.getAdminUsers(),
        API.getAdminAuditLogs(80),
        API.getAdminStats()
      ]);

      if (prodsRes.success) setProducts(prodsRes.data || []);
      if (ordersRes.success) setOrders(ordersRes.data || []);
      if (couponsRes.success) setCoupons(couponsRes.data || []);
      if (usersRes.success) setAdminUsers(usersRes.data || []);
      if (logsRes.success) setAuditLogs(logsRes.data || []);
      if (statsRes.success) setStats(statsRes.data || stats);
    } catch (e) {
      console.error(e);
      showToast('Erro ao atualizar painel administrativo.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAdminData();
  }, []);

  // =========================================================================
  // TAB 1: PRODUTOS CRUD & LIST
  // =========================================================================
  const [editingId, setEditingId] = useState(null);
  const [prodForm, setProdForm] = useState({
    name: '',
    category: 'brincos',
    price: '',
    oldPrice: '',
    sku: '',
    icon: '💍',
    badge: '',
    is_active: true,
    stock_status: 'available',
    stock_quantity: '10',
    low_stock_alert: '2',
    weight_grams: '100',
    height_cm: '2.00',
    width_cm: '10.00',
    length_cm: '15.00',
    shipping_profile: 'default',
    description: '',
    features: ''
  });

  const [galleryImages, setGalleryImages] = useState([]);
  const [productFilter, setProductFilter] = useState('all');
  const [productSearch, setProductSearch] = useState('');

  const handleProdInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setProdForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleAddImageUrl = (url) => {
    if (!url.trim()) return;
    setGalleryImages(prev => [...new Set([...prev, url.trim()])]);
  };

  const handleRemoveImage = (index) => {
    setGalleryImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleMoveImage = (index, direction) => {
    const target = index + direction;
    if (target < 0 || target >= galleryImages.length) return;
    const newImgs = [...galleryImages];
    const temp = newImgs[index];
    newImgs[index] = newImgs[target];
    newImgs[target] = temp;
    setGalleryImages(newImgs);
  };

  const handleEditProduct = (prod) => {
    setEditingId(prod.id);
    setProdForm({
      name: prod.name || '',
      category: prod.category || 'brincos',
      price: prod.price || '',
      oldPrice: prod.oldPrice || '',
      sku: prod.sku || '',
      icon: prod.icon || '💍',
      badge: prod.badge || '',
      is_active: prod.is_active !== false,
      stock_status: prod.stock_status || 'available',
      stock_quantity: prod.stock_quantity ?? 10,
      low_stock_alert: prod.low_stock_alert ?? 2,
      weight_grams: prod.weight_grams ?? 100,
      height_cm: prod.height_cm ?? 2,
      width_cm: prod.width_cm ?? 10,
      length_cm: prod.length_cm ?? 15,
      shipping_profile: prod.shipping_profile || 'default',
      description: prod.description || '',
      features: (prod.features || []).map(f => f.replace(/^✓\s*/, '')).join('\n')
    });
    setGalleryImages(prod.images || (prod.image ? [prod.image] : []));
    // Scroll form into view
    window.scrollTo({ top: 350, behavior: 'smooth' });
  };

  const handleResetProdForm = () => {
    setEditingId(null);
    setProdForm({
      name: '',
      category: 'brincos',
      price: '',
      oldPrice: '',
      sku: '',
      icon: '💍',
      badge: '',
      is_active: true,
      stock_status: 'available',
      stock_quantity: '10',
      low_stock_alert: '2',
      weight_grams: '100',
      height_cm: '2.00',
      width_cm: '10.00',
      length_cm: '15.00',
      shipping_profile: 'default',
      description: '',
      features: ''
    });
    setGalleryImages([]);
  };

  const handleProductSubmit = async (e) => {
    e.preventDefault();
    if (!prodForm.name || !prodForm.price || !prodForm.description) {
      showToast('Preencha os campos obrigatórios.', 'error');
      return;
    }

    const categoryMap = {
      'brincos': 'Brincos',
      'colares': 'Colares',
      'pulseiras': 'Pulseiras',
      'aneis': 'Anéis',
      'pingentes': 'Pingentes',
      'chaveiros': 'Chaveiros',
      'conjuntos': 'Conjuntos'
    };

    const payload = {
      ...prodForm,
      categoryName: categoryMap[prodForm.category] || prodForm.category,
      price: parseFloat(prodForm.price) || 0,
      oldPrice: prodForm.oldPrice ? parseFloat(prodForm.oldPrice) : null,
      sku: prodForm.sku || null,
      stock_quantity: parseInt(prodForm.stock_quantity) || 0,
      low_stock_alert: parseInt(prodForm.low_stock_alert) || 0,
      weight_grams: parseInt(prodForm.weight_grams) || 100,
      height_cm: parseFloat(prodForm.height_cm) || 2,
      width_cm: parseFloat(prodForm.width_cm) || 10,
      length_cm: parseFloat(prodForm.length_cm) || 15,
      images: [...galleryImages],
      image: galleryImages[0] || null,
      features: prodForm.features
        .split('\n')
        .map(f => f.trim())
        .filter(f => f.length > 0)
        .map(f => f.startsWith('✓') ? f : `✓ ${f}`)
    };

    try {
      let result;
      if (editingId) {
        result = await API.updateProduct(editingId, payload);
      } else {
        result = await API.createProduct(payload);
      }

      if (result.success) {
        showToast(editingId ? 'Produto atualizado com sucesso!' : 'Produto criado!', 'success');
        handleResetProdForm();
        refreshAdminData();
      } else {
        showToast(result.error || 'Erro ao salvar produto.', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Falha na comunicação com o servidor.', 'error');
    }
  };

  const handleDeleteProduct = async (id, name) => {
    if (window.confirm(`Tem certeza que deseja excluir "${name}"?`)) {
      const res = await API.deleteProduct(id);
      if (res.success) {
        showToast('Produto excluído com sucesso.', 'info');
        refreshAdminData();
      } else {
        showToast(res.error || 'Erro ao excluir.', 'error');
      }
    }
  };

  const handleClearCatalog = async () => {
    const typed = window.prompt('Digite LIMPAR CATALOGO para confirmar a exclusão de TODOS os produtos:');
    if (typed === 'LIMPAR CATALOGO') {
      const res = await API.deleteAllProducts(typed);
      if (res.success) {
        showToast('Catálogo limpo com sucesso!', 'success');
        refreshAdminData();
      } else {
        showToast(res.error || 'Falha ao limpar catálogo.', 'error');
      }
    } else {
      showToast('Confirmação incorreta. Ação abortada.', 'info');
    }
  };

  // Gallery file handler
  const handleFileDrop = (e) => {
    e.preventDefault();
    const files = Array.from(e.target.files || []);
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          setGalleryImages(prev => [...new Set([...prev, ev.target.result])]);
        };
        reader.readAsDataURL(file);
      }
    });
  };

  const filteredProductsList = products.filter(p => {
    // Category Filter
    if (productFilter !== 'all') {
      if (productFilter === 'inactive' && p.is_active !== false) return false;
      if (productFilter === 'low_stock' && !p.stock_is_low) return false;
      if (productFilter === 'out_of_stock' && p.stock_status !== 'out_of_stock') return false;
      if (productFilter !== 'inactive' && productFilter !== 'low_stock' && productFilter !== 'out_of_stock' && p.category !== productFilter) return false;
    }
    // Search Filter
    if (productSearch) {
      const search = productSearch.toLowerCase();
      return (p.name || '').toLowerCase().includes(search) || (p.sku || '').toLowerCase().includes(search);
    }
    return true;
  });

  // =========================================================================
  // TAB 2: PEDIDOS / ORDERS
  // =========================================================================
  const [orderFilter, setOrderFilter] = useState('all');
  const [orderSearch, setOrderSearch] = useState('');

  const orderStatusLabels = {
    pending: 'Pendente',
    payment_pending: 'Aguardando Pagamento',
    paid: 'Pago',
    processing: 'Em Separação',
    shipped: 'Enviado',
    delivered: 'Entregue',
    canceled: 'Cancelado',
    failed: 'Falhou'
  };

  const handleStatusChange = async (orderId, newStatus) => {
    let payload = {};
    if (newStatus === 'shipped') {
      const trackingCode = window.prompt('Código de rastreamento:');
      if (trackingCode === null) return;
      const carrier = window.prompt('Transportadora:', 'Correios');
      if (carrier === null) return;

      payload.tracking_code = trackingCode.trim();
      payload.tracking_carrier = carrier.trim();
    }

    try {
      const res = await API.updateOrderStatus(orderId, newStatus, payload);
      if (res.success) {
        showToast(`Pedido ${orderId} atualizado para ${orderStatusLabels[newStatus]}`, 'success');
        refreshAdminData();
      } else {
        showToast(res.error || 'Erro ao alterar status.', 'error');
      }
    } catch (err) {
      showToast('Erro de rede ao salvar status.', 'error');
    }
  };

  const filteredOrders = orders.filter(o => {
    if (orderFilter !== 'all' && o.status !== orderFilter) return false;
    if (orderSearch) {
      const search = orderSearch.toLowerCase();
      return (
        String(o.id).toLowerCase().includes(search) ||
        (o.customer_name || '').toLowerCase().includes(search) ||
        (o.customer_email || '').toLowerCase().includes(search)
      );
    }
    return true;
  });

  // =========================================================================
  // TAB 3: CUPONS DE DESCONTO
  // =========================================================================
  const [couponForm, setCouponForm] = useState({
    id: '',
    code: '',
    discount_type: 'percent',
    discount_value: '',
    minimum_subtotal: '0',
    usage_limit: '0',
    per_customer_limit: '0',
    starts_at: '',
    ends_at: '',
    is_active: true
  });

  const handleCouponInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setCouponForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleEditCoupon = (cp) => {
    setCouponForm({
      id: cp.id,
      code: cp.code || '',
      discount_type: cp.discount_type || 'percent',
      discount_value: cp.discount_value || '',
      minimum_subtotal: cp.minimum_subtotal || '0',
      usage_limit: cp.usage_limit || '0',
      per_customer_limit: cp.per_customer_limit || '0',
      starts_at: cp.starts_at ? cp.starts_at.slice(0, 10) : '',
      ends_at: cp.ends_at ? cp.ends_at.slice(0, 10) : '',
      is_active: cp.is_active !== false
    });
  };

  const handleResetCouponForm = () => {
    setCouponForm({
      id: '',
      code: '',
      discount_type: 'percent',
      discount_value: '',
      minimum_subtotal: '0',
      usage_limit: '0',
      per_customer_limit: '0',
      starts_at: '',
      ends_at: '',
      is_active: true
    });
  };

  const handleCouponSubmit = async (e) => {
    e.preventDefault();
    if (!couponForm.code || !couponForm.discount_value) {
      showToast('Código e valor do desconto são obrigatórios.', 'error');
      return;
    }

    const payload = {
      code: couponForm.code.trim().toUpperCase(),
      discount_type: couponForm.discount_type,
      discount_value: parseFloat(couponForm.discount_value) || 0,
      minimum_subtotal: parseFloat(couponForm.minimum_subtotal) || 0,
      usage_limit: parseInt(couponForm.usage_limit) || 0,
      per_customer_limit: parseInt(couponForm.per_customer_limit) || 0,
      starts_at: couponForm.starts_at || null,
      ends_at: couponForm.ends_at || null,
      is_active: couponForm.is_active
    };

    try {
      let res;
      if (couponForm.id) {
        res = await API.updateAdminCoupon(couponForm.id, payload);
      } else {
        res = await API.createAdminCoupon(payload);
      }

      if (res.success) {
        showToast('Cupom salvo com sucesso!', 'success');
        handleResetCouponForm();
        refreshAdminData();
      } else {
        showToast(res.error || 'Erro ao salvar cupom.', 'error');
      }
    } catch (err) {
      showToast('Erro de rede ao salvar cupom.', 'error');
    }
  };

  const handleToggleCoupon = async (id, currentActive) => {
    const res = await API.updateAdminCoupon(id, { is_active: !currentActive });
    if (res.success) {
      showToast(currentActive ? 'Cupom desativado' : 'Cupom reativado', 'info');
      refreshAdminData();
    } else {
      showToast(res.error || 'Erro ao alterar status.', 'error');
    }
  };

  // =========================================================================
  // TAB 4: AUDITORIA & SECURITY
  // =========================================================================
  const [newAdmin, setNewAdmin] = useState({ name: '', email: '', password: '' });

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    if (!newAdmin.name || !newAdmin.email || !newAdmin.password) return;
    try {
      const res = await API.createAdminUser(newAdmin);
      if (res.success) {
        showToast('Novo administrador criado!', 'success');
        setNewAdmin({ name: '', email: '', password: '' });
        refreshAdminData();
      } else {
        showToast(res.error || 'Falha ao criar admin.', 'error');
      }
    } catch (err) {
      showToast('Erro de comunicação.', 'error');
    }
  };

  // =========================================================================
  // TAB 5: CONFIGURAÇÃO DA LOJA
  // =========================================================================
  const [configForm, setConfigForm] = useState({
    preorder_days: '10',
    shipping_free_minimum: '150.0',
    shipping_flat_rate: '15.0',
    infinitepay_enabled: false,
    credit_card_enabled: true,
    pix_enabled: true
  });

  useEffect(() => {
    const loadConfig = async () => {
      const res = await API.getAdminStoreConfig();
      if (res.success && res.data?.values) {
        const val = res.data.values;
        setConfigForm({
          preorder_days: val.preorder_days ?? '10',
          shipping_free_minimum: val.shipping_free_minimum ?? '150.0',
          shipping_flat_rate: val.shipping_flat_rate ?? '15.0',
          infinitepay_enabled: String(val.infinitepay_enabled).toLowerCase() === 'true',
          credit_card_enabled: String(val.credit_card_enabled).toLowerCase() === 'true',
          pix_enabled: String(val.pix_enabled).toLowerCase() === 'true'
        });
      }
    };
    if (activeTab === 'config') loadConfig();
  }, [activeTab]);

  const handleConfigChange = (e) => {
    const { name, value, type, checked } = e.target;
    setConfigForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleConfigSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await API.updateAdminStoreConfig(configForm);
      if (res.success) {
        showToast('Configurações salvas com sucesso!', 'success');
      } else {
        showToast(res.error || 'Falha ao salvar.', 'error');
      }
    } catch (err) {
      showToast('Erro de rede.', 'error');
    }
  };

  // =========================================================================
  // TAB 6: CATALOGO PDF & IMPORT
  // =========================================================================
  const [pdfConfig, setPdfConfig] = useState({
    title: 'Coleção Oficial',
    collection: 'Semijoias Luxo',
    slogan: 'VJ Semijoias - Brilho com Propósito',
    contact_line: 'Contato: contato@vjsemijoias.com.br',
    filename: 'catalogo-vj-semijoias.pdf'
  });

  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  const handlePdfConfigChange = (e) => {
    setPdfConfig(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleGeneratePdf = async (e) => {
    e.preventDefault();
    setGeneratingPdf(true);
    showToast('Iniciando geração de PDF de catálogo...', 'info');

    const formData = new FormData();
    Object.entries(pdfConfig).forEach(([k, v]) => formData.append(k, v));

    try {
      const result = await API.generateCatalogPdf(formData);
      if (result.success && result.blob) {
        const fileUrl = window.URL.createObjectURL(result.blob);
        const link = document.createElement('a');
        link.href = fileUrl;
        link.download = result.filename || 'catalogo-vj-semijoias.pdf';
        document.body.appendChild(link);
        link.click();
        link.remove();
        showToast(`Catálogo gerado com sucesso! ${result.products} produtos, ${result.pages} páginas.`, 'success');
      } else {
        showToast(result.error || 'Erro ao gerar catálogo PDF.', 'error');
      }
    } catch (err) {
      showToast('Erro de conexão ao gerar PDF.', 'error');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleImportFolder = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setImportLoading(true);
    showToast('Importando catálogo de produtos...', 'info');

    try {
      const res = await API.importProductFolder(files);
      if (res.success) {
        showToast(`Importação concluída! ${res.data.imported || 0} produtos importados, ${res.data.images || 0} imagens.`, 'success');
        refreshAdminData();
      } else {
        showToast(res.error || 'Falha na importação do catálogo.', 'error');
      }
    } catch (err) {
      showToast('Erro ao importar folder.', 'error');
    } finally {
      setImportLoading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="admin-container" style={{ padding: '4rem 2rem' }}>
      
      {/* Header Panel */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem', marginBottom: '3rem', borderBottom: '2px solid var(--gold-pale)', paddingBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', margin: 0 }}>
            Painel <span>Administrativo</span>
          </h1>
          <p style={{ color: 'var(--gray)', margin: '0.4rem 0 0' }}>Gerenciamento e controle completo do e-commerce</p>
        </div>
        <div style={{ display: 'flex', gap: '0.8rem' }}>
          <button onClick={refreshAdminData} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.7rem 1.4rem', fontSize: '0.8rem' }} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin-anim' : ''} /> Atualizar
          </button>
          <button onClick={logoutAdmin} className="btn btn-danger" style={{ padding: '0.7rem 1.4rem', fontSize: '0.8rem' }}>
            Sair
          </button>
        </div>
      </div>

      {/* STATS OVERVIEW CARDS */}
      <div className="admin-stats">
        <div className="stat-card">
          <div className="stat-icon">📦</div>
          <div className="stat-value">{stats.total_products || products.length}</div>
          <div className="stat-label">Produtos</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💎</div>
          <div className="stat-value">{stats.total_categories || 4}</div>
          <div className="stat-label">Categorias</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-value">{stats.pending_orders || orders.filter(o => ['pending', 'payment_pending'].includes(o.status)).length}</div>
          <div className="stat-label">Pendentes</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💳</div>
          <div className="stat-value">{stats.paid_orders || orders.filter(o => ['paid', 'processing', 'shipped', 'delivered'].includes(o.status)).length}</div>
          <div className="stat-label">Pagos</div>
        </div>
      </div>

      {/* DASHBOARD TABBED NAVIGATION */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--gray-light)', marginBottom: '2.5rem', overflowX: 'auto', gap: '1rem', paddingBottom: '0.2rem' }}>
        {[
          { id: 'products', name: 'Produtos', icon: <Package size={16} /> },
          { id: 'orders', name: 'Pedidos', icon: <ShoppingBag size={16} /> },
          { id: 'coupons', name: 'Cupons', icon: <Tag size={16} /> },
          { id: 'security', name: 'Segurança & Logs', icon: <Shield size={16} /> },
          { id: 'config', name: 'Configuração', icon: <Sliders size={16} /> },
          { id: 'pdf', name: 'PDF & Importar', icon: <FileText size={16} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.8rem 1.4rem',
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              borderBottom: activeTab === tab.id ? '2px solid var(--gold-dark)' : '2px solid transparent',
              color: activeTab === tab.id ? 'var(--gold-dark)' : 'var(--gray)',
              transition: 'all 0.3s ease',
              whiteSpace: 'nowrap'
            }}
          >
            {tab.icon}
            {tab.name}
          </button>
        ))}
      </div>

      {/* TAB CONTENT: PRODUCTS */}
      {activeTab === 'products' && (
        <div className="admin-grid">
          {/* Left Form creator */}
          <div className="admin-card">
            <h2 id="form-title">{editingId ? '✏️ Editar Produto' : '➕ Adicionar Novo Produto'}</h2>
            
            <form onSubmit={handleProductSubmit}>
              <div className="form-group">
                <label>Nome do Produto <span className="required">*</span></label>
                <input type="text" name="name" required value={prodForm.name} onChange={handleProdInputChange} placeholder="Ex: Brinco Argola Gold" />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Categoria <span className="required">*</span></label>
                  <select name="category" value={prodForm.category} onChange={handleProdInputChange}>
                    <option value="brincos">Brincos</option>
                    <option value="colares">Colares</option>
                    <option value="pulseiras">Pulseiras</option>
                    <option value="aneis">Anéis</option>
                    <option value="pingentes">Pingentes</option>
                    <option value="chaveiros">Chaveiros</option>
                    <option value="conjuntos">Conjuntos</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Preço <span className="required">*</span></label>
                  <input type="number" name="price" step="0.01" required value={prodForm.price} onChange={handleProdInputChange} placeholder="0.00" />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Preço Antigo (Opcional)</label>
                  <input type="number" name="oldPrice" step="0.01" value={prodForm.oldPrice} onChange={handleProdInputChange} placeholder="0.00" />
                </div>
                <div className="form-group">
                  <label>SKU / Referência</label>
                  <input type="text" name="sku" value={prodForm.sku} onChange={handleProdInputChange} placeholder="REF123" />
                </div>
              </div>

              {/* Stock settings */}
              <div className="form-row">
                <div className="form-group">
                  <label>Status de Estoque</label>
                  <select name="stock_status" value={prodForm.stock_status} onChange={handleProdInputChange}>
                    <option value="available">Disponível</option>
                    <option value="preorder">Sob Encomenda</option>
                    <option value="out_of_stock">Sem Estoque</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Quantidade em Estoque</label>
                  <input type="number" name="stock_quantity" value={prodForm.stock_quantity} onChange={handleProdInputChange} />
                </div>
              </div>

              {/* Dimensions */}
              <div className="form-row" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                <div className="form-group">
                  <label>Peso (g)</label>
                  <input type="number" name="weight_grams" value={prodForm.weight_grams} onChange={handleProdInputChange} />
                </div>
                <div className="form-group">
                  <label>Altura (cm)</label>
                  <input type="number" step="0.1" name="height_cm" value={prodForm.height_cm} onChange={handleProdInputChange} />
                </div>
                <div className="form-group">
                  <label>Largura (cm)</label>
                  <input type="number" step="0.1" name="width_cm" value={prodForm.width_cm} onChange={handleProdInputChange} />
                </div>
                <div className="form-group">
                  <label>Compr. (cm)</label>
                  <input type="number" step="0.1" name="length_cm" value={prodForm.length_cm} onChange={handleProdInputChange} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Selo da Vitrine (Badge)</label>
                  <select name="badge" value={prodForm.badge} onChange={handleProdInputChange}>
                    <option value="">Sem selo</option>
                    <option value="new">Novidade (NEW)</option>
                    <option value="sale">Oferta (SALE)</option>
                    <option value="bestseller">Destaque (BESTSELLER)</option>
                  </select>
                </div>
                <div className="form-group" style={{ display: 'flex', alignItems: 'center', paddingLeft: '0.5rem' }}>
                  <label className="admin-toggle" style={{ margin: 0, width: '100%' }}>
                    <input type="checkbox" name="is_active" checked={prodForm.is_active} onChange={handleProdInputChange} />
                    <span></span>
                    <strong>Ativo no Site</strong>
                  </label>
                </div>
              </div>

              <div className="form-group">
                <label>Descrição do Produto <span className="required">*</span></label>
                <textarea name="description" rows="3" required value={prodForm.description} onChange={handleProdInputChange} placeholder="Descreva a peça..." />
              </div>

              <div className="form-group">
                <label>Especificações Técnicas (uma por linha)</label>
                <textarea name="features" rows="3" value={prodForm.features} onChange={handleProdInputChange} placeholder="Banho de Ouro 18k&#10;Tecnologia Hipoalergênica" />
              </div>

              {/* Image upload area */}
              <div className="form-group">
                <label>Imagens da Peça</label>
                <div id="image-upload" className="image-upload" style={{ minHeight: '160px' }}>
                  <input type="file" multiple onChange={handleFileDrop} accept="image/*" aria-label="Carregar imagens" />
                  <div className="upload-placeholder">
                    <div style={{ fontSize: '2rem' }}>📷</div>
                    <p>Clique ou arraste as fotos aqui</p>
                    <small>JPG, PNG até 5MB cada</small>
                  </div>
                </div>
                
                {/* Images URL textarea bypass helper */}
                <div style={{ marginTop: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--gray)', fontWeight: 600 }}>Endereços de Imagem (URLs - um por linha)</label>
                  <textarea
                    id="image-url"
                    placeholder="Cole URLs ou use o upload acima"
                    rows="3"
                    value={galleryImages.join('\n')}
                    onChange={(e) => setGalleryImages(e.target.value.split('\n').map(l => l.trim()).filter(Boolean))}
                    style={{ fontSize: '0.8rem', marginTop: '0.4rem' }}
                  />
                </div>

                {/* Image Gallery Manager */}
                {galleryImages.length > 0 && (
                  <div className="product-gallery-admin" style={{ marginTop: '1.2rem' }}>
                    {galleryImages.map((img, idx) => (
                      <div key={idx} className={`product-gallery-admin-item ${idx === 0 ? 'main' : ''}`}>
                        <img src={img.startsWith('data:') || img.startsWith('http') || img.startsWith('/') ? img : `/images/catalog/${img}`} alt={`Preview ${idx + 1}`} />
                        <span>{idx === 0 ? 'Principal' : `Foto ${idx + 1}`}</span>
                        <div className="product-gallery-admin-actions">
                          <button type="button" onClick={() => handleMoveImage(idx, -1)} disabled={idx === 0}>◀</button>
                          <button type="button" onClick={() => handleMoveImage(idx, 1)} disabled={idx === galleryImages.length - 1}>▶</button>
                          <button type="button" onClick={() => handleRemoveImage(idx)} className="danger">✕</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.8rem', marginTop: '2rem' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 2 }}>
                  {editingId ? 'Atualizar Produto' : 'Salvar Peça'}
                </button>
                <button type="button" onClick={handleResetProdForm} className="btn btn-secondary" style={{ flex: 1 }}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>

          {/* Right Product List side */}
          <div className="admin-card">
            <h2>Estoque & Catálogo</h2>
            
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem', alignItems: 'center' }}>
              <div className="search-box" style={{ flex: 1, minWidth: '150px' }}>
                <input
                  type="text"
                  placeholder="Buscar no estoque..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  style={{ padding: '0.6rem 1rem 0.6rem 2.4rem' }}
                />
              </div>

              <select value={productFilter} onChange={(e) => setProductFilter(e.target.value)} className="sort-select" style={{ minWidth: '130px', padding: '0.6rem 1rem' }}>
                <option value="all">Filtros (Todos)</option>
                <option value="brincos">Brincos</option>
                <option value="colares">Colares</option>
                <option value="pulseiras">Pulseiras</option>
                <option value="aneis">Anéis</option>
                <option value="pingentes">Pingentes</option>
                <option value="inactive">Inativos</option>
                <option value="low_stock">Estoque Baixo</option>
                <option value="out_of_stock">Esgotados</option>
              </select>

              <button onClick={handleClearCatalog} className="btn btn-danger" style={{ padding: '0.6rem 1rem', fontSize: '0.75rem', borderRadius: '30px' }}>
                Limpar Tudo
              </button>
            </div>

            <div className="admin-products-list">
              {filteredProductsList.length === 0 ? (
                <div className="empty-admin-list">
                  <div className="icon">📦</div>
                  <p>Nenhum produto cadastrado.</p>
                </div>
              ) : (
                filteredProductsList.map((p) => {
                  const imgUrl = p.image || (p.images && p.images[0]);
                  return (
                    <div key={p.id} className="admin-product-item">
                      <div className="admin-product-thumb">
                        {imgUrl ? (
                          <img src={imgUrl.startsWith('data:') || imgUrl.startsWith('http') || imgUrl.startsWith('/') ? imgUrl : `/images/catalog/${imgUrl}`} alt={p.name} />
                        ) : (
                          p.icon || '💍'
                        )}
                      </div>
                      
                      <div className="admin-product-info">
                        <h4 style={{ margin: 0, fontSize: '0.92rem' }}>{p.name}</h4>
                        <p style={{ margin: '0.15rem 0', fontSize: '0.75rem' }}>
                          SKU {p.sku || '-'} | Estoque: <strong>{p.stock_quantity ?? 0}</strong>
                        </p>
                        <div className="product-meta" style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginTop: '0.2rem' }}>
                          <span className="admin-product-price" style={{ fontSize: '0.85rem' }}>{formatPrice(p.price)}</span>
                          <span className={`badge-mini ${p.is_active ? 'active' : 'inactive'}`} style={{ fontSize: '0.65rem' }}>
                            {p.is_active ? 'ATIVO' : 'INATIVO'}
                          </span>
                          <span className={`badge-mini stock ${p.stock_status}`} style={{ fontSize: '0.65rem' }}>
                            {p.stock_status === 'available' ? 'DISPONÍVEL' : (p.stock_status === 'preorder' ? 'SOB ENCOMENDA' : 'ESGOTADO')}
                          </span>
                          {p.stock_is_low && <span className="badge-mini stock low" style={{ fontSize: '0.65rem' }}>BAIXO</span>}
                        </div>
                      </div>

                      <div className="admin-product-actions">
                        <button type="button" onClick={() => handleEditProduct(p)} className="btn-edit" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}>
                          Editar
                        </button>
                        <button type="button" onClick={() => handleDeleteProduct(p.id, p.name)} className="btn-delete" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}>
                          Excluir
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: ORDERS */}
      {activeTab === 'orders' && (
        <div className="admin-card orders-card">
          <h2>Controle de Vendas / Pedidos</h2>
          
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.8rem', alignItems: 'center' }}>
            <div className="search-box" style={{ flex: 1, minWidth: '180px' }}>
              <input
                type="text"
                placeholder="Buscar por ID ou Cliente..."
                value={orderSearch}
                onChange={(e) => setOrderSearch(e.target.value)}
              />
            </div>

            <select value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)} className="sort-select" style={{ minWidth: '150px' }}>
              <option value="all">Status (Todos)</option>
              <option value="pending">Pendente</option>
              <option value="payment_pending">Aguardando Pagamento</option>
              <option value="paid">Pago</option>
              <option value="processing">Em Separação</option>
              <option value="shipped">Enviado</option>
              <option value="delivered">Entregue</option>
              <option value="canceled">Cancelado</option>
              <option value="failed">Falhou</option>
            </select>
          </div>

          <div className="admin-orders-list">
            {filteredOrders.length === 0 ? (
              <div className="empty-admin-list">
                <div className="icon">PED</div>
                <p>Nenhum pedido correspondente encontrado.</p>
              </div>
            ) : (
              filteredOrders.map((order) => {
                const itemsList = Array.isArray(order.items) ? order.items : [];
                return (
                  <article key={order.id} className="admin-order-item">
                    <div className="order-main">
                      <div>
                        <strong>{order.id}</strong>
                        <span>{new Date(order.created_at).toLocaleString('pt-BR')}</span>
                      </div>
                      <span className={`order-status ${order.status}`}>
                        {orderStatusLabels[order.status] || order.status}
                      </span>
                    </div>

                    <div className="order-customer">
                      <strong>{order.customer_name || 'Cliente'}</strong>
                      <span>{order.customer_email}</span>
                      <span>{order.customer_phone}</span>
                    </div>

                    <p className="order-items-summary">
                      {itemsList.map(i => `${i.quantity || 1}x ${i.name || `Produto ${i.id}`}`).join(', ')}
                    </p>

                    <div className="order-footer">
                      <strong style={{ fontSize: '1.1rem', display: 'block', marginBottom: '0.4rem' }}>
                        {formatPrice(order.total || 0)}
                      </strong>
                      <select
                        value={order.status}
                        onChange={(e) => handleStatusChange(order.id, e.target.value)}
                        style={{ padding: '0.4rem 0.6rem', border: '1px solid rgba(166, 124, 61, 0.2)', borderRadius: '8px', fontSize: '0.82rem' }}
                      >
                        {Object.entries(orderStatusLabels).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                    </div>

                    {/* Tracking details */}
                    {(order.tracking_code || order.tracking_carrier) && (
                      <div className="order-tracking-summary" style={{ gridColumn: 'span 4' }}>
                        <span>
                          Rastreio: <strong>{order.tracking_code || '-'}</strong> ({order.tracking_carrier})
                        </span>
                      </div>
                    )}
                  </article>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: COUPONS */}
      {activeTab === 'coupons' && (
        <div className="coupon-admin-grid">
          {/* Coupon Form */}
          <div className="admin-coupon-form">
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', color: 'var(--gold-dark)', borderBottom: '1px solid rgba(166, 124, 61, 0.15)', paddingBottom: '0.5rem', marginBottom: '1.2rem' }}>
              {couponForm.id ? '✏️ Editar Cupom' : '🎟️ Novo Cupom'}
            </h3>
            
            <form onSubmit={handleCouponSubmit}>
              <div className="form-group">
                <label>Código do Cupom <span className="required">*</span></label>
                <input type="text" name="code" required value={couponForm.code} onChange={handleCouponInputChange} placeholder="EX: VJ10OFF" />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Tipo de Desconto</label>
                  <select name="discount_type" value={couponForm.discount_type} onChange={handleCouponInputChange}>
                    <option value="percent">Porcentagem (%)</option>
                    <option value="fixed">Valor Fixo (R$)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Valor do Desconto <span className="required">*</span></label>
                  <input type="number" name="discount_value" required value={couponForm.discount_value} onChange={handleCouponInputChange} placeholder="10.00" />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Subtotal Mínimo</label>
                  <input type="number" name="minimum_subtotal" value={couponForm.minimum_subtotal} onChange={handleCouponInputChange} />
                </div>
                <div className="form-group">
                  <label>Limite Global de Usos</label>
                  <input type="number" name="usage_limit" value={couponForm.usage_limit} onChange={handleCouponInputChange} placeholder="0 = Sem limite" />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Início da Validade</label>
                  <input type="date" name="starts_at" value={couponForm.starts_at} onChange={handleCouponInputChange} />
                </div>
                <div className="form-group">
                  <label>Fim da Validade</label>
                  <input type="date" name="ends_at" value={couponForm.ends_at} onChange={handleCouponInputChange} />
                </div>
              </div>

              <div className="form-group" style={{ display: 'flex', alignItems: 'center', marginTop: '0.5rem' }}>
                <label className="admin-toggle" style={{ margin: 0, width: '100%' }}>
                  <input type="checkbox" name="is_active" checked={couponForm.is_active} onChange={handleCouponInputChange} />
                  <span></span>
                  <strong>Cupom Ativo</strong>
                </label>
              </div>

              <div style={{ display: 'flex', gap: '0.8rem', marginTop: '1.8rem' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  Salvar Cupom
                </button>
                <button type="button" onClick={handleResetCouponForm} className="btn btn-secondary">
                  Limpar
                </button>
              </div>
            </form>
          </div>

          {/* Coupon List */}
          <div className="admin-coupons-list">
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', color: 'var(--gold-dark)', borderBottom: '1px solid rgba(166, 124, 61, 0.15)', paddingBottom: '0.5rem', marginBottom: '1.2rem' }}>
              Cupons Cadastrados
            </h3>
            
            {coupons.length === 0 ? (
              <div className="empty-admin-list" style={{ background: 'transparent', border: 'none' }}>
                <p>Nenhum cupom ativo cadastrado.</p>
              </div>
            ) : (
              coupons.map((cp) => (
                <div key={cp.id} className={`admin-coupon-row ${cp.is_active ? '' : 'inactive'}`}>
                  <div className="admin-coupon-main">
                    <div>
                      <strong>{cp.code}</strong>
                      <span>
                        {cp.discount_type === 'percent' ? `${cp.discount_value}% OFF` : `${formatPrice(cp.discount_value)} OFF`}
                      </span>
                    </div>
                    <span className="coupon-status" style={{ background: cp.is_active ? '#e7f8ec' : '#ffe8e8', color: cp.is_active ? 'var(--success)' : 'var(--error)' }}>
                      {cp.is_active ? 'Ativo' : 'Pausado'}
                    </span>
                  </div>

                  <div className="admin-coupon-meta" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.4rem', fontSize: '0.78rem', color: 'var(--gray)', margin: '0.6rem 0' }}>
                    <span>Usos: {cp.used_count || 0} / {cp.usage_limit > 0 ? cp.usage_limit : 'Sem limite'}</span>
                    <span>Mínimo: {formatPrice(cp.minimum_subtotal || 0)}</span>
                    {cp.ends_at && <span style={{ gridColumn: 'span 2' }}>Expira em: {new Date(cp.ends_at).toLocaleDateString('pt-BR')}</span>}
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.8rem' }}>
                    <button type="button" onClick={() => handleEditCoupon(cp)} className="btn btn-outline" style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem', flex: 1 }}>
                      <Edit3 size={12} /> Editar
                    </button>
                    <button type="button" onClick={() => handleToggleCoupon(cp.id, cp.is_active)} className="btn btn-outline" style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem', flex: 1 }}>
                      {cp.is_active ? 'Pausar' : 'Ativar'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: SECURITY & LOGS */}
      {activeTab === 'security' && (
        <div className="admin-security-grid">
          {/* Create new Admin user Form */}
          <div className="admin-user-form">
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', color: 'var(--gold-dark)', borderBottom: '1px solid rgba(166, 124, 61, 0.15)', paddingBottom: '0.5rem', marginBottom: '1.2rem' }}>
              👤 Novo Administrador
            </h3>
            
            <form onSubmit={handleCreateAdmin}>
              <div className="form-group">
                <label>Nome Completo</label>
                <input
                  type="text"
                  required
                  value={newAdmin.name}
                  onChange={(e) => setNewAdmin(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Nome do administrador"
                />
              </div>

              <div className="form-group">
                <label>E-mail / Login</label>
                <input
                  type="email"
                  required
                  value={newAdmin.email}
                  onChange={(e) => setNewAdmin(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="email@exemplo.com"
                />
              </div>

              <div className="form-group">
                <label>Senha de Acesso</label>
                <input
                  type="password"
                  required
                  value={newAdmin.password}
                  onChange={(e) => setNewAdmin(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Mínimo 6 caracteres"
                />
              </div>

              <button type="submit" className="btn btn-primary btn-block" style={{ marginTop: '1.5rem' }}>
                <Plus size={16} /> Adicionar Administrador
              </button>
            </form>

            <div className="admin-users-list" style={{ marginTop: '2.5rem', background: 'var(--white)', border: '1px solid var(--gray-light)', padding: '1rem', borderRadius: '12px' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.8rem', color: 'var(--gray-dark)' }}>Administradores Ativos</h4>
              {adminUsers.map((usr) => (
                <div key={usr.id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--gray-pale)', padding: '0.5rem 0', fontSize: '0.82rem' }}>
                  <strong>{usr.name}</strong>
                  <span style={{ color: 'var(--gray)' }}>{usr.email}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Audit Logs list */}
          <div className="admin-audit-list">
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', color: 'var(--gold-dark)', borderBottom: '1px solid rgba(166, 124, 61, 0.15)', paddingBottom: '0.5rem', marginBottom: '1.2rem' }}>
              🛡️ Log de Atividades (Auditoria)
            </h3>
            
            <div style={{ display: 'grid', gap: '0.8rem', maxHeight: '550px', overflowY: 'auto', paddingRight: '0.4rem' }}>
              {auditLogs.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--gray)', textAlign: 'center' }}>Nenhum log gravado.</p>
              ) : (
                auditLogs.map((log) => {
                  const isWarning = log.action.includes('failed') || log.action.includes('delete');
                  return (
                    <div
                      key={log.id}
                      className="admin-audit-row"
                      style={{
                        borderColor: isWarning ? '#f59e0b' : 'rgba(166, 124, 61, 0.12)',
                        background: isWarning ? '#fffbeb' : 'var(--white)'
                      }}
                    >
                      <div>
                        <strong style={{ fontSize: '0.88rem', display: 'block' }}>
                          {log.action}
                        </strong>
                        <span style={{ fontSize: '0.78rem', color: 'var(--gray)' }}>
                          {log.resource || 'sem detalhes'}
                        </span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <small style={{ display: 'block', fontSize: '0.75rem', color: 'var(--gray)' }}>
                          {new Date(log.created_at).toLocaleString('pt-BR')}
                        </small>
                        <small style={{ display: 'block', fontSize: '0.75rem', color: 'var(--gray)' }}>
                          IP: {log.ip_address || 'local'}
                        </small>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: STORE CONFIG */}
      {activeTab === 'config' && (
        <div className="admin-card store-config-card" style={{ maxWidth: '700px', margin: '0 auto' }}>
          <h2>Configuração da Loja</h2>
          <p style={{ fontSize: '0.88rem', color: 'var(--gray)', marginBottom: '2rem' }}>Configure regras de negócio, prazos de produção e opções de pagamento.</p>

          <form onSubmit={handleConfigSubmit}>
            <h3>📦 Prazos e Envio</h3>
            
            <div className="form-row">
              <div className="form-group">
                <label>Dias de Produção (Pre-Order)</label>
                <input
                  type="number"
                  name="preorder_days"
                  value={configForm.preorder_days}
                  onChange={handleConfigChange}
                  placeholder="10"
                />
                <small style={{ display: 'block', color: 'var(--gray)', marginTop: '0.3rem', fontSize: '0.75rem' }}>
                  Número de dias úteis adicionados ao frete de peças sob encomenda.
                </small>
              </div>

              <div className="form-group">
                <label>Valor Mínimo para Frete Grátis (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  name="shipping_free_minimum"
                  value={configForm.shipping_free_minimum}
                  onChange={handleConfigChange}
                  placeholder="150.00"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Taxa de Envio Padrão (Fixa - R$)</label>
              <input
                type="number"
                step="0.01"
                name="shipping_flat_rate"
                value={configForm.shipping_flat_rate}
                onChange={handleConfigChange}
                placeholder="15.00"
              />
            </div>

            <h3>💳 Meios de Pagamento</h3>
            
            <div style={{ display: 'grid', gap: '0.85rem', marginBottom: '2.5rem' }}>
              <label className="admin-toggle">
                <input
                  type="checkbox"
                  name="infinitepay_enabled"
                  checked={configForm.infinitepay_enabled}
                  onChange={handleConfigChange}
                />
                <span></span>
                <div>
                  <strong>Habilitar InfinitePay</strong>
                  <small style={{ display: 'block', color: 'var(--gray)', fontSize: '0.75rem' }}>Direciona clientes ao checkout seguro da InfinitePay.</small>
                </div>
              </label>

              <label className="admin-toggle">
                <input
                  type="checkbox"
                  name="credit_card_enabled"
                  checked={configForm.credit_card_enabled}
                  onChange={handleConfigChange}
                />
                <span></span>
                <div>
                  <strong>Aceitar Cartão de Crédito</strong>
                  <small style={{ display: 'block', color: 'var(--gray)', fontSize: '0.75rem' }}>Permite parcelamento no cartão de crédito.</small>
                </div>
              </label>

              <label className="admin-toggle">
                <input
                  type="checkbox"
                  name="pix_enabled"
                  checked={configForm.pix_enabled}
                  onChange={handleConfigChange}
                />
                <span></span>
                <div>
                  <strong>Aceitar PIX</strong>
                  <small style={{ display: 'block', color: 'var(--gray)', fontSize: '0.75rem' }}>Gera QR Code Pix com confirmação de pagamento instantânea.</small>
                </div>
              </label>
            </div>

            <button type="submit" className="btn btn-primary btn-block" style={{ minHeight: '48px' }}>
              Salvar Configurações da Loja
            </button>
          </form>
        </div>
      )}

      {/* TAB CONTENT: PDF & IMPORT */}
      {activeTab === 'pdf' && (
        <div className="catalog-pdf-layout">
          {/* PDF configuration form */}
          <div className="admin-card">
            <h2>Gerar Catálogo em PDF</h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--gray)', marginBottom: '1.8rem' }}>Gere um arquivo PDF diagramado de luxo contendo as imagens e preços de suas peças.</p>

            <form onSubmit={handleGeneratePdf}>
              <div className="form-group">
                <label>Título da Capa</label>
                <input type="text" name="title" value={pdfConfig.title} onChange={handlePdfConfigChange} />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nome da Coleção / Subtítulo</label>
                  <input type="text" name="collection" value={pdfConfig.collection} onChange={handlePdfConfigChange} />
                </div>
                <div className="form-group">
                  <label>Slogan da Capa</label>
                  <input type="text" name="slogan" value={pdfConfig.slogan} onChange={handlePdfConfigChange} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Linha de Contato (Rodapé)</label>
                  <input type="text" name="contact_line" value={pdfConfig.contact_line} onChange={handlePdfConfigChange} />
                </div>
                <div className="form-group">
                  <label>Nome do Arquivo PDF</label>
                  <input type="text" name="filename" value={pdfConfig.filename} onChange={handlePdfConfigChange} />
                </div>
              </div>

              <button type="submit" className="btn btn-primary btn-block" style={{ marginTop: '1.2rem', minHeight: '48px' }} disabled={generatingPdf}>
                {generatingPdf ? (
                  <>
                    <RefreshCw size={14} className="spin-anim" /> Gerando PDF...
                  </>
                ) : (
                  <>
                    <FileDown size={16} /> Gerar PDF do Catálogo
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Import product folder area */}
          <div className="admin-card">
            <h2>Importar Pasta de Produtos</h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--gray)', marginBottom: '1.8rem' }}>Faça upload em massa de uma pasta de produtos contendo imagens e descrições estruturadas.</p>

            <div className="catalog-upload-box" style={{ minHeight: '180px' }}>
              <input
                type="file"
                webkitdirectory="true"
                directory="true"
                multiple
                onChange={handleImportFolder}
                aria-label="Pasta de produtos"
              />
              <Upload size={32} className="text-gold" />
              <strong>Selecionar Pasta de Catálogo</strong>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--gray)' }}>Selecione a pasta raiz contendo arquivos de imagem e textos do catálogo.</p>
            </div>

            {importLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--gold-dark)', margin: '1.2rem 0 0', fontWeight: 600, justifyContent: 'center' }}>
                <RefreshCw size={16} className="spin-anim" /> Importação em andamento... Por favor, aguarde.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Spinner keyframe styles for refresh transitions */}
      <style>{`
        .spin-anim {
          animation: spin 1.2s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Admin;
