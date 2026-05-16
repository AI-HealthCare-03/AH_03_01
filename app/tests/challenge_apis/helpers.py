from datetime import date, timedelta

from app.tests.health_apis.helpers import make_client, signup_and_login


def today() -> date:
    return date.today()


def future_range(days: int = 7) -> tuple[str, str]:
    start = today()
    end = start + timedelta(days=days)
    return start.isoformat(), end.isoformat()


__all__ = ["make_client", "signup_and_login", "today", "future_range"]
