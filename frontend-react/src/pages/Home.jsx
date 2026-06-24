import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { API } from '../services/api';
import ProductCard from '../components/ProductCard';
import { ShieldCheck, Truck, RotateCcw, ArrowRight } from 'lucide-react';

const Home = () => {
  const { formatPrice } = useStore();
  const navigate = useNavigate();
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Category Icon Fallbacks
  const getCategoryIcon = (categoryName) => {
    const icons = {
      'Brincos': '💍',
      'Colares': '📿',
      'Pulseiras': '💎',
      'Anéis': '💫',
      'Pingentes': '✨'
    };
    return icons[categoryName] || '💍';
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          API.getProducts('all', '', { perPage: 8 }),
          API.getCategories()
        ]);

        if (productsRes.success && productsRes.data?.products) {
          // Filter bestsellers or just take the first 4 products as featured
          const prods = productsRes.data.products;
          const bestsellers = prods.filter(p => p.storefront_badge === 'bestseller');
          setFeaturedProducts(bestsellers.length > 0 ? bestsellers : prods.slice(0, 4));
        }

        if (categoriesRes.success && categoriesRes.data) {
          setCategories(categoriesRes.data);
        } else {
          // Fallback static categories if backend response is empty
          setCategories([
            { name: 'Brincos', count: 0 },
            { name: 'Colares', count: 0 },
            { name: 'Pulseiras', count: 0 },
            { name: 'Anéis', count: 0 }
          ]);
        }
      } catch (err) {
        console.error('Erro ao buscar dados da Home', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return (
    <div>
      {/* Hero Section */}
      <header className="hero">
        <div className="hero-container">
          <div className="hero-content">
            <span className="section-tag" style={{ padding: 0 }}>Lançamentos Exclusivos</span>
            <h1>
              Elegância em cada <span>detalhe</span>
            </h1>
            <p>
              Coleção de semijoias finas banhadas a Ouro 18k. Desenvolvidas com tecnologia hipoalergênica premium e garantia de brilho eterno.
            </p>
            <div className="hero-buttons">
              <Link to="/catalogo" className="btn btn-primary">
                Ver Coleções <ArrowRight size={16} />
              </Link>
            </div>
          </div>
          <div className="hero-image">
            <img src="/images/logo.png" alt="VJ Semijoias Logo" className="hero-logo" />
          </div>
        </div>
      </header>

      {/* Categories Medallion Section */}
      <section className="section categories">
        <div className="section-container">
          <div className="section-header">
            <span className="section-tag">Coleções</span>
            <h2 className="section-title">Navegue por <span>Categoria</span></h2>
            <p className="section-subtitle">Escolha sua categoria e encante-se com nossos designs exclusivos.</p>
          </div>

          <div className="categories-grid">
            {categories.map((cat, idx) => (
              <Link
                key={idx}
                to={`/catalogo?category=${encodeURIComponent(cat.name)}`}
                className="category-card"
              >
                <span className="category-icon">{getCategoryIcon(cat.name)}</span>
                <h3>{cat.name}</h3>
                {cat.count !== undefined && cat.count > 0 ? (
                  <p>{cat.count} peças</p>
                ) : (
                  <p>Ver coleção</p>
                )}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Highlights / Featured Grid */}
      <section className="section">
        <div className="section-container">
          <div className="section-header">
            <span className="section-tag">Destaques</span>
            <h2 className="section-title">Mais <span>Desejados</span></h2>
            <p className="section-subtitle">Nossas peças mais cobiçadas selecionadas especialmente para você.</p>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', fontSize: '1.2rem', color: 'var(--gray)' }}>
              Carregando destaques...
            </div>
          ) : featuredProducts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray)' }}>
              Nenhum produto cadastrado no momento.
            </div>
          ) : (
            <div className="products-grid">
              {featuredProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '4rem' }}>
            <Link to="/catalogo" className="btn btn-outline">
              Ver Catálogo Completo
            </Link>
          </div>
        </div>
      </section>

      {/* Features Checklist */}
      <section className="section features">
        <div className="section-container">
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <ShieldCheck size={38} strokeWidth={1.5} style={{ margin: '0 auto 1rem', color: 'var(--gold-dark)' }} />
              </div>
              <h4>Qualidade Garantida</h4>
              <p>Banho de Ouro 18k com acabamento de alta verniz e 1 ano de garantia total.</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <Truck size={38} strokeWidth={1.5} style={{ margin: '0 auto 1rem', color: 'var(--gold-dark)' }} />
              </div>
              <h4>Frete Especial</h4>
              <p>Envios seguros para todo o Brasil com frete grátis em compras selecionadas.</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <RotateCcw size={38} strokeWidth={1.5} style={{ margin: '0 auto 1rem', color: 'var(--gold-dark)' }} />
              </div>
              <h4>Troca Fácil</h4>
              <p>Primeira troca grátis em até 7 dias após o recebimento sem burocracias.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
