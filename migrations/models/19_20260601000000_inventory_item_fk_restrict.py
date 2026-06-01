from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """inventories.item_id FK 를 ON DELETE CASCADE → RESTRICT.

    아이템(items) 삭제 시 보유 인벤토리가 함께 CASCADE 삭제되어 유저 구매 자산이
    사라지는 것을 DB 차원에서 차단한다. 아이템 은퇴는 삭제가 아니라 is_active=FALSE
    로만 처리해야 한다. (FK 인라인 자동명: inventories_item_id_fkey)
    """
    return """
        ALTER TABLE "inventories" DROP CONSTRAINT IF EXISTS "inventories_item_id_fkey";
        ALTER TABLE "inventories" ADD CONSTRAINT "inventories_item_id_fkey"
            FOREIGN KEY ("item_id") REFERENCES "items" ("id") ON DELETE RESTRICT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "inventories" DROP CONSTRAINT IF EXISTS "inventories_item_id_fkey";
        ALTER TABLE "inventories" ADD CONSTRAINT "inventories_item_id_fkey"
            FOREIGN KEY ("item_id") REFERENCES "items" ("id") ON DELETE CASCADE;
    """
