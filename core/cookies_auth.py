import streamlit as st

from services.auth import extract_tokens, restore_session_from_tokens


def restore_auth_once(cookies, supabase_auth) -> None:
    if st.session_state.auth_restored:
        return

    access_token = cookies.get("access_token")
    refresh_token = cookies.get("refresh_token")

    restored = restore_session_from_tokens(
        supabase_auth,
        access_token,
        refresh_token,
    )

    if restored:
        st.session_state.session = restored.get("session")
        st.session_state.user = restored.get("user")

    st.session_state.auth_restored = True


def save_auth_cookies(cookies, auth_response: dict) -> None:
    access_token, refresh_token = extract_tokens(auth_response)

    if access_token and refresh_token:
        cookies["access_token"] = access_token
        cookies["refresh_token"] = refresh_token
        cookies.save()


def clear_auth_cookies(cookies) -> None:
    if "access_token" in cookies:
        del cookies["access_token"]
    if "refresh_token" in cookies:
        del cookies["refresh_token"]
    cookies.save()