from unittest import mock

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.jwt.state import token_backend
from app.core.utils.security import generate_oauth_state
from app.main import app
from app.services.kakao_oauth import KakaoProfile

BASE = "/api/v1/auth"


def _patch_kakao(social_id: str, email: str | None = None, nickname: str | None = None):
    """카카오 HTTP 경계(exchange_code/fetch_profile)를 대체해 실제 호출 없이 프로필을 주입한다."""
    return mock.patch.multiple(
        "app.services.auth.KakaoOAuthService",
        exchange_code=mock.AsyncMock(return_value="fake-kakao-token"),
        fetch_profile=mock.AsyncMock(return_value=KakaoProfile(social_id=social_id, email=email, nickname=nickname)),
    )


def _signup_payload(ticket: str, **overrides) -> dict:
    payload = {
        "signup_ticket": ticket,
        "email": "kakao_user@example.com",
        "name": "카카오테스터",
        "nickname": "카카오테스",
        "gender": "MALE",
        "birth_date": "1990-01-01",
        "phone_number": "01033334444",
        "terms_agreed": True,
        "privacy_agreed": True,
    }
    payload.update(overrides)
    return payload


class TestKakaoOAuthAPI(TestCase):
    async def test_authorize_url_returns_url_and_state(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(f"{BASE}/kakao/authorize-url")
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert "authorize_url" in body
        assert body["state"] in body["authorize_url"]

    async def test_callback_new_user_returns_signup_required(self):
        state = generate_oauth_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900001", email="new@kakao.com", nickname="신규"):
                res = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["status"] == "signup_required"
        assert body["signup_ticket"]
        assert body["prefill"]["email"] == "new@kakao.com"

    async def test_callback_invalid_state_returns_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900002"):
                res = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": "tampered.sig"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_signup_with_valid_ticket_creates_account(self):
        state = generate_oauth_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900003", email="s3@kakao.com", nickname="삼번"):
                cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
            ticket = cb.json()["signup_ticket"]
            res = await client.post(f"{BASE}/kakao/signup", json=_signup_payload(ticket))

        assert res.status_code == status.HTTP_201_CREATED
        assert "access_token" in res.json()
        assert any("refresh_token" in h for h in res.headers.get_list("set-cookie"))

    async def test_existing_social_user_logs_in(self):
        state = generate_oauth_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 최초 가입
            with _patch_kakao(social_id="900004", email="s4@kakao.com", nickname="사번"):
                cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
            ticket = cb.json()["signup_ticket"]
            await client.post(
                f"{BASE}/kakao/signup",
                json=_signup_payload(ticket, email="s4@kakao.com", nickname="사번", phone_number="01055556666"),
            )
            # 동일 social_id 재방문 → 로그인 분기
            with _patch_kakao(social_id="900004", email="s4@kakao.com", nickname="사번"):
                res = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode2", "state": generate_oauth_state()}
                )

        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["status"] == "login"
        assert body["access_token"]
        assert any("refresh_token" in h for h in res.headers.get_list("set-cookie"))

    async def test_signup_with_invalid_ticket_returns_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(f"{BASE}/kakao/signup", json=_signup_payload("not-a-valid-jwt"))
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_signup_with_wrong_type_ticket_returns_401(self):
        # access 토큰처럼 type 이 다른 토큰은 가입 티켓으로 거부되어야 한다.
        bogus = token_backend.encode({"type": "access", "social_id": "900005"})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(f"{BASE}/kakao/signup", json=_signup_payload(bogus))
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_signup_duplicate_email_returns_409(self):
        state = generate_oauth_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 기존 로컬 계정 선점
            await client.post(
                f"{BASE}/signup",
                json={
                    "email": "taken@example.com",
                    "password": "Password123!",
                    "name": "기존",
                    "nickname": "기존유저",
                    "gender": "FEMALE",
                    "birth_date": "1992-02-02",
                    "phone_number": "01077778888",
                },
            )
            with _patch_kakao(social_id="900006", email="taken@example.com", nickname="중복"):
                cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
            ticket = cb.json()["signup_ticket"]
            res = await client.post(
                f"{BASE}/kakao/signup",
                json=_signup_payload(ticket, email="taken@example.com", nickname="다른닉", phone_number="01099990000"),
            )
        assert res.status_code == status.HTTP_409_CONFLICT
