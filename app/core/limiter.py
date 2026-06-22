"""공개 엔드포인트 레이트리밋 (slowapi).

인증 등 익명 호출이 가능한 엔드포인트의 무차별 호출(브루트포스·계정 열거·메일 폭탄)을
IP 단위로 제한한다. 저장소는 Redis(멀티 워커 공유), Redis 장애 시 fail-open(인증 차단 방지).
"""

import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core import config


def _is_trusted_proxy(host: str | None) -> bool:
    """직접 소켓 피어가 신뢰 가능한 리버스 프록시(사설/루프백 대역)인지."""
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


def _client_ip(request: Request) -> str:
    """프록시(nginx) 뒤에서 실제 클라이언트 IP 추출.

    nginx 가 `X-Real-IP $remote_addr` 로 매 요청 덮어쓰므로(infra/nginx) 프록시를 거친 경우 이 값은
    클라이언트가 위조할 수 없다. 단, nginx 를 거치지 않는 직접 접속(직접 EC2 접근 등)에서는 클라이언트가
    임의 X-Real-IP 를 주입해 레이트리밋 키를 바꿀 수 있으므로, **소켓 피어가 사설/루프백(=리버스 프록시)
    일 때만** X-Real-IP 를 신뢰한다. 그 외에는 위조 불가능한 소켓 주소를 사용한다.
    클라이언트가 임의로 채울 수 있는 X-Forwarded-For 의 first-hop 은 신뢰하지 않는다.
    """
    peer = request.client.host if request.client else None
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and _is_trusted_proxy(peer):
        return real_ip.strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_ip,
    storage_uri=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
    swallow_errors=True,
)
