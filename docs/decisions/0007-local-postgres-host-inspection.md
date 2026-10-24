# ADR 0007 — Local PostgreSQL inspection from DBeaver

2026-10-24 · Accepted user revision: enable host-machine DBeaver access and share the existing database credentials.

The default profile keeps PostgreSQL inside Docker. The user now explicitly requests host inspection. Add an opt-in Compose override binding `127.0.0.1:15432` to PostgreSQL's internal port 5432; retain service database/role isolation. Persist only the enabled flag/port in ignored local state so ordinary restarts and deployment scripts preserve the choice. Never bind this override to all interfaces.

Use the existing generated PostgreSQL administrator credential from ignored `devops/.local/bootstrap.env`; do not rotate it or place it in tracked files, shell arguments, logs or saved connection exports. The user explicitly authorized sharing this one credential in the conversation and using it in their local DBeaver application. Other service credentials remain private.

Applying the port mapping recreates the PostgreSQL container on its existing volume, followed by service recovery checks. Failure restores the previous binding/configuration. Verification covers default-private and explicit-loopback composition, native host TCP/authentication and service readiness. The prior default-private tests remain valid for the default profile; the live binding test must recognize the explicitly enabled loopback override.

Implementation-owner review resolved default-vs-opt-in behavior, fixed loopback address, port collision handling, retained volume/password state, credential containment and rollback. No cloud or remote database exposure is introduced.
