"""Value-only answers. A sentence is not a value, and a value in prose form is graded wrong."""

from __future__ import annotations

import re

MAX_VALUE_CHARS = 64
MAX_VALUE_WORDS = 6
PROSE = re.compile(
    r"(?i)^(i\s|i'm\b|sorry\b|unknown\b|none\b|n/?a\b|not\s+(found|available|stated|specified|given)\b|no\s+(answer|information|data)\b"
    r"|cannot\b|can't\b|unable\b|the\s+answer\b|it\s+is\b|answer\s*:|there\s+is\b)"
)
# Graders normalise these away per the Match 3 kit. Longest alternatives first.
UNIT = (
    r"(?:°\s*[CFK]|º\s*[CF]|degrees?(?:\s+(?:celsius|fahrenheit|c|f))?|deg\s*[CF]?|celsius|fahrenheit|[CFK]"
    r"|seconds?|secs?|s|milliseconds?|ms|microseconds?|us|nanoseconds?|ns|minutes?|mins?|hours?|hrs?|h|days?|weeks?|months?|years?"
    r"|kW|mW|W|kV|mV|V|mA|A|kHz|MHz|GHz|Hz|KiB|MiB|GiB|TiB|KB|MB|GB|TB|B|kbps|Mbps|Gbps|bytes?|bits?"
    r"|kg|mg|g|mm|cm|km|m|%|percent)"
)
NUMBER_WITH_UNIT = re.compile(rf"^([-+]?\d[\d,]*(?:\.\d+)?)\s*{UNIT}$")


def clean_value(value: object, strip_units: bool = True) -> str | None:
    """The value to write, or None when this is prose or empty and must not be written."""
    if not isinstance(value, str):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        value = str(value)
    text = re.sub(r"\s+", " ", value).strip().strip("\"'`“”‘’").strip()
    text = text.rstrip(".;,:").strip()
    if not text or len(text) > MAX_VALUE_CHARS or len(text.split()) > MAX_VALUE_WORDS or PROSE.search(text):
        return None
    if strip_units:
        match = NUMBER_WITH_UNIT.match(text)
        if match:
            return match.group(1)
    return text


def same_value(left: str, right: str) -> bool:
    return comparison_key(left) == comparison_key(right)


def comparison_key(value: str) -> str:
    """Spacing, case and thousands separators do not make two values different."""
    text = clean_value(value) or value
    return re.sub(r"[\s,]+", "", text).casefold()
