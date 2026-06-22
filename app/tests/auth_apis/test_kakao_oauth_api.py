from datetime import datetime, timedelta
from unittest import mock

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.core.jwt.state import token_backend
from app.core.utils.security import generate_oauth_state, register_oauth_state
from app.main import app
from app.models.users import User
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


async def _signup_kakao_user(client: AsyncClient, social_id: str, **overrides) -> str:
    """카카오 신규 가입을 끝내고 social_id 를 반환하는 헬퍼(테스트 픽스처용)."""
    # email 은 카카오 프로필(_patch_kakao) 주입용일 뿐, 가입 요청 바디엔 들어가지 않는다(소셜=이메일 미수집).
    email = overrides.pop("email", None)
    with _patch_kakao(social_id=social_id, email=email, nickname=overrides.get("nickname")):
        cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()})
    ticket = cb.json()["signup_ticket"]
    await client.post(f"{BASE}/kakao/signup", json=_signup_payload(ticket, **overrides))
    return social_id


async def _fresh_state() -> str:
    """authorize-url 처럼 state 를 발급+Redis 등록한다(콜백의 단일사용 소비 검증 통과용)."""
    state = generate_oauth_state()
    await register_oauth_state(state)
    return state


async def _soft_delete(social_id: str, *, deleted_at: datetime | None = None) -> None:
    """가입된 카카오 계정을 탈퇴(soft delete) 상태로 만든다."""
    user = await User.get(social_provider="kakao", social_id=social_id)
    user.is_deleted = True
    user.is_active = False
    user.deleted_at = deleted_at or datetime.now(config.TIMEZONE)
    await user.save()


class TestKakaoOAuthAPI(TestCase):
    async def test_authorize_url_returns_url_and_state(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(f"{BASE}/kakao/authorize-url")
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert "authorize_url" in body
        assert body["state"] in body["authorize_url"]
        assert "prompt=login" in body["authorize_url"]  # 매 로그인 재인증 강제

    async def test_callback_new_user_returns_signup_required(self):
        state = await _fresh_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900001", email="new@kakao.com", nickname="신규"):
                res = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["status"] == "signup_required"
        assert body["signup_ticket"]
        # 소셜 계정은 이메일 미수집 → prefill 은 닉네임만.
        assert body["prefill"]["nickname"] == "신규"

    async def test_callback_invalid_state_returns_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900002"):
                res = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": "tampered.sig"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_signup_with_valid_ticket_creates_account(self):
        state = await _fresh_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="900003", email="s3@kakao.com", nickname="삼번"):
                cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
            ticket = cb.json()["signup_ticket"]
            res = await client.post(f"{BASE}/kakao/signup", json=_signup_payload(ticket))

        assert res.status_code == status.HTTP_201_CREATED
        assert "access_token" in res.json()
        assert any("refresh_token" in h for h in res.headers.get_list("set-cookie"))
        # 소셜 계정은 이메일을 수집/저장하지 않는다.
        created = await User.get(social_provider="kakao", social_id="900003")
        assert created.email is None

    async def test_existing_social_user_logs_in(self):
        state = await _fresh_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 최초 가입
            with _patch_kakao(social_id="900004", email="s4@kakao.com", nickname="사번"):
                cb = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
            ticket = cb.json()["signup_ticket"]
            await client.post(
                f"{BASE}/kakao/signup",
                json=_signup_payload(ticket, nickname="사번", phone_number="01055556666"),
            )
            # 동일 social_id 재방문 → 로그인 분기
            with _patch_kakao(social_id="900004", email="s4@kakao.com", nickname="사번"):
                res = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode2", "state": await _fresh_state()}
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

    async def test_callback_deleted_user_returns_restore_required(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await _signup_kakao_user(
                client, "910001", email="d1@kakao.com", nickname="탈퇴일", phone_number="01010001000"
            )
            await _soft_delete("910001")
            with _patch_kakao(social_id="910001", email="d1@kakao.com", nickname="탈퇴일"):
                res = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["status"] == "restore_required"
        assert body["restore_ticket"]
        # 소셜 계정은 이메일이 없어 masked_email 은 None. 복구 안내엔 탈퇴일·복구마감만 필요.
        assert body["masked_email"] is None
        assert body["deleted_at"] and body["restore_deadline"]

    async def test_kakao_restore_restores_and_logs_in(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await _signup_kakao_user(
                client, "910002", email="d2@kakao.com", nickname="복구이", phone_number="01010002000"
            )
            await _soft_delete("910002")
            with _patch_kakao(social_id="910002", email="d2@kakao.com", nickname="복구이"):
                cb = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
            ticket = cb.json()["restore_ticket"]
            res = await client.post(f"{BASE}/kakao/restore", json={"restore_ticket": ticket})

        assert res.status_code == status.HTTP_200_OK
        assert res.json()["access_token"]
        assert any("refresh_token" in h for h in res.headers.get_list("set-cookie"))
        user = await User.get(social_provider="kakao", social_id="910002")
        assert user.is_deleted is False and user.deleted_at is None

    async def test_kakao_destroy_hard_deletes_and_allows_resignup(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await _signup_kakao_user(
                client, "910003", email="d3@kakao.com", nickname="파기삼", phone_number="01010003000"
            )
            await _soft_delete("910003")
            with _patch_kakao(social_id="910003", email="d3@kakao.com", nickname="파기삼"):
                cb = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
            ticket = cb.json()["restore_ticket"]
            res = await client.post(f"{BASE}/kakao/destroy", json={"restore_ticket": ticket})
            assert res.status_code == status.HTTP_200_OK
            assert await User.filter(social_provider="kakao", social_id="910003").count() == 0
            # 파기 후 동일 social_id 재방문 → 신규 가입 분기
            with _patch_kakao(social_id="910003", email="d3@kakao.com", nickname="파기삼"):
                again = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
        assert again.json()["status"] == "signup_required"

    async def test_kakao_restore_after_retention_window_returns_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await _signup_kakao_user(
                client, "910004", email="d4@kakao.com", nickname="만료사", phone_number="01010004000"
            )
            # 보관 기간(30일) 경과한 탈퇴 — 복구 불가
            await _soft_delete("910004", deleted_at=datetime.now(config.TIMEZONE) - timedelta(days=31))
            with _patch_kakao(social_id="910004", email="d4@kakao.com", nickname="만료사"):
                cb = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
            ticket = cb.json()["restore_ticket"]
            res = await client.post(f"{BASE}/kakao/restore", json={"restore_ticket": ticket})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_kakao_restore_invalid_ticket_returns_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(f"{BASE}/kakao/restore", json={"restore_ticket": "not-a-valid-jwt"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_callback_banned_user_returns_403(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await _signup_kakao_user(
                client, "910005", email="b5@kakao.com", nickname="정지오", phone_number="01010005000"
            )
            user = await User.get(social_provider="kakao", social_id="910005")
            user.is_banned = True
            await user.save()
            # 정지 계정은 인가 거부 → 403(앱 전반·복구/파기와 동일 컨벤션)
            with _patch_kakao(social_id="910005", email="b5@kakao.com", nickname="정지오"):
                res = await client.post(
                    f"{BASE}/kakao/callback", json={"code": "authcode", "state": await _fresh_state()}
                )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    async def test_callback_state_replay_returns_400(self):
        # 동일 state 재사용(replay)은 단일사용 소비로 두 번째에 차단되어야 한다.
        state = await _fresh_state()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with _patch_kakao(social_id="910007", email="r7@kakao.com", nickname="리플세븐"):
                first = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
                second = await client.post(f"{BASE}/kakao/callback", json={"code": "authcode", "state": state})
        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_400_BAD_REQUEST
