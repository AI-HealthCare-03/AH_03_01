import asyncio
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)
_fcm_initialized = False


def _init_firebase() -> bool:
    global _fcm_initialized
    if _fcm_initialized:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials

        from app.core import config

        cred_path = Path(config.FIREBASE_CREDENTIALS_PATH)
        if not cred_path.exists():
            _logger.warning("Firebase 서비스 계정 파일 없음: %s — FCM 비활성화", cred_path)
            return False
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
        _fcm_initialized = True
        return True
    except Exception as e:  # noqa: BLE001
        _logger.warning("Firebase 초기화 실패: %s", e)
        return False


async def send_medication_push(fcm_token: str, medicine_name: str) -> None:
    if not _init_firebase():
        return
    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title="💊 복약 알림",
                body=f"{medicine_name} 복용 시간이에요!",
            ),
            token=fcm_token,
        )
        await asyncio.to_thread(messaging.send, message)
    except Exception as e:  # noqa: BLE001
        _logger.warning("FCM 발송 실패 (token=%.20s...): %s", fcm_token, e)
