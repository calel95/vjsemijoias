from backend.config import settings
from backend.models import Order, Payment, User
from backend.services.email import OutgoingEmail, send_email


def absolute_url(path: str) -> str:
    base = settings.public_base_url or "http://localhost:5000"
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def money_br(value) -> str:
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def public_order_url(order: Order) -> str:
    return absolute_url(f"pedido?id={order.id}&token={order.public_token or ''}")


def send_registration_email(user: User) -> bool:
    return send_email(
        OutgoingEmail(
            to=user.email,
            subject="Cadastro recebido - VJ Semijoias",
            text=(
                f"Ola, {user.name}!\n\n"
                "Seu cadastro na VJ Semijoias foi criado com sucesso.\n"
                "Voce ja pode acompanhar pedidos e finalizar compras com mais praticidade.\n\n"
                "Com carinho,\nVJ Semijoias"
            ),
        )
    )


def send_order_created_email(order: Order, payment: Payment | None = None) -> bool:
    payment_line = ""
    if payment and payment.status == "pending":
        payment_line = "\nPagamento: aguardando conclusao no checkout seguro."
    return send_email(
        OutgoingEmail(
            to=order.customer_email,
            subject=f"Pedido {order.id} recebido - VJ Semijoias",
            text=(
                f"Ola, {order.customer_name}!\n\n"
                f"Recebemos seu pedido {order.id}.\n"
                f"Total: {money_br(order.total)}.{payment_line}\n"
                f"Acompanhe seu pedido: {public_order_url(order)}\n\n"
                "Obrigada por comprar na VJ Semijoias."
            ),
        )
    )


def send_payment_approved_email(order: Order, payment: Payment) -> bool:
    return send_email(
        OutgoingEmail(
            to=order.customer_email,
            subject=f"Pagamento aprovado - Pedido {order.id}",
            text=(
                f"Ola, {order.customer_name}!\n\n"
                f"O pagamento do pedido {order.id} foi aprovado.\n"
                f"Forma de pagamento: {payment.method}.\n"
                "Agora vamos preparar tudo por aqui.\n\n"
                f"Acompanhe seu pedido: {public_order_url(order)}"
            ),
        )
    )


def send_order_shipped_email(order: Order) -> bool:
    tracking = ""
    if order.tracking_code:
        tracking = f"\nCodigo de rastreio: {order.tracking_code}"
    if order.tracking_carrier:
        tracking += f"\nTransportadora: {order.tracking_carrier}"
    return send_email(
        OutgoingEmail(
            to=order.customer_email,
            subject=f"Pedido {order.id} enviado",
            text=(
                f"Ola, {order.customer_name}!\n\n"
                f"Seu pedido {order.id} foi enviado.{tracking}\n\n"
                f"Acompanhe seu pedido: {public_order_url(order)}"
            ),
        )
    )


def send_password_reset_email(user: User, token: str) -> bool:
    reset_url = absolute_url(f"login?reset_token={token}")
    return send_email(
        OutgoingEmail(
            to=user.email,
            subject="Recuperacao de senha - VJ Semijoias",
            text=(
                f"Ola, {user.name}!\n\n"
                "Recebemos uma solicitacao para redefinir sua senha.\n"
                f"Use este link em ate 1 hora: {reset_url}\n\n"
                "Se voce nao pediu isso, ignore este e-mail."
            ),
        )
    )
