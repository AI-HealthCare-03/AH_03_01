"""미디어 signed-URL 서명/검증 + /media 서빙 라우트 테스트.

서명은 상태 비저장(HMAC)이라 DB 불필요. 라우트는 ASGI 클라이언트로 직접 친다.
정책: 비공개(PHI) 경로(challenge_verification·inquiry_attachment·report_pdf)만
서명 게이트, 공개 경로(profile_image·community 등)는 무서명 서빙.
"""

from urllib.parse import parse_qsl, urlsplit

from httpx import ASGITransport, AsyncClient

from app.core import config
from app.core.media import resolve_media_root, sign_media_url, verify_media_signature
from app.main import app

# 비공개(서명 대상) / 공개(무서명) 경로 샘플
PRIVATE_URL = f"{config.MEDIA_URL_PREFIX}/uploads/challenge_verification/20260615/1/abc.jpg"
PUBLIC_URL = f"{config.MEDIA_URL_PREFIX}/uploads/profile_image/20260615/1/abc.jpg"


def _parts(signed: str) -> tuple[str, dict[str, str]]:
    s = urlsplit(signed)
    return s.path, dict(parse_qsl(s.query))


# ── 단위: 서명/검증 ────────────────────────────────────────────────────────


def test_sign_then_verify_roundtrip():
    signed = sign_media_url(PRIVATE_URL)
    assert signed is not None and "?" in signed
    path, q = _parts(signed)
    assert verify_media_signature(path, q["exp"], q["sig"]) is True


def test_tampered_signature_fails():
    signed = sign_media_url(PRIVATE_URL)
    assert signed is not None
    path, q = _parts(signed)
    assert verify_media_signature(path, q["exp"], "deadbeef") is False
    # 경로를 바꾸면 서명 불일치
    other = PRIVATE_URL.replace("abc.jpg", "other.jpg")
    assert verify_media_signature(other, q["exp"], q["sig"]) is False


def test_expired_signature_fails():
    signed = sign_media_url(PRIVATE_URL, expires_in=-10)
    assert signed is not None
    path, q = _parts(signed)
    assert verify_media_signature(path, q["exp"], q["sig"]) is False


def test_missing_params_fail():
    assert verify_media_signature(PRIVATE_URL, None, None) is False
    assert verify_media_signature(PRIVATE_URL, "not-int", "abc") is False


def test_public_path_is_not_signed():
    # 공개 경로(아바타 등)는 서명하지 않고 그대로 반환 → <img> 등 어디서나 동작
    assert sign_media_url(PUBLIC_URL) == PUBLIC_URL
    assert sign_media_url(f"{config.MEDIA_URL_PREFIX}/community/x.jpg") == f"{config.MEDIA_URL_PREFIX}/community/x.jpg"


def test_non_media_url_passthrough():
    assert sign_media_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"
    assert sign_media_url(None) is None
    assert sign_media_url("") == ""


def test_already_signed_is_resigned_not_doubled():
    once = sign_media_url(PRIVATE_URL)
    assert once is not None
    twice = sign_media_url(once)
    assert twice is not None
    assert twice.count("?") == 1
    assert twice.count("exp=") == 1


# ── 라우트: /media 서빙 ────────────────────────────────────────────────────


async def test_private_media_requires_valid_signature():
    root = resolve_media_root()
    rel_dir = "uploads/challenge_verification/testseg"
    (root / rel_dir).mkdir(parents=True, exist_ok=True)
    (root / rel_dir / "sig_test.jpg").write_bytes(b"hello-private")
    access_url = f"{config.MEDIA_URL_PREFIX}/{rel_dir}/sig_test.jpg"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 서명 없음 → 403
        assert (await client.get(access_url)).status_code == 403

        # 유효 서명 → 200 + 내용
        signed = sign_media_url(access_url)
        assert signed is not None
        res = await client.get(signed)
        assert res.status_code == 200
        assert res.content == b"hello-private"

        # 변조 서명 → 403
        _, q = _parts(signed)
        assert (await client.get(f"{access_url}?exp={q['exp']}&sig=deadbeef")).status_code == 403


async def test_public_media_served_without_signature():
    root = resolve_media_root()
    rel_dir = "uploads/profile_image/testseg"
    (root / rel_dir).mkdir(parents=True, exist_ok=True)
    (root / rel_dir / "pub.jpg").write_bytes(b"hello-public")
    access_url = f"{config.MEDIA_URL_PREFIX}/{rel_dir}/pub.jpg"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 공개 경로는 서명 없이도 200
        res = await client.get(access_url)
        assert res.status_code == 200
        assert res.content == b"hello-public"


async def test_media_route_blocks_path_traversal():
    # 비공개 경로로 서명을 발급해도 미디어 루트를 벗어나는 경로는 차단.
    traversal = f"{config.MEDIA_URL_PREFIX}/uploads/challenge_verification/../../../etc/passwd"
    signed = sign_media_url(traversal)
    assert signed is not None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(signed)
        assert res.status_code in (403, 404)
