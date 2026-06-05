import asyncio
import smtplib
from email.message import EmailMessage

from app.core import config, default_logger


def _smtp_configured() -> bool:
    """SMTP 자격증명이 채워져 있는지 여부. 비어 있으면 콘솔(로그) 모드."""
    return bool(config.SMTP_HOST and config.SMTP_USER)


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    """blocking smtplib 발송. asyncio.to_thread 로 감싸 호출한다.

    포트 465 는 implicit TLS(SMTP_SSL), 그 외(587 등)는 STARTTLS 로 자동 분기한다.
    """
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM or config.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if config.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_TIMEOUT) as server:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)


async def send_email(to_email: str, subject: str, body: str) -> None:
    """이메일 발송.

    SMTP 자격증명이 설정돼 있으면 실제 발송하고, 없으면(개발 단계) 본문을 로그로 출력한다.
    blocking smtplib 호출은 asyncio.to_thread 로 이벤트 루프 밖에서 실행한다.
    발송 실패 시 예외를 그대로 전파해 호출 측에서 사용자에게 안내할 수 있게 한다.
    """
    if not _smtp_configured():
        default_logger.info("[EMAIL:console] To=%s | Subject=%s\n%s", to_email, subject, body)
        return

    try:
        await asyncio.to_thread(_send_smtp, to_email, subject, body)
        default_logger.info("[EMAIL:sent] To=%s | Subject=%s", to_email, subject)
    except Exception:
        default_logger.exception("[EMAIL:failed] To=%s | Subject=%s", to_email, subject)
        raise
