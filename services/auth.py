from typing import Any

from supabase import Client, create_client



def create_supabase_auth_client(url: str, anon_key: str) -> Client:
    return create_client(url, anon_key)



def create_supabase_admin_client(url: str, service_key: str) -> Client:
    return create_client(url, service_key)



def sign_up(client: Client, email: str, password: str) -> dict[str, Any]:
    response = client.auth.sign_up({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)



def sign_in(client: Client, email: str, password: str) -> dict[str, Any]:
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)



def sign_out(client: Client) -> None:
    client.auth.sign_out()
