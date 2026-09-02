"""Shared constants across tests."""

from datetime import date
from decimal import Decimal

from app.services.extraction.model import ExtractedInvoice
from app.services.rules.config import RuleConfig

RULE_CONFIG = RuleConfig(
    max_expense_amount=Decimal("1000.00"),
    max_expense_age_days=90,
    allowed_currencies=frozenset({"USD", "EUR", "GBP"}),
    reconciliation_tolerance=Decimal("0.01"),
)
TODAY = date(2000, 1, 10)

VENDOR_NAME = "Acme Supplies"
INVOICE_DATE = date(2000, 1, 1)
CURRENCY = "USD"
TAX_AMOUNT = Decimal("50.00")
TOTAL_AMOUNT = Decimal("500.00")
LINE_ITEMS = [
    ("Monitor arm", Decimal("150.00")),
    ("Standing desk", Decimal("300.00")),
]

# A schema-valid extraction result
RAW_INVOICE_DATA = {
    "vendor_name": "Acme Supplies",
    "invoice_date": "2000-01-01",
    "currency": "USD",
    "tax_amount": "50.00",
    "total_amount": "500.00",
    "line_items": [
        {"description": "Monitor arm", "amount": "150.00"},
        {"description": "Standing desk", "amount": "300.00"},
    ],
}
EXTRACTED_INVOICE = ExtractedInvoice.model_validate(RAW_INVOICE_DATA)

# Canonical invoice passing all deterministic rule checks
COMPLIANT_INVOICE = EXTRACTED_INVOICE


VALID_SUBMISSION_PAYLOAD: dict[str, object] = {
    "expense_title": "Annual Figma subscription",
    "business_purpose": "Design tooling for the product team's roadmap work.",
    "category": "software_hosting",
    "cost_center": "PRODUCT-DESIGN",
    "vendor": "Figma Inc.",
    "invoice_number": "FIG-2026-00417",
    "invoice_date": "2026-02-14",
    "total_amount": "144.00",
    "currency": "usd",
    "tax_amount": "0.00",
    "line_items": [
        {"description": "Design seat", "amount": "120.00", "quantity": "1"},
        {"description": "Dev seat", "amount": "24.00"},
    ],
    "certified": True,
}
