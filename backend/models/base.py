from datetime import UTC, datetime

from sqlalchemy import Numeric

from backend.database import Base


MONEY_COLUMN = Numeric(12, 2)
PERCENT_COLUMN = Numeric(5, 2)
RATIO_COLUMN = Numeric(8, 4)


def utc_now():
    return datetime.now(UTC)


def decimal_to_float(value):
    if value is None:
        return None
    return float(value)
