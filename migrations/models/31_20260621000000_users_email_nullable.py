from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """users.email 을 NULL 허용으로 변경.

    소셜(카카오) 계정은 이메일을 수집하지 않으므로(카카오가 본인인증 대행) email 이 NULL 일 수 있다.
    기존 일반 가입 계정의 email 값은 그대로 유지된다(데이터 무손실).
    """
    return """
        ALTER TABLE "users" ALTER COLUMN "email" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    """롤백: NULL email 행이 없을 때만 NOT NULL 복원이 가능하다.

    소셜 계정(email NULL)이 이미 생성됐다면 이 다운그레이드는 실패한다 — 의도된 동작.
    """
    return """
        ALTER TABLE "users" ALTER COLUMN "email" SET NOT NULL;
    """
