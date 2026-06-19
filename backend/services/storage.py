import hashlib
import hmac
import os
from datetime import UTC, datetime
from urllib.parse import quote

import requests


R2_SERVICE = "s3"
R2_REGION = "auto"


def storage_backend():
    return os.getenv("STORAGE_BACKEND", "local").strip().lower()


def r2_enabled():
    return storage_backend() == "r2"


def public_url(base_url, key):
    return f"{base_url.rstrip('/')}/{quote(key.strip('/'), safe='/')}"


def r2_config():
    config = {
        "account_id": os.getenv("R2_ACCOUNT_ID", "").strip(),
        "bucket": os.getenv("R2_BUCKET", "").strip(),
        "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        "public_base_url": os.getenv("R2_PUBLIC_BASE_URL", "").strip().rstrip("/"),
    }
    missing = [key for key, value in config.items() if not value]
    if missing:
        raise RuntimeError(f"Configuracao R2 incompleta: {', '.join(missing)}")
    return config


def storage_status():
    config = {
        "backend": storage_backend(),
        "r2": {
            "account_id_configured": bool(os.getenv("R2_ACCOUNT_ID", "").strip()),
            "bucket": os.getenv("R2_BUCKET", "").strip(),
            "access_key_configured": bool(os.getenv("R2_ACCESS_KEY_ID", "").strip()),
            "secret_key_configured": bool(os.getenv("R2_SECRET_ACCESS_KEY", "").strip()),
            "public_base_url": os.getenv("R2_PUBLIC_BASE_URL", "").strip().rstrip("/"),
        },
    }
    config["r2"]["ready"] = all(
        [
            config["r2"]["account_id_configured"],
            config["r2"]["bucket"],
            config["r2"]["access_key_configured"],
            config["r2"]["secret_key_configured"],
            config["r2"]["public_base_url"],
        ]
    )
    return config


def signing_key(secret_key, date_stamp):
    date_key = hmac.new(
        ("AWS4" + secret_key).encode("utf-8"),
        date_stamp.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    region_key = hmac.new(date_key, R2_REGION.encode("utf-8"), hashlib.sha256).digest()
    service_key = hmac.new(region_key, R2_SERVICE.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def upload_r2_object(key, content, content_type, cache_control="public, max-age=31536000, immutable"):
    config = r2_config()
    clean_key = key.strip("/")
    encoded_key = quote(clean_key, safe="/")
    host = f"{config['account_id']}.r2.cloudflarestorage.com"
    canonical_uri = f"/{config['bucket']}/{encoded_key}"
    endpoint = f"https://{host}{canonical_uri}"

    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(content).hexdigest()
    headers = {
        "cache-control": cache_control,
        "content-type": content_type,
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(
        f"{name}:{headers[name]}\n" for name in sorted(headers)
    )
    canonical_request = "\n".join(
        [
            "PUT",
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date_stamp}/{R2_REGION}/{R2_SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        signing_key(config["secret_access_key"], date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={config['access_key_id']}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    session = requests.Session()
    session.trust_env = False
    response = session.put(
        endpoint,
        data=content,
        headers={**headers, "authorization": authorization},
        timeout=30,
    )
    response.raise_for_status()
    return public_url(config["public_base_url"], clean_key)


def store_public_file(key, content, content_type):
    if not r2_enabled():
        raise RuntimeError("Storage R2 nao esta habilitado")
    return upload_r2_object(key, content, content_type)
