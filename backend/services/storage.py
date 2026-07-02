import hashlib
import hmac
import os
from datetime import UTC, datetime
from urllib.parse import quote

import requests


R2_SERVICE = "s3"
R2_REGION = "auto"
STORAGE_BACKENDS = {"local", "r2"}
R2_REQUIRED_ENV = {
    "account_id": "R2_ACCOUNT_ID",
    "bucket": "R2_BUCKET",
    "access_key_id": "R2_ACCESS_KEY_ID",
    "secret_access_key": "R2_SECRET_ACCESS_KEY",
    "public_base_url": "R2_PUBLIC_BASE_URL",
}


def _storage_backend_value():
    return (os.getenv("STORAGE_BACKEND", "").strip().lower() or "local")


def storage_backend():
    backend = _storage_backend_value()
    if backend not in STORAGE_BACKENDS:
        raise RuntimeError("STORAGE_BACKEND invalido: use local ou r2")
    return backend


def r2_enabled():
    return storage_backend() == "r2"


def public_url(base_url, key):
    return f"{base_url.rstrip('/')}/{quote(key.strip('/'), safe='/')}"


def public_asset_url(key, *, base_url=""):
    base_url = (base_url or "").strip().rstrip("/")
    clean_key = str(key or "").strip().lstrip("/")
    if not base_url:
        return clean_key
    return public_url(base_url, clean_key)


def _r2_env_config():
    return {
        "account_id": os.getenv("R2_ACCOUNT_ID", "").strip(),
        "bucket": os.getenv("R2_BUCKET", "").strip(),
        "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        "public_base_url": os.getenv("R2_PUBLIC_BASE_URL", "").strip().rstrip("/"),
    }


def missing_r2_config(config=None):
    config = config or _r2_env_config()
    return [env_name for key, env_name in R2_REQUIRED_ENV.items() if not config.get(key)]


def validate_r2_config():
    config = _r2_env_config()
    missing = missing_r2_config(config)
    if missing:
        raise RuntimeError(f"Configuracao R2 incompleta: {', '.join(missing)}")
    return config


def validate_storage_config():
    backend = storage_backend()
    if backend == "local":
        return {"backend": "local", "ready": True, "r2_enabled": False}
    validate_r2_config()
    return {"backend": "r2", "ready": True, "r2_enabled": True}


def r2_config():
    return validate_r2_config()


def storage_status():
    backend = _storage_backend_value()
    backend_valid = backend in STORAGE_BACKENDS
    r2_config_values = _r2_env_config()
    missing = missing_r2_config(r2_config_values)
    r2_ready = not missing
    errors = []

    if not backend_valid:
        errors.append("STORAGE_BACKEND invalido: use local ou r2")
    elif backend == "r2" and missing:
        errors.append(f"Configuracao R2 incompleta: {', '.join(missing)}")

    return {
        "backend": backend,
        "backend_valid": backend_valid,
        "ready": backend_valid and (backend == "local" or r2_ready),
        "errors": errors,
        "r2": {
            "enabled": backend_valid and backend == "r2",
            "ready": r2_ready,
            "configured": r2_ready,
            "missing": missing if backend == "r2" else [],
            "account_id_configured": bool(r2_config_values["account_id"]),
            "bucket": r2_config_values["bucket"],
            "bucket_configured": bool(r2_config_values["bucket"]),
            "access_key_configured": bool(r2_config_values["access_key_id"]),
            "secret_key_configured": bool(r2_config_values["secret_access_key"]),
            "public_base_url": r2_config_values["public_base_url"],
            "public_base_url_configured": bool(r2_config_values["public_base_url"]),
        },
    }


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
    return public_asset_url(clean_key, base_url=config["public_base_url"])


def store_public_file(key, content, content_type):
    if not r2_enabled():
        raise RuntimeError("Storage R2 nao esta habilitado")
    validate_storage_config()
    return upload_r2_object(key, content, content_type)