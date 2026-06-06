"""공개 엔드포인트 레이트리밋 (slowapi).

인증 등 익명 호출이 가능한 엔드포인트의 무차별 호출(브루트포스·계정 열거·메일 폭탄)을
IP 단위로 제한한다. 저장소는 Redis(멀티 워커 공유), Redis 장애 시 fail-open(인증 차단 방지).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core import config


def _client_ip(request: Request) -> str:
    """프록시(nginx) 뒤에서 실제 클라이언트 IP 추출.

    nginx 가 X-Real-IP / X-Forwarded-For 를 설정한다(infra/nginx). 헤더가 없으면(직접 접속)
    소켓 주소로 폴백. 신뢰 프록시 전제 — 외부 직노출 시 헤더 스푸핑 가능성에 유의.
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_ip,
    storage_uri=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
    swallow_errors=True,
)
