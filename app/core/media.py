"""미디어(/media) signed-URL 서명/검증.

업로드 파일은 PHI(예: 챌린지 인증 사진)를 포함할 수 있으므로 무인증 정적 서빙을
막는다. DB 에는 상대경로(``/media/...``)만 저장하고, 클라이언트로 내보낼 때마다
짧은 만료의 HMAC 서명을 붙인다(sign-on-read). ``/media`` 서빙 라우트가 서명과
만료를 검증한 뒤에만 파일을 내려준다.

서명 대상은 쿼리스트링을 제외한 경로 문자열(``/media/uploads/...``)이며,
비밀키는 JWT 와 동일한 ``config.SECRET_KEY`` 를 사용한다.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from functools import lru_cache
from pathlib import Path

from app.core import config

# PHI 민감 업로드만 서명 게이트를 건다. 나머지(프로필 아바타·커뮤니티 이미지·
# 게시글 첨부)는 앱 내 공개 콘텐츠라 무서명 서빙(서명 시 회귀만 큼).
# FileUploadService 저장 경로 = /media/uploads/{file_type.lower()}/...
_PRIVATE_MEDIA_PREFIXES: tuple[str, ...] = (
    f"{config.MEDIA_URL_PREFIX}/uploads/challenge_verification/",
    f"{config.MEDIA_URL_PREFIX}/uploads/inquiry_attachment/",
    f"{config.MEDIA_URL_PREFIX}/uploads/report_pdf/",
)


def is_private_media_path(path: str) -> bool:
    """서명 게이트가 필요한 비공개(PHI) 미디어 경로인지."""
    return path.startswith(_PRIVATE_MEDIA_PREFIXES)


def _secret() -> bytes:
    return str(config.SECRET_KEY).encode()


def _expected_sig(path: str, exp: int) -> str:
    return hmac.new(_secret(), f"{path}:{exp}".encode(), hashlib.sha256).hexdigest()


def sign_media_url(access_url: str | None, *, expires_in: int | None = None) -> str | None:
    """상대 미디어 경로에 ``?exp=&sig=`` 서명을 붙여 반환.

    비공개(PHI) 미디어 경로만 서명한다. 공개 경로·외부 URL·falsy 는 그대로 둔다.
    이미 쿼리가 붙어 있으면 경로 부분만 취해 재서명한다(중복 서명 방지).
    """
    if not access_url:
        return access_url
    path = access_url.split("?", 1)[0]
    if not is_private_media_path(path):
        return access_url
    ttl = config.MEDIA_URL_TTL if expires_in is None else expires_in
    exp = int(time.time()) + ttl
    return f"{path}?exp={exp}&sig={_expected_sig(path, exp)}"


def verify_media_signature(path: str, exp: str | None, sig: str | None) -> bool:
    """``path`` 에 대한 ``exp``/``sig`` 가 유효하고 만료되지 않았는지 검증."""
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_int < int(time.time()):
        return False
    return hmac.compare_digest(_expected_sig(path, exp_int), sig)


@lru_cache(maxsize=1)
def resolve_media_root() -> Path:
    """업로드/서빙 공용 미디어 루트. main.py 마운트와 동일한 폴백 규칙."""
    try:
        root = Path(config.MEDIA_ROOT)
        root.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        root = Path.cwd() / ".media"
        root.mkdir(parents=True, exist_ok=True)
    return root.resolve()
