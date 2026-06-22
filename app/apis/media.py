"""서명 검증 기반 /media 서빙 라우트.

무인증 StaticFiles 마운트를 대체한다. ``?exp=&sig=`` 서명이 유효할 때만 파일을
내려주며(서명이 곧 인가), 경로 이탈(path traversal)을 차단한다. ``<img src>`` 등
헤더를 못 싣는 클라이언트도 서명 URL 로 접근할 수 있다.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core import config
from app.core.media import is_private_media_path, resolve_media_root, verify_media_signature

media_router = APIRouter(prefix=config.MEDIA_URL_PREFIX, tags=["media"])


@media_router.get("/{file_path:path}")
async def serve_media(
    file_path: str,
    exp: str | None = Query(default=None),
    sig: str | None = Query(default=None),
) -> FileResponse:
    full_path = f"{config.MEDIA_URL_PREFIX}/{file_path}"
    # 비공개(PHI) 경로만 서명 검증. 공개 경로(아바타·커뮤니티 등)는 그대로 서빙한다.
    private = is_private_media_path(full_path)
    if private and not verify_media_signature(full_path, exp, sig):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않거나 만료된 링크입니다.")

    base = resolve_media_root()
    target = (base / file_path).resolve()
    # 경로 이탈 차단: 반드시 미디어 루트 하위여야 한다.
    if base != target and base not in target.parents:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="잘못된 경로입니다.")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다.")
    # PHI 파일은 공유 캐시/프록시에 잔존하지 않도록 캐시 금지 + MIME 스니핑 차단.
    headers = {"X-Content-Type-Options": "nosniff"}
    if private:
        headers["Cache-Control"] = "private, no-store, max-age=0"
    return FileResponse(target, headers=headers)
