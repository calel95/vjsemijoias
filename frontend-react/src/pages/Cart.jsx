import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { Trash2, ShoppingBag, Plus, Minus, ArrowRight, Truck, Tag, Percent } from 'lucide-react';

const Cart = () => {
  const {
    cartItems,
    cartSubtotal,
    cartTotal,
    removeFromCart,
    updateQuantity,
    formatPrice,
    shipping,
    shippingMessage,
    calculateShipping,
    couponCode,
    discountPercent,
    discountAmount,
    applyCoupon,
    removeCoupon,
    storeConfig
  } = useStore();

  const [cep, setCep] = useState('');
  const [calculatingShipping, setCalculatingShipping] = useState(false);
  const [couponInput, setCouponInput] = useState('');
  const [applyingCoupon, setApplyingCoupon] = useState(false);

  // Mask CEP input: 00000-000
  const handleCepChange = (e) => {
    let val = e.target.value.replace(/\D/g, '');
    if (val.length > 5) {
      val = val.substring(0, 5) + '-' + val.substring(5, 8);
    }
    setCep(val.substring(0, 9));
  };

  const handleCalculateShipping = async (e) => {
    e.preventDefault();
    const rawCep = cep.replace(/\D/g, '');
    if (rawCep.length !== 8) {
      alert('CEP inválido. Digite 8 números.');
      return;
    }
    setCalculatingShipping(true);
    await calculateShipping(rawCep);
    setCalculatingShipping(false);
  };

  const handleApplyCoupon = async (e) => {
    e.preventDefault();
    if (!couponInput.trim()) return;
    setApplyingCoupon(true);
    await applyCoupon(couponInput.trim());
    setApplyingCoupon(false);
    setCouponInput('');
  };

  const getProductImageUrl = (imageName) => {
    if (!imageName) return null;
    if (imageName.startsWith('http') || imageName.startsWith('/')) {
      return imageName;
    }
    return `/images/catalog/${imageName}`;
  };

  if (cartItems.length === 0) {
    return (
      <div className="cart-page">
        <div className="empty-cart">
          <div className="empty-cart-icon">🛒</div>
          <h2>Sua sacola está vazia</h2>
          <p>Explore nosso catálogo e adicione lindas semijoias à sua sacola.</p>
          <Link to="/catalogo" className="btn btn-primary">
            Conhecer Coleções <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="cart-page">
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', marginBottom: '2rem' }}>Sacola de Compras</h1>

      <div className="cart-grid">
        {/* Cart Items List */}
        <div className="cart-items">
          {cartItems.map((item) => (
            <div key={item.id} className="cart-item">
              <div className="cart-item-image">
                {item.image ? (
                  <img src={getProductImageUrl(item.image)} alt={item.name} />
                ) : (
                  <div className="cart-item-placeholder">💍</div>
                )}
              </div>

              <div className="cart-item-info">
                <Link to={`/produto/${item.id}`}>
                  <h4>{item.name}</h4>
                </Link>
                <p>Preço unitário: {formatPrice(item.price)}</p>
                {item.stock_status === 'preorder' && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--gold-dark)', display: 'block', marginTop: '4px', fontWeight: 600 }}>
                    Peça sob encomenda
                  </span>
                )}
              </div>

              <div className="cart-item-actions">
                <div className="cart-item-price">
                  {formatPrice(item.price * item.quantity)}
                </div>

                <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', marginTop: '0.3rem' }}>
                  <div className="quantity-controls" style={{ transform: 'scale(0.85)', originX: 'right' }}>
                    <button onClick={() => updateQuantity(item.id, item.quantity - 1)} type="button" aria-label="Diminuir">
                      <Minus size={14} />
                    </button>
                    <input
                      type="text"
                      value={item.quantity}
                      readOnly
                      aria-label="Quantidade"
                    />
                    <button onClick={() => updateQuantity(item.id, item.quantity + 1)} type="button" aria-label="Aumentar">
                      <Plus size={14} />
                    </button>
                  </div>

                  <button
                    onClick={() => removeFromCart(item.id)}
                    className="cart-item-remove"
                    title="Remover produto"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Pricing Summary Sidepanel */}
        <div className="cart-summary">
          <h3>Resumo do Pedido</h3>

          {/* Subtotal */}
          <div className="summary-row">
            <span>Subtotal</span>
            <span>{formatPrice(cartSubtotal)}</span>
          </div>

          {/* Shipping calculation */}
          <div style={{ borderTop: '1px solid rgba(166, 124, 61, 0.1)', borderBottom: '1px solid rgba(166, 124, 61, 0.1)', padding: '1rem 0', margin: '1rem 0' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.6rem', color: 'var(--gray-dark)' }}>
              <Truck size={16} /> Calcular Frete
            </span>
            <form onSubmit={handleCalculateShipping} style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="00000-000"
                value={cep}
                onChange={handleCepChange}
                style={{ padding: '0.5rem 0.8rem', border: '1px solid rgba(166, 124, 61, 0.2)', borderRadius: '30px', fontSize: '0.85rem', flex: 1, minWidth: '100px' }}
                aria-label="CEP"
              />
              <button
                type="submit"
                className="btn btn-outline"
                style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', borderRadius: '30px' }}
                disabled={calculatingShipping}
              >
                {calculatingShipping ? 'Calculando...' : 'Calcular'}
              </button>
            </form>
            {shippingMessage && (
              <p style={{ fontSize: '0.78rem', color: 'var(--gray)', margin: '0.6rem 0 0', lineHeight: 1.4 }}>
                {shippingMessage}
              </p>
            )}
            {cartSubtotal >= storeConfig.shipping_free_minimum && (
              <p style={{ fontSize: '0.78rem', color: 'var(--success)', margin: '0.4rem 0 0', fontWeight: 600 }}>
                Parabéns! Você ganhou Frete Grátis 🎉
              </p>
            )}
          </div>

          {/* Coupon Code section */}
          <div style={{ paddingBottom: '1rem', borderBottom: '1px solid rgba(166, 124, 61, 0.1)', marginBottom: '1rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.6rem', color: 'var(--gray-dark)' }}>
              <Tag size={16} /> Cupom de Desconto
            </span>
            {couponCode ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--white)', padding: '0.6rem 1rem', borderRadius: '30px', border: '1px dashed var(--gold-primary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.85rem', color: 'var(--gold-dark)', fontWeight: 700 }}>
                  <Percent size={14} /> {couponCode} ({discountPercent}%)
                </span>
                <button
                  type="button"
                  onClick={removeCoupon}
                  style={{ color: 'var(--error)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                >
                  Remover
                </button>
              </div>
            ) : (
              <form onSubmit={handleApplyCoupon} style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  placeholder="DIGITE O CUPOM"
                  value={couponInput}
                  onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                  style={{ padding: '0.5rem 0.8rem', border: '1px solid rgba(166, 124, 61, 0.2)', borderRadius: '30px', fontSize: '0.85rem', flex: 1, minWidth: '100px' }}
                  aria-label="Cupom"
                />
                <button
                  type="submit"
                  className="btn btn-outline"
                  style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', borderRadius: '30px' }}
                  disabled={applyingCoupon}
                >
                  Aplicar
                </button>
              </form>
            )}
          </div>

          {/* Pricing Details */}
          {shipping > 0 && (
            <div className="summary-row">
              <span>Frete</span>
              <span>{formatPrice(shipping)}</span>
            </div>
          )}

          {discountAmount > 0 && (
            <div className="summary-row" style={{ color: 'var(--success)', fontWeight: 600 }}>
              <span>Desconto Cupom</span>
              <span>-{formatPrice(discountAmount)}</span>
            </div>
          )}

          {/* Total Price */}
          <div className="summary-row total">
            <span>Total</span>
            <span className="price">{formatPrice(cartTotal)}</span>
          </div>

          {/* Checkout Button */}
          <Link
            to="/checkout"
            className="btn btn-primary btn-block"
            style={{ marginTop: '1.8rem', minHeight: '52px' }}
          >
            Finalizar Compra <ArrowRight size={16} />
          </Link>
          
          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <Link to="/catalogo" style={{ fontSize: '0.82rem', color: 'var(--gray)', textDecoration: 'underline' }}>
              Continuar Comprando
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Cart;
