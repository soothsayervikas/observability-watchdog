from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return naive UTC datetime for consistent DB storage and comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)
