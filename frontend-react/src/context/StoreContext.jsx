import React, { createContext, useContext, useState, useEffect } from 'react';
import { API } from '../services/api';

const StoreContext = createContext();

export const useStore = () => useContext(StoreContext);

const CART_KEY = 'vj_cart';
const USER_KEY = 'vj_user';
const COUPON_KEY = 'vj_coupon';
const COUPON_PERCENT_KEY = 'vj_coupon_percent';

export const StoreProvider = ({ children }) => {
  // --- STATE ---
  const [cartItems, setCartItems] = useState([]);
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  
  // Pricing & Coupon state
  const [shipping, setShipping] = useState(0);
  const [shippingMessage, setShippingMessage] = useState('Frete calculado no checkout');
  const [shippingService, setShippingService] = useState('');
  const [shippingEstimatedDays, setShippingEstimatedDays] = useState('');
  const [shippingOption, setShippingOption] = useState(null);
  
  const [couponCode, setCouponCode] = useState('');
  const [discountPercent, setDiscountPercent] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  
  // Store Global Config
  const [storeConfig, setStoreConfig] = useState({
    preorder_days: 10,
    shipping_free_minimum: 150.0,
    shipping_flat_rate: 15.0,
    infinitepay_enabled: false,
    credit_card_enabled: true,
    pix_enabled: true,
  });

  // Toast state
  const [toasts, setToasts] = useState([]);

  // --- TOAST FUNCTION ---
  const showToast = (message, type = 'success', title = '') => {
    const id = Date.now() + Math.random().toString(36).substr(2, 9);
    const titles = {
      success: title || 'Sucesso!',
      error: title || 'Erro',
      info: title || 'Informação'
    };
    
    const newToast = { id, message, type, title: titles[type] };
    setToasts((prev) => [...prev, newToast]);

    setTimeout(() => {
      setToasts((prev) => prev.map(t => t.id === id ? { ...t, removing: true } : t));
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 300);
    }, 3500);
  };

  // --- INITIAL LOAD ---
  useEffect(() => {
    // 1. Stored Cart
    const storedCart = localStorage.getItem(CART_KEY);
    if (storedCart) {
      try {
        setCartItems(JSON.parse(storedCart));
      } catch (e) {
        console.error('Erro ao carregar o carrinho', e);
      }
    }

    // 2. Coupon from localStorage
    const savedCoupon = localStorage.getItem(COUPON_KEY);
    const savedPercent = localStorage.getItem(COUPON_PERCENT_KEY);
    if (savedCoupon) {
      setCouponCode(savedCoupon);
      setDiscountPercent(parseFloat(savedPercent || '0'));
    }

    // 3. Admin Authentication check
    const adminAuthenticated = API.hasAdminToken();
    setIsAdmin(adminAuthenticated);

    // 4. User Profile check
    const storedUser = localStorage.getItem(USER_KEY);
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        setIsLoggedIn(true);
      } catch (e) {}
    }

    API.getMe().then((result) => {
      if (result.success) {
        if (result.data?.is_admin && adminAuthenticated) {
          // If admin is active, do not login as regular client
          setUser(null);
          setIsLoggedIn(false);
          localStorage.removeItem(USER_KEY);
          return;
        }
        setUser(result.data);
        setIsLoggedIn(true);
        localStorage.setItem(USER_KEY, JSON.stringify(result.data));
      } else {
        setUser(null);
        setIsLoggedIn(false);
        localStorage.removeItem(USER_KEY);
      }
    }).catch(() => {
      if (storedUser) {
        setIsLoggedIn(true);
      }
    });

    // 5. Store Config load
    API.getStoreConfig().then((result) => {
      if (result.success && result.data) {
        setStoreConfig(result.data);
      }
    });
  }, []);

  // Sync Cart to LocalStorage
  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cartItems));
  }, [cartItems]);

  // Recalculate discount whenever subtotal or discountPercent changes
  const cartSubtotal = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  useEffect(() => {
    if (discountPercent > 0) {
      setDiscountAmount(cartSubtotal * (discountPercent / 100));
    } else {
      setDiscountAmount(0);
    }
  }, [cartSubtotal, discountPercent]);

  // --- CART OPERATIONS ---
  const addToCart = (product, quantity = 1) => {
    if (!product) return false;
    setCartItems((prev) => {
      const existing = prev.find((item) => item.id === product.id);
      let updated;
      if (existing) {
        updated = prev.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + quantity } : item
        );
      } else {
        const image = product.image || (product.images && product.images[0]) || '';
        updated = [
          ...prev,
          {
            id: product.id,
            name: product.name,
            price: product.price,
            icon: product.icon || '',
            image: image,
            quantity: quantity,
            stock_status: product.stock_status,
          },
        ];
      }
      return updated;
    });
    showToast(`${product.name} adicionado ao carrinho!`, 'success');
    return true;
  };

  const removeFromCart = (productId) => {
    setCartItems((prev) => prev.filter((item) => item.id !== productId));
    showToast('Item removido do carrinho.', 'info');
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    setCartItems((prev) =>
      prev.map((item) => (item.id === productId ? { ...item, quantity } : item))
    );
  };

  const clearCart = () => {
    setCartItems([]);
    setShipping(0);
    setShippingOption(null);
    setShippingMessage('Frete calculado no checkout');
    removeCoupon();
  };

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const cartTotal = Math.max(0, cartSubtotal + shipping - discountAmount);

  // --- SHIPPING ---
  const calculateShipping = async (zipCode) => {
    if (!zipCode) {
      setShipping(0);
      setShippingMessage('Frete calculado no checkout');
      setShippingOption(null);
      return { success: false, error: 'CEP não informado' };
    }
    
    const result = await API.calculateShipping(cartSubtotal, zipCode, cartItems);
    if (result.success) {
      const option = result.data.selected_option || result.data.options?.[0] || null;
      setShippingOption(option);
      const cost = Number((option?.shipping ?? result.data.shipping) || 0);
      setShipping(cost);
      setShippingMessage(option?.message || result.data.message || '');
      setShippingService(option?.service || result.data.service || '');
      setShippingEstimatedDays(option?.estimated_days || result.data.estimated_days || '');
      return { success: true, data: result.data };
    } else {
      setShipping(0);
      setShippingMessage('Erro ao calcular frete. Utilizando taxa fixa.');
      setShippingOption(null);
      return { success: false, error: result.error || 'Erro de conexão' };
    }
  };

  // --- COUPON ---
  const applyCoupon = async (code) => {
    const cleanCode = (code || '').trim().toUpperCase();
    if (!cleanCode) return { success: false, error: 'Insira o código do cupom' };

    const result = await API.validateCoupon(cleanCode, { total: cartSubtotal });
    if (result.success && result.data.valid) {
      const percent = Number(result.data.discount_percent || 0);
      const discount = Number(result.data.discount || 0);
      
      setCouponCode(result.data.code);
      setDiscountPercent(percent);
      
      localStorage.setItem(COUPON_KEY, result.data.code);
      localStorage.setItem(COUPON_PERCENT_KEY, String(percent));
      
      showToast(`Cupom ${result.data.code} aplicado com sucesso!`, 'success');
      return { success: true, percent, discount };
    } else {
      removeCoupon();
      const err = result.error || (result.data && !result.data.valid ? result.data.message : 'Cupom inválido');
      showToast(err, 'error');
      return { success: false, error: err };
    }
  };

  const removeCoupon = () => {
    setCouponCode('');
    setDiscountPercent(0);
    localStorage.removeItem(COUPON_KEY);
    localStorage.removeItem(COUPON_PERCENT_KEY);
  };

  // --- CLIENT AUTH ---
  const loginUser = async (email, password) => {
    const result = await API.login(email, password);
    if (result.success) {
      setUser(result.data.user);
      setIsLoggedIn(true);
      localStorage.setItem(USER_KEY, JSON.stringify(result.data.user));
      showToast('Login realizado com sucesso!', 'success');
    }
    return result;
  };

  const registerUser = async (userData) => {
    const result = await API.register(userData);
    if (result.success) {
      setUser(result.data.user);
      setIsLoggedIn(true);
      localStorage.setItem(USER_KEY, JSON.stringify(result.data.user));
      showToast('Cadastro realizado com sucesso!', 'success');
    }
    return result;
  };

  const logoutUser = async () => {
    await API.logout();
    setUser(null);
    setIsLoggedIn(false);
    localStorage.removeItem(USER_KEY);
    showToast('Logout realizado.', 'info');
  };

  // --- ADMIN AUTH ---
  const loginAdmin = async (email, password) => {
    const result = await API.adminLogin(email, password);
    if (result.success) {
      setIsAdmin(true);
      setUser(null); // Clear client session
      setIsLoggedIn(false);
      localStorage.removeItem(USER_KEY);
      showToast('Painel Administrativo logado!', 'success');
    }
    return result;
  };

  const logoutAdmin = async () => {
    await API.logout();
    setIsAdmin(false);
    showToast('Sessão administrativa encerrada.', 'info');
  };

  // --- UTILS ---
  const formatPrice = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  return (
    <StoreContext.Provider
      value={{
        cartItems,
        cartCount,
        cartSubtotal,
        cartTotal,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        
        shipping,
        shippingMessage,
        shippingService,
        shippingEstimatedDays,
        shippingOption,
        calculateShipping,
        
        couponCode,
        discountPercent,
        discountAmount,
        applyCoupon,
        removeCoupon,
        
        storeConfig,
        setStoreConfig,
        
        user,
        isLoggedIn,
        loginUser,
        registerUser,
        logoutUser,
        
        isAdmin,
        loginAdmin,
        logoutAdmin,
        
        toasts,
        showToast,
        formatPrice,
      }}
    >
      {children}
    </StoreContext.Provider>
  );
};
