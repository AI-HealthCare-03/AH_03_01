from starlette import status
from tortoise.contrib.test import TestCase

from app.models.pet import Item, ItemCategory, PointSource
from app.tests.health_apis.helpers import make_client, signup_and_login


class TestPetApi(TestCase):
    async def test_create_and_get_pet(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_create@example.com", phone_number="01070000001")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post(
                "/api/v1/pets",
                headers=headers,
                json={"name": "멍이", "pet_type": "DOG"},
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["name"] == "멍이"
            assert body["level"] == 1
            assert body["current_xp"] == 0

            get_res = await client.get("/api/v1/pets/me", headers=headers)
            assert get_res.status_code == status.HTTP_200_OK
            assert get_res.json()["name"] == "멍이"
            assert get_res.json()["xp_to_next_level"] == 100

    async def test_create_pet_duplicate_conflict(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_dup@example.com", phone_number="01070000002")
            headers = {"Authorization": f"Bearer {token}"}
            first = await client.post("/api/v1/pets", headers=headers, json={"name": "멍이"})
            assert first.status_code == status.HTTP_201_CREATED
            second = await client.post("/api/v1/pets", headers=headers, json={"name": "멍이2"})
            assert second.status_code == status.HTTP_409_CONFLICT

    async def test_update_pet_name(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_upd@example.com", phone_number="01070000003")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post("/api/v1/pets", headers=headers, json={"name": "초기"})
            res = await client.patch("/api/v1/pets/me", headers=headers, json={"name": "변경"})
            assert res.status_code == status.HTTP_200_OK
            assert res.json()["name"] == "변경"

    async def test_get_pet_404_when_none(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_none@example.com", phone_number="01070000004")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get("/api/v1/pets/me", headers=headers)
            assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_interaction_requires_points(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_int@example.com", phone_number="01070000005")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post("/api/v1/pets", headers=headers, json={"name": "멍이"})

            # 포인트가 없는 상태에서 상호작용 → 409
            res = await client.post(
                "/api/v1/pets/me/interactions",
                headers=headers,
                json={"type": "FEED"},
            )
            assert res.status_code == status.HTTP_409_CONFLICT


class TestStoreAndInventoryApi(TestCase):
    async def _seed_item(self, **kwargs: object) -> Item:
        defaults: dict[str, object] = {
            "category": ItemCategory.BACKGROUND,
            "name": "기본 배경",
            "price": 100,
            "item_metadata": {},
            "is_active": True,
        }
        defaults.update(kwargs)
        return await Item.create(**defaults)  # type: ignore[arg-type]

    async def _seed_balance(self, user_id: int, amount: int):
        # 테스트용으로 PointTransaction 직접 적립
        from app.models.pet import PointTransaction, PointTransactionType

        await PointTransaction.create(
            user_id=user_id,
            type=PointTransactionType.EARN,
            amount=amount,
            balance_after=amount,
            source=PointSource.ETC,
            description="테스트 시드",
        )

    async def test_store_list_and_purchase_flow(self):
        item = await self._seed_item(name="고급 배경", price=100)
        async with make_client() as client:
            token = await signup_and_login(client, email="store_buy@example.com", phone_number="01080000001")
            headers = {"Authorization": f"Bearer {token}"}

            me_res = await client.get("/api/v1/users/me", headers=headers)
            uid = me_res.json()["id"]
            await self._seed_balance(uid, 500)

            list_res = await client.get("/api/v1/store/items?category=BACKGROUND", headers=headers)
            assert list_res.status_code == status.HTTP_200_OK
            assert any(i["name"] == "고급 배경" for i in list_res.json()["items"])

            purchase = await client.post(
                "/api/v1/store/purchases",
                headers=headers,
                json={"item_id": item.id, "quantity": 2},
            )
            assert purchase.status_code == status.HTTP_201_CREATED
            body = purchase.json()
            assert body["point_spent"] == 200
            assert body["point_balance"] == 300

            inv = await client.get("/api/v1/inventory", headers=headers)
            assert inv.status_code == status.HTTP_200_OK
            assert inv.json()["items"][0]["quantity"] == 2

    async def test_purchase_insufficient_balance(self):
        item = await self._seed_item(price=1000, name="비싼 가구", category=ItemCategory.FURNITURE)
        async with make_client() as client:
            token = await signup_and_login(client, email="store_low@example.com", phone_number="01080000002")
            headers = {"Authorization": f"Bearer {token}"}
            purchase = await client.post(
                "/api/v1/store/purchases",
                headers=headers,
                json={"item_id": item.id},
            )
            assert purchase.status_code == status.HTTP_409_CONFLICT
