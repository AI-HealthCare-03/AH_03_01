from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """아이템 카테고리 확장(동물/식물 전용 소모품) 및 시드 데이터 삽입.

    - items.species_lock : 사용 가능한 펫 종(DOG/CAT/PLANT). NULL 이면 모든 종 사용 가능.

    ItemCategory enum 값 추가(DECORATION, FOOD_ANIMAL, FOOD_ANIMAL_PREMIUM,
    SNACK_ANIMAL, FERTILIZER_PLANT, FERTILIZER_PLANT_PREMIUM, SUPPLEMENT_PLANT, WATER)는
    items.category 가 VARCHAR 컬럼이므로 DB 스키마 변경 없음 — 코드 측에서만 반영.
    """
    return """
        ALTER TABLE "items" ALTER COLUMN "category" TYPE VARCHAR(40);
        ALTER TABLE "items" ADD COLUMN "species_lock" VARCHAR(10);

        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at) VALUES
          ('FOOD_ANIMAL', '기본 사료(강아지)', '강아지가 좋아하는 일반 사료', 30, '{}'::jsonb, TRUE, 'DOG', NOW(), NOW()),
          ('FOOD_ANIMAL', '기본 사료(고양이)', '고양이가 좋아하는 일반 사료', 30, '{}'::jsonb, TRUE, 'CAT', NOW(), NOW()),
          ('FOOD_ANIMAL_PREMIUM', '프리미엄 사료(강아지)', '영양 듬뿍 고급 사료', 80, '{}'::jsonb, TRUE, 'DOG', NOW(), NOW()),
          ('FOOD_ANIMAL_PREMIUM', '프리미엄 사료(고양이)', '영양 듬뿍 고급 사료', 80, '{}'::jsonb, TRUE, 'CAT', NOW(), NOW()),
          ('SNACK_ANIMAL', '강아지 간식', '쫄깃한 강아지 간식', 20, '{}'::jsonb, TRUE, 'DOG', NOW(), NOW()),
          ('SNACK_ANIMAL', '고양이 간식', '바삭한 고양이 간식', 20, '{}'::jsonb, TRUE, 'CAT', NOW(), NOW()),
          ('FERTILIZER_PLANT', '일반 비료', '식물 성장용 일반 비료', 30, '{}'::jsonb, TRUE, 'PLANT', NOW(), NOW()),
          ('FERTILIZER_PLANT_PREMIUM', '프리미엄 비료', '식물 성장용 고급 비료', 80, '{}'::jsonb, TRUE, 'PLANT', NOW(), NOW()),
          ('SUPPLEMENT_PLANT', '식물 영양제', '식물 회복용 영양제', 40, '{}'::jsonb, TRUE, 'PLANT', NOW(), NOW()),
          ('WATER', '맑은 물', '모든 펫에게 사용 가능', 10, '{}'::jsonb, TRUE, NULL, NOW(), NOW());
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "items" WHERE category IN ('FOOD_ANIMAL','FOOD_ANIMAL_PREMIUM','SNACK_ANIMAL','FERTILIZER_PLANT','FERTILIZER_PLANT_PREMIUM','SUPPLEMENT_PLANT','WATER');
        ALTER TABLE "items" DROP COLUMN "species_lock";
        ALTER TABLE "items" ALTER COLUMN "category" TYPE VARCHAR(10);
    """
