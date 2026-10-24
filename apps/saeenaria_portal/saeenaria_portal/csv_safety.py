"""Protect textual CSV cells intended for viewing in spreadsheet applications."""

from decimal import Decimal, InvalidOperation


def safe_csv_cell(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    candidate = value.lstrip()
    if candidate.startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠")):
        # Preserve plain numeric source values, including negative quantities.
        try:
            numeric = Decimal(candidate)
        except InvalidOperation:
            numeric = None
        if numeric is None or not numeric.is_finite():
            return "'" + value
    if value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value
