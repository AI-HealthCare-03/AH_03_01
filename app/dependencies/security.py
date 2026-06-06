from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

security = HTTPBearer()


async def get_request_user(credential: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> User:
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    raw_user_id = verified.payload["user_id"]
    try:
        user_id = UUID(str(raw_user_id))
    except (ValueError, TypeError) as err:
        raise HTTPException(detail="Invalid token subject.", status_code=status.HTTP_401_UNAUTHORIZED) from err
    user = await UserRepository().get_user(user_id)
    if not user:
        raise HTTPException(detail="Authenticate Failed.", status_code=status.HTTP_401_UNAUTHORIZED)
    # 탈퇴/비활성/정지 계정은 기존 access token 으로도 즉시 차단(토큰은 stateless 라 만료 전까지 유효하므로).
    if user.is_deleted or not user.is_active:
        raise HTTPException(detail="비활성화되었거나 탈퇴한 계정입니다.", status_code=status.HTTP_401_UNAUTHORIZED)
    if user.is_banned:
        raise HTTPException(detail="정지된 계정입니다.", status_code=status.HTTP_403_FORBIDDEN)
    return user
