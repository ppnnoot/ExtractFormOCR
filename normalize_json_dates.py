import os
import json
import re
from datetime import datetime
from typing import Any, Tuple


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y%m%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


ISO_DT_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:\d{2})?)$"
)


def try_parse_date(text: str) -> datetime | None:
    """Try parsing a date string using multiple strategies."""
    t = text.strip()
    if not t:
        return None

    # Handle ISO date/time strings (keep date only)
    if ISO_DT_PATTERN.match(t):
        base_date = t[:10]
        try:
            return datetime.strptime(base_date, "%Y-%m-%d")
        except Exception:
            return None

    # Normalize common separators to '-' for patterns like YYYY/MM/DD or YYYY.MM.DD
    # But rely on formats list below.
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt)
        except Exception:
            continue

    # Heuristic for ambigious dd/mm/yyyy or mm/dd/yyyy with single digits
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", t)
    if m:
        first, second, year = map(int, m.groups())
        # If first > 12, treat as day/month
        # If second > 12, treat as month/day
        # If both <= 12, default to day/month (common in many locales like TH)
        day, month = (first, second) if (first > 12 or (first <= 12 and second <= 12)) else (second, first)
        try:
            return datetime(year, month, day)
        except Exception:
            return None

    # YYYYMMDD or YYYY-MM-DD without leading zeros
    m = re.match(r"^(\d{4})[-/]?(\d{1,2})[-/]?(\d{1,2})$", t)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return datetime(y, mo, d)
        except Exception:
            return None

    return None


EMPTY_STRINGS = {"", " ", "\t", "\n", "null", "none", "n/a", "N/A", "Null", "None"}


def transform_value(value: Any) -> Any:
    """Recursively transform values:
    - Strings that represent dates -> normalized 'YYYY-MM-DD'
    - Empty strings/None -> '-'
    - Lists/Dicts -> recurse into children
    """
    if value is None:
        return "-"

    if isinstance(value, str):
        if value.strip() in EMPTY_STRINGS:
            return "-"
        # Attempt to parse date
        dt = try_parse_date(value)
        if dt is not None:
            return dt.strftime("%Y-%m-%d")
        return value

    if isinstance(value, list):
        return [transform_value(v) for v in value]

    if isinstance(value, dict):
        return {k: transform_value(v) for k, v in value.items()}

    # Leave numbers/bools unchanged
    return value


def process_json_file(path: str) -> Tuple[bool, str]:
    """Process a single JSON file. Returns (changed, message)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            original_text = f.read()
        data = json.loads(original_text)
    except Exception as e:
        return False, f"ERROR reading '{path}': {e}"

    transformed = transform_value(data)

    # Compare serialized to determine change
    try:
        original_obj = json.loads(original_text)
    except Exception:
        original_obj = None

    changed = transformed != original_obj
    if changed:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(transformed, f, ensure_ascii=False, indent=2)
            return True, f"UPDATED {path}"
        except Exception as e:
            return False, f"ERROR writing '{path}': {e}"
    else:
        return False, f"SKIPPED {path} (no changes)"


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in {".git", "__pycache__", "libs", "models"}


def find_json_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        # Remove skipped dirs from traversal
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for fn in filenames:
            if fn.lower().endswith(".json"):
                yield os.path.join(dirpath, fn)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    json_files = list(find_json_files(root))
    total = len(json_files)
    changed_cnt = 0
    errors = []
    messages = []

    for path in json_files:
        changed, msg = process_json_file(path)
        messages.append(msg)
        if changed:
            changed_cnt += 1
        if msg.startswith("ERROR"):
            errors.append(msg)

    print(f"Found {total} JSON files")
    print(f"Updated {changed_cnt} files")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(" - ", e)
    else:
        print("No errors encountered.")

    # Optionally print messages; keep concise
    for m in messages[:50]:
        print(m)
    if len(messages) > 50:
        print(f"... ({len(messages) - 50} more)")


if __name__ == "__main__":
    main()