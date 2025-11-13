"""Date-time helpers for month bucket calculations."""

from datetime import date, datetime, timezone


def month_bucket(now: datetime | None = None) -> date:
    """Return the first day of the month for the provided timestamp (UTC)."""

    current = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    return date(current.year, current.month, 1)


def previous_month_bucket(bucket: date) -> date:
    """Return the first day of the month preceding the supplied bucket."""

    year = bucket.year
    month = bucket.month - 1
    if month == 0:
        year -= 1
        month = 12
    return date(year, month, 1)
