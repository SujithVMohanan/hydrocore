from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from utils.jwt_blacklist import is_access_token_blacklisted


class JWTAccessBlacklistAuthentication(JWTTokenUserAuthentication):
    
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        if is_access_token_blacklisted(validated_token):
            raise InvalidToken(_("Token has been expired by logout."))
        return validated_token
