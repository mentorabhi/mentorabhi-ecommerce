# Milestone evidence convention

Every milestone must have its own `manual-acceptance.md`, separate from its design and automated test records. Write the guide before asking the user to review the milestone. It is a practical end-user checklist, not a copy of automated test cases.

Each checklist covers:

1. How to start the required local profile and confirm each service is running and healthy.
2. The UI URL, sign-in account roles (without copying passwords), pages to visit, and visible results to expect.
3. Manual actions for each user-facing feature, including safe cleanup or a note when local data persists.
4. Database checks using owner/admin access, with read-only SQL for migrations, seeded records, and important state. Never query another service's private tables as a normal service role.
5. A result area for the user's date, outcome, and notes, kept separate from automated verification evidence.

Use milestone-specific service names, ports, data and actions. Document test credentials by username and the ignored local credential key/file they come from; never place generated passwords or tokens in tracked documentation. Update the guide as the milestone changes, and link it from that milestone's README.

- [S1-M10 — Local analytics dataset](S1-M10/README.md): 1,000 synthetic customers, 100 sellable variants, realistic product photography, and bounded prior-year order history for reports.
