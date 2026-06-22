import base64
import binascii
import io
import re
from html import unescape
from pathlib import Path

from PIL import Image, UnidentifiedImageError


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]*>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
PIL_FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


def digits_only(value) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def normalize_email(value, *, required=True) -> str:
    email = str(value or "").strip().lower()
    if not email:
        if required:
            raise ValueError("E-mail obrigatorio")
        return ""
    if len(email) > 200 or not EMAIL_RE.match(email):
        raise ValueError("E-mail invalido")
    return email


def validate_cpf(value, *, required=True) -> str:
    cpf = digits_only(value)
    if not cpf:
        if required:
            raise ValueError("CPF obrigatorio")
        return ""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValueError("CPF invalido")

    for digit_index in (9, 10):
        total = sum(
            int(cpf[index]) * (digit_index + 1 - index)
            for index in range(digit_index)
        )
        check_digit = (total * 10) % 11
        if check_digit == 10:
            check_digit = 0
        if check_digit != int(cpf[digit_index]):
            raise ValueError("CPF invalido")
    return cpf


def normalize_phone(value, *, required=False) -> str:
    phone = digits_only(value)
    if not phone:
        if required:
            raise ValueError("Telefone obrigatorio")
        return ""
    if phone.startswith("55") and len(phone) in {12, 13}:
        phone = phone[2:]
    if len(phone) not in {10, 11}:
        raise ValueError("Telefone invalido")
    return phone


def clean_text(
    value,
    *,
    field="campo",
    max_length=200,
    required=False,
    allow_newlines=False,
) -> str:
    text = str(value or "")
    text = unescape(text)
    text = TAG_RE.sub("", text)
    text = text.replace("<", "").replace(">", "")
    text = CONTROL_RE.sub("", text)
    if not allow_newlines:
        text = " ".join(text.split())
    else:
        text = "\n".join(" ".join(line.split()) for line in text.splitlines())
        text = "\n".join(line for line in text.splitlines() if line)
    text = text.strip()
    if required and not text:
        raise ValueError(f"Campo obrigatorio: {field}")
    if len(text) > max_length:
        raise ValueError(f"{field} deve ter no maximo {max_length} caracteres")
    return text


def clean_text_list(values, *, field="campo", max_items=20, max_item_length=120) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_items = values.splitlines()
    elif isinstance(values, list):
        raw_items = values
    else:
        raise ValueError(f"{field} deve ser uma lista")
    if len(raw_items) > max_items:
        raise ValueError(f"{field} deve ter no maximo {max_items} itens")
    return [
        cleaned
        for item in raw_items
        if (cleaned := clean_text(item, field=field, max_length=max_item_length))
    ]


def normalize_money_float(value, *, field="valor", required=True, minimum=0.0):
    if value in (None, ""):
        if required:
            raise ValueError(f"Campo obrigatorio: {field}")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} invalido") from exc
    if number < minimum:
        raise ValueError(f"{field} nao pode ser negativo")
    return number


def safe_image_extension(content_type: str, filename: str = "") -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise ValueError(f"Formato de imagem nao suportado: {content_type or 'desconhecido'}")
    filename_extension = Path(filename or "").suffix.lower()
    allowed_extensions = set(ALLOWED_IMAGE_TYPES.values()) | {".jpeg"}
    if filename_extension and filename_extension not in allowed_extensions:
        raise ValueError(f"Extensao de imagem nao suportada: {filename_extension}")
    return extension


def validate_image_bytes(
    content: bytes,
    content_type: str,
    *,
    filename: str = "",
    max_bytes: int,
) -> tuple[str, str]:
    if not content:
        raise ValueError("Imagem vazia")
    if len(content) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise ValueError(f"Imagem maior que {max_mb} MB")

    declared_content_type = (content_type or "").split(";")[0].strip().lower()
    declared_extension = safe_image_extension(declared_content_type, filename)
    try:
        with Image.open(io.BytesIO(content)) as image:
            detected_content_type = PIL_FORMAT_CONTENT_TYPES.get(image.format)
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Arquivo de imagem invalido") from exc

    if not detected_content_type:
        raise ValueError("Formato de imagem nao suportado")
    normalized_declared = (
        "image/jpeg" if declared_content_type == "image/jpg" else declared_content_type
    )
    if detected_content_type != normalized_declared:
        raise ValueError("Tipo de imagem nao corresponde ao conteudo enviado")
    return detected_content_type, declared_extension


def decode_base64_image(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Imagem enviada em base64 invalida") from exc
