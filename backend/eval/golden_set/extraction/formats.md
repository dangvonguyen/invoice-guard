# Invoice layout templates

Generated from the template registry by `python -m eval.extraction.build`.
Do not edit by hand.

## `classic-column`

Vendor header, top-right meta panel, Qty/Unit price/Amount columns, totals below the lines.

- **Slots:** _none_
- **Non-default labels:** _none_

## `itemized-vat`

EU itemized-VAT invoice: No./Description/Qty/UM/Net price/Net worth/VAT %/Gross worth columns, a VAT-by-rate summary, 2-column scramble Seller/Client party blocks.

- **Slots:** `buyer`
- **Non-default labels:** `buyer_party` = 'Client:', `invoice_date` = 'Date of issue:', `vendor_party` = 'Seller:'

## `service-minimal`

Minimal service invoice: Description/Amount columns only, no quantity, tax line only when stated.

- **Slots:** _none_
- **Non-default labels:** _none_
