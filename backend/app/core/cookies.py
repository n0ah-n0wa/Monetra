"""Secure cookie helpers for refresh-token transport."""

from fastapi import Response

from app.core.config import Settings


def set_refresh_token_cookie(
    response: Response,
    *,
    token: str,
    settings: Settings,
) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.refresh_token_cookie_secure,
        samesite=settings.refresh_token_cookie_samesite,
        path=settings.refresh_token_cookie_path,
        domain=settings.refresh_token_cookie_domain,
    )


def clear_refresh_token_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
        domain=settings.refresh_token_cookie_domain,
    )
