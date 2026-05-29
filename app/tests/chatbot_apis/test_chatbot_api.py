from starlette import status
from tortoise.contrib.test import TestCase

from app.models.chatbot import ChatbotFaq, FaqCategory
from app.tests.health_apis.helpers import make_client, signup_and_login


class TestChatbotFaqApi(TestCase):
    async def _seed_faqs(self):
        await ChatbotFaq.create(
            category=FaqCategory.SERVICE,
            question="물 마시기 인증법이 궁금해요",
            answer="사진 인증으로 물병을 찍어 올리면 됩니다.",
            sort_order=0,
        )
        await ChatbotFaq.create(
            category=FaqCategory.DISEASE,
            question="HbA1c 정상 수치는?",
            answer="정상은 5.7% 미만입니다.",
            sort_order=0,
        )

    async def test_list_faqs(self):
        await self._seed_faqs()
        async with make_client() as client:
            token = await signup_and_login(client, email="faq@example.com", phone_number="01000000301")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get("/api/v1/chat/faqs", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            assert len(res.json()["faqs"]) == 2

    async def test_list_faqs_with_category_filter(self):
        await self._seed_faqs()
        async with make_client() as client:
            token = await signup_and_login(client, email="faq_cat@example.com", phone_number="01000000302")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get("/api/v1/chat/faqs?category=DISEASE", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert len(body["faqs"]) == 1
            assert body["faqs"][0]["category"] == "DISEASE"

    async def test_list_faqs_with_keyword(self):
        await self._seed_faqs()
        async with make_client() as client:
            token = await signup_and_login(client, email="faq_kw@example.com", phone_number="01000000303")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get("/api/v1/chat/faqs?keyword=HbA1c", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            assert len(res.json()["faqs"]) == 1


class TestChatbotMessagesApi(TestCase):
    async def test_send_message_faq_mode_matches_faq(self):
        await ChatbotFaq.create(
            category=FaqCategory.SERVICE,
            question="HbA1c 정상 수치는?",
            answer="정상은 5.7% 미만입니다.",
            sort_order=0,
        )
        async with make_client() as client:
            token = await signup_and_login(client, email="msg_faq@example.com", phone_number="01000000401")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post(
                "/api/v1/chat/messages?mode=faq",
                headers=headers,
                json={"message": "HbA1c 알려줘"},
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["message_type"] == "FAQ"
            assert "5.7%" in body["answer"]
            assert body["confidence"] == 1.0

    async def test_send_message_rag_mode_returns_fallback(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="msg_rag@example.com", phone_number="01000000402")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post(
                "/api/v1/chat/messages?mode=rag",
                headers=headers,
                json={"message": "고혈압 위험도 줄이는 방법은?"},
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            # ChatRAGGraph 가 OPENAI_API_KEY 없는 환경(CI)에서 RuntimeError 를
            # 던지면 service 가 SYSTEM placeholder + fallback=True 로 흡수한다.
            # 사양 §6: fallback → SYSTEM 매핑 (app/services/chatbot.py 참고).
            assert body["message_type"] == "SYSTEM"
            assert body["confidence"] == 0.0
            assert body["model_version"] == "chatragraph-v1"
            assert body["is_fallback"] is True
            assert body["disclaimer"]

    async def test_message_creates_session_and_history(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="msg_hist@example.com", phone_number="01000000403")
            headers = {"Authorization": f"Bearer {token}"}
            first = await client.post(
                "/api/v1/chat/messages?mode=rag",
                headers=headers,
                json={"message": "안녕"},
            )
            sid = first.json()["conversation_id"]

            second = await client.post(
                "/api/v1/chat/messages?mode=rag",
                headers=headers,
                json={"message": "한 번 더", "conversation_id": sid},
            )
            assert second.json()["conversation_id"] == sid

            sessions = await client.get("/api/v1/chat/sessions", headers=headers)
            assert sessions.status_code == status.HTTP_200_OK
            assert len(sessions.json()["sessions"]) == 1
            assert sessions.json()["sessions"][0]["message_count"] == 4

            detail = await client.get(f"/api/v1/chat/sessions/{sid}", headers=headers)
            assert detail.status_code == status.HTTP_200_OK
            assert len(detail.json()["messages"]) == 4

    async def test_other_user_cannot_access_session(self):
        async with make_client() as client:
            token_a = await signup_and_login(client, email="msg_a@example.com", phone_number="01000000501")
            headers_a = {"Authorization": f"Bearer {token_a}"}
            first = await client.post(
                "/api/v1/chat/messages?mode=rag",
                headers=headers_a,
                json={"message": "비밀 대화"},
            )
            sid = first.json()["conversation_id"]

            token_b = await signup_and_login(
                client, email="msg_b@example.com", phone_number="01000000502", name="다른사람"
            )
            headers_b = {"Authorization": f"Bearer {token_b}"}
            res = await client.get(f"/api/v1/chat/sessions/{sid}", headers=headers_b)
            assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_unknown_mode_returns_400(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="msg_mode@example.com", phone_number="01000000601")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post(
                "/api/v1/chat/messages?mode=stream",
                headers=headers,
                json={"message": "test"},
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST
