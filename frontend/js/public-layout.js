// ============================================
// PUBLIC LAYOUT - componentes reutilizados da loja publica
// ============================================

const PUBLIC_INSTITUTIONAL_LINKS = [
    { href: '/#sobre', label: 'Sobre Nós' },
    { href: '/politica-troca.html', label: 'Política de Troca e Devolução' },
    { href: '/politica-privacidade.html', label: 'Política de Privacidade' },
    { href: '/termos-uso.html', label: 'Termos de Uso' },
    { href: '/garantia.html', label: 'Garantia' },
    { href: '/faq.html', label: 'FAQ' },
];

const PUBLIC_CATEGORY_LINKS = [
    { href: '/catalogo?cat=brincos', label: 'Brincos' },
    { href: '/catalogo?cat=colares', label: 'Colares' },
    { href: '/catalogo?cat=pulseiras', label: 'Pulseiras' },
    { href: '/catalogo?cat=aneis', label: 'Anéis' },
    { href: '/catalogo?cat=pingentes', label: 'Pingentes' },
    { href: '/catalogo?cat=chaveiros', label: 'Chaveiros' },
];

function renderPublicFooter() {
    document.querySelectorAll('[data-public-footer]').forEach(footer => {
        footer.innerHTML = `
            <div class="footer-container">
                <div class="footer-col">
                    <img src="images/logo-medium.png" alt="VJ Semijoias" class="footer-logo" width="90" height="90" data-store-logo="small">
                    <p data-store-description>Semijoias finas banhadas a ouro 18k, com curadoria, garantia e atendimento próximo em cada compra.</p>
                    <div class="social-links">
                        <a data-store-instagram-link aria-label="Instagram VJ Semijoias">Instagram</a>
                        <a data-store-whatsapp-link aria-label="WhatsApp VJ Semijoias">WhatsApp</a>
                    </div>
                </div>
                <div class="footer-col">
                    <h3>Categorias</h3>
                    <ul>
                        ${PUBLIC_CATEGORY_LINKS.map(link => `<li><a href="${link.href}">${link.label}</a></li>`).join('')}
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>Institucional</h3>
                    <ul>
                        ${PUBLIC_INSTITUTIONAL_LINKS.map(link => `<li><a href="${link.href}">${link.label}</a></li>`).join('')}
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>Atendimento</h3>
                    <ul>
                        <li data-store-email>e-mail: [E-MAIL DA LOJA]</li>
                        <li data-store-phone>telefone: [TELEFONE DA LOJA]</li>
                        <li data-store-whatsapp>WhatsApp: [TELEFONE DA LOJA]</li>
                        <li data-store-location>[ENDEREÇO DA LOJA]</li>
                        <li data-store-hours>Segunda a sexta, 9h às 18h</li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <p data-store-copyright>&copy; 2026 VJ Semijoias. Todos os direitos reservados.</p>
            </div>
        `;
    });
}

renderPublicFooter();