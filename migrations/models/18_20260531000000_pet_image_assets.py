from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """펫 키우기 이미지 에셋 전환 (배경/가구/꾸미기/소비재 썸네일).

    - BACKGROUND: gradient → 이미지 키(main/sunset/star) 전환 + '바다'(beach) 추가
    - FURNITURE : emoji 3종 제거 → 이미지 소품 재시드(방석/인형/조명/화분/소파/그루터기/밥·물그릇)
    - DECORATION: emoji 3종 제거 → 리본/꽃(pet_skin 교체), 장난감 공(play), 나비(stage_top)
                  리본/꽃/공은 species_block=["PLANT"] 로 식물 잠금
    - 소비재    : 기존 사료/간식/비료/영양제/물/티켓 metadata 에 asset 썸네일 추가
    - MEDICINE  : '회복약' 신규 추가(상점 약 탭 비어 있던 항목 보강)
    """
    return """
        -- 맑은 하늘(main)은 프론트 기본 배경 → 상점 비노출(is_active=FALSE), 레코드는 유지
        UPDATE "items" SET item_metadata = '{"image":"main"}'::jsonb, is_active=FALSE WHERE category='BACKGROUND' AND name='맑은 하늘';
        UPDATE "items" SET item_metadata = '{"image":"sunset"}'::jsonb WHERE category='BACKGROUND' AND name='저녁 노을';
        UPDATE "items" SET item_metadata = '{"image":"star"}'::jsonb   WHERE category='BACKGROUND' AND name='별이 빛나는 밤';
        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at)
        SELECT 'BACKGROUND', '바다', '시원한 바닷가 무대', 150, '{"image":"beach"}'::jsonb, TRUE, NULL, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM "items" WHERE category='BACKGROUND' AND name='바다');

        DELETE FROM "items" WHERE category IN ('FURNITURE','DECORATION');
        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at) VALUES
          ('FURNITURE','폭신한 방석','잠자기 좋은 방석',50,'{"asset":"/pets/items/cushion_1.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','동그란 방석','아늑한 동그란 방석',50,'{"asset":"/pets/items/cushion_2.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','인형 세트','함께 노는 인형',70,'{"asset":"/pets/items/dolls.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','무드등','은은한 무드등',40,'{"asset":"/pets/items/light_1.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','꼬마전구','반짝이는 꼬마전구',40,'{"asset":"/pets/items/light_2.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','화분','싱그러운 화분',60,'{"asset":"/pets/items/plants_1.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','소파','푹신한 소파',120,'{"asset":"/pets/items/sofa_1.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','큰 소파','넉넉한 큰 소파',150,'{"asset":"/pets/items/sofa_2.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','나무 그루터기','앉아 쉬는 그루터기',60,'{"asset":"/pets/items/stump.png","placement":"stage_bottom"}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('FURNITURE','강아지 나무 밥그릇','나무 무늬 강아지 밥그릇',30,'{"asset":"/pets/items/bowl_food_dog_1.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','강아지 발바닥 밥그릇','발바닥 무늬 강아지 밥그릇',30,'{"asset":"/pets/items/bowl_food_dog_2.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','강아지 고급 밥그릇','고급 강아지 밥그릇',30,'{"asset":"/pets/items/bowl_food_dog_3.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','강아지 나무 물그릇','나무 무늬 강아지 물그릇',30,'{"asset":"/pets/items/bowl_water_dog_1.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','강아지 발바닥 물그릇','발바닥 무늬 강아지 물그릇',30,'{"asset":"/pets/items/bowl_water_dog_2.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','강아지 고급 물그릇','고급 강아지 물그릇',30,'{"asset":"/pets/items/bowl_water_dog_3.png","placement":"stage_bottom"}'::jsonb,TRUE,'DOG',NOW(),NOW()),
          ('FURNITURE','고양이 생선 밥그릇','생선 모양 고양이 밥그릇',30,'{"asset":"/pets/items/bowl_food_cat_1.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('FURNITURE','고양이 얼굴 밥그릇','고양이 얼굴 밥그릇',30,'{"asset":"/pets/items/bowl_food_cat_2.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('FURNITURE','고양이 고급 밥그릇','고급 고양이 밥그릇',30,'{"asset":"/pets/items/bowl_food_cat_3.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('FURNITURE','고양이 생선 물그릇','생선 모양 고양이 물그릇',30,'{"asset":"/pets/items/bowl_water_cat_1.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('FURNITURE','고양이 얼굴 물그릇','고양이 얼굴 물그릇',30,'{"asset":"/pets/items/bowl_water_cat_2.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('FURNITURE','고양이 고급 물그릇','고급 고양이 물그릇',30,'{"asset":"/pets/items/bowl_water_cat_3.png","placement":"stage_bottom"}'::jsonb,TRUE,'CAT',NOW(),NOW()),
          ('DECORATION','리본','펫에게 달아주는 귀여운 리본',30,'{"variant":"ribbon","asset":"/pets/items/ribbon.png","placement":"pet_skin","species_block":["PLANT"]}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('DECORATION','꽃','펫에게 달아주는 꽃 장식',20,'{"variant":"flower","asset":"/pets/items/flower.png","placement":"pet_skin","species_block":["PLANT"]}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('DECORATION','장난감 공','함께 가지고 노는 공',30,'{"variant":"ball","asset":"/pets/items/ball.png","placement":"play","species_block":["PLANT"]}'::jsonb,TRUE,NULL,NOW(),NOW()),
          ('DECORATION','나비','무대를 날아다니는 나비',25,'{"variant":"butterfly","asset":"/pets/items/butterfly_1.png","placement":"stage_top"}'::jsonb,TRUE,NULL,NOW(),NOW());

        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/food_dog.png"}'::jsonb         WHERE category='FOOD_ANIMAL' AND species_lock='DOG';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/food_cat.png"}'::jsonb         WHERE category='FOOD_ANIMAL' AND species_lock='CAT';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/food_dog_premium.png"}'::jsonb WHERE category='FOOD_ANIMAL_PREMIUM' AND species_lock='DOG';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/food_cat_premium.png"}'::jsonb WHERE category='FOOD_ANIMAL_PREMIUM' AND species_lock='CAT';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/snack_dog.png"}'::jsonb        WHERE category='SNACK_ANIMAL' AND species_lock='DOG';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/snack_cat.png"}'::jsonb        WHERE category='SNACK_ANIMAL' AND species_lock='CAT';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/fertilizer.png"}'::jsonb         WHERE category='FERTILIZER_PLANT';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/fertilizer_premium.png"}'::jsonb WHERE category='FERTILIZER_PLANT_PREMIUM';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/supplement_plant.png"}'::jsonb   WHERE category='SUPPLEMENT_PLANT';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/water.png"}'::jsonb              WHERE category='WATER';
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/ticket.png"}'::jsonb             WHERE category='TICKET';

        -- 회복약(MEDICINE)은 migration 11 에서 이미 시드됨 → asset 만 보강. 없을 때만 신규 추가.
        UPDATE "items" SET item_metadata = item_metadata || '{"asset":"/pets/items/medicine.png"}'::jsonb WHERE category='MEDICINE';
        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at)
        SELECT 'MEDICINE','회복약','아픈 펫을 회복시키는 약',80,'{"asset":"/pets/items/medicine.png"}'::jsonb,TRUE,NULL,NOW(),NOW()
        WHERE NOT EXISTS (SELECT 1 FROM "items" WHERE category='MEDICINE');
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "items" WHERE category IN ('FURNITURE','DECORATION');
        INSERT INTO "items" (category, name, description, price, item_metadata, is_active, species_lock, created_at, updated_at) VALUES
          ('FURNITURE', '주황 공', '가지고 노는 공', 30, '{"emoji":"🟠","slot":"left"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('FURNITURE', '폭신한 방석', '잠자기 좋은 방석', 50, '{"emoji":"🛏️","slot":"right"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('FURNITURE', '나무 그루터기', '앉아 쉬는 그루터기', 60, '{"emoji":"🪵","slot":"right"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '꽃 한 송이', '봄 분위기 꽃 장식', 20, '{"emoji":"🌸"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '리본 장식', '귀여운 핑크 리본', 30, '{"emoji":"🎀"}'::jsonb, TRUE, NULL, NOW(), NOW()),
          ('DECORATION', '나비', '날아드는 나비', 25, '{"emoji":"🦋"}'::jsonb, TRUE, NULL, NOW(), NOW());

        DELETE FROM "items" WHERE category='BACKGROUND' AND name='바다';
        UPDATE "items" SET item_metadata = item_metadata - 'asset' WHERE category='MEDICINE';

        UPDATE "items" SET item_metadata = '{"gradient":"linear-gradient(to bottom, #FFF6D6 0%, #FFE9A8 60%, #C8E6A0 60%, #A6D88B 100%)"}'::jsonb, is_active=TRUE WHERE category='BACKGROUND' AND name='맑은 하늘';
        UPDATE "items" SET item_metadata = '{"gradient":"linear-gradient(to bottom, #FFB07A 0%, #FF8A6A 35%, #7B5BA0 60%, #4D3B72 100%)"}'::jsonb WHERE category='BACKGROUND' AND name='저녁 노을';
        UPDATE "items" SET item_metadata = '{"gradient":"linear-gradient(to bottom, #0E1B3A 0%, #1A2E5A 50%, #243B6B 60%, #2E4878 100%)"}'::jsonb WHERE category='BACKGROUND' AND name='별이 빛나는 밤';

        UPDATE "items" SET item_metadata = item_metadata - 'asset'
          WHERE category IN ('FOOD_ANIMAL','FOOD_ANIMAL_PREMIUM','SNACK_ANIMAL','FERTILIZER_PLANT','FERTILIZER_PLANT_PREMIUM','SUPPLEMENT_PLANT','WATER','TICKET');
    """
