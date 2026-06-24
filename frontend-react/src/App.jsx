import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { StoreProvider } from './context/StoreContext';

// Components
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Toast from './components/Toast';

// Pages
import Home from './pages/Home';
import Catalog from './pages/Catalog';
import ProductDetail from './pages/ProductDetail';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Login from './pages/Login';
import Admin from './pages/Admin';

// CSS Styling Entrypoint
import './index.css';

function App() {
  return (
    <StoreProvider>
      <Router>
        <div id="root">
          {/* Main Navigation bar */}
          <Navbar />
          
          {/* Floating Toast Notification alerts */}
          <Toast />
          
          {/* Page Routing */}
          <main style={{ flex: 1 }}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/catalogo" element={<Catalog />} />
              <Route path="/produto/:id" element={<ProductDetail />} />
              <Route path="/carrinho" element={<Cart />} />
              <Route path="/checkout" element={<Checkout />} />
              <Route path="/login" element={<Login />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </main>

          {/* Luxury bottom info links footer */}
          <Footer />
        </div>
      </Router>
    </StoreProvider>
  );
}

export default App;
