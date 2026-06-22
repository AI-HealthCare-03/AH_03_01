from calendar import timegm
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Self
from uuid import uuid4

from app.core import config
from app.core.jwt.exceptions import ExpiredTokenError, TokenBackendError, TokenBackendExpiredError, TokenError
from app.core.jwt.state import token_backend
from app.models.users import User

if TYPE_CHECKING:
    from app.core.jwt.backends import TokenBackend


class Token:
    token_type: str | None = None
    lifetime: timedelta | None = None
    _token_backend: "TokenBackend" = token_backend

    def __init__(self, token: str | None = None, verify: bool = True) -> None:
        if not self.token_type:
            raise TokenError("token_type must be set")
        if not self.lifetime:
            raise TokenError("lifetime must be set")

        self.token = token
        self.current_time = datetime.now(tz=config.TIMEZONE)
        self.payload: dict[str, Any] = {}

        if token is not None:
            try:
                self.payload = token_backend.decode(token, verify=verify)
            except TokenBackendExpiredError as err:
                raise ExpiredTokenError("Token is expired") from err
            except TokenBackendError as err:
                raise TokenError("Token is invalid") from err
            # 토큰 종류 검증: 모든 토큰이 같은 SECRET_KEY 로 서명되므로 type 을 확인하지 않으면
            # refresh 토큰을 access 로 쓰는 등의 토큰 혼동(token confusion)이 가능하다.
            if verify and self.payload.get("type") != self.token_type:
                raise TokenError("Token has wrong type")
        else:
            self.payload = {"type": self.token_type}
            self.set_exp(from_time=self.current_time, lifetime=self.lifetime)
            self.set_jti()

    def __repr__(self) -> str:
        return repr(self.payload)

    def __getitem__(self, key: str):
        return self.payload[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.payload[key] = value

    def __delitem__(self, key: str) -> None:
        del self.payload[key]

    def __contains__(self, key: str) -> Any:
        return key in self.payload

    def __str__(self) -> str:
        """
        Signs and returns a token as a base64 encoded string.
        """
        return self._token_backend.encode(self.payload)

    def set_exp(self, from_time: datetime | None = None, lifetime: timedelta | None = None) -> None:
        if from_time is None:
            from_time = self.current_time

        if lifetime is None:
            lifetime = self.lifetime

        assert lifetime is not None

        dt = from_time + lifetime
        self.payload["exp"] = timegm(dt.timetuple())

    def set_jti(self) -> None:
        self.payload["jti"] = uuid4().hex

    @classmethod
    def for_user(cls, user: User) -> Self:
        token = cls()
        # User.id 가 UUID 가 된 이후 JWT 페이로드는 문자열로 직렬화한다.
        token["user_id"] = str(user.id)
        return token


class AccessToken(Token):
    token_type = "access"
    lifetime = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)


class RefreshToken(Token):
    token_type = "refresh"
    lifetime = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    no_copy_claims = ("type", "exp", "jti")

    @property
    def access_token(self) -> AccessToken:
        access = AccessToken()
        access.set_exp(from_time=self.current_time)

        no_copy = self.no_copy_claims
        for claim, value in self.payload.items():
            if claim in no_copy:
                continue
            access[claim] = value

        return access
