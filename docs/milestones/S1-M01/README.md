# S1-M01 — Scope, domain and architecture
Revision 2 · 2026-10-23 · Status: complete — reviewed design checkpoint s1-m01-design-v1.

Manual end-user review: [S1-M01 manual acceptance](manual-acceptance.md).

## Objective
Translate the original three-stage plan and subsequent user decisions into a consistent, implementable SuperSports baseline. Establish ownership and acceptance examples before deploying services.

## Prerequisites and source map
Read requirements/accepted-requirements.md, docs/context/project-context.md and the preserved original requirements/planning baseline.
Original stage diagrams: architecture/stage-1/S1-00.excalidraw and S1-M01.excalidraw.
Current design: design/S1-M01/architecture.md, with companion editable Excalidraw and SVG ownership diagram.
Decision record: docs/decisions/0001-local-first-monorepo.md.
Testing strategy: docs/testing/strategy.md. Traceability: docs/traceability.md.

## Deliverables
- Requirements and actor/journey acceptance contract.
- Service ownership, entity relationships, checkout happy/failure paths and local deployment diagrams.
- Currency/coupon/configuration/simulation policies; API/event conventions.
- Monorepo/project conventions, local resource profile proposals and dependency decision backlog.
- Design review with findings/dispositions, revision log, teaching walkthrough and next-milestone handoff.

## Sequence and exit gate
1. Save design and diagrams before implementation.
2. Review coherence, feasibility, scope, security, interaction design and failure paths. Correct verified issues.
3. Establish persistent repository guidance, .gitignore and project documentation entry points.
4. Validate document links, editable diagrams, requirements traceability, ignore behavior and repository whitespace.
5. Record actual outcomes and limitations. Never substitute documentation checks for application tests.
Done when all deliverables exist, review has no unresolved design blocker for bootstrap, and structural checks pass. Runtime acceptance remains future work.

## Teaching walkthrough
1. Read accepted requirements and identify authoritative versus derived data.
2. Follow a final-unit checkout through Inventory, Pricing and Orders.
3. Explain why compensation is a new business action rather than database rollback.
4. Explain why changing store currency cannot rewrite historical orders.
5. Compare a runtime setting change with an infrastructure adapter migration.
6. Select a local profile and explain what is stopped to fit the Mac.
Exercise: add a hypothetical Tennis category and a new storage adapter on paper. Expected outcome: no commerce invariant or private table ownership changes.
Exercise: replay an approved purchase after a price change. Expected outcome: revalidation rejects the stale proposal and asks for renewed approval.

## Next: S1-M02
Verify official stable versions, ARM64 support and licenses; write compatibility lock record before building templates.
Create independent service build projects, Dockerfiles, devops Compose core, health endpoints, migrations, local identity, configuration foundation and seed/reset/validation scripts.
Design and review bootstrap deployment and security boundaries before implementing.
No cloud provider, remote Git hosting, SaaS CI or remote model is required. Start with local CI-equivalent scripts; remote CI integration waits for a hosting decision.

## Design review — 2026-10-23
Compound Engineering ce-doc-review, non-interactive; seven separately dispatched session reviewers, no external model CLI.
| Reviewer | Outcome |
|---|---|
| Coherence | One P2 finding; corrected diagram's unknown-payment timeout path |
| Feasibility | No findings |
| Security | No findings |
| Scope | No findings |
| Interaction design | No findings |
| Adversarial | No findings |
| Product | No findings |

Applied fix: unknown payment outcomes now persist as pending reconciliation and query the simulator's authoritative operation result before confirmation/compensation. Confirmed failures remain compensatable. This aligns the sequence diagram with the existing written rule.
No unresolved review decision or design blocker was returned. This review is not a benchmark or security certification.
Compound pack resolver initially reported that Git was not initialized; no packs were declared. Git was subsequently initialized. Cross-model judgment/whole-document sweep: not run; local-only review, no external model CLI invoked. peer.outcome: in-process-fallback.

### Review evidence
#### coherence
```json
{
  "reviewer": "coherence",
  "findings": [
    {
      "title": "Checkout diagram treats unknown payment timeouts as failures",
      "severity": "P2",
      "section": "Checkout and compensation",
      "why_it_matters": "An implementer following the diagram would release inventory and coupon holds on a payment timeout even when capture might have succeeded. The accompanying prose explicitly requires unknown payment outcomes to remain pending and be queried before retrying. Updating the diagram to show that pending path makes its compensation instructions consistent with that rule.",
      "finding_type": "error",
      "autofix_class": "safe_auto",
      "suggested_fix": "Update the checkout sequence diagram to distinguish an unknown payment outcome from a confirmed failure: keep the Saga pending and query the payment operation until its outcome is known, then continue confirmation or compensation under the existing validity checks. Remove unqualified timeout from the branch that immediately releases reservations and redemption holds.",
      "confidence": 100,
      "evidence": [
        "else Decline, timeout or expired allocation",
        "O->>I: Release active reservations",
        "O->>P: Release redemption hold",
        "If a response is lost, query the operation outcome before retrying; persisted Saga state and operation keys prevent duplicate effects.",
        "A pending payment result remains pending, never guessed as failure."
      ]
    }
  ],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### feasibility
```json
{
  "reviewer": "feasibility",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### security-lens
```json
{
  "reviewer": "security-lens",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### design-lens
```json
{
  "reviewer": "design-lens",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### product-lens
```json
{
  "reviewer": "product-lens",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### adversarial
```json
{
  "reviewer": "adversarial",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

#### scope-guardian
```json
{
  "reviewer": "scope-guardian",
  "findings": [],
  "residual_risks": [],
  "deferred_questions": []
}
```

## Verification evidence — 2026-10-23
- PASS: Python 3.14.7, pip 26.2.1, sys.prefix differs from sys.base_prefix; execution uses .venv.
- PASS: 12 Markdown files checked for local Markdown links and trailing whitespace.
- PASS: R01–R20 are represented in the traceability register; AE01–AE20 are defined.
- PASS: unknown-payment outcome persists pending reconciliation; the old unconditional timeout compensation branch is absent.
- PASS: typed configuration and endpoint allowlist constraints are present.
- PASS: all 23 original Excalidraw/SVG pairs and the new ownership pair parse; element IDs are unique.
- PASS: git check-ignore verified virtualenv, secrets, builds, dependencies, volumes and Terraform state are excluded; source files and .env.example remain eligible.
- Git diff --check returned no issues, but this is an unborn repository with untracked files; direct Markdown whitespace assertions provided the meaningful content check.
- Unit/integration/E2E/load tests: not applicable to this documentation-only deliverable; no application tests executed.
- Diagram verification covers JSON/SVG structure, not a rendered visual inspection. Mermaid blocks have not yet been rendered by a browser.
- Git repository initialized on docs/s1-m01; no commit, tag, remote or publication created. The tagged milestone checkpoint remains outstanding.

### Reproduce the core document checks
Run from the repository root:

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import json, re, sys
import xml.etree.ElementTree as ET
assert sys.prefix != sys.base_prefix
paths = [Path('README.md'), Path('AGENTS.md'), Path('devops/README.md'),
         Path('requirements/accepted-requirements.md'),
         *Path('docs').rglob('*.md'), *Path('design/S1-M01').glob('*.md')]
for path in paths:
    text = path.read_text()
    assert all(line.rstrip() == line for line in text.splitlines()), path
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in target and not target.startswith('#'):
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
requirements = Path('requirements/accepted-requirements.md').read_text()
trace = Path('docs/traceability.md').read_text()
for number in range(1, 21):
    assert f'R{number:02d}' in requirements and f'R{number:02d}' in trace
    assert re.search(rf'^- AE{number:02d}:', requirements, re.M)
original = list(Path('architecture').rglob('*.excalidraw'))
assert len(original) == 23
for path in [*original, Path('design/S1-M01/ownership.excalidraw')]:
    diagram = json.loads(path.read_text())
    assert diagram['type'] == 'excalidraw' and diagram['version'] == 2
    assert len({item['id'] for item in diagram['elements']}) == len(diagram['elements'])
    ET.parse(path.with_suffix('.svg'))
design = Path('design/S1-M01/architecture.md').read_text()
assert 'else Unknown payment outcome' in design
assert 'else Decline, timeout' not in design
print('PASS: document links, whitespace, traceability and diagram structures')
PY
```

Next step: S1-M02 design and bootstrap, including official version/compatibility verification. No prerequisite application implementation is claimed by this package.

## Git checkpoint
The reviewed design was committed as 7ef04c4 and tagged s1-m01-design-v1 before bootstrap implementation. Earlier verification statements above describe the pre-commit inspection; this entry closes the pending checkpoint.
