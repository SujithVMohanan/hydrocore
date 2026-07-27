from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


ACCESS_BLACKLIST_PREFIX = "jwt:blacklist:access:"


def blacklist_access_token(raw_token: str) -> None:
    token = AccessToken(raw_token)
    jti = token["jti"]
    exp = int(token["exp"])
    ttl = max(exp - int(timezone.now().timestamp()), 1)
    cache.set(f"{ACCESS_BLACKLIST_PREFIX}{jti}", "1", timeout=ttl)


def is_access_token_blacklisted(validated_token) -> bool:
    jti = validated_token.get("jti")
    if not jti:
        return False
    return cache.get(f"{ACCESS_BLACKLIST_PREFIX}{jti}") is not None


def blacklist_refresh_token(raw_refresh: str) -> None:
    refresh = RefreshToken(raw_refresh)
    refresh.blacklist()


def logout_tokens(*, access_token: str | None, refresh_token: str) -> None:
    
    try:
        blacklist_refresh_token(refresh_token)
    except TokenError as exc:
        raise TokenError(str(exc)) from exc

    if access_token:
        try:
            blacklist_access_token(access_token)
        except TokenError:
            # Access may already be expired; refresh blacklist is still enough.
            pass
