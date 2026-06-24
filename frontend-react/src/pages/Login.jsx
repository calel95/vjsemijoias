import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { Lock, Mail, User, ShieldAlert, BadgeInfo } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const { loginUser, registerUser, loginAdmin, showToast } = useStore();

  const [isRegister, setIsRegister] = useState(false);
  const [isAdminMode, setIsAdminMode] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    cpf: '',
    phone: '',
    birthdate: ''
  });

  const [loading, setLoading] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isAdminMode) {
        // Admin Login Flow
        const res = await loginAdmin(formData.email, formData.password);
        if (res.success) {
          navigate('/admin');
        } else {
          showToast(res.error || 'Credenciais administrativas inválidas.', 'error');
        }
      } else if (isRegister) {
        // Client Register Flow
        const cleanPayload = {
          ...formData,
          cpf: formData.cpf.replace(/\D/g, ''),
          phone: formData.phone.replace(/\D/g, '')
        };
        const res = await registerUser(cleanPayload);
        if (res.success) {
          navigate('/');
        } else {
          showToast(res.error || 'Erro ao realizar cadastro.', 'error');
        }
      } else {
        // Client Login Flow
        const res = await loginUser(formData.email, formData.password);
        if (res.success) {
          navigate('/');
        } else {
          showToast(res.error || 'E-mail ou senha incorretos.', 'error');
        }
      }
    } catch (err) {
      console.error(err);
      showToast('Ocorreu um erro na requisição.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegister(!isRegister);
    setIsAdminMode(false);
  };

  const toggleAdminMode = () => {
    setIsAdminMode(!isAdminMode);
    setIsRegister(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <img src="/images/logo.png" alt="VJ Semijoias Logo" className="auth-logo-img" />
          <span className="auth-logo-text">VJ</span>
          <span className="auth-logo-tagline">SEMIJOIAS</span>
        </div>

        <h2>
          {isAdminMode 
            ? 'Acesso Admin' 
            : (isRegister ? 'Criar Conta' : 'Acesse sua Conta')
          }
        </h2>
        <p>
          {isAdminMode
            ? 'Painel Administrativo da Loja'
            : (isRegister 
                ? 'Preencha seus dados para receber novidades' 
                : 'Acesse seus pedidos e agilize suas compras'
              )
          }
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegister && (
            <div className="form-group">
              <label>Nome Completo</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Seu nome completo"
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label>{isAdminMode ? 'E-mail ou Usuário Admin' : 'E-mail'}</label>
            <input
              type="text"
              name="email"
              required
              value={formData.email}
              onChange={handleInputChange}
              placeholder={isAdminMode ? 'admin' : 'seu-email@exemplo.com'}
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label>Senha</label>
            <input
              type="password"
              name="password"
              required
              value={formData.password}
              onChange={handleInputChange}
              placeholder="Digite sua senha"
              autoComplete="current-password"
            />
          </div>

          {isRegister && (
            <>
              <div className="form-row">
                <div className="form-group">
                  <label>CPF</label>
                  <input
                    type="text"
                    name="cpf"
                    required
                    value={formData.cpf}
                    onChange={handleCpfChange}
                    placeholder="000.000.000-00"
                  />
                </div>
                <div className="form-group">
                  <label>WhatsApp / Telefone</label>
                  <input
                    type="text"
                    name="phone"
                    required
                    value={formData.phone}
                    onChange={handlePhoneChange}
                    placeholder="(00) 99999-9999"
                  />
                </div>
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
            </>
          )}

          {isAdminMode && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'var(--cream)', padding: '0.6rem 0.8rem', borderRadius: '8px', fontSize: '0.8rem', color: 'var(--gold-dark)', marginBottom: '1.2rem', fontWeight: 600 }}>
              <BadgeInfo size={16} />
              <span>Dica: Use a senha mestre configurada em seu arquivo .env</span>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary btn-block"
            style={{ marginTop: '0.8rem' }}
            disabled={loading}
          >
            {loading 
              ? 'Processando...' 
              : (isAdminMode ? 'Acessar Painel' : (isRegister ? 'Cadastrar' : 'Entrar'))
            }
          </button>
        </form>

        <div className="auth-divider">
          <span>OU</span>
        </div>

        <div className="auth-footer">
          {isAdminMode ? (
            <button onClick={toggleAdminMode} style={{ color: 'var(--gold-dark)', fontWeight: '700', fontSize: '0.9rem' }}>
              Voltar ao Acesso do Cliente
            </button>
          ) : (
            <>
              <p>
                {isRegister ? 'Já possui conta?' : 'Ainda não tem conta?'}
                <button onClick={toggleMode} style={{ color: 'var(--gold-dark)', fontWeight: '700', marginLeft: '0.3rem', fontSize: '0.9rem' }}>
                  {isRegister ? 'Faça Login' : 'Cadastre-se'}
                </button>
              </p>
              
              <button onClick={toggleAdminMode} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--gray)', fontSize: '0.8rem', margin: '1.2rem auto 0', opacity: 0.85 }}>
                <ShieldAlert size={14} /> Acesso de Administrador
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
