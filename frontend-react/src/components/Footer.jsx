import React from 'react';
import { Link } from 'react-router-dom';
import { Instagram, Phone, Mail, MapPin } from 'lucide-react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-col">
          <img src="/images/logo.png" alt="VJ Semijoias" className="footer-logo" />
          <p>
            Semijoias banhadas a Ouro 18k com tecnologia hipoalergênica e design editorial premium. A beleza e sofisticação que você merece.
          </p>
          <div className="social-links">
            <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" title="Instagram">
              <Instagram size={18} />
            </a>
          </div>
        </div>

        <div className="footer-col">
          <h3>Coleções</h3>
          <ul>
            <li><Link to="/catalogo?category=Brincos">Brincos</Link></li>
            <li><Link to="/catalogo?category=Colares">Colares</Link></li>
            <li><Link to="/catalogo?category=Pulseiras">Pulseiras</Link></li>
            <li><Link to="/catalogo?category=Aneis">Anéis</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h3>Institucional</h3>
          <ul>
            <li><Link to="/">Início</Link></li>
            <li><Link to="/catalogo">Todos os Produtos</Link></li>
            <li><Link to="/login">Minha Conta</Link></li>
            <li><Link to="/admin">Administração</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h3>Contato</h3>
          <ul style={{ display: 'grid', gap: '0.8rem' }}>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.92rem' }}>
              <Phone size={16} className="text-gold" />
              <span>(11) 99999-9999</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.92rem' }}>
              <Mail size={16} className="text-gold" />
              <span>contato@vjsemijoias.com.br</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.92rem' }}>
              <MapPin size={16} className="text-gold" />
              <span>São Paulo - SP</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p>&copy; {currentYear} VJ Semijoias. Todos os direitos reservados. CNPJ: 00.000.000/0001-00</p>
      </div>
    </footer>
  );
};

export default Footer;
