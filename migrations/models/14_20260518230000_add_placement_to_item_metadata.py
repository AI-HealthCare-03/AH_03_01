from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """장착 아이템 시각화를 위해 item_metadata 에 placement 키 추가.

    head         : 펫 머리 위 부착 (펫 따라 이동) — 꽃·리본
    paws         : 펫 발 앞 (펫 따라 이동) — 공
    stage_top    : 무대 우상단 고정 — 나비
    stage_bottom : 무대 안 자유 배치 (사용자 드래그) — 방석·그루터기

    프론트가 placement 값으로 분기해 무대에서 위치/추적을 결정한다.
    """
    return """
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"head"}'::jsonb         WHERE name = '꽃 한 송이';
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"head"}'::jsonb         WHERE name = '리본 장식';
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"stage_top"}'::jsonb    WHERE name = '나비';
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"paws"}'::jsonb         WHERE name = '주황 공';
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"stage_bottom"}'::jsonb WHERE name = '폭신한 방석';
        UPDATE "items" SET item_metadata = item_metadata || '{"placement":"stage_bottom"}'::jsonb WHERE name = '나무 그루터기';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "items" SET item_metadata = item_metadata - 'placement' WHERE name IN
            ('꽃 한 송이','리본 장식','나비','주황 공','폭신한 방석','나무 그루터기');
    """
