# M07 Units 6–7 — verified reviews and owned support

Revision 1 · 2026-10-24 · Design before implementation

## Service boundaries

Reviews owns review submissions, moderation state, aggregate visibility and moderation audit. A customer submits one review per owned order line. Reviews forwards the customer's bearer token to the Orders owner API, which confirms that the subject owns the delivered order and purchased SKU; it never reads Orders tables. New reviews are PENDING. Only published reviews and aggregates are public. Moderation decisions retain operator subject, reason and revision. Customer content is rendered as text and is not placed on the order event stream.

Support owns tickets and messages. Customer ticket creation stores the verified JWT subject and optionally links an order only after Orders confirms ownership. Support never stores bearer tokens. Operators see the minimum ticket/order facts and may add replies or change status with an audit record. There is no customer impersonation API. Ticket content is excluded from commerce events.

Each service is an independent project with a separate database/schema credential and migration set. Public product review reads are anonymous; writes require the customer realm. Ticket reads/writes require the customer realm and enforce subject ownership in SQL. Operator endpoints require the operator API audience. Calls to Orders use forwarded customer authorization, not a privileged cross-customer identity.

## State and API

- Reviews: `PENDING -> PUBLISHED | REJECTED`; published reviews may be hidden by a separately audited operator action. Unique `(customer_subject, order_id, sku_id)` prevents duplicate submissions.
- Support: `OPEN -> IN_PROGRESS -> WAITING_FOR_CUSTOMER -> RESOLVED`; customer messages may reopen a resolved case. All transitions and messages are append-only audited.
- Review public API: `GET /api/v1/reviews/products/{productId}`. Customer API: `POST /api/v1/reviews`, `GET /api/v1/reviews/mine`. Operator API: queue and moderation endpoints.
- Support customer API: create/list/detail/message. Operator API: queue/detail/status/reply. Ticket and message reads are scoped by JWT subject.
- Orders adds an owner-scoped delivered-line verification response without exposing address or payment details.

## Failure and privacy

If Orders is unavailable or cannot verify the customer, reject creation and persist no review/ticket. Exact idempotency is not needed for review uniqueness; the database constraint is authoritative. Support message requests use operation UUIDs and reject changed replays. Bound text length, normalize whitespace, escape output, and never interpret review or ticket text as instructions. Public review aggregates include only PUBLISHED records.

## Verification sources and manual acceptance

Add unit tests for state and text rules, contract tests for ownership and anonymous/public scopes, integration tests for cross-owner rejection, duplicate review prevention, moderation audit, support message replay, and DB isolation. Add Selenium flows for review submission/moderation and support creation/reply. A separate UI/service/database guide is required. Tests remain unexecuted during the Stage 1 development-first pass.
