from __future__ import annotations

from uuid import UUID

from app.models.support import FAQ, FAQCategory, Inquiry, InquiryAnswer, InquiryCategory


class FAQRepository:
    async def list_faqs(self, category: FAQCategory | None = None) -> list[FAQ]:
        qs = FAQ.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return list(await qs.order_by("order", "id"))


class InquiryRepository:
    async def list_inquiries(self, user_id: UUID) -> list[Inquiry]:
        return list(await Inquiry.filter(user_id=user_id).order_by("-created_at"))

    async def get_inquiry(self, inquiry_id: int) -> Inquiry | None:
        return await Inquiry.get_or_none(id=inquiry_id)

    async def get_answer(self, inquiry_id: int) -> InquiryAnswer | None:
        return await InquiryAnswer.get_or_none(inquiry_id=inquiry_id)

    async def create_inquiry(
        self,
        user_id: UUID,
        title: str,
        content: str,
        category: InquiryCategory,
        attachment_url: str | None,
    ) -> Inquiry:
        return await Inquiry.create(
            user_id=user_id,
            title=title,
            content=content,
            category=category,
            attachment_url=attachment_url,
        )

    async def update_inquiry(self, inquiry: Inquiry, title: str | None, content: str | None) -> Inquiry:
        if title is not None:
            inquiry.title = title
        if content is not None:
            inquiry.content = content
        await inquiry.save()
        return inquiry

    async def delete_inquiry(self, inquiry: Inquiry) -> None:
        await inquiry.delete()
