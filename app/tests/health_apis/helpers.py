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
) -> str:
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "name": name,
            "gender": gender,
            "birth_date": birth_date,
            "phone_number": phone_number,
        },
    )
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)
