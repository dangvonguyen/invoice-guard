"""Authored-input schema for ``source.json``, validated at load time."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

# Canonical money: optional sign, integer part, exactly two decimals.
MONEY_RE = r"^-?\d+\.\d{2}$"
# Canonical quantity: non-negative, optional fractional part.
QUANTITY_RE = r"^\d+(\.\d+)?$"
# ISO 4217 alphabetic code.
CURRENCY_RE = r"^[A-Z]{3}$"
# VAT percentage as printed, e.g. "23" or "5.5".
VAT_RATE_RE = r"^\d+(\.\d+)?$"

Money = Annotated[str, StringConstraints(pattern=MONEY_RE)]
Quantity = Annotated[str, StringConstraints(pattern=QUANTITY_RE)]
Currency = Annotated[str, StringConstraints(pattern=CURRENCY_RE)]
VatRate = Annotated[str, StringConstraints(pattern=VAT_RATE_RE)]

_CENT = Decimal("0.01")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Party(_Strict):
    """A named party on the document, plus authored chrome that never projects."""

    name: str
    address: list[str] = []
    contact: list[str] = []


class ShipTo(_Strict):
    """Ship-to distractor block."""

    name: str
    address: list[str] = []


class SourceLineItem(_Strict):
    """One authored line item.

    ``description``/``amount``/``quantity``/``unit_price`` project verbatim into
    ``expected.json``; ``unit`` and ``vat_rate`` are render-only.
    """

    description: str
    amount: Money
    quantity: Quantity | None = None
    unit_price: Money | None = None
    unit: str | None = None
    vat_rate: VatRate | None = None


class InvoiceBlock(_Strict):
    """The invoice's own fields."""

    number: str | None = None
    date: date
    currency: Currency
    tax_amount: Money | None = None
    total_amount: Money


class Distractors(_Strict):
    """Sparse map of ambiguity traps; only the keys a case needs are set."""

    po_number: str | None = None
    bank_account: str | None = None
    ship_to: ShipTo | None = None


class RenderDirectives(_Strict):
    """Data-shaped formatting."""

    amount_grouping: bool = True
    currency_display: Literal["code", "symbol", "symbol-and-code"] = "code"
    date_format: Literal["iso", "us-slash", "eu-slash", "long-month", "dotted"] = "iso"


class Checks(_Strict):
    """Per-case opt-out for the two arithmetic self-checks."""

    line_arithmetic: bool = True
    total_reconciliation: bool = True


class SourceDocument(_Strict):
    """The whole authored invoice."""

    vendor: Party
    buyer: Party | None = None
    invoice: InvoiceBlock
    line_items: list[SourceLineItem]
    distractors: Distractors = Distractors()
    render: RenderDirectives = RenderDirectives()
    checks: Checks = Checks()

    @property
    def subtotal(self) -> str:
        """Sum of line amounts as a canonical string. Never projected."""
        total = sum((Decimal(li.amount) for li in self.line_items), Decimal("0"))
        return f"{total.quantize(_CENT)}"

    def gross(self, item: SourceLineItem) -> str:
        """Line amount grossed up by its ``vat_rate``. Never projected."""
        if item.vat_rate is None:
            raise ValueError("gross() requires a line item with a vat_rate")
        rate = Decimal(item.vat_rate) / Decimal("100")
        value = Decimal(item.amount) * (Decimal("1") + rate)
        return f"{value.quantize(_CENT)}"

    def vat_of(self, item: SourceLineItem) -> str:
        """The VAT portion of a line as a canonical string. Never projected."""
        if item.vat_rate is None:
            raise ValueError("vat_of() requires a line item with a vat_rate")
        rate = Decimal(item.vat_rate) / Decimal("100")
        return f"{(Decimal(item.amount) * rate).quantize(_CENT)}"


def provided_optionals(doc: SourceDocument) -> frozenset[str]:
    """Return the optional-slot keys this document actually populates."""
    keys: set[str] = set()
    if doc.buyer is not None:
        keys.add("buyer")
    if doc.distractors.po_number is not None:
        keys.add("po_number")
    if doc.distractors.bank_account is not None:
        keys.add("bank_account")
    if doc.distractors.ship_to is not None:
        keys.add("ship_to")
    return frozenset(keys)
