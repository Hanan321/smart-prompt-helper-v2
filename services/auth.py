from typing import Any, Dict, Optional, Tuple

from supabase import Client, create_client


# ----------------------------
# Clients
# ----------------------------

def create_supabase_auth_client(url: str, anon_key: str) -> Client:
    return create_client(url, anon_key)


def create_supabase_admin_client(url: str, service_key: str) -> Client:
    return create_client(url, service_key)


# ----------------------------
# Helpers
# ----------------------------

def _to_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


# ----------------------------
# Auth Actions
# ----------------------------

def sign_up(
    client: Client,
    email: str,
    password: str,
    username: str,
    email_redirect_to: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "email": email,
        "password": password,
        "options": {
            "data": {
                "username": username,
            }
        },
    }

    if email_redirect_to:
        payload["options"]["email_redirect_to"] = email_redirect_to

    response = client.auth.sign_up(payload)
    return _to_dict(response)


def sign_in(client: Client, email: str, password: str) -> Dict[str, Any]:
    response = client.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    return _to_dict(response)


def sign_out(client: Client) -> None:
    try:
        client.auth.sign_out()
    except Exception as e:
        print("Sign out error:", e)


# ----------------------------
# Token Handling
# ----------------------------

def extract_tokens(auth_response: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    session = auth_response.get("session") or {}
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    return access_token, refresh_token


def restore_session_from_tokens(
    client: Client,
    access_token: Optional[str],
    refresh_token: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not access_token or not refresh_token:
        return None

    try:
        session_response = client.auth.set_session(access_token, refresh_token)
        session_response = _to_dict(session_response)

        user_response = client.auth.get_user()
        user = getattr(user_response, "user", None)

        if user is None and hasattr(user_response, "model_dump"):
            user = user_response.model_dump().get("user")

        user = _to_dict(user)

        session = session_response.get("session", session_response)

        if not user:
            return None

        return {"session": session, "user": user}

    except Exception as e:
        print("Session restore error:", e)
        return None


# ----------------------------
# Email Actions
# ----------------------------

def resend_signup_confirmation(
    client: Client,
    email: str,
    email_redirect_to: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": "signup",
        "email": email,
    }

    if email_redirect_to:
        payload["options"] = {
            "email_redirect_to": email_redirect_to,
        }

    response = client.auth.resend(payload)
    return _to_dict(response)


def reset_password_for_email(
    client: Client,
    email: str,
    redirect_to: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        if redirect_to:
            response = client.auth.reset_password_email(
                email,
                {"redirect_to": redirect_to},
            )
        else:
            response = client.auth.reset_password_email(email)

        return _to_dict(response)

    except Exception as e:
        print("Password reset error:", e)
        raise