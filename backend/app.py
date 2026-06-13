# ============================================
# VJ SEMIJOIAS - Backend Flask API
# ============================================

import json
import os
import secrets
import shutil
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
from pathlib import Path, PurePosixPath

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity,
    get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

try:
    from backend.infinitepay_client import (
        InfinitePayClient,
        InfinitePayError,
        checkout_token,
    )
except ModuleNotFoundError:
    from infinitepay_client import (
        InfinitePayClient,
        InfinitePayError,
        checkout_token,
    )

load_dotenv(Path(__file__).with_name('.env'))
load_dotenv()

app = Flask(__name__, static_folder='../', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vj-semijoias-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///vjsemijoias.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', '')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['INFINITEPAY_HANDLE'] = os.getenv('INFINITEPAY_HANDLE', '').strip().lstrip('$')
app.config['INFINITEPAY_API_BASE'] = os.getenv(
    'INFINITEPAY_API_BASE',
    'https://api.checkout.infinitepay.io',
)
app.config['PUBLIC_BASE_URL'] = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')

# CORS para permitir requisições do frontend
CORS(app, resources={r"/api/*": {"origins": "*"}})

db = SQLAlchemy(app)
jwt = JWTManager(app)


def utc_now():
    return datetime.now(UTC)


# ============================================
# MODELOS DO BANCO DE DADOS
# ============================================

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    categoryName = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    oldPrice = db.Column(db.Float, nullable=True)
    image = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(10), nullable=True)
    badge = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=False)
    features = db.Column(db.Text, nullable=True)  # JSON string
    custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    gallery_images = db.relationship(
        'ProductImage',
        backref='product',
        cascade='all, delete-orphan',
        order_by='ProductImage.position',
    )

    def to_dict(self):
        features_list = []
        if self.features:
            try:
                features_list = __import__('json').loads(self.features)
            except:
                features_list = self.features.split('\n') if self.features else []
        
        images = [item.path for item in self.gallery_images]
        if not images and self.image:
            images = [self.image]

        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'categoryName': self.categoryName,
            'price': self.price,
            'oldPrice': self.oldPrice,
            'image': self.image,
            'images': images,
            'icon': self.icon or '💎',
            'badge': self.badge,
            'description': self.description,
            'features': features_list,
            'custom': self.custom
        }


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    path = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)


class ProductImport(db.Model):
    __tablename__ = 'product_imports'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id'),
        unique=True,
        nullable=False,
    )
    source_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    source_page = db.Column(db.Integer, nullable=True)
    source_folder = db.Column(db.String(255), nullable=True)
    imported_at = db.Column(db.DateTime(timezone=True), default=utc_now)
    product = db.relationship('Product', backref=db.backref('import_record', uselist=False))


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    birthdate = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'cpf': self.cpf,
            'phone': self.phone,
            'birthdate': self.birthdate,
            'is_admin': self.is_admin
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(200), nullable=False)
    customer_cpf = db.Column(db.String(20), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=True)
    address_zip = db.Column(db.String(20), nullable=True)
    address_street = db.Column(db.String(200), nullable=True)
    address_number = db.Column(db.String(20), nullable=True)
    address_complement = db.Column(db.String(200), nullable=True)
    address_neighborhood = db.Column(db.String(100), nullable=True)
    address_city = db.Column(db.String(100), nullable=True)
    address_state = db.Column(db.String(10), nullable=True)
    items = db.Column(db.Text, nullable=False)  # JSON string
    subtotal = db.Column(db.Float, nullable=False)
    shipping = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default='pending')
    coupon = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_cpf': self.customer_cpf,
            'customer_phone': self.customer_phone,
            'address_zip': self.address_zip,
            'address_street': self.address_street,
            'address_number': self.address_number,
            'address_complement': self.address_complement,
            'address_neighborhood': self.address_neighborhood,
            'address_city': self.address_city,
            'address_state': self.address_state,
            'items': __import__('json').loads(self.items) if self.items else [],
            'subtotal': self.subtotal,
            'shipping': self.shipping,
            'discount': self.discount,
            'total': self.total,
            'payment_method': self.payment_method,
            'status': self.status,
            'coupon': self.coupon,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), unique=True, nullable=False)
    provider = db.Column(db.String(30), default='infinitepay', nullable=False)
    provider_order_id = db.Column(db.String(100), unique=True, nullable=True)
    provider_payment_id = db.Column(db.String(100), nullable=True)
    checkout_token = db.Column(db.String(100), unique=True, nullable=False)
    method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    status_detail = db.Column(db.String(100), nullable=True)
    pix_qr_code = db.Column(db.Text, nullable=True)
    pix_qr_code_base64 = db.Column(db.Text, nullable=True)
    pix_ticket_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    order = db.relationship('Order', backref=db.backref('payment', uselist=False))

    def to_dict(self, include_pix=True):
        data = {
            'order_id': self.order_id,
            'provider': self.provider,
            'provider_order_id': self.provider_order_id,
            'provider_payment_id': self.provider_payment_id,
            'method': self.method,
            'status': self.status,
            'status_detail': self.status_detail,
            'checkout_token': self.checkout_token,
        }
        if include_pix and self.method == 'pix':
            data.update({
                'pix_qr_code': self.pix_qr_code,
                'pix_qr_code_base64': self.pix_qr_code_base64,
                'pix_ticket_url': self.pix_ticket_url,
            })
        return data


class Newsletter(db.Model):
    __tablename__ = 'newsletters'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    coupon = db.Column(db.String(20), default='VJ10')
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)


class Coupon(db.Model):
    __tablename__ = 'coupons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_percent = db.Column(db.Float, default=10)
    is_active = db.Column(db.Boolean, default=True)
    usage_limit = db.Column(db.Integer, default=100)
    used_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)


# ============================================
# DECORATOR ADMIN
# ============================================

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get('is_admin'):
            return jsonify({'error': 'Acesso restrito a administradores'}), 403
        return fn(*args, **kwargs)
    return wrapper


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Valor monetário inválido')


def calculate_order(items, coupon_code='', zip_code=''):
    if not isinstance(items, list) or not items:
        raise ValueError('O pedido deve conter ao menos um produto')

    product_ids = []
    quantities = {}
    for item in items:
        try:
            product_id = int(item['id'])
            quantity = int(item.get('quantity', 1))
        except (KeyError, TypeError, ValueError):
            raise ValueError('Item do pedido inválido')
        if quantity < 1 or quantity > 20:
            raise ValueError('A quantidade deve estar entre 1 e 20')
        if product_id not in quantities:
            product_ids.append(product_id)
            quantities[product_id] = 0
        quantities[product_id] += quantity

    products = Product.query.filter(Product.id.in_(product_ids)).all()
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(product_ids):
        raise ValueError('Um ou mais produtos não estão disponíveis')

    normalized_items = []
    subtotal = Decimal('0.00')
    for product_id in product_ids:
        product = products_by_id[product_id]
        quantity = quantities[product_id]
        unit_price = money(product.price)
        line_total = unit_price * quantity
        subtotal += line_total
        normalized_items.append({
            'id': product.id,
            'name': product.name,
            'price': float(unit_price),
            'quantity': quantity,
            'image': product.image,
            'icon': product.icon,
        })

    shipping = Decimal('0.00') if subtotal >= Decimal('199.00') else Decimal('19.90')
    coupon_code = str(coupon_code or '').strip().upper()
    discount = Decimal('0.00')
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if not coupon or coupon.used_count >= coupon.usage_limit:
            raise ValueError('Cupom inválido, expirado ou esgotado')
        discount = (subtotal * money(coupon.discount_percent) / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    total = subtotal + shipping - discount
    return {
        'items': normalized_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'total': total,
        'coupon': coupon_code,
    }


def infinitepay():
    return InfinitePayClient(
        app.config['INFINITEPAY_HANDLE'],
        app.config['INFINITEPAY_API_BASE'],
    )


def validate_order_data(data):
    required = ['customer_name', 'customer_email', 'customer_cpf', 'items']
    for field in required:
        if not data.get(field):
            raise ValueError(f'Campo obrigatório: {field}')
    if '@' not in str(data['customer_email']):
        raise ValueError('E-mail inválido')
    return calculate_order(
        data['items'],
        coupon_code=data.get('coupon', ''),
        zip_code=data.get('address_zip', ''),
    )


def create_local_order(data, totals, payment_method):
    order_id = 'VJ' + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(2).upper()
    identity = get_jwt_identity()
    order = Order(
        id=order_id,
        user_id=int(identity) if identity else None,
        customer_name=data['customer_name'],
        customer_email=data['customer_email'],
        customer_cpf=data['customer_cpf'],
        customer_phone=data.get('customer_phone', ''),
        address_zip=data.get('address_zip', ''),
        address_street=data.get('address_street', ''),
        address_number=data.get('address_number', ''),
        address_complement=data.get('address_complement', ''),
        address_neighborhood=data.get('address_neighborhood', ''),
        address_city=data.get('address_city', ''),
        address_state=data.get('address_state', ''),
        items=json.dumps(totals['items'], ensure_ascii=False),
        subtotal=float(totals['subtotal']),
        shipping=float(totals['shipping']),
        discount=float(totals['discount']),
        total=float(totals['total']),
        payment_method=payment_method,
        status='pending',
        coupon=totals['coupon'],
    )
    db.session.add(order)
    return order


def public_url(path):
    base = app.config['PUBLIC_BASE_URL'] or request.host_url.rstrip('/')
    return f'{base}/{path.lstrip("/")}'


def cents(value):
    return int((money(value) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def update_infinitepay_payment(payment, provider_data):
    expected_amount = cents(payment.order.total)
    received_amount = int(provider_data.get('amount') or 0)
    if received_amount != expected_amount:
        raise ValueError('Valor confirmado pela InfinitePay não corresponde ao pedido')

    if not provider_data.get('success') or not provider_data.get('paid'):
        return False

    payment.provider = 'infinitepay'
    payment.provider_order_id = (
        provider_data.get('slug')
        or provider_data.get('invoice_slug')
        or payment.provider_order_id
    )
    payment.provider_payment_id = (
        provider_data.get('transaction_nsu')
        or payment.provider_payment_id
    )
    payment.method = provider_data.get('capture_method') or payment.method
    payment.status = 'paid'
    payment.status_detail = 'approved'
    payment.order.payment_method = payment.method
    payment.order.status = 'paid'
    return True


# ============================================
# ROTAS DE PRODUTOS
# ============================================

@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').lower()
    
    query = Product.query
    
    if category and category != 'all':
        query = query.filter_by(category=category)
    
    products = query.order_by(Product.id).all()
    
    if search:
        products = [p for p in products if search in p.name.lower() or search in p.description.lower()]
    
    return jsonify([p.to_dict() for p in products])


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@app.route('/api/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    
    if not data.get('name') or not data.get('category') or not data.get('price') or not data.get('description'):
        return jsonify({'error': 'Campos obrigatórios: name, category, price, description'}), 400
    
    features_json = __import__('json').dumps(data.get('features', []))
    
    product = Product(
        name=data['name'],
        category=data['category'],
        categoryName=data.get('categoryName', data['category'].capitalize()),
        price=float(data['price']),
        oldPrice=float(data['oldPrice']) if data.get('oldPrice') else None,
        image=data.get('image'),
        icon=data.get('icon', '💎'),
        badge=data.get('badge'),
        description=data['description'],
        features=features_json,
        custom=True
    )
    
    db.session.add(product)
    if product.image:
        product.gallery_images.append(ProductImage(path=product.image, position=0))
    db.session.commit()
    
    return jsonify(product.to_dict()), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    
    if data.get('name') is not None:
        product.name = data['name']
    if data.get('category') is not None:
        product.category = data['category']
    if data.get('categoryName') is not None:
        product.categoryName = data['categoryName']
    if data.get('price') is not None:
        product.price = float(data['price'])
    if 'oldPrice' in data:
        product.oldPrice = float(data['oldPrice']) if data['oldPrice'] else None
    if data.get('image') is not None:
        product.image = data['image']
        product.gallery_images.clear()
        if product.image:
            product.gallery_images.append(ProductImage(path=product.image, position=0))
    if data.get('icon') is not None:
        product.icon = data['icon']
    if data.get('badge') is not None:
        product.badge = data['badge']
    if data.get('description') is not None:
        product.description = data['description']
    if data.get('features') is not None:
        product.features = __import__('json').dumps(data['features'])
    
    db.session.commit()
    
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Produto removido com sucesso'}), 200


@app.route('/api/products/import-folder', methods=['POST'])
@admin_required
def import_product_folder():
    uploaded_files = request.files.getlist('files')
    if not uploaded_files:
        return jsonify({'error': 'Selecione a pasta completa do catálogo'}), 400

    normalized_files = []
    for uploaded in uploaded_files:
        raw_name = (uploaded.filename or '').replace('\\', '/').strip('/')
        relative_path = PurePosixPath(raw_name)
        if (
            not raw_name
            or relative_path.is_absolute()
            or '..' in relative_path.parts
        ):
            return jsonify({'error': f'Caminho de arquivo inválido: {raw_name}'}), 400
        normalized_files.append((uploaded, relative_path))

    manifest_candidates = [
        path for _, path in normalized_files
        if path.name == 'manifest.json'
    ]
    if len(manifest_candidates) != 1:
        return jsonify({
            'error': 'A pasta deve conter exatamente um arquivo manifest.json',
        }), 400

    manifest_path = manifest_candidates[0]
    catalog_prefix = manifest_path.parent

    import_temp_root = Path(app.static_folder).resolve() / 'import_data' / 'uploads'
    import_temp_root.mkdir(parents=True, exist_ok=True)
    temp_root = import_temp_root / secrets.token_hex(12)
    temp_root.mkdir()
    try:
        for uploaded, relative_path in normalized_files:
            if catalog_prefix != PurePosixPath('.'):
                try:
                    relative_path = relative_path.relative_to(catalog_prefix)
                except ValueError:
                    continue

            destination = temp_root.joinpath(*relative_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            uploaded.save(destination)

        try:
            from backend.import_products import import_catalog
            summary = import_catalog(temp_root)
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return jsonify({'error': f'Catálogo inválido: {exc}'}), 400
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return jsonify({
        'message': 'Catálogo importado com sucesso',
        **summary,
    })


# ============================================
# CATEGORIAS
# ============================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = [
        {"id": "all", "name": "Todos", "icon": "💎"},
        {"id": "brincos", "name": "Brincos", "icon": "✨"},
        {"id": "colares", "name": "Colares", "icon": "📿"},
        {"id": "pulseiras", "name": "Pulseiras", "icon": "⚜️"},
        {"id": "aneis", "name": "Anéis", "icon": "💍"},
        {"id": "pingentes", "name": "Pingentes", "icon": "🔮"},
        {"id": "chaveiros", "name": "Chaveiros", "icon": "🔑"},
        {"id": "conjuntos", "name": "Conjuntos", "icon": "🎁"}
    ]
    return jsonify(categories)


# ============================================
# AUTENTICAÇÃO
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Campos obrigatórios: name, email, password'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'E-mail já cadastrado'}), 409
    
    if len(data['password']) < 6:
        return jsonify({'error': 'A senha deve ter no mínimo 6 caracteres'}), 400
    
    user = User(
        name=data['name'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        cpf=data.get('cpf', ''),
        phone=data.get('phone', ''),
        birthdate=data.get('birthdate', '')
    )
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            'is_admin': user.is_admin,
            'name': user.name,
            'email': user.email
        }
    )
    
    return jsonify({
        'token': access_token,
        'user': user.to_dict()
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Preencha e-mail e senha'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'E-mail ou senha incorretos'}), 401
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            'is_admin': user.is_admin,
            'name': user.name,
            'email': user.email
        }
    )
    
    return jsonify({
        'token': access_token,
        'user': user.to_dict()
    })


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(int(user_id))
    return jsonify(user.to_dict())


@app.route('/api/auth/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')

    if not app.config['ADMIN_PASSWORD']:
        return jsonify({'error': 'ADMIN_PASSWORD não foi configurada no servidor'}), 503
    
    if password != app.config['ADMIN_PASSWORD']:
        return jsonify({'error': 'Senha administrativa incorreta'}), 401
    
    # Tenta encontrar usuário admin ou cria um temporário
    admin_user = User.query.filter_by(is_admin=True).first()
    if not admin_user:
        admin_user = User(
            name='Administrador',
            email='admin@vjsemijoias.com',
            password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
    
    access_token = create_access_token(
        identity=str(admin_user.id),
        additional_claims={
            'is_admin': True,
            'name': 'Administrador',
            'email': 'admin@vjsemijoias.com'
        }
    )
    
    return jsonify({
        'token': access_token,
        'user': admin_user.to_dict()
    })


# ============================================
# PAGAMENTOS
# ============================================

@app.route('/api/payments/config', methods=['GET'])
def payment_config():
    return jsonify({
        'provider': 'infinitepay',
        'enabled': bool(app.config['INFINITEPAY_HANDLE']),
        'max_installments': 12,
    })


@app.route('/api/payments/<string:order_id>/status', methods=['GET'])
def payment_status(order_id):
    token = request.args.get('token', '')
    payment = Payment.query.filter_by(order_id=order_id, checkout_token=token).first_or_404()
    return jsonify(payment.to_dict())


@app.route('/api/payments/infinitepay/checkout', methods=['POST'])
@jwt_required(optional=True)
def create_infinitepay_checkout():
    data = request.get_json(silent=True) or {}
    try:
        totals = validate_order_data(data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    order = create_local_order(data, totals, 'infinitepay_checkout')
    payment = Payment(
        order_id=order.id,
        checkout_token=checkout_token(),
        provider='infinitepay',
        method='checkout',
    )
    db.session.add(payment)
    db.session.flush()

    payload = {
        'order_nsu': order.id,
        'redirect_url': public_url('checkout.html'),
        'webhook_url': public_url('api/payments/webhook/infinitepay'),
        'items': [{
            'quantity': 1,
            'price': cents(totals['total']),
            'description': f'Pedido {order.id} - VJ Semijoias',
        }],
        'customer': {
            'name': order.customer_name,
            'email': order.customer_email,
            'phone_number': f'+55{"".join(filter(str.isdigit, order.customer_phone))}',
        },
        'address': {
            'cep': ''.join(filter(str.isdigit, order.address_zip or '')),
            'street': order.address_street or '',
            'neighborhood': order.address_neighborhood or '',
            'number': order.address_number or '',
            'complement': order.address_complement or '',
        },
    }

    try:
        provider_order = infinitepay().create_link(payload)
        checkout_url = provider_order.get('url')
        if not checkout_url:
            raise InfinitePayError(
                'A InfinitePay não retornou o link de pagamento',
                details=provider_order,
            )
        db.session.commit()
    except InfinitePayError as exc:
        payment.status = 'failed'
        payment.status_detail = str(exc)
        order.status = 'failed'
        db.session.commit()
        return jsonify({
            'error': str(exc),
            'order_id': order.id,
            'details': exc.details,
        }), exc.status_code

    return jsonify({
        'order': order.to_dict(),
        'payment': payment.to_dict(),
        'checkout_url': checkout_url,
    }), 201


@app.route('/api/payments/infinitepay/confirm', methods=['POST'])
def confirm_infinitepay_payment():
    data = request.get_json(silent=True) or {}
    required = ['order_nsu', 'transaction_nsu', 'slug']
    if any(not data.get(field) for field in required):
        return jsonify({'error': 'Dados de confirmação incompletos'}), 400

    payment = Payment.query.filter_by(
        order_id=data['order_nsu'],
        provider='infinitepay',
    ).first_or_404()
    try:
        provider_data = infinitepay().check_payment(
            data['order_nsu'],
            data['transaction_nsu'],
            data['slug'],
        )
        provider_data.update({
            'transaction_nsu': data['transaction_nsu'],
            'slug': data['slug'],
            'capture_method': data.get('capture_method'),
        })
        update_infinitepay_payment(payment, provider_data)
        db.session.commit()
    except (InfinitePayError, ValueError) as exc:
        return jsonify({
            'error': str(exc),
            'details': getattr(exc, 'details', None),
        }), getattr(exc, 'status_code', 400)

    return jsonify({
        'order': payment.order.to_dict(),
        'payment': payment.to_dict(),
    })


@app.route('/api/payments/webhook/infinitepay', methods=['POST'])
def infinitepay_webhook():
    data = request.get_json(silent=True) or {}
    order_nsu = data.get('order_nsu')
    transaction_nsu = data.get('transaction_nsu')
    slug = data.get('invoice_slug') or data.get('slug')
    if not order_nsu or not transaction_nsu or not slug:
        return jsonify({'error': 'Webhook incompleto'}), 400

    payment = Payment.query.filter_by(
        order_id=order_nsu,
        provider='infinitepay',
    ).first()
    if not payment:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    try:
        provider_data = infinitepay().check_payment(order_nsu, transaction_nsu, slug)
        provider_data.update({
            'transaction_nsu': transaction_nsu,
            'slug': slug,
            'capture_method': data.get('capture_method'),
        })
        update_infinitepay_payment(payment, provider_data)
        db.session.commit()
    except (InfinitePayError, ValueError) as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'received': True}), 200


# ============================================
# PEDIDOS
# ============================================

@app.route('/api/orders', methods=['POST'])
@jwt_required(optional=True)
def create_order():
    data = request.get_json(silent=True) or {}

    try:
        totals = validate_order_data(data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    order = create_local_order(data, totals, data.get('payment_method', 'manual'))
    db.session.commit()
    
    return jsonify(order.to_dict()), 201


@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get('is_admin'):
        orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=int(user_id)).order_by(Order.created_at.desc()).all()
    
    return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders/<string:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    identity = int(get_jwt_identity())
    claims = get_jwt()
    if not claims.get('is_admin') and order.user_id != identity:
        return jsonify({'error': 'Acesso negado'}), 403
    return jsonify(order.to_dict())


# ============================================
# NEWSLETTER
# ============================================

@app.route('/api/newsletter', methods=['POST'])
def subscribe_newsletter():
    data = request.get_json()
    email = data.get('email', '')
    
    if not email or '@' not in email:
        return jsonify({'error': 'E-mail inválido'}), 400
    
    existing = Newsletter.query.filter_by(email=email).first()
    if existing:
        return jsonify({
            'message': 'E-mail já cadastrado! Use o cupom VJ10 para 10% off',
            'coupon': 'VJ10'
        })
    
    newsletter = Newsletter(email=email, coupon='VJ10')
    db.session.add(newsletter)
    db.session.commit()
    
    return jsonify({
        'message': 'E-mail cadastrado! Use o cupom VJ10 e ganhe 10% off',
        'coupon': 'VJ10'
    }), 201


# ============================================
# CUPONS
# ============================================

@app.route('/api/coupons/validate', methods=['POST'])
def validate_coupon():
    data = request.get_json()
    code = data.get('code', '').upper()
    
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        # Cupom fixo VJ10
        if code == 'VJ10':
            return jsonify({
                'valid': True,
                'code': 'VJ10',
                'discount_percent': 10,
                'message': 'Cupom VJ10 aplicado! 10% de desconto'
            })
        return jsonify({'valid': False, 'message': 'Cupom inválido ou expirado'}), 404
    
    if coupon.used_count >= coupon.usage_limit:
        return jsonify({'valid': False, 'message': 'Cupom esgotado'}), 400
    
    return jsonify({
        'valid': True,
        'code': coupon.code,
        'discount_percent': coupon.discount_percent,
        'message': f'Cupom {coupon.code} aplicado! {coupon.discount_percent:.0f}% de desconto'
    })


# ============================================
# FRETE SIMULADO
# ============================================

@app.route('/api/shipping/calculate', methods=['POST'])
def calculate_shipping():
    data = request.get_json()
    total = float(data.get('total', 0))
    zip_code = data.get('zip_code', '')
    
    # Frete grátis acima de R$ 199
    if total >= 199:
        return jsonify({
            'shipping': 0,
            'message': 'Frete Grátis!',
            'estimated_days': '5-10'
        })
    
    # Simulação de frete por região baseado no CEP
    if zip_code:
        # Simplificação: ceps começando com 0-2 = SP/RJ/MG = mais barato
        first_digit = zip_code[0] if zip_code else '0'
        if first_digit in '012':
            shipping_value = 14.90
            days = '3-7'
        elif first_digit in '345':
            shipping_value = 19.90
            days = '5-10'
        else:
            shipping_value = 24.90
            days = '7-14'
    else:
        shipping_value = 19.90
        days = '5-10'
    
    return jsonify({
        'shipping': shipping_value,
        'message': f'Frete: R$ {shipping_value:.2f}',
        'estimated_days': days
    })


# ============================================
# ESTATÍSTICAS DO ADMIN
# ============================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_newsletter = Newsletter.query.count()
    
    total_revenue = db.session.query(db.func.sum(Order.total)).filter(
        Order.status.in_(['paid', 'confirmed'])
    ).scalar() or 0
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return jsonify({
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_newsletter': total_newsletter,
        'total_revenue': total_revenue,
        'recent_orders': [o.to_dict() for o in recent_orders]
    })


# ============================================
# SEED DATA - Produtos iniciais do catálogo
# ============================================

def seed_products():
    if Product.query.first() is not None:
        return  # Já existem produtos
    
    initial_products = [
        {
            "id": 1,
            "name": "Brinco Marguerite",
            "category": "brincos",
            "categoryName": "Brincos",
            "price": 149.90,
            "oldPrice": None,
            "image": "images/products/brinco-marguerite.svg",
            "icon": "✨",
            "badge": None,
            "description": "Brinco argolão cravejado com cristais, acabamento impecável. Peça statement para ocasiões especiais.",
            "features": ["Banho de Ouro 18k", "Cravejado com cristais", "Fecho de tarraxa", "Diâmetro aproximado: 3cm"],
            "custom": False
        },
        {
            "id": 2,
            "name": "Colar Sol Dourado",
            "category": "colares",
            "categoryName": "Colares",
            "price": 199.90,
            "oldPrice": None,
            "image": "images/products/colar-sol-dourado.svg",
            "icon": "☀️",
            "badge": "new",
            "description": "Colar delicado com pingente sol, folheado a ouro 18k. Energia e brilho para o seu dia a dia.",
            "features": ["Banho de Ouro 18k", "Pingente formato sol", "Corrente delicada", "Comprimento: 45cm"],
            "custom": False
        },
        {
            "id": 3,
            "name": "Pulseira Corrente Tennis",
            "category": "pulseiras",
            "categoryName": "Pulseiras",
            "price": 179.90,
            "oldPrice": None,
            "image": "images/products/pulseira-tennis.svg",
            "icon": "⚜️",
            "badge": None,
            "description": "Clássica pulseira de elos, banho 18k, fecho seguro. Elegância atemporal.",
            "features": ["Banho de Ouro 18k", "Modelo tennis clássico", "Fecho de segurança", "Comprimento: 18cm + extensor"],
            "custom": False
        },
        {
            "id": 4,
            "name": "Anel Luna",
            "category": "aneis",
            "categoryName": "Anéis",
            "price": 129.90,
            "oldPrice": None,
            "image": "images/products/anel-luna.svg",
            "icon": "🌙",
            "badge": None,
            "description": "Anel ajustável com zircônias, banhado a ouro 18k. Delicadeza que combina com tudo.",
            "features": ["Banho de Ouro 18k", "Zircônias incrustadas", "Modelo ajustável", "Hipoalergênico"],
            "custom": False
        },
        {
            "id": 5,
            "name": "Pingente Flor de Lis",
            "category": "pingentes",
            "categoryName": "Pingentes",
            "price": 99.90,
            "oldPrice": None,
            "image": "images/products/pingente-flor-lis.svg",
            "icon": "🌸",
            "badge": None,
            "description": "Pingente moderno com acabamento diamantado, 18k. Símbolo de nobreza e elegância.",
            "features": ["Banho de Ouro 18k", "Acabamento diamantado", "Modelo Flor de Lis", "Vendido sem corrente"],
            "custom": False
        },
        {
            "id": 6,
            "name": "Brinco Argola Crocodilo",
            "category": "brincos",
            "categoryName": "Brincos",
            "price": 159.90,
            "oldPrice": None,
            "image": "images/products/brinco-argola-crocodilo.svg",
            "icon": "🐊",
            "badge": "new",
            "description": "Argola texturizada, banho ouro 18k, 3cm de diâmetro. Design moderno e marcante.",
            "features": ["Banho de Ouro 18k", "Textura Crocodilo", "Diâmetro: 3cm", "Fecho de pressão"],
            "custom": False
        },
        {
            "id": 7,
            "name": "Colar Gota de Orvalho",
            "category": "colares",
            "categoryName": "Colares",
            "price": 229.90,
            "oldPrice": None,
            "image": "images/products/colar-gota-orvalho.svg",
            "icon": "💧",
            "badge": None,
            "description": "Colar com pedra gota, folheado 18k, comprimento 40cm. Sofisticação em cada detalhe.",
            "features": ["Banho de Ouro 18k", "Pedra em formato gota", "Comprimento: 40cm", "Fecho mosquetão"],
            "custom": False
        },
        {
            "id": 8,
            "name": "Pulseira Elo Coração",
            "category": "pulseiras",
            "categoryName": "Pulseiras",
            "price": 149.90,
            "oldPrice": None,
            "image": "images/products/pulseira-elo-coracao.svg",
            "icon": "💕",
            "badge": None,
            "description": "Elos em formato coração, banho 18k, ideal para presentear. Romântico e delicado.",
            "features": ["Banho de Ouro 18k", "Elos coração", "Ideal para presente", "Comprimento: 17cm + extensor"],
            "custom": False
        },
        {
            "id": 9,
            "name": "Anel Duas Cores",
            "category": "aneis",
            "categoryName": "Anéis",
            "price": 139.90,
            "oldPrice": None,
            "image": "images/products/anel-duas-cores.svg",
            "icon": "💍",
            "badge": "new",
            "description": "Anel bicolor (ouro e rose) banho 18k, tala larga. Tendência e exclusividade.",
            "features": ["Banho de Ouro 18k + Rose", "Modelo bicolor", "Tala larga", "Ajustável"],
            "custom": False
        },
        {
            "id": 10,
            "name": "Pingente Estrela",
            "category": "pingentes",
            "categoryName": "Pingentes",
            "price": 109.90,
            "oldPrice": None,
            "image": "images/products/pingente-estrela.svg",
            "icon": "⭐",
            "badge": None,
            "description": "Pingente estrela cravejada, folheado 18k, corrente fina inclusa. Brilhe sempre.",
            "features": ["Banho de Ouro 18k", "Estrela cravejada", "Acompanha corrente 45cm", "Fecho mosquetão"],
            "custom": False
        }
    ]
    
    for prod_data in initial_products:
        features_json = __import__('json').dumps(prod_data['features'])
        
        product = Product(
            id=prod_data['id'],
            name=prod_data['name'],
            category=prod_data['category'],
            categoryName=prod_data['categoryName'],
            price=prod_data['price'],
            oldPrice=prod_data['oldPrice'],
            image=prod_data['image'],
            icon=prod_data['icon'],
            badge=prod_data['badge'],
            description=prod_data['description'],
            features=features_json,
            custom=False
        )
        db.session.add(product)
    
    # Criar cupom inicial
    coupon = Coupon(code='VJ10', discount_percent=10, is_active=True)
    db.session.add(coupon)
    
    db.session.commit()
    print('✅ Catálogo inicial carregado com sucesso!')


# ============================================
# INICIALIZAÇÃO
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'vj-semijoias-api'})


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

with app.app_context():
    db.create_all()
    seed_products()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    print(f'VJ Semijoias rodando em http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
