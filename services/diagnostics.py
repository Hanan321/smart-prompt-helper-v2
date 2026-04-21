import hashlib


def secret_fingerprint(value: str | None) -> str:
    if not value:
        return "missing"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def key_label(value: str | None) -> str:
    if not value:
        return "missing"
    if value.startswith("sk_test_"):
        return f"sk_test fingerprint={secret_fingerprint(value)}"
    if value.startswith("sk_live_"):
        return f"sk_live fingerprint={secret_fingerprint(value)}"
    if value.startswith("pk_test_"):
        return f"pk_test fingerprint={secret_fingerprint(value)}"
    if value.startswith("pk_live_"):
        return f"pk_live fingerprint={secret_fingerprint(value)}"
    if value.startswith("whsec_"):
        return f"whsec fingerprint={secret_fingerprint(value)}"
    return f"unknown-prefix fingerprint={secret_fingerprint(value)}"
