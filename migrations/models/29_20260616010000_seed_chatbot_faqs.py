from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """chatbot_faqs 시드 데이터 10건 삽입 (고객센터 FAQ 화면과 동일한 질문/답변).

    챗봇 FAQ 칩 UI에서 표시할 기본 데이터. category/short_label 포함.
    """
    return """
        INSERT INTO "chatbot_faqs" (category, question, answer, short_label, sort_order, is_active, created_at, updated_at) VALUES
          ('ACCOUNT', '비밀번호를 잊어버렸어요. 어떻게 재설정하나요?', '로그인 화면에서 비밀번호 찾기를 눌러 이메일을 입력하시면 재설정 링크를 보내드립니다.', '비밀번호 재설정', 1, TRUE, NOW(), NOW()),
          ('ACCOUNT', '닉네임은 어떻게 변경하나요?', '마이페이지 > 프로필 편집에서 닉네임을 변경할 수 있습니다. 닉네임은 2~15자 이내로 설정 가능합니다.', '닉네임 변경', 2, TRUE, NOW(), NOW()),
          ('ACCOUNT', '회원 탈퇴는 어떻게 하나요?', '마이페이지 > 설정 > 회원 탈퇴에서 진행할 수 있습니다. 탈퇴 시 모든 데이터는 30일 후 영구 삭제되며 복구가 불가능합니다.', '회원 탈퇴', 3, TRUE, NOW(), NOW()),
          ('CHALLENGE', '챌린지 인증이 거부됐어요. 왜 그런가요?', '인증 사진이 챌린지 조건에 맞지 않거나 이미지가 불명확한 경우 거부될 수 있습니다. 가이드라인을 확인하고 명확한 사진으로 재시도해 주세요.', '챌린지 인증거부', 1, TRUE, NOW(), NOW()),
          ('CHALLENGE', '챌린지는 하루에 몇 번 인증할 수 있나요?', '챌린지는 하루에 1회 인증할 수 있습니다. 인증은 매일 자정에 초기화됩니다.', '하루 인증 횟수', 2, TRUE, NOW(), NOW()),
          ('CHALLENGE', '챌린지 중도 포기가 가능한가요?', '챌린지 상세 페이지에서 중도 포기가 가능합니다. 단, 추가 보상은 지급되지 않습니다.', '챌린지 중도포기', 3, TRUE, NOW(), NOW()),
          ('DISEASE', '혈압/혈당 기록을 수정하고 싶어요.', '건강 기록 페이지에서 수정하려는 기록을 선택한 후 편집할 수 있습니다.', '혈압/혈당 수정', 1, TRUE, NOW(), NOW()),
          ('DISEASE', '건강 리포트는 얼마나 자주 업데이트되나요?', '새로운 건강 데이터를 입력할 때마다 자동으로 업데이트됩니다. 주간 리포트는 매주 월요일에 생성됩니다.', '건강 리포트', 2, TRUE, NOW(), NOW()),
          ('SERVICE', '포인트 내역은 어디서 확인하나요?', '마이페이지 > 포인트 내역에서 적립 및 사용 내역을 확인할 수 있습니다.', '포인트 내역', 1, TRUE, NOW(), NOW()),
          ('SERVICE', '상점에서 구매한 아이템을 환불할 수 있나요?', '포인트로 구매한 아이템은 환불이 불가능합니다. 구매 전 신중하게 결정해 주세요.', '아이템 환불', 2, TRUE, NOW(), NOW());
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "chatbot_faqs" WHERE short_label IN (
          '비밀번호 재설정', '닉네임 변경', '회원 탈퇴',
          '챌린지 인증거부', '하루 인증 횟수', '챌린지 중도포기',
          '혈압/혈당 수정', '건강 리포트',
          '포인트 내역', '아이템 환불'
        );
    """
