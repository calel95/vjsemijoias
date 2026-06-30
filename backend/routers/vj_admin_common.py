def admin_user_id(claims) -> int | None:
    try:
        return int(claims.get("sub")) if claims and claims.get("sub") else None
    except (TypeError, ValueError):
        return None