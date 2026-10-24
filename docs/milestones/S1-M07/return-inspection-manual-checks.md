# M07 Unit 5 — manual return inspection checks

Development checklist dated 2026-10-24. Automated and manual execution is deferred until Stage 1 development is complete.

## Services and operator UI

1. Start the core profile with `devops/scripts/supersports up --profile core` and confirm Inventory, Orders, Payment, Configuration and Storefront readiness.
2. Sign in to the operator UI at `http://localhost:3000/admin`, open Inventory, and create a delivered order, request a return, and wait for its refund to complete.
3. Confirm the return appears in “Items waiting for inspection,” with the expected order, SKU and unit ordinal.
4. Mark one unit SELLABLE with an observation, and another unit DAMAGED or DISPUTED with an observation. Submit once; confirm the receipt leaves the pending queue and success feedback is shown.
5. Confirm an incomplete decision form cannot be submitted. Refresh after a successful submission and confirm the same receipt is not offered again.

## Database and idempotency

1. Connect to the local PostgreSQL databases using the credentials in ignored `devops/.local/bootstrap.env`; do not copy credentials into tracked files.
2. In the `inventory` database, inspect `inventory_return`, `inventory_return_unit`, `inventory_return_inspection_audit`, `stock_movement`, and `inventory_balance` for the return.
3. Confirm every received unit has one condition, actor, reason and inspection timestamp. Exactly the SELLABLE units have one positive movement with source `return-inspection`; DAMAGED/DISPUTED units have none.
4. Confirm each corresponding balance increased by the number of sellable units only. Verify a repeated identical operation does not add another movement; changed decisions under the same operation ID conflict.
5. In the `orders` database, confirm the return/refund remains completed independently of inspection outcome, and registration state becomes `REGISTERED`.
6. Confirm an ordinary checkout reservation and its movement history are unchanged by return inspection.

## Result record

Record date, commit, profile, observed service health, return/order IDs, unit outcomes, movement/balance query results, and any discrepancy. This guide is not evidence of a passed runtime check.
