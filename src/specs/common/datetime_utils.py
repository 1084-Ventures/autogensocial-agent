from datetime import datetime
from typing import Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(dt_str, ISO_FORMAT)
    except Exception:
        return None

def format_iso_datetime(dt: datetime) -> str:
    return dt.strftime(ISO_FORMAT)
