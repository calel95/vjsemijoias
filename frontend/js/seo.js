// ============================================
// SEO PUBLICO - metadados, compartilhamento e dados estruturados
// ============================================

(function () {
    'use strict';

    const DEFAULT_ORIGIN = 'https://www.vjsemijoias.com';
    const SITE_NAME = 'VJ Semijoias';
    const DEFAULT_IMAGE = '/images/logo-medium.png';
    const DEFAULT_DESCRIPTION = 'VJ Semijoias: semijoias banhadas a ouro 18K com curadoria, garantia e atendimento próximo.';

    const FAQ_ITEMS = [
        {
            question: 'As peças têm garantia?',
            answer: 'Sim. As semijoias VJ possuem garantia de 2 anos para defeitos de fabricação, conforme as condições descritas na página de Garantia.',
        },
        {
            question: 'As semijoias são banhadas a ouro?',
            answer: 'Sim. Trabalhamos com peças banhadas a ouro 18K e curadoria voltada a acabamento, brilho e durabilidade.',
        },
        {
            question: 'Como calculo o frete?',
            answer: 'O frete pode ser consultado na página do produto e no carrinho. No carrinho, selecione uma opção de entrega antes de seguir para o checkout.',
        },
        {
            question: 'Posso trocar uma peça?',
            answer: 'Sim. Solicitações de troca podem ser feitas em até 30 dias corridos após o recebimento, desde que a peça esteja sem sinais de uso e dentro das condições da política de troca.',
        },
        {
            question: 'O pagamento é seguro?',
            answer: 'Sim. O pagamento é realizado em ambiente seguro do provedor integrado. A VJ Semijoias não solicita dados sensíveis de cartão por WhatsApp, telefone ou e-mail.',
        },
        {
            question: 'Consigo acompanhar meu pedido?',
            answer: 'Sim. Após a compra, você pode acompanhar o pedido pela página Acompanhar Pedido usando o número do pedido e as informações enviadas pela loja.',
        },
    ];

    const PAGES = {
        '/': {
            path: '/',
            title: 'VJ Semijoias - Semijoias Banhadas a Ouro 18K',
            description: 'Semijoias banhadas a ouro 18K com garantia, curadoria e atendimento próximo. Conheça brincos, colares, pulseiras, anéis e presentes especiais.',
            keywords: 'semijoias, semijoias ouro 18k, loja de semijoias, VJ Semijoias, brincos, colares, pulseiras, anéis',
        },
        '/catalogo': {
            path: '/catalogo',
            title: 'Catálogo de Semijoias - VJ Semijoias',
            description: 'Explore o catálogo da VJ Semijoias com peças banhadas a ouro 18K, opções de presente, cálculo de frete e compra segura.',
            keywords: 'catálogo de semijoias, comprar semijoias, semijoias banhadas a ouro 18k',
        },
        '/produto': {
            path: '/produto',
            title: 'Produto - VJ Semijoias',
            description: 'Veja detalhes, preço, parcelamento e frete de uma semijoia VJ banhada a ouro 18K.',
            robots: 'noindex,follow',
        },
        '/carrinho': {
            path: '/carrinho',
            title: 'Carrinho - VJ Semijoias',
            description: 'Revise seus produtos, calcule o frete e siga para a finalização da compra na VJ Semijoias.',
            robots: 'noindex,follow',
        },
        '/checkout': {
            path: '/checkout',
            title: 'Finalizar Compra - VJ Semijoias',
            description: 'Finalize sua compra com segurança na VJ Semijoias.',
            robots: 'noindex,nofollow',
        },
        '/login': {
            path: '/login',
            title: 'Entrar - VJ Semijoias',
            description: 'Acesse sua conta para acompanhar pedidos e comprar na VJ Semijoias.',
            robots: 'noindex,follow',
        },
        '/cadastro': {
            path: '/cadastro',
            title: 'Cadastro - VJ Semijoias',
            description: 'Crie sua conta na VJ Semijoias para comprar, receber novidades e acompanhar pedidos.',
            robots: 'noindex,follow',
        },
        '/pedido': {
            path: '/pedido',
            title: 'Acompanhar Pedido - VJ Semijoias',
            description: 'Consulte o status, frete, rastreio e histórico do seu pedido na VJ Semijoias.',
            robots: 'noindex,follow',
        },
        '/pdf-visualizar': {
            path: '/pdf-visualizar',
            title: 'Catálogo PDF - VJ Semijoias',
            description: 'Visualize o catálogo PDF da VJ Semijoias com a coleção de semijoias.',
        },
        '/politica-troca.html': {
            path: '/politica-troca.html',
            title: 'Política de Troca e Devolução - VJ Semijoias',
            description: 'Entenda as condições de troca, devolução e atendimento pós-compra da VJ Semijoias.',
            type: 'article',
        },
        '/politica-privacidade.html': {
            path: '/politica-privacidade.html',
            title: 'Política de Privacidade - VJ Semijoias',
            description: 'Saiba como a VJ Semijoias utiliza dados de cadastro, compra, entrega e atendimento.',
            type: 'article',
        },
        '/termos-uso.html': {
            path: '/termos-uso.html',
            title: 'Termos de Uso - VJ Semijoias',
            description: 'Condições de navegação, cadastro, compra e acompanhamento de pedidos na VJ Semijoias.',
            type: 'article',
        },
        '/garantia.html': {
            path: '/garantia.html',
            title: 'Garantia de 2 Anos - VJ Semijoias',
            description: 'Conheça a garantia de 2 anos da VJ Semijoias e os cuidados para preservar suas peças.',
            type: 'article',
        },
        '/faq.html': {
            path: '/faq.html',
            title: 'FAQ - Perguntas Frequentes - VJ Semijoias',
            description: 'Dúvidas frequentes sobre garantia, banho ouro 18K, troca, frete, pagamento e cuidados com semijoias.',
            type: 'article',
            schema: 'faq',
        },
    };

    const HTML_ROUTE_ALIASES = {
        '/index.html': '/',
        '/catalogo.html': '/catalogo',
        '/produto.html': '/produto',
        '/carrinho.html': '/carrinho',
        '/checkout.html': '/checkout',
        '/login.html': '/login',
        '/cadastro.html': '/cadastro',
        '/pedido.html': '/pedido',
        '/pdf-visualizar.html': '/pdf-visualizar',
    };

    function origin() {
        if (window.location.origin && window.location.origin !== 'null') {
            return window.location.origin;
        }
        return DEFAULT_ORIGIN;
    }

    function absoluteUrl(value) {
        if (!value) return `${origin()}${DEFAULT_IMAGE}`;
        try {
            return new URL(value, origin()).href;
        } catch (_) {
            return `${origin()}${DEFAULT_IMAGE}`;
        }
    }

    function canonicalFor(path, search = '') {
        return `${origin()}${path}${search}`;
    }

    function currentRoute() {
        const path = window.location.pathname || '/';
        return HTML_ROUTE_ALIASES[path] || path.replace(/\/$/, '') || '/';
    }

    function text(value, fallback = '') {
        return String(value || fallback || '').replace(/\s+/g, ' ').trim();
    }

    function shortText(value, fallback, maxLength = 155) {
        const normalized = text(value, fallback);
        if (normalized.length <= maxLength) return normalized;
        return `${normalized.slice(0, maxLength - 1).trim()}…`;
    }

    function upsertMeta(selector, attributes) {
        let element = document.head.querySelector(selector);
        if (!element) {
            element = document.createElement('meta');
            document.head.appendChild(element);
        }
        Object.entries(attributes).forEach(([key, value]) => {
            element.setAttribute(key, value);
        });
        return element;
    }

    function setMetaName(name, content) {
        upsertMeta(`meta[name="${name}"]`, { name, content });
    }

    function setMetaProperty(property, content) {
        upsertMeta(`meta[property="${property}"]`, { property, content });
    }

    function setCanonical(url) {
        let link = document.head.querySelector('link[rel="canonical"]');
        if (!link) {
            link = document.createElement('link');
            link.rel = 'canonical';
            document.head.appendChild(link);
        }
        link.href = url;
    }

    function setJsonLd(id, data) {
        let script = document.getElementById(id);
        if (!data) {
            if (script) script.remove();
            return;
        }
        if (!script) {
            script = document.createElement('script');
            script.id = id;
            script.type = 'application/ld+json';
            document.head.appendChild(script);
        }
        script.textContent = JSON.stringify(data);
    }

    function organizationSchema() {
        return {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            name: SITE_NAME,
            url: origin(),
            logo: absoluteUrl('/images/logo.png'),
        };
    }

    function websiteSchema() {
        return {
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            name: SITE_NAME,
            url: origin(),
            potentialAction: {
                '@type': 'SearchAction',
                target: `${canonicalFor('/catalogo')}?q={search_term_string}`,
                'query-input': 'required name=search_term_string',
            },
        };
    }

    function faqSchema() {
        return {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: FAQ_ITEMS.map(item => ({
                '@type': 'Question',
                name: item.question,
                acceptedAnswer: {
                    '@type': 'Answer',
                    text: item.answer,
                },
            })),
        };
    }

    function availability(product) {
        if (product?.stock_status === 'out_of_stock') return 'https://schema.org/OutOfStock';
        if (product?.stock_status === 'preorder') return 'https://schema.org/PreOrder';
        return 'https://schema.org/InStock';
    }

    function productSchema(product, canonical) {
        const images = Array.isArray(product.images) && product.images.length
            ? product.images
            : (product.image ? [product.image] : [DEFAULT_IMAGE]);
        const category = product.categoryName || product.category || 'Semijoias';
        const schema = {
            '@context': 'https://schema.org',
            '@type': 'Product',
            name: text(product.name, 'Semijoia VJ'),
            description: shortText(product.description, DEFAULT_DESCRIPTION, 500),
            image: images.map(absoluteUrl),
            brand: {
                '@type': 'Brand',
                name: SITE_NAME,
            },
            category,
            url: canonical,
            offers: {
                '@type': 'Offer',
                url: canonical,
                priceCurrency: 'BRL',
                price: Number(product.price || 0).toFixed(2),
                availability: availability(product),
                itemCondition: 'https://schema.org/NewCondition',
            },
        };
        if (product.sku || product.reference) schema.sku = String(product.sku || product.reference);
        return schema;
    }

    function applyBaseSchemas(page) {
        setJsonLd('vj-schema-organization', organizationSchema());
        setJsonLd('vj-schema-website', websiteSchema());
        setJsonLd('vj-schema-faq', page.schema === 'faq' ? faqSchema() : null);
        setJsonLd('vj-schema-product', null);
    }

    function applySEO(config) {
        const title = text(config.title, SITE_NAME);
        const description = shortText(config.description, DEFAULT_DESCRIPTION);
        const canonical = config.canonical || canonicalFor(config.path || currentRoute());
        const image = absoluteUrl(config.image || DEFAULT_IMAGE);
        const type = config.type || 'website';

        document.title = title;
        setMetaName('description', description);
        setMetaName('robots', config.robots || 'index,follow');
        if (config.keywords) setMetaName('keywords', config.keywords);
        setCanonical(canonical);

        setMetaProperty('og:locale', 'pt_BR');
        setMetaProperty('og:site_name', SITE_NAME);
        setMetaProperty('og:type', type);
        setMetaProperty('og:title', title);
        setMetaProperty('og:description', description);
        setMetaProperty('og:image', image);
        setMetaProperty('og:url', canonical);

        setMetaName('twitter:card', 'summary_large_image');
        setMetaName('twitter:title', title);
        setMetaName('twitter:description', description);
        setMetaName('twitter:image', image);

        return { title, description, canonical, image };
    }

    function applyPageSEO(route = currentRoute()) {
        const page = { ...(PAGES[route] || PAGES['/']) };
        const productId = route === '/produto' ? productIdFromLocation() : null;
        if (productId) {
            page.robots = 'index,follow';
            page.canonical = canonicalFor('/produto', `?id=${encodeURIComponent(productId)}`);
        }
        const result = applySEO(page);
        applyBaseSchemas(page);
        return result;
    }

    function applyProductSEO(product) {
        if (!product) return applyPageSEO('/produto');
        const productId = product.id ? `?id=${encodeURIComponent(product.id)}` : window.location.search;
        const canonical = canonicalFor('/produto', productId || '');
        const image = Array.isArray(product.images) && product.images.length
            ? product.images[0]
            : product.image;
        const title = `${text(product.name, 'Produto')} - VJ Semijoias`;
        const description = shortText(
            product.description,
            `${text(product.name, 'Semijoia VJ')} banhada a ouro 18K com garantia, compra segura e atendimento VJ.`
        );
        const seo = applySEO({
            path: '/produto',
            title,
            description,
            canonical,
            image,
            type: 'product',
            robots: product.stock_status === 'out_of_stock' ? 'index,follow' : 'index,follow',
            keywords: `${text(product.name)}, semijoia, ouro 18K, VJ Semijoias`,
        });
        setJsonLd('vj-schema-organization', organizationSchema());
        setJsonLd('vj-schema-website', websiteSchema());
        setJsonLd('vj-schema-faq', null);
        setJsonLd('vj-schema-product', productSchema(product, seo.canonical));
        return seo;
    }
    function normalizeProductsPayload(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.items)) return payload.items;
        return [];
    }

    function productIdFromLocation() {
        const id = new URLSearchParams(window.location.search || '').get('id');
        return id ? parseInt(id, 10) : null;
    }

    async function applyProductSEOFromAPI() {
        if (currentRoute() !== '/produto') return null;
        const productId = productIdFromLocation();
        if (!productId || !window.fetch) return null;

        try {
            const response = await fetch('/api/products', { credentials: 'same-origin' });
            if (!response.ok) return null;
            const products = normalizeProductsPayload(await response.json());
            const product = products.find(item => Number(item.id) === productId);
            if (!product) return null;
            return applyProductSEO(product);
        } catch (_) {
            return null;
        }
    }

    window.VJSEO = {
        applyPageSEO,
        applyProductSEO,
        applyProductSEOFromAPI,
        setJsonLd,
        absoluteUrl,
    };

    applyPageSEO();
    if (currentRoute() === '/produto') {
        applyProductSEOFromAPI();
    }
})();