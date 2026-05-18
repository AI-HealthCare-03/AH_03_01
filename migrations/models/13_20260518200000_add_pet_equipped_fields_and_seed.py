from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """펫 장착 슬롯(배경/가구/꾸미기) 컬럼 + 시드 데이터 (백로그 10 잔여).

    - pets.equipped_background_id : 장착한 배경 아이템 id (BigInt, null)
    - pets.equipped_furniture_ids : 장착한 가구 id 배열 (JSONB)
    - pets.equipped_decoration_ids: 장착한 꾸미기 id 배열 (JSONB)

    시드: BACKGROUND 3종(맑은 하늘/저녁 노을/별이 빛나는 밤) +
          FURNITURE 3종(주황 공/방석/그루터기) +
          DECORATION 3종(꽃/리본/나비) +
          TICKET 1종(실패 방지권).
    """
    return """
        ALTER TABLE "pets" ADD COLUMN "equipped_background_id" BIGINT;
        ALTER TABLE "pets" ADD COLUMN "equipped_furniture_ids" JSONB NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE "pets" ADD COLUMN "equipped_decoration_ids" JSONB NOT NULL DEFAULT '[]'::jsonb;

        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at) VALUES
          ('BACKGROUND', '맑은 하늘', '기본 노을 잔디 무대', 0, '{"gradient":"linear-gradient(to bottom, #FFF6D6 0%, #FFE9A8 60%, #C8E6A0 60%, #A6D88B 100%)"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('BACKGROUND', '저녁 노을', '주황빛 하늘과 보랏빛 들판', 120, '{"gradient":"linear-gradient(to bottom, #FFB07A 0%, #FF8A6A 35%, #7B5BA0 60%, #4D3B72 100%)"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('BACKGROUND', '별이 빛나는 밤', '짙은 남색 밤하늘', 200, '{"gradient":"linear-gradient(to bottom, #0E1B3A 0%, #1A2E5A 50%, #243B6B 60%, #2E4878 100%)"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('FURNITURE', '주황 공', '가지고 노는 공', 30, '{"emoji":"🟠","slot":"left"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('FURNITURE', '폭신한 방석', '잠자기 좋은 방석', 50, '{"emoji":"🛏️","slot":"right"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('FURNITURE', '나무 그루터기', '앉아 쉬는 그루터기', 60, '{"emoji":"🪵","slot":"right"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '꽃 한 송이', '봄 분위기 꽃 장식', 20, '{"emoji":"🌸"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '리본 장식', '귀여운 핑크 리본', 30, '{"emoji":"🎀"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '나비', '날아드는 나비', 25, '{"emoji":"🦋"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('TICKET', '실패 방지권', '챌린지 인증 실패를 방지', 100, '{}'::jsonb, TRUE, NULL, NOW(), NOW());
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "items" WHERE category IN ('BACKGROUND','FURNITURE','DECORATION','TICKET');
        ALTER TABLE "pets" DROP COLUMN "equipped_decoration_ids";
        ALTER TABLE "pets" DROP COLUMN "equipped_furniture_ids";
        ALTER TABLE "pets" DROP COLUMN "equipped_background_id";
    """
