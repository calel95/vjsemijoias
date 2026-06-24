import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { API } from '../services/api';
import { ShieldCheck, Truck, ArrowLeft, CreditCard, ChevronRight, Copy, CheckCircle2 } from 'lucide-react';

const Checkout = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    cartItems,
    cartSubtotal,
    cartTotal,
    clearCart,
    formatPrice,
    shipping,
    calculateShipping,
    couponCode,
    discountPercent,
    discountAmount,
    user,
    logoutUser,
    isLoggedIn,
    showToast
  } = useStore();

  // --- CHECKOUT FORM STATE ---
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    cpf: '',
    phone: '',
    birthdate: '',
    cep: '',
    address: '',
    number: '',
    complement: '',
    neighborhood: '',
    city: '',
    state: ''
  });

  const [shippingOptions, setShippingOptions] = useState([]);
  const [selectedShippingId, setSelectedShippingId] = useState('');
  const [shippingLoading, setShippingLoading] = useState(false);
  const [shippingError, setShippingError] = useState('');
  
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [createdOrder, setCreatedOrder] = useState(null);
  
  // Pix states
  const [pollingActive, setPollingActive] = useState(false);
  const [pollingPaid, setPollingPaid] = useState(false);

  const lookupTimerRef = useRef(null);
  const pollTimerRef = useRef(null);

  // Sync user profile fields if logged in
  useEffect(() => {
    if (user) {
      setFormData(prev => ({
        ...prev,
        name: user.name || '',
        email: user.email || '',
        cpf: user.cpf || '',
        phone: user.phone || '',
        birthdate: user.birthdate || ''
      }));
    }
  }, [user]);

  // --- NSU / RETURN CHECK ON MOUNT ---
  useEffect(() => {
    const checkReturn = async () => {
      const orderNsu = searchParams.get('order_nsu');
      const transactionNsu = searchParams.get('transaction_nsu');
      const slug = searchParams.get('slug');

      if (orderNsu && transactionNsu && slug) {
        setCheckoutBusy(true);
        try {
          const result = await API.confirmInfinitePayPayment({
            order_nsu: orderNsu,
            transaction_nsu: transactionNsu,
            slug,
            capture_method: searchParams.get('capture_method') || '',
          });

          if (result.success && result.data.payment.status === 'paid') {
            clearCart();
            localStorage.removeItem('vj_pending_payment');
            localStorage.removeItem('vj_checkout_idempotency_key');
            setCreatedOrder(result.data.order);
            setPaymentInfo(result.data.payment);
            setCheckoutSuccess(true);
            showToast('Pagamento confirmado com sucesso!', 'success');
          } else {
            showToast(result.error || 'A confirmação do pagamento está pendente.', 'error');
          }
        } catch (e) {
          console.error(e);
        } finally {
          setCheckoutBusy(false);
        }
      }
    };

    checkReturn();
  }, [searchParams]);

  // --- PIX POLLING ---
  useEffect(() => {
    if (pollingActive && createdOrder && paymentInfo) {
      let attempts = 0;
      pollTimerRef.current = setInterval(async () => {
        attempts += 1;
        try {
          const result = await API.getPaymentStatus(createdOrder.id, paymentInfo.checkout_token);
          if (result.success && result.data.status === 'paid') {
            clearInterval(pollTimerRef.current);
            setPollingActive(false);
            setPollingPaid(true);
            showToast('Pagamento Pix confirmado!', 'success');
          }
        } catch (err) {}
        if (attempts >= 60) {
          clearInterval(pollTimerRef.current);
          setPollingActive(false);
        }
      }, 5000);
    }

    return () => clearInterval(pollTimerRef.current);
  }, [pollingActive, createdOrder, paymentInfo]);

  // Handle CEP Lookup and autofill address
  const handleCepChange = (e) => {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length > 5) {
      value = value.substring(0, 5) + '-' + value.substring(5, 8);
    }
    setFormData(prev => ({ ...prev, cep: value.substring(0, 9) }));

    const rawCep = value.replace(/\D/g, '');
    if (rawCep.length === 8) {
      clearTimeout(lookupTimerRef.current);
      lookupTimerRef.current = setTimeout(() => triggerCepLookup(rawCep), 400);
    } else {
      setShippingOptions([]);
      setSelectedShippingId('');
    }
  };

  const triggerCepLookup = async (cepDigits) => {
    setShippingLoading(true);
    setShippingError('');
    try {
      const addressRes = await API.lookupCep(cepDigits);
      if (addressRes.success && addressRes.data) {
        const addr = addressRes.data;
        setFormData(prev => ({
          ...prev,
          address: addr.street || '',
          neighborhood: addr.neighborhood || '',
          city: addr.city || '',
          state: addr.state || ''
        }));

        // Calculate shipping immediately for this CEP
        const shipRes = await API.calculateShipping(cartSubtotal, cepDigits, cartItems);
        if (shipRes.success) {
          const opts = Array.isArray(shipRes.data.options) 
            ? shipRes.data.options 
            : (shipRes.data.selected_option ? [shipRes.data.selected_option] : []);
          setShippingOptions(opts);
          if (opts.length > 0) {
            setSelectedShippingId(opts[0].id);
            // Apply first option by triggering store state update
            calculateShipping(cepDigits);
          }
        } else {
          setShippingError(shipRes.error || 'Não foi possível calcular as opções de frete.');
        }
      } else {
        showToast(addressRes.error || 'CEP não encontrado', 'error');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setShippingLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Mask Phone and CPF inputs
  const handlePhoneChange = (e) => {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length > 2) {
      value = `(${value.substring(0, 2)}) ${value.substring(2)}`;
    }
    if (value.length > 9) {
      value = `${value.substring(0, 9)}-${value.substring(9, 13)}`;
    }
    setFormData(prev => ({ ...prev, phone: value.substring(0, 15) }));
  };

  const handleCpfChange = (e) => {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length > 3) value = `${value.substring(0, 3)}.${value.substring(3)}`;
    if (value.length > 7) value = `${value.substring(0, 7)}.${value.substring(7)}`;
    if (value.length > 11) value = `${value.substring(0, 11)}-${value.substring(11, 13)}`;
    setFormData(prev => ({ ...prev, cpf: value.substring(0, 14) }));
  };

  const selectShippingOption = async (optionId) => {
    setSelectedShippingId(optionId);
    const selected = shippingOptions.find(o => o.id === optionId);
    if (selected) {
      // Simulate selected option update in StoreContext
      await calculateShipping(formData.cep.replace(/\D/g, ''));
    }
  };

  // Generate idempotency key for transactions
  const getIdempotencyKey = () => {
    let key = localStorage.getItem('vj_checkout_idempotency_key');
    if (!key) {
      key = `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      localStorage.setItem('vj_checkout_idempotency_key', key);
    }
    return key;
  };

  // Process Checkout submission redirecting to InfinitePay
  const handleSubmitCheckout = async (e) => {
    e.preventDefault();
    if (cartItems.length === 0) return;

    // Validate fields
    const requiredFields = ['name', 'email', 'cpf', 'phone', 'cep', 'address', 'number', 'neighborhood', 'city', 'state'];
    const missing = requiredFields.filter(f => !formData[f]);
    if (missing.length > 0) {
      showToast('Por favor, preencha todos os campos obrigatórios.', 'error');
      return;
    }

    if (!selectedShippingId) {
      showToast('Por favor, selecione uma opção de frete.', 'error');
      return;
    }

    setCheckoutBusy(true);
    try {
      const orderPayload = {
        customer_name: formData.name,
        customer_email: formData.email,
        customer_cpf: formData.cpf.replace(/\D/g, ''),
        customer_phone: formData.phone.replace(/\D/g, ''),
        address_zip: formData.cep.replace(/\D/g, ''),
        address_street: formData.address,
        address_number: formData.number,
        address_complement: formData.complement,
        address_neighborhood: formData.neighborhood,
        address_city: formData.city,
        address_state: formData.state,
        items: cartItems.map(item => ({ id: item.id, quantity: item.quantity })),
        coupon: couponCode || '',
        shipping_option_id: selectedShippingId,
        idempotency_key: getIdempotencyKey()
      };

      const result = await API.createInfinitePayCheckout(orderPayload);
      if (result.success && result.data.checkout_url) {
        // Save pending payment state
        localStorage.setItem('vj_pending_payment', JSON.stringify({
          order_id: result.data.order.id,
          checkout_token: result.data.payment.checkout_token,
        }));
        
        // Redirect to safe InfinitePay portal
        window.location.href = result.data.checkout_url;
      } else {
        showToast(result.error || 'Erro ao gerar checkout seguro. Verifique suas informações.', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Erro de conexão com o servidor.', 'error');
    } finally {
      setCheckoutBusy(false);
    }
  };

  const handleCopyPix = async () => {
    if (paymentInfo?.pix_qr_code) {
      await navigator.clipboard.writeText(paymentInfo.pix_qr_code);
      showToast('Pix Copia e Cola copiado com sucesso!', 'success');
    }
  };

  // --- RENDER SUCCESS BLOCK ---
  if (checkoutSuccess) {
    const isPaid = paymentInfo?.status === 'paid' || pollingPaid;
    return (
      <div className="checkout-page" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center', padding: '6rem 2rem' }}>
        <div style={{ fontSize: '4.5rem', marginBottom: '1.5rem', color: isPaid ? 'var(--success)' : 'var(--gold-dark)' }}>
          {isPaid ? '🎉' : '⏳'}
        </div>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.2rem', marginBottom: '1rem' }}>
          {isPaid ? 'Pedido Confirmado!' : 'Aguardando Pagamento'}
        </h2>
        <p style={{ color: 'var(--gray)', fontSize: '1.05rem', lineHeight: 1.6, marginBottom: '2rem' }}>
          {isPaid 
            ? 'Seu pagamento foi confirmado com sucesso. O pedido já está sendo preparado com muito carinho para envio.'
            : 'Seu pedido foi registrado! Conclua o pagamento via Pix ou Cartão na InfinitePay para confirmação.'
          }
        </p>

        <div style={{ background: 'var(--cream)', padding: '1.5rem', borderRadius: '20px', border: '1px solid rgba(166, 124, 61, 0.12)', margin: '2rem 0' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--gray)', display: 'block', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.4rem', fontWeight: 600 }}>
            Código do Pedido
          </span>
          <code style={{ fontSize: '1.5rem', color: 'var(--gold-dark)', fontWeight: 800 }}>
            {createdOrder?.id}
          </code>
        </div>

        {paymentInfo?.method === 'pix' && !isPaid && (
          <div style={{ background: 'var(--white)', border: '1px solid var(--gray-light)', borderRadius: '20px', padding: '2rem', marginTop: '1.5rem' }}>
            {paymentInfo.pix_qr_code_base64 && (
              <img
                src={`data:image/png;base64,${paymentInfo.pix_qr_code_base64}`}
                alt="QR Code Pix"
                style={{ width: '220px', height: '220px', margin: '0 auto 1.5rem', display: 'block' }}
              />
            )}
            <p style={{ fontSize: '0.9rem', color: 'var(--gray-dark)', marginBottom: '1rem' }}>
              Escaneie o código acima ou copie o código Pix copia e cola abaixo para efetuar o pagamento.
            </p>
            
            <textarea
              readOnly
              value={paymentInfo.pix_qr_code}
              style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1px solid rgba(166, 124, 61, 0.2)', fontSize: '0.8rem', fontFamily: 'monospace', resize: 'none', background: 'var(--gray-pale)', marginBottom: '1rem' }}
              rows={3}
            />

            <button type="button" onClick={handleCopyPix} className="btn btn-secondary btn-block">
              <Copy size={16} /> Copiar Código Pix
            </button>
            
            {paymentInfo.pix_ticket_url && (
              <a href={paymentInfo.pix_ticket_url} target="_blank" rel="noopener noreferrer" className="btn btn-outline btn-block" style={{ marginTop: '0.6rem' }}>
                Abrir Link do Pix
              </a>
            )}

            <div style={{ marginTop: '1.5rem', fontSize: '0.85rem', color: 'var(--gold-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontWeight: 600 }}>
              <span className="spinner" style={{ width: '16px', height: '16px', border: '2px solid var(--gold-dark)', borderTopColor: 'transparent', borderRadius: '50%', display: 'inline-block', animation: 'spin 1s linear infinite' }}></span>
              Verificando pagamento Pix em tempo real...
            </div>
          </div>
        )}

        <div style={{ marginTop: '2.5rem' }}>
          <Link to="/" className="btn btn-primary btn-block">Voltar para a Página Inicial</Link>
        </div>
      </div>
    );
  }

  // --- EMPTY CART REDIRECT ---
  if (cartItems.length === 0) {
    return (
      <div className="checkout-page" style={{ textAlign: 'center', padding: '8rem 2rem' }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2rem', marginBottom: '1rem' }}>Seu carrinho está vazio</h2>
        <p style={{ color: 'var(--gray)', marginBottom: '2.5rem' }}>Não há itens na sacola para finalizar a compra.</p>
        <Link to="/catalogo" className="btn btn-primary">Ver Coleções</Link>
      </div>
    );
  }

  return (
    <div className="checkout-page">
      <div style={{ textSelf: 'center', textAlign: 'center', marginBottom: '2.5rem' }}>
        <span className="section-tag" style={{ padding: 0 }}>Finalizar Compra</span>
        <h1 className="section-title" style={{ fontSize: '2.6rem', marginTop: '0.5rem' }}>Dados do <span>Pedido</span></h1>
      </div>

      <form onSubmit={handleSubmitCheckout}>
        <div className="checkout-grid">
          {/* Checkout Forms side */}
          <div className="checkout-form">
            
            {/* Personal Details */}
            <div className="checkout-section">
              <h3>👤 Dados Pessoais</h3>
              {isLoggedIn && user && (
                <div style={{ background: 'var(--cream)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(166, 124, 61, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.2rem' }}>
                  <div>
                    <strong style={{ fontSize: '0.92rem' }}>Identificado como {user.name}</strong>
                    <p style={{ fontSize: '0.78rem', color: 'var(--gray)', margin: 0 }}>{user.email}</p>
                  </div>
                  <button type="button" onClick={logoutUser} style={{ fontSize: '0.78rem', color: 'var(--error)', textDecoration: 'underline', fontWeight: 600 }}>
                    Sair
                  </button>
                </div>
              )}
              
              <div className="form-group">
                <label>Nome Completo <span className="required">*</span></label>
                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Nome Completo"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>E-mail <span className="required">*</span></label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="email@exemplo.com"
                  />
                </div>
                <div className="form-group">
                  <label>CPF <span className="required">*</span></label>
                  <input
                    type="text"
                    name="cpf"
                    required
                    value={formData.cpf}
                    onChange={handleCpfChange}
                    placeholder="000.000.000-00"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Telefone / WhatsApp <span className="required">*</span></label>
                  <input
                    type="text"
                    name="phone"
                    required
                    value={formData.phone}
                    onChange={handlePhoneChange}
                    placeholder="(00) 99999-9999"
                  />
                </div>
                <div className="form-group">
                  <label>Data de Nascimento</label>
                  <input
                    type="date"
                    name="birthdate"
                    value={formData.birthdate}
                    onChange={handleInputChange}
                  />
                </div>
              </div>
            </div>

            {/* Delivery Address */}
            <div className="checkout-section">
              <h3>📦 Endereço de Entrega</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label>CEP <span className="required">*</span></label>
                  <input
                    type="text"
                    name="cep"
                    required
                    value={formData.cep}
                    onChange={handleCepChange}
                    placeholder="00000-000"
                  />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label>Logradouro / Endereço <span className="required">*</span></label>
                  <input
                    type="text"
                    name="address"
                    required
                    value={formData.address}
                    onChange={handleInputChange}
                    placeholder="Rua, Avenida, etc."
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Número <span className="required">*</span></label>
                  <input
                    type="text"
                    name="number"
                    required
                    value={formData.number}
                    onChange={handleInputChange}
                    placeholder="123"
                  />
                </div>
                <div className="form-group">
                  <label>Complemento</label>
                  <input
                    type="text"
                    name="complement"
                    value={formData.complement}
                    onChange={handleInputChange}
                    placeholder="Apto, Bloco, etc."
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Bairro <span className="required">*</span></label>
                  <input
                    type="text"
                    name="neighborhood"
                    required
                    value={formData.neighborhood}
                    onChange={handleInputChange}
                    placeholder="Bairro"
                  />
                </div>
                <div className="form-group">
                  <label>Cidade <span className="required">*</span></label>
                  <input
                    type="text"
                    name="city"
                    required
                    value={formData.city}
                    onChange={handleInputChange}
                    placeholder="Cidade"
                  />
                </div>
                <div className="form-group">
                  <label>Estado <span className="required">*</span></label>
                  <select
                    name="state"
                    required
                    value={formData.state}
                    onChange={handleInputChange}
                  >
                    <option value="">UF</option>
                    {['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'].map(uf => (
                      <option key={uf} value={uf}>{uf}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Payment Method Details */}
            <div className="checkout-section">
              <h3>💳 Forma de Pagamento</h3>
              <div style={{ background: 'var(--cream)', padding: '1.5rem', borderRadius: '16px', border: '1px solid rgba(166, 124, 61, 0.1)', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <CreditCard size={32} className="text-gold" style={{ flexShrink: 0 }} />
                <div>
                  <strong style={{ fontSize: '0.95rem', display: 'block', marginBottom: '0.2rem' }}>
                    Checkout Seguro da InfinitePay
                  </strong>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--gray)', lineHeight: 1.4 }}>
                    Pague com Pix ou Cartão de Crédito em até 12x sem juros. Você será redirecionada de forma criptografada para a InfinitePay para concluir o pagamento.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right summary column */}
          <div>
            <div className="order-summary">
              <h3>Resumo da Compra</h3>
              
              <div className="order-items">
                {cartItems.map((item) => (
                  <div key={item.id} className="order-item">
                    <div className="order-item-image">
                      {item.image ? (
                        <img src={getProductImageUrl(item.image)} alt={item.name} />
                      ) : (
                        <span className="order-item-placeholder">💎</span>
                      )}
                    </div>
                    <div className="order-item-info">
                      <h5>{item.name}</h5>
                      <p>Qtd: {item.quantity} × {formatPrice(item.price)}</p>
                    </div>
                    <div className="order-item-price">
                      {formatPrice(item.price * item.quantity)}
                    </div>
                  </div>
                ))}
              </div>

              <div className="summary-row">
                <span>Subtotal:</span>
                <span>{formatPrice(cartSubtotal)}</span>
              </div>

              {/* Shipping options selection list */}
              <div style={{ margin: '1.2rem 0', borderTop: '1px solid rgba(166, 124, 61, 0.1)', borderBottom: '1px solid rgba(166, 124, 61, 0.1)', padding: '1.2rem 0' }}>
                <strong style={{ fontSize: '0.85rem', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.6rem', color: 'var(--gray-dark)' }}>
                  Opções de Envio
                </strong>
                
                {shippingLoading ? (
                  <p style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>Carregando opções...</p>
                ) : shippingError ? (
                  <p style={{ fontSize: '0.85rem', color: 'var(--error)' }}>{shippingError}</p>
                ) : shippingOptions.length === 0 ? (
                  <p style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>Informe seu CEP para calcular opções de envio.</p>
                ) : (
                  <div style={{ display: 'grid', gap: '0.6rem' }}>
                    {shippingOptions.map((opt) => (
                      <label
                        key={opt.id}
                        style={{ display: 'block', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid var(--gray-light)', cursor: 'pointer', background: selectedShippingId === opt.id ? 'var(--cream)' : 'var(--white)', transition: 'all 0.3s ease' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.88rem', fontWeight: 700 }}>
                            <input
                              type="radio"
                              name="shipping_opt"
                              value={opt.id}
                              checked={selectedShippingId === opt.id}
                              onChange={() => selectShippingOption(opt.id)}
                            />
                            {opt.company ? `${opt.company} - ${opt.service}` : opt.service}
                          </span>
                          <strong style={{ fontSize: '0.88rem', color: 'var(--gold-dark)' }}>
                            {opt.shipping === 0 ? 'Grátis' : formatPrice(opt.shipping)}
                          </strong>
                        </div>
                        <small style={{ display: 'block', marginLeft: '1.6rem', color: 'var(--gray)', fontSize: '0.78rem' }}>
                          Prazo estimado: {opt.estimated_days ? `${opt.estimated_days} dias úteis` : 'A combinar'}
                        </small>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {shipping > 0 && (
                <div className="summary-row">
                  <span>Frete:</span>
                  <span>{formatPrice(shipping)}</span>
                </div>
              )}

              {discountAmount > 0 && (
                <div className="summary-row" style={{ color: 'var(--success)' }}>
                  <span>Desconto:</span>
                  <span>-{formatPrice(discountAmount)}</span>
                </div>
              )}

              <div className="summary-row total">
                <span>Total:</span>
                <span className="price">{formatPrice(cartTotal)}</span>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                style={{ marginTop: '1.8rem', minHeight: '52px' }}
                disabled={checkoutBusy}
              >
                {checkoutBusy ? 'Gerando Pagamento...' : 'Ir Para Pagamento Seguro'} <ChevronRight size={16} />
              </button>

              <Link to="/carrinho" className="btn btn-secondary btn-block" style={{ marginTop: '0.6rem' }}>
                Voltar à Sacola
              </Link>
            </div>
          </div>
        </div>
      </form>
      
      {/* Keyframe animations styles for Pix polling spinner */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Checkout;
