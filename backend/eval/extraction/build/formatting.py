"""Pure render-time formatters for dates, amounts and currency."""

from datetime import date

_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "$",
    "AUD": "$",
    "CHF": "CHF ",
}

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def format_date(iso: str, style: str) -> str:
    """Render an ISO ``YYYY-MM-DD`` string in one of the authored styles."""
    d = date.fromisoformat(iso)
    if style == "iso":
        return d.isoformat()
    if style == "us-slash":
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    if style == "eu-slash":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    if style == "dotted":
        return f"{d.day:02d}.{d.month:02d}.{d.year}"
    if style == "long-month":
        return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"
    raise ValueError(f"unknown date style: {style!r}")


def format_amount(canonical: str, *, grouping: bool) -> str:
    """Render a canonical ``-?\\d+\\.\\d{2}`` string; comma thousands, dot decimal."""
    negative = canonical.startswith("-")
    integer, _, fraction = canonical.lstrip("-").partition(".")
    if grouping:
        integer = f"{int(integer):,}"
    sign = "-" if negative else ""
    return f"{sign}{integer}.{fraction}"


def format_currency(amount_str: str, code: str, *, display: str) -> str:
    """Wrap an already amount-formatted string with a symbol and/or ISO code."""
    symbol = _SYMBOLS.get(code, code + " ")
    if display == "code":
        return f"{amount_str} {code}"
    if display == "symbol":
        return f"{symbol}{amount_str}"
    if display == "symbol-and-code":
        return f"{symbol}{amount_str} {code}"
    raise ValueError(f"unknown currency display: {display!r}")
