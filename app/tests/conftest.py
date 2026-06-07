import asyncio
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest
from tortoise import generate_config
from tortoise.contrib.test import finalizer, initializer

from app.core import config
from app.core.db.databases import TORTOISE_APP_MODELS
from app.core.limiter import limiter
from app.services.email_verification import EmailVerificationService

TEST_BASE_URL = "http://test"
TEST_DB_LABEL = "models"
TEST_DB_TZ = "Asia/Seoul"


def get_test_db_config() -> dict[str, Any]:
    tortoise_config = generate_config(
        db_url=f"postgres://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/test",
        app_modules={TEST_DB_LABEL: TORTOISE_APP_MODELS},
        connection_label=TEST_DB_LABEL,
        testing=True,
    )
    tortoise_config["timezone"] = TEST_DB_TZ

    return tortoise_config


@pytest.fixture(scope="session", autouse=True)
def initialize(request: FixtureRequest) -> Generator[None, None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with patch("tortoise.contrib.test.getDBConfig", Mock(return_value=get_test_db_config())):
        initializer(modules=TORTOISE_APP_MODELS)
    yield
    finalizer()
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def disable_rate_limiter() -> Generator[None, None]:
    """테스트 중 인증 엔드포인트 레이트리밋 비활성화.

    한 IP(127.0.0.1)에서 로그인/가입을 반복 호출하므로 slowapi 제한(예 login 5/min)에
    걸려 429 가 난다. 레이트리밋 동작은 전용 테스트에서 검증하고, 일반 테스트에서는 끈다.
    """
    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original


@pytest_asyncio.fixture(autouse=True, scope="session")  # type: ignore[type-var]
def event_loop() -> None:
    pass


@pytest.fixture(autouse=True)
def bypass_email_verification() -> Generator[None, None]:
    """테스트에서는 회원가입 이메일 인증 게이트를 통과시킨다.

    실제 signup 은 EmailVerificationService.is_verified() 통과가 필요하지만(Redis 의존),
    대부분의 테스트는 가입을 사전조건으로만 쓰므로 인증을 True 로 우회한다.
    게이트 자체의 동작은 test_signup_email_verification_gate.py 에서 별도 검증.
    """
    with patch.object(EmailVerificationService, "is_verified", new=AsyncMock(return_value=True)):
        yield
