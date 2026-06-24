import React from 'react';
import { useStore } from '../context/StoreContext';

const Toast = () => {
  const { toasts } = useStore();

  if (toasts.length === 0) return null;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast ${toast.type} ${toast.removing ? 'removing' : ''}`}
        >
          <div className="toast-icon">{icons[toast.type]}</div>
          <div className="toast-content">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Toast;
