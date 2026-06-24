import React from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { ShoppingCart } from 'lucide-react';

const ProductCard = ({ product }) => {
  const { addToCart, formatPrice } = useStore();

  if (!product) return null;

  // Resolve image source URL
  const getProductImageUrl = (imageName) => {
    if (!imageName) return null;
    if (imageName.startsWith('http') || imageName.startsWith('/')) {
      return imageName;
    }
    return `/images/catalog/${imageName}`;
  };

  const mainImage = product.image || (product.images && product.images[0]);
  const imageUrl = getProductImageUrl(mainImage);

  // Status badges
  const renderBadge = () => {
    if (!product.storefront_badge) return null;
    
    const badgeLabels = {
      new: 'Novidade',
      sale: 'Oferta',
      bestseller: 'Destaque'
    };

    const label = badgeLabels[product.storefront_badge] || product.storefront_badge;
    return (
      <span className={`product-badge ${product.storefront_badge}`}>
        {label}
      </span>
    );
  };

  // Stock note
  const renderStockNote = () => {
    if (product.stock_status === 'preorder') {
      return <span className="stock-note preorder">Sob Encomenda</span>;
    }
    if (product.stock_status === 'out_of_stock' || product.stock_status === 'inactive') {
      return <span className="stock-note unavailable">Esgotado</span>;
    }
    return null;
  };

  const isUnavailable = product.stock_status === 'out_of_stock' || product.stock_status === 'inactive';

  return (
    <div className="product-card">
      <div className="product-image">
        {renderBadge()}
        
        {imageUrl ? (
          <Link to={`/produto/${product.id}`}>
            <img src={imageUrl} alt={product.name} loading="lazy" />
          </Link>
        ) : (
          <Link to={`/produto/${product.id}`} className="placeholder">
            💍
          </Link>
        )}
      </div>

      <div className="product-info">
        <span className="product-category">{product.category}</span>
        
        <Link to={`/produto/${product.id}`}>
          <h3 className="product-title">{product.name}</h3>
        </Link>
        
        <p className="product-description">
          {product.description ? (
            product.description.length > 80 
              ? `${product.description.substring(0, 80)}...` 
              : product.description
          ) : (
            'Semijoia hipoalergênica com acabamento impecável banhado a ouro.'
          )}
        </p>

        {renderStockNote()}

        <div className="product-footer">
          <div className="product-price-wrapper">
            <div className="product-price">
              {product.old_price && product.old_price > product.price && (
                <span className="old-price">{formatPrice(product.old_price)}</span>
              )}
              {formatPrice(product.price)}
            </div>
            <div className="product-installment">
              3x de {formatPrice(product.price / 3)} s/ juros
            </div>
          </div>

          <button
            className="btn-add-cart"
            onClick={() => addToCart(product, 1)}
            disabled={isUnavailable}
            title={isUnavailable ? 'Produto indisponível' : 'Adicionar à sacola'}
          >
            <ShoppingCart size={14} />
            <span>Adicionar</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
