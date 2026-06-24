import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { API } from '../services/api';
import { ShoppingBag, ArrowLeft, Plus, Minus, Star, Heart, Calendar } from 'lucide-react';

const ProductDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToCart, formatPrice, storeConfig } = useStore();

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [activeImage, setActiveImage] = useState('');

  useEffect(() => {
    const fetchProduct = async () => {
      setLoading(true);
      try {
        const res = await API.getProduct(id);
        if (res.success && res.data) {
          setProduct(res.data);
          // Set initial active image
          const mainImage = res.data.image || (res.data.images && res.data.images[0]) || '';
          setActiveImage(mainImage);
        } else {
          setProduct(null);
        }
      } catch (err) {
        console.error('Erro ao carregar detalhes do produto', err);
      } finally {
        setLoading(false);
      }
    };

    if (id) fetchProduct();
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '10rem 2rem', fontSize: '1.2rem', color: 'var(--gray)' }}>
        Carregando detalhes do produto...
      </div>
    );
  }

  if (!product) {
    return (
      <div style={{ textAlign: 'center', padding: '10rem 2rem' }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2rem', marginBottom: '1.5rem' }}>Produto não encontrado</h2>
        <p style={{ color: 'var(--gray)', marginBottom: '2.5rem' }}>O produto que você procura não está disponível ou foi removido.</p>
        <Link to="/catalogo" className="btn btn-primary">Voltar ao Catálogo</Link>
      </div>
    );
  }

  // Resolve image URL
  const getImageUrl = (imageName) => {
    if (!imageName) return '';
    if (imageName.startsWith('http') || imageName.startsWith('/')) {
      return imageName;
    }
    return `/images/catalog/${imageName}`;
  };

  const imagesList = product.images && product.images.length > 0 ? product.images : (product.image ? [product.image] : []);

  const handleIncrement = () => setQuantity(prev => prev + 1);
  const handleDecrement = () => setQuantity(prev => Math.max(1, prev - 1));

  const handleAddToCart = () => {
    addToCart(product, quantity);
  };

  const isPreorder = product.stock_status === 'preorder';
  const isUnavailable = product.stock_status === 'out_of_stock' || product.stock_status === 'inactive';

  return (
    <div className="product-detail">
      <Link to="/catalogo" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--gold-dark)', fontWeight: 600, marginBottom: '2.5rem', textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '1px' }}>
        <ArrowLeft size={16} /> Voltar ao Catálogo
      </Link>

      <div className="product-detail-grid">
        {/* Asymmetric Image Gallery */}
        <div className={`product-gallery ${imagesList.length > 1 ? 'has-thumbnails' : ''}`}>
          {imagesList.length > 1 && (
            <div className="product-gallery-thumbnails">
              {imagesList.map((img, index) => (
                <div
                  key={index}
                  className={`product-gallery-thumb ${img === activeImage ? 'active' : ''}`}
                  onClick={() => setActiveImage(img)}
                >
                  <img src={getImageUrl(img)} alt={`${product.name} - foto ${index + 1}`} />
                </div>
              ))}
            </div>
          )}
          
          <div className="product-detail-image">
            {activeImage ? (
              <img src={getImageUrl(activeImage)} alt={product.name} />
            ) : (
              <div className="placeholder-large">💍</div>
            )}
          </div>
        </div>

        {/* Product Details Info */}
        <div className="product-detail-info">
          <span className="product-category">{product.category}</span>
          <h1>{product.name}</h1>
          
          {/* Reviews Rating Placeholder (Aesthetics) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--gold-dark)', margin: '-0.5rem 0 1.5rem' }}>
            <div style={{ display: 'flex' }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={15} fill="var(--gold-primary)" stroke="none" />)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--gray)', fontWeight: 600 }}>(12 avaliações)</span>
          </div>

          <div className="product-price">
            {product.old_price && product.old_price > product.price && (
              <span className="old-price" style={{ fontSize: '1.2rem', marginBottom: '0.4rem' }}>
                {formatPrice(product.old_price)}
              </span>
            )}
            {formatPrice(product.price)}
            <div className="product-installment">
              Ou em 3x de {formatPrice(product.price / 3)} sem juros no cartão
            </div>
          </div>

          <p className="product-description">
            {product.description || 'Esta semijoia traz consigo um design exclusivo e moderno, ideal para destacar qualquer look. Confeccionada com as melhores ligas de metal, recebe um banho multicamadas de Ouro 18k e uma cobertura extra de verniz protetor que estende seu brilho e durabilidade.'}
          </p>

          {/* Pre-order delay notification */}
          {isPreorder && (
            <div className="stock-note preorder detail" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1rem', fontSize: '0.85rem' }}>
              <Calendar size={15} />
              <span>
                <strong>Prazo de Produção:</strong> Peça sob encomenda. Será produzida e enviada em até <strong>{storeConfig.preorder_days || 10} dias úteis</strong>.
              </span>
            </div>
          )}

          {isUnavailable && (
            <div className="stock-note unavailable detail" style={{ padding: '0.6rem 1rem', fontSize: '0.85rem' }}>
              <span>Desculpe, este item encontra-se indisponível no momento.</span>
            </div>
          )}

          {/* Core Features */}
          <div className="product-features">
            <h4>Especificações Premium</h4>
            <ul>
              <li>Livre de Níquel (Hipoalergênico)</li>
              <li>Banho de Ouro 18k multicamadas</li>
              <li>Verniz Protetor Antialérgico de Alta Resistência</li>
              <li>Garantia Oficial de 1 Ano</li>
            </ul>
          </div>

          {/* Quantity and Checkout Actions */}
          {!isUnavailable && (
            <div className="quantity-selector">
              <label>Quantidade:</label>
              <div className="quantity-controls">
                <button onClick={handleDecrement} type="button" aria-label="Diminuir">
                  <Minus size={14} />
                </button>
                <input
                  type="text"
                  value={quantity}
                  readOnly
                  aria-label="Quantidade selecionada"
                />
                <button onClick={handleIncrement} type="button" aria-label="Aumentar">
                  <Plus size={14} />
                </button>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleAddToCart}
                style={{ flex: 1, minWidth: '200px' }}
              >
                <ShoppingBag size={16} /> Adicionar à Sacola
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
