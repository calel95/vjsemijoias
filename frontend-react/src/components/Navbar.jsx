import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { ShoppingBag, User, Settings, LogOut, Menu, X } from 'lucide-react';

const Navbar = () => {
  const { cartCount, isLoggedIn, user, logoutUser, isAdmin, logoutAdmin } = useStore();
  const [menuActive, setMenuActive] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const toggleMobileMenu = () => {
    setMenuActive(!menuActive);
  };

  const closeMenu = () => {
    setMenuActive(false);
  };

  const handleLogout = async () => {
    if (isAdmin) {
      await logoutAdmin();
      navigate('/admin');
    } else {
      await logoutUser();
      navigate('/');
    }
    closeMenu();
  };

  const getFirstName = (fullName) => {
    if (!fullName) return '';
    return fullName.split(' ')[0];
  };

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="logo" onClick={closeMenu}>
          <img src="/images/logo.png" alt="VJ Semijoias" className="logo-img" />
          <div className="logo-text">
            <span className="logo-vj">VJ</span>
            <span className="logo-tagline">SEMIJOIAS</span>
          </div>
        </Link>

        {/* Menu Items */}
        <ul className={`nav-menu ${menuActive ? 'active' : ''}`}>
          <li>
            <Link
              to="/"
              className={location.pathname === '/' ? 'active' : ''}
              onClick={closeMenu}
            >
              Início
            </Link>
          </li>
          <li>
            <Link
              to="/catalogo"
              className={location.pathname === '/catalogo' ? 'active' : ''}
              onClick={closeMenu}
            >
              Coleções
            </Link>
          </li>
          {isAdmin && (
            <li>
              <Link
                to="/admin"
                className={location.pathname === '/admin' ? 'active' : ''}
                onClick={closeMenu}
                style={{ color: 'var(--gold-dark)', fontWeight: '700' }}
              >
                Painel Admin
              </Link>
            </li>
          )}
        </ul>

        {/* Nav Actions */}
        <div className="nav-actions">
          {/* Cart Icon */}
          <Link to="/carrinho" className="nav-icon" title="Sacola de Compras" onClick={closeMenu}>
            <ShoppingBag size={18} strokeWidth={1.8} />
            {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
          </Link>

          {/* User Profile / Admin Link */}
          {isAdmin ? (
            <div className="nav-actions" style={{ gap: '0.4rem' }}>
              <Link to="/admin" className="nav-icon" title="Administração" onClick={closeMenu}>
                <Settings size={18} strokeWidth={1.8} />
              </Link>
              <button onClick={handleLogout} className="nav-icon" title="Sair da Admin">
                <LogOut size={18} strokeWidth={1.8} style={{ color: 'var(--error)' }} />
              </button>
            </div>
          ) : isLoggedIn ? (
            <div className="nav-actions" style={{ gap: '0.4rem' }}>
              <span className="nav-icon" style={{ fontSize: '0.78rem', width: 'auto', padding: '0 0.8rem', borderRadius: '30px', fontWeight: 600 }}>
                Olá, {getFirstName(user?.name)}
              </span>
              <button onClick={handleLogout} className="nav-icon" title="Sair da Conta">
                <LogOut size={18} strokeWidth={1.8} />
              </button>
            </div>
          ) : (
            <Link to="/login" className="nav-icon" title="Minha Conta" onClick={closeMenu}>
              <User size={18} strokeWidth={1.8} />
            </Link>
          )}

          {/* Mobile Menu Toggle */}
          <button className="hamburger" onClick={toggleMobileMenu} aria-label="Menu">
            {menuActive ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
