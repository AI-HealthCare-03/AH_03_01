from httpx import ASGITransport, AsyncClient

from app.main import app

BASE_URL = "http://test"


async def signup_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "Password123!",
    name: str = "건강이",
    gender: str = "MALE",
    birth_date: str = "1990-01-01",
    phone_number: str = "01000000000",
    nickname: str | None = None,
) -> str:
    # User.nickname 은 unique 라 테스트마다 다른 값이어야 함. 명시 안 하면 email local-part 의
    # 앞 10자(영문/숫자만 추출 + min_length=2 보장)로 자동 생성.
    if nickname is None:
        local = "".join(ch for ch in email.split("@")[0] if ch.isalnum())[:10]
        nickname = (local or "user") + ("x" if len(local) < 2 else "")
        nickname = nickname[:10]
    signup_payload = {
        "email": email,
        "password": password,
        "name": name,
        "nickname": nickname,
        "gender": gender,
        "birth_date": birth_date,
        "phone_number": phone_number,
    }
    signup_res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_res.status_code in (201, 409), f"signup failed: {signup_res.status_code} {signup_res.json()}"
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    body = login_res.json()
    assert login_res.status_code == 200, f"login failed: {login_res.status_code} {body}"
    assert "access_token" in body, f"login body missing access_token: {body}"
    return body["access_token"]


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)
