import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { API } from '../services/api';
import ProductCard from '../components/ProductCard';
import { Search, RotateCcw, FileText, Download } from 'lucide-react';

const Catalog = () => {
  const { formatPrice } = useStore();
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse filters from URL query parameters
  const currentCategory = searchParams.get('cat') || 'all';
  const currentSearch = searchParams.get('q') || '';
  const currentSort = searchParams.get('sort') || 'newest';

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [visibleCount, setVisibleCount] = useState(12);
  const PRODUCTS_PER_PAGE = 12;

  const searchInputRef = useRef(null);

  // Category Icon Fallbacks
  const getCategoryIcon = (categoryName) => {
    const icons = {
      'all': '💎',
      'Todos': '💎',
      'Brincos': '💍',
      'Colares': '📿',
      'Pulseiras': '⚜️',
      'Aneis': '💍',
      'Anéis': '💍',
      'Pingentes': '🔮',
      'Chaveiros': '🔑'
    };
    return icons[categoryName] || '✨';
  };

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await API.getCategories();
        if (res.success && res.data) {
          // Add "Todos" if not present
          const list = res.data;
          const hasAll = list.some(c => c.id === 'all');
          if (!hasAll) {
            setCategories([{ id: 'all', name: 'Todos' }, ...list]);
          } else {
            setCategories(list);
          }
        } else {
          // Static fallback
          setCategories([
            { id: 'all', name: 'Todos' },
            { id: 'brincos', name: 'Brincos' },
            { id: 'colares', name: 'Colares' },
            { id: 'pulseiras', name: 'Pulseiras' },
            { id: 'aneis', name: 'Aneis' },
            { id: 'pingentes', name: 'Pingentes' }
          ]);
        }
      } catch (err) {
        console.error('Erro ao buscar categorias', err);
      }
    };
    loadCategories();
  }, []);

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        // Fetch all products since local client does filtering
        const res = await API.getProducts();
        if (res.success) {
          const items = Array.isArray(res.data) 
            ? res.data 
            : (res.data?.products || res.data?.items || []);
          setProducts(items);
        }
      } catch (err) {
        console.error('Erro ao buscar produtos', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  // Sync search input value with URL param
  useEffect(() => {
    if (searchInputRef.current) {
      searchInputRef.current.value = currentSearch;
    }
  }, [currentSearch]);

  const updateURLParams = (updates) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, val]) => {
      if (val === null || val === undefined || val === 'all' || val === '') {
        newParams.delete(key);
      } else {
        newParams.set(key, val);
      }
    });
    setSearchParams(newParams);
    setVisibleCount(PRODUCTS_PER_PAGE);
  };

  const handleCategoryChange = (categoryId) => {
    updateURLParams({ cat: categoryId });
  };

  const handleSearchChange = (e) => {
    updateURLParams({ q: e.target.value.trim() });
  };

  const handleSortChange = (e) => {
    updateURLParams({ sort: e.target.value });
  };

  const handleResetFilters = () => {
    setSearchParams({});
    setVisibleCount(PRODUCTS_PER_PAGE);
    if (searchInputRef.current) {
      searchInputRef.current.value = '';
    }
  };

  const handleLoadMore = () => {
    setVisibleCount(prev => prev + PRODUCTS_PER_PAGE);
  };

  // Helper matching rule to align with backend categories comparison
  const isCategoryMatch = (productCategory, filterCategory) => {
    if (!productCategory || !filterCategory) return false;
    const norm = (str) => str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return norm(productCategory) === norm(filterCategory);
  };

  // Filter & Sort logic
  const filteredProducts = (() => {
    let result = [...products];

    // 1. Category Filter
    if (currentCategory && currentCategory !== 'all') {
      // Find category name by ID
      const selectedCat = categories.find(c => c.id === currentCategory);
      const catName = selectedCat ? selectedCat.name : currentCategory;
      result = result.filter(p => isCategoryMatch(p.category, catName) || isCategoryMatch(p.category, currentCategory));
    }

    // 2. Search Filter
    if (currentSearch) {
      const search = currentSearch.toLowerCase();
      result = result.filter(p =>
        (p.name && p.name.toLowerCase().includes(search)) ||
        (p.description && p.description.toLowerCase().includes(search)) ||
        (p.category && p.category.toLowerCase().includes(search))
      );
    }

    // 3. Sorting
    const byName = (a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'pt-BR');
    const byPrice = (a, b) => Number(a.price || 0) - Number(b.price || 0);

    if (currentSort === 'name_asc') {
      result.sort(byName);
    } else if (currentSort === 'price_asc') {
      result.sort(byPrice);
    } else if (currentSort === 'price_desc') {
      result.sort((a, b) => byPrice(b, a));
    } else {
      // Default: newest (higher IDs first)
      result.sort((a, b) => Number(b.id || 0) - Number(a.id || 0));
    }

    return result;
  })();

  const visibleProducts = filteredProducts.slice(0, visibleCount);

  return (
    <div>
      {/* Hero Catalog */}
      <section className="catalog-hero">
        <h1>Nosso <span>Catálogo</span></h1>
        <p>Explore a coleção oficial de semijoias VJ banhadas a ouro 18k</p>
        <div className="breadcrumb">
          <a href="/">Início</a>
          <span>›</span>
          <span>Catálogo</span>
        </div>
      </section>

      <section className="section">
        <div className="section-container">
          
          {/* PDF DOWNLOAD BAR */}
          <div className="pdf-download-bar">
            <p style={{ margin: 0 }}>
              <strong>📄 Baixe nosso catálogo oficial em PDF</strong>
              Acesse offline a coleção completa de semijoias VJ
            </p>
            <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
              <a href="/pdf/catalogo-vj.pdf" download="catalogo-vj-semijoias.pdf" className="btn btn-secondary">
                <Download size={14} /> Baixar PDF
              </a>
              <a href="/pdf-visualizar.html" target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{ borderColor: 'white', color: 'white' }}>
                <FileText size={14} /> Visualizar
              </a>
            </div>
          </div>

          {/* FILTERS */}
          <div className="filters">
            <div className="filter-group">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  className={`filter-btn ${cat.id === currentCategory ? 'active' : ''}`}
                  onClick={() => handleCategoryChange(cat.id)}
                >
                  <span style={{ marginRight: '4px' }}>{getCategoryIcon(cat.name)}</span>
                  {cat.name}
                </button>
              ))}
            </div>

            <div className="catalog-controls">
              <div className="search-box">
                <input
                  type="text"
                  ref={searchInputRef}
                  defaultValue={currentSearch}
                  onChange={(e) => {
                    // Debounce input to prevent heavy updates
                    const val = e.target.value;
                    clearTimeout(window.searchTimeout);
                    window.searchTimeout = setTimeout(() => {
                      updateURLParams({ q: val.trim() });
                    }, 400);
                  }}
                  placeholder="Buscar produto..."
                />
              </div>

              <select value={currentSort} onChange={handleSortChange} className="sort-select" aria-label="Ordenar produtos">
                <option value="newest">Mais recentes</option>
                <option value="name_asc">Nome A-Z</option>
                <option value="price_asc">Menor preço</option>
                <option value="price_desc">Maior preço</option>
              </select>

              <button type="button" onClick={handleResetFilters} className="btn-reset-filters">
                <RotateCcw size={13} style={{ marginRight: '4px', display: 'inline' }} />
                Limpar
              </button>
            </div>
          </div>

          {/* RESULTS COUNTER */}
          <div className="catalog-results-bar">
            <span>
              <strong>{filteredProducts.length}</strong> produto{filteredProducts.length !== 1 ? 's' : ''} encontrado{filteredProducts.length !== 1 ? 's' : ''}
            </span>
            {filteredProducts.length > 0 && (
              <span id="products-page-info">
                Mostrando {visibleProducts.length} de {filteredProducts.length}
              </span>
            )}
          </div>

          {/* PRODUCTS LIST */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '5rem', fontSize: '1.2rem', color: 'var(--gray)' }}>
              Carregando catálogo de semijoias...
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="empty-cart" style={{ boxShadow: 'none', border: 'none' }}>
              <div className="empty-cart-icon">🔍</div>
              <h2>Nenhum produto encontrado</h2>
              <p>Tente refinar seus termos de busca ou mudar os filtros de categoria.</p>
              <button onClick={handleResetFilters} className="btn btn-primary">Limpar Filtros</button>
            </div>
          ) : (
            <>
              <div className="products-grid">
                {visibleProducts.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>

              {filteredProducts.length > visibleProducts.length && (
                <div className="catalog-load-more">
                  <button type="button" onClick={handleLoadMore} className="btn btn-secondary">
                    Carregar mais produtos
                  </button>
                </div>
              )}
            </>
          )}

        </div>
      </section>
    </div>
  );
};

export default Catalog;
